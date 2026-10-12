"""Arq task definitions.

The task body is `pipeline.ingest`, unchanged from when it ran inline. That was
the point of giving it a `doc_id`-only signature.
"""

import logging
from uuid import UUID

from app.services.embeddings.embedder import warm_up
from app.services.ingestion.pipeline import ingest

logger = logging.getLogger(__name__)


async def ingest_document(ctx: dict, doc_id: str) -> None:
    await ingest(UUID(doc_id))


async def startup(ctx: dict) -> None:
    # Load the embedding model once per worker process rather than per job.
    warm_up()
    logger.info("worker ready")
