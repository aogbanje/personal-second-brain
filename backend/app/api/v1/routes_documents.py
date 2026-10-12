import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.api.deps import Principal, current_user
from app.core.config import get_settings
from app.db.postgres import get_session
from app.models.schemas import (
    DocumentSummary,
    IngestTextRequest,
    IngestUrlRequest,
)
from app.services.ingestion.pipeline import create_document
from app.services.status import channel, current
from app.workers.queue import enqueue_ingest

router = APIRouter(prefix="/documents", tags=["documents"])

# The workspace filter is part of the base query rather than something each
# caller appends, so a new call site cannot forget it and quietly read the whole
# table. Callers add `AND ...`, never `WHERE ...`.
_SUMMARY_SQL = """
    SELECT d.id, d.title, d.source_type, d.source_ref, d.status, d.page_count,
           d.error, d.created_at,
           (SELECT count(*) FROM chunks c WHERE c.document_id = d.id)
               AS chunk_count,
           (SELECT count(DISTINCT e.source_id)
              FROM entity_edges e
              JOIN chunks c2 ON c2.id = e.chunk_id
             WHERE c2.document_id = d.id) AS entity_count
    FROM documents d
    WHERE d.workspace_id = :ws
"""


@router.post("", response_model=DocumentSummary, status_code=202)
async def upload_pdf(
    file: UploadFile = File(...),
    principal: Principal = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> DocumentSummary:
    if file.content_type != "application/pdf":
        raise HTTPException(415, "expected application/pdf")

    doc_id = await create_document(
        workspace_id=principal.workspace_id,
        title=file.filename or "untitled.pdf",
        source_type="pdf",
        source_ref=file.filename,
        blob=await file.read(),
    )
    queued = await enqueue_ingest(doc_id)
    return await _summary(session, principal, doc_id, queued=queued)


@router.post("/text", response_model=DocumentSummary, status_code=202)
async def ingest_text(
    body: IngestTextRequest,
    principal: Principal = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> DocumentSummary:
    doc_id = await create_document(
        workspace_id=principal.workspace_id,
        title=body.title,
        source_type="text",
        body_text=body.text,
    )
    queued = await enqueue_ingest(doc_id)
    return await _summary(session, principal, doc_id, queued=queued)


@router.post("/url", response_model=DocumentSummary, status_code=202)
async def ingest_url(
    body: IngestUrlRequest,
    principal: Principal = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> DocumentSummary:
    url = body.url.strip()
    if not url.lower().startswith(("http://", "https://")):
        raise HTTPException(422, "url must start with http:// or https://")

    # The title is a placeholder; the worker replaces it with the page's own
    # title once it has fetched and parsed the page.
    doc_id = await create_document(
        workspace_id=principal.workspace_id,
        title=url,
        source_type="url",
        source_ref=url,
    )
    queued = await enqueue_ingest(doc_id)
    return await _summary(session, principal, doc_id, queued=queued)


@router.get("", response_model=list[DocumentSummary])
async def list_documents(
    principal: Principal = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> list[DocumentSummary]:
    rows = (
        await session.execute(
            text(_SUMMARY_SQL + " ORDER BY d.created_at DESC"),
            {"ws": principal.workspace_id},
        )
    ).mappings()
    return [DocumentSummary(**row) for row in rows]


@router.get("/{doc_id}", response_model=DocumentSummary)
async def get_document(
    doc_id: UUID,
    principal: Principal = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> DocumentSummary:
    return await _summary(session, principal, doc_id)


@router.get("/{doc_id}/text")
async def get_document_text(
    doc_id: UUID,
    principal: Principal = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Full extracted text, for rendering citation highlights against."""
    row = (
        await session.execute(
            text(
                """
                SELECT title, raw_text FROM documents
                WHERE id = :id AND workspace_id = :ws
                """
            ),
            {"id": doc_id, "ws": principal.workspace_id},
        )
    ).first()
    if row is None:
        raise HTTPException(404, "document not found")
    return {"id": str(doc_id), "title": row.title, "text": row.raw_text}


@router.post("/{doc_id}/reindex", response_model=DocumentSummary, status_code=202)
async def reindex(
    doc_id: UUID,
    principal: Principal = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> DocumentSummary:
    """Re-run the pipeline, e.g. after changing the embedding model."""
    await _summary(session, principal, doc_id)  # 404s if unknown or not ours
    queued = await enqueue_ingest(doc_id)
    return await _summary(session, principal, doc_id, queued=queued)


@router.delete("/{doc_id}", status_code=204)
async def delete_document(
    doc_id: UUID,
    principal: Principal = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    result = await session.execute(
        text("DELETE FROM documents WHERE id = :id AND workspace_id = :ws"),
        {"id": doc_id, "ws": principal.workspace_id},
    )
    await session.commit()
    if result.rowcount == 0:
        raise HTTPException(404, "document not found")


@router.get("/{doc_id}/events")
async def document_events(
    doc_id: UUID,
    request: Request,
    principal: Principal = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> EventSourceResponse:
    """Server-sent ingestion progress.

    The current state is sent immediately so a client that connects after the
    interesting messages were published still renders the truth, then live
    events stream until the document reaches a terminal state.
    """
    import redis.asyncio as redis

    # Checked before the stream opens: once the generator is running there is no
    # clean way to turn a rejection into an HTTP status.
    owned = await session.scalar(
        text(
            """
            SELECT 1 FROM documents
            WHERE id = :id AND workspace_id = :ws
            """
        ),
        {"id": doc_id, "ws": principal.workspace_id},
    )
    if not owned:
        raise HTTPException(404, "document not found")

    async def stream():
        snapshot = await current(doc_id)
        if snapshot is None:
            yield {"event": "error", "data": json.dumps({"message": "not found"})}
            return

        yield {"event": "progress", "data": json.dumps(snapshot.to_dict())}
        if snapshot.status in ("ready", "failed"):
            return

        client = redis.from_url(get_settings().redis_url, decode_responses=True)
        pubsub = client.pubsub()
        await pubsub.subscribe(channel(doc_id))
        try:
            while not await request.is_disconnected():
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=15.0
                )
                if message is None:
                    # Keeps proxies from closing an idle stream.
                    yield {"event": "ping", "data": "{}"}
                    continue

                yield {"event": "progress", "data": message["data"]}
                payload = json.loads(message["data"])
                if payload.get("status") in ("ready", "failed"):
                    return
        except asyncio.CancelledError:
            raise
        finally:
            await pubsub.unsubscribe(channel(doc_id))
            await pubsub.aclose()
            await client.aclose()

    return EventSourceResponse(stream())


async def _summary(
    session: AsyncSession,
    principal: Principal,
    doc_id: UUID,
    queued: bool | None = None,
) -> DocumentSummary:
    row = (
        (
            await session.execute(
                text(_SUMMARY_SQL + " AND d.id = :id"),
                {"id": doc_id, "ws": principal.workspace_id},
            )
        )
        .mappings()
        .first()
    )
    if row is None:
        raise HTTPException(404, "document not found")
    return DocumentSummary(**row, queued=queued)
