"""Enqueue side of the job queue.

Falls back to running ingestion inline when Redis is unreachable, so the app
still works for someone who has not started a worker. The response says which
path was taken rather than pretending it was queued.
"""

import asyncio
import logging
from uuid import UUID

from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_pool = None
_lock = asyncio.Lock()


async def _get_pool():
    global _pool
    if _pool is None:
        async with _lock:
            if _pool is None:
                settings = get_settings()
                _pool = await create_pool(
                    RedisSettings.from_dsn(settings.redis_url)
                )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None


async def enqueue_ingest(doc_id: UUID) -> bool:
    """Queue ingestion. Returns True if queued, False if run inline."""
    try:
        pool = await _get_pool()
        await pool.enqueue_job("ingest_document", str(doc_id))
        return True
    except Exception:
        logger.warning(
            "could not reach Redis; ingesting %s inline. Start a worker with "
            "`arq app.workers.arq_app.WorkerSettings` to process in the "
            "background.",
            doc_id,
            exc_info=True,
        )
        from app.services.ingestion.pipeline import ingest

        await ingest(doc_id)
        return False
