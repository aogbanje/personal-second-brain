"""Persist an extracted graph.

Entities deduplicate per workspace on a normalized name, so the same person
mentioned in five documents is one node with five supporting edges rather than
five disconnected nodes. Relations whose endpoints do not resolve to an
extracted entity are dropped -- a dangling edge is worse than a missing one.
"""

import logging
import re
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.graph.entity_extractor import ExtractedEntity, ExtractedRelation

logger = logging.getLogger(__name__)

_WHITESPACE = re.compile(r"\s+")


def normalize(name: str) -> str:
    return _WHITESPACE.sub(" ", name).strip().casefold()


async def persist_graph(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    document_id: UUID,
    chunk_ids: dict[int, UUID],
    entities: list[ExtractedEntity],
    relations: list[ExtractedRelation],
) -> tuple[int, int]:
    """Upsert entities and edges. Returns (entity_count, edge_count)."""
    # Re-extraction of a document replaces its edges rather than duplicating
    # them. Entities are workspace-scoped and survive, since other documents
    # may reference them.
    await session.execute(
        text(
            """
            DELETE FROM entity_edges
            WHERE chunk_id IN (SELECT id FROM chunks WHERE document_id = :doc)
            """
        ),
        {"doc": document_id},
    )

    ids_by_name: dict[str, UUID] = {}
    for entity in entities:
        key = normalize(entity.name)
        if not key or key in ids_by_name:
            continue
        row = (
            await session.execute(
                text(
                    """
                    INSERT INTO entities (workspace_id, name, normalized_name,
                                          entity_type)
                    VALUES (:ws, :name, :norm, :type)
                    ON CONFLICT (workspace_id, normalized_name) DO UPDATE
                        SET name = CASE
                                WHEN length(EXCLUDED.name) > length(entities.name)
                                THEN EXCLUDED.name ELSE entities.name END,
                            entity_type = COALESCE(entities.entity_type,
                                                   EXCLUDED.entity_type)
                    RETURNING id
                    """
                ),
                {
                    "ws": workspace_id,
                    "name": entity.name.strip(),
                    "norm": key,
                    "type": entity.type,
                },
            )
        ).first()
        ids_by_name[key] = row.id

    edge_count = 0
    seen: set[tuple[UUID, UUID, str]] = set()
    for relation in relations:
        source_id = ids_by_name.get(normalize(relation.source))
        target_id = ids_by_name.get(normalize(relation.target))
        if source_id is None or target_id is None or source_id == target_id:
            continue

        label = relation.relation.strip().casefold()
        if not label or (source_id, target_id, label) in seen:
            continue
        seen.add((source_id, target_id, label))

        await session.execute(
            text(
                """
                INSERT INTO entity_edges (workspace_id, source_id, target_id,
                                          relation, chunk_id)
                VALUES (:ws, :source, :target, :relation, :chunk)
                """
            ),
            {
                "ws": workspace_id,
                "source": source_id,
                "target": target_id,
                "relation": label,
                "chunk": chunk_ids.get(relation.chunk_index),
            },
        )
        edge_count += 1

    return len(ids_by_name), edge_count
