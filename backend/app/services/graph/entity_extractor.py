"""Entity and relationship extraction.

Chunks are batched into one call each so the model sees a little surrounding
context and the per-document call count stays bounded, while every relation
still names the chunk index it came from -- that index becomes `entity_edges
.chunk_id`, so any claim the graph makes traces back to a citable passage.
"""

import asyncio
import logging
from functools import lru_cache
from typing import Literal

from anthropic import AsyncAnthropic
from pydantic import BaseModel, Field

from app.core.config import get_settings

logger = logging.getLogger(__name__)

EntityType = Literal[
    "person", "organization", "concept", "place", "product", "event", "other"
]

_SYSTEM = """You extract a knowledge graph from document excerpts.

Extract the entities that matter to what the text is actually about, and the \
relationships the text explicitly states between them. Skip generic filler \
("the report", "this document", "the author") and anything you would have to \
infer -- only relationships the excerpt states.

Use the entity's most complete surface form ("Alan Turing", not "Turing"), and \
use that exact same string in relations so they resolve. Keep relation labels \
short, lowercase, verb-like: "founded", "works at", "cites", "located in".

For every relation, set chunk_index to the [n] marker of the excerpt that \
stated it. Return empty lists if the text carries no real entities."""


class ExtractedEntity(BaseModel):
    name: str = Field(description="Most complete surface form of the entity")
    type: EntityType


class ExtractedRelation(BaseModel):
    source: str = Field(description="Entity name, matching an extracted entity")
    target: str = Field(description="Entity name, matching an extracted entity")
    relation: str = Field(description="Short lowercase verb phrase")
    chunk_index: int = Field(description="The [n] marker of the stating excerpt")


class ExtractionResult(BaseModel):
    entities: list[ExtractedEntity]
    relations: list[ExtractedRelation]


@lru_cache
def _client() -> AsyncAnthropic:
    settings = get_settings()
    return AsyncAnthropic(
        api_key=settings.anthropic_api_key,
        base_url=settings.anthropic_base_url,
    )


async def _extract_batch(
    batch: list[tuple[int, str]],
) -> tuple[list[ExtractedEntity], list[ExtractedRelation]]:
    """Extract from one batch of (chunk_index, text) pairs."""
    settings = get_settings()
    excerpts = "\n\n".join(f"[{index}]\n{body}" for index, body in batch)
    valid = {index for index, _ in batch}

    try:
        response = await _client().messages.parse(
            model=settings.extraction_model,
            max_tokens=8000,
            system=_SYSTEM,
            messages=[{"role": "user", "content": excerpts}],
            output_format=ExtractionResult,
        )
    except Exception:
        # One bad batch should not lose the graph for the whole document.
        logger.exception("extraction call failed for chunks %s", sorted(valid))
        return [], []

    if response.stop_reason == "refusal":
        logger.warning("extraction refused for chunks %s", sorted(valid))
        return [], []

    result = response.parsed_output
    if result is None:
        return [], []

    # The model can hallucinate an index outside the batch it was shown; those
    # relations would attach to the wrong passage, so drop them.
    relations = [r for r in result.relations if r.chunk_index in valid]
    if len(relations) != len(result.relations):
        logger.info(
            "dropped %d relation(s) citing an out-of-batch chunk",
            len(result.relations) - len(relations),
        )
    return result.entities, relations


async def extract_graph(
    chunks: list[tuple[int, str]],
) -> tuple[list[ExtractedEntity], list[ExtractedRelation]]:
    """Extract entities and relations from (chunk_index, text) pairs."""
    settings = get_settings()
    if not chunks:
        return [], []

    capped = chunks[: settings.graph_max_chunks_per_document]
    if len(capped) < len(chunks):
        logger.info(
            "graph extraction capped at %d of %d chunks", len(capped), len(chunks)
        )

    size = settings.graph_chunks_per_call
    batches = [capped[i : i + size] for i in range(0, len(capped), size)]
    gate = asyncio.Semaphore(settings.graph_max_concurrency)

    async def run(batch):
        async with gate:
            return await _extract_batch(batch)

    results = await asyncio.gather(*(run(b) for b in batches))

    entities: list[ExtractedEntity] = []
    relations: list[ExtractedRelation] = []
    for batch_entities, batch_relations in results:
        entities.extend(batch_entities)
        relations.extend(batch_relations)

    return entities, relations
