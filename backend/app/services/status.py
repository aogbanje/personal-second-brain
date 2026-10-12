"""Ingestion progress, published to Redis and persisted to Postgres.

Two sinks on purpose. Redis pub/sub drives the live SSE stream, but a client
that connects late or reloads the page has missed those messages, so the latest
event is also written to `documents.progress` and replayed on connect.
"""

import json
import logging
from dataclasses import asdict, dataclass
from typing import Any
from uuid import UUID

import redis.asyncio as redis
from sqlalchemy import text

from app.core.config import get_settings
from app.db.postgres import SessionLocal

logger = logging.getLogger(__name__)

# Coarse stages, in order. `pct` is derived from these so the UI never has to
# know the pipeline's internals.
STEPS = ("queued", "parsing", "chunking", "embedding", "graph", "ready")


@dataclass(frozen=True)
class Progress:
    status: str  # pending | processing | ready | failed
    step: str
    pct: int
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def channel(doc_id: UUID) -> str:
    return f"psb:doc:{doc_id}"


def _pool() -> redis.Redis:
    return redis.from_url(get_settings().redis_url, decode_responses=True)


async def publish(doc_id: UUID, progress: Progress) -> None:
    payload = json.dumps(progress.to_dict())

    async with SessionLocal() as session:
        await session.execute(
            text(
                """
                UPDATE documents
                SET progress = CAST(:payload AS jsonb),
                    status = :status,
                    error = CASE WHEN :status = 'failed' THEN :message ELSE NULL END
                WHERE id = :id
                """
            ),
            {
                "payload": payload,
                "status": progress.status,
                "message": progress.message,
                "id": doc_id,
            },
        )
        await session.commit()

    client = _pool()
    try:
        await client.publish(channel(doc_id), payload)
    except Exception:
        # A dropped notification must not fail the ingestion that produced it;
        # the row is already updated, so a reconnect still shows the truth.
        logger.warning("could not publish progress for %s", doc_id, exc_info=True)
    finally:
        await client.aclose()


async def current(doc_id: UUID) -> Progress | None:
    async with SessionLocal() as session:
        row = (
            await session.execute(
                text("SELECT status, progress FROM documents WHERE id = :id"),
                {"id": doc_id},
            )
        ).first()

    if row is None:
        return None
    status, stored = row
    if not stored:
        return Progress(status=status, step="queued", pct=0)
    return Progress(
        status=stored.get("status", status),
        step=stored.get("step", "queued"),
        pct=stored.get("pct", 0),
        message=stored.get("message"),
    )
