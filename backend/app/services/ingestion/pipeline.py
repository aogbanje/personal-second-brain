"""Ingestion pipeline.

`ingest` takes only a document id and owns its own session and transactions, so
it runs identically awaited inline or picked up by an Arq worker.

Parsing, OCR and URL fetching all happen *here* rather than in `create_document`
-- they are the slow, blocking parts, and doing them in the upload request is
what async ingestion exists to avoid. The upload stores bytes and returns.
"""

import json
import logging
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import text

from app.core.config import get_settings
from app.db.postgres import SessionLocal
from app.services.embeddings.embedder import embed_passages
from app.services.graph.entity_extractor import extract_graph
from app.services.graph.graph_builder import persist_graph
from app.services.ingestion.chunker import chunk_document
from app.services.ingestion.document_text import (
    PageSpan,
    ParsedDocument,
    parse_plain_text,
)
from app.services.status import Progress, publish

logger = logging.getLogger(__name__)


def _upload_dir() -> Path:
    path = Path(get_settings().upload_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


async def create_document(
    *,
    workspace_id: UUID,
    title: str,
    source_type: str,
    source_ref: str | None = None,
    blob: bytes | None = None,
    body_text: str | None = None,
) -> UUID:
    """Persist a pending document. Fast: no parsing, no network."""
    doc_id = uuid4()

    blob_path: str | None = None
    if blob is not None:
        blob_path = str(_upload_dir() / f"{doc_id}.bin")
        Path(blob_path).write_bytes(blob)

    async with SessionLocal() as session:
        await session.execute(
            text(
                """
                INSERT INTO documents (id, workspace_id, title, source_type,
                                       source_ref, blob_path, raw_text, status,
                                       progress)
                VALUES (:id, :ws, :title, :source_type, :source_ref, :blob_path,
                        :raw_text, 'pending',
                        CAST(:progress AS jsonb))
                """
            ),
            {
                "id": doc_id,
                "ws": workspace_id,
                "title": title,
                "source_type": source_type,
                "source_ref": source_ref,
                "blob_path": blob_path,
                "raw_text": body_text or "",
                "progress": json.dumps(
                    Progress(status="pending", step="queued", pct=0).to_dict()
                ),
            },
        )
        await session.commit()

    return doc_id


async def _materialize(doc_id: UUID, row) -> ParsedDocument:
    """Turn the stored source into text plus page offsets."""
    source_type = row.source_type
    source_ref = row.source_ref
    blob_path = row.blob_path
    raw_text = row.raw_text
    page_spans = row.page_spans

    if source_type == "pdf":
        if not blob_path or not Path(blob_path).exists():
            raise ValueError("uploaded file is missing from disk")
        # Imported here so the API process does not need PyMuPDF loaded to serve
        # reads, and so a missing OCR stack surfaces in the worker.
        from app.services.ingestion.pdf_parser import parse_pdf

        return parse_pdf(Path(blob_path).read_bytes())

    if source_type == "url":
        from app.services.ingestion.web_scraper import scrape_url

        if not source_ref:
            raise ValueError("no URL recorded for this document")
        page = await scrape_url(source_ref)
        async with SessionLocal() as session:
            await session.execute(
                text(
                    """
                    UPDATE documents SET title = :title, source_ref = :url
                    WHERE id = :id
                    """
                ),
                {"title": page.title, "url": page.url, "id": doc_id},
            )
            await session.commit()
        return parse_plain_text(page.text)

    if page_spans:
        return ParsedDocument(
            text=raw_text, pages=[PageSpan(*span) for span in page_spans]
        )
    return parse_plain_text(raw_text)


async def ingest(doc_id: UUID) -> None:
    """Parse, chunk, embed, index and graph a document. The Arq task body."""
    settings = get_settings()

    async with SessionLocal() as session:
        row = (
            await session.execute(
                text(
                    """
                    SELECT workspace_id, source_type, source_ref, blob_path,
                           raw_text, page_spans
                    FROM documents WHERE id = :id
                    """
                ),
                {"id": doc_id},
            )
        ).first()
    if row is None:
        raise ValueError(f"document {doc_id} not found")

    # The worker has no request context, so the document row is the only
    # trustworthy source for which workspace this content belongs to.
    workspace_id = row.workspace_id

    try:
        await publish(doc_id, Progress("processing", "parsing", 10))
        parsed = await _materialize(doc_id, row)
        if not parsed.text.strip():
            raise ValueError(
                "no extractable text. If this is a scanned PDF, install tesseract "
                "(apt install tesseract-ocr) so the OCR fallback can run."
            )

        async with SessionLocal() as session:
            await session.execute(
                text(
                    """
                    UPDATE documents
                    SET raw_text = :raw_text, page_count = :page_count,
                        page_spans = CAST(:page_spans AS jsonb)
                    WHERE id = :id
                    """
                ),
                {
                    "raw_text": parsed.text,
                    "page_count": parsed.page_count,
                    "page_spans": json.dumps(
                        [
                            [p.page_number, p.char_start, p.char_end]
                            for p in parsed.pages
                        ]
                    ),
                    "id": doc_id,
                },
            )
            await session.commit()

        await publish(doc_id, Progress("processing", "chunking", 30))
        chunks = chunk_document(
            parsed,
            target_chars=settings.chunk_target_chars,
            overlap_chars=settings.chunk_overlap_chars,
        )
        if not chunks:
            raise ValueError("document produced no chunks")

        await publish(
            doc_id,
            Progress("processing", "embedding", 50, f"{len(chunks)} chunks"),
        )
        vectors = await embed_passages([c.text for c in chunks])

        chunk_ids: dict[int, UUID] = {}
        async with SessionLocal() as session:
            await session.execute(
                text("DELETE FROM chunks WHERE document_id = :id"), {"id": doc_id}
            )
            for chunk, vector in zip(chunks, vectors, strict=True):
                inserted = (
                    await session.execute(
                        text(
                            """
                            INSERT INTO chunks (document_id, workspace_id, ordinal,
                                                text, char_start, char_end,
                                                page_number, embedding_model,
                                                embedding_dim, embedding)
                            VALUES (:doc, :ws, :ordinal, :text, :char_start,
                                    :char_end, :page_number, :model, :dim,
                                    CAST(:embedding AS vector))
                            RETURNING id
                            """
                        ),
                        {
                            "doc": doc_id,
                            "ws": workspace_id,
                            "ordinal": chunk.ordinal,
                            "text": chunk.text,
                            "char_start": chunk.char_start,
                            "char_end": chunk.char_end,
                            "page_number": chunk.page_number,
                            "model": settings.embedding_model,
                            "dim": settings.embedding_dim,
                            "embedding": vector_literal(vector),
                        },
                    )
                ).first()
                chunk_ids[chunk.ordinal] = inserted.id
            await session.commit()

        if settings.enable_graph_extraction:
            await publish(doc_id, Progress("processing", "graph", 75))
            entities, relations = await extract_graph(
                [(c.ordinal, c.text) for c in chunks]
            )
            async with SessionLocal() as session:
                entity_count, edge_count = await persist_graph(
                    session,
                    workspace_id=workspace_id,
                    document_id=doc_id,
                    chunk_ids=chunk_ids,
                    entities=entities,
                    relations=relations,
                )
                await session.commit()
            logger.info(
                "graph for %s: %d entities, %d edges", doc_id, entity_count, edge_count
            )

        await publish(
            doc_id, Progress("ready", "ready", 100, f"{len(chunks)} chunks indexed")
        )

    except Exception as exc:
        logger.exception("ingestion failed for %s", doc_id)
        await publish(doc_id, Progress("failed", "failed", 100, str(exc)))
        raise


def vector_literal(vector: list[float]) -> str:
    """pgvector's text input format, for binding through CAST(:p AS vector)."""
    return "[" + ",".join(f"{v:.8f}" for v in vector) + "]"
