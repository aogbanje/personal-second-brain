from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Principal, current_user
from app.db.postgres import get_session
from app.models.schemas import (
    EntityDetail,
    EntityEvidence,
    GraphEdge,
    GraphNode,
    GraphResponse,
)

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("", response_model=GraphResponse)
async def get_graph(
    limit: int = Query(150, ge=1, le=1000, description="Max nodes, by degree"),
    document_id: UUID | None = None,
    principal: Principal = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> GraphResponse:
    """The graph, or the slice of it a single document contributed.

    Nodes are capped by degree rather than arbitrarily: a graph view that drops
    the hubs is worse than one that drops the leaves.
    """
    nodes = (
        await session.execute(
            text(
                """
                WITH degrees AS (
                    SELECT e.id, count(*) AS degree
                    FROM entities e
                    JOIN entity_edges ed
                      ON ed.source_id = e.id OR ed.target_id = e.id
                    LEFT JOIN chunks c ON c.id = ed.chunk_id
                    WHERE e.workspace_id = :ws
                      AND (:doc IS NULL OR c.document_id = :doc)
                    GROUP BY e.id
                )
                SELECT e.id, e.name, e.entity_type, d.degree
                FROM degrees d
                JOIN entities e ON e.id = d.id
                ORDER BY d.degree DESC, e.name
                LIMIT :limit
                """
            ),
            {"ws": principal.workspace_id, "doc": document_id, "limit": limit},
        )
    ).mappings().all()

    node_ids = [row["id"] for row in nodes]
    if not node_ids:
        return GraphResponse(nodes=[], edges=[])

    # Only edges between surviving nodes, or the client renders dangling ends.
    edges = (
        await session.execute(
            text(
                """
                SELECT ed.id, ed.source_id AS source, ed.target_id AS target,
                       ed.relation, ed.chunk_id, c.document_id, doc.title AS
                       document_title
                FROM entity_edges ed
                LEFT JOIN chunks c ON c.id = ed.chunk_id
                LEFT JOIN documents doc ON doc.id = c.document_id
                WHERE ed.workspace_id = :ws
                  AND ed.source_id = ANY(:ids) AND ed.target_id = ANY(:ids)
                  AND (:doc IS NULL OR c.document_id = :doc)
                """
            ),
            {
                "ws": principal.workspace_id,
                "ids": node_ids,
                "doc": document_id,
            },
        )
    ).mappings().all()

    return GraphResponse(
        nodes=[GraphNode(**row) for row in nodes],
        edges=[GraphEdge(**row) for row in edges],
    )


@router.get("/entities/{entity_id}", response_model=EntityDetail)
async def get_entity(
    entity_id: UUID,
    principal: Principal = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> EntityDetail:
    """One entity plus the passages that justify each of its edges."""
    entity = (
        await session.execute(
            text(
                """
                SELECT id, name, entity_type FROM entities
                WHERE id = :id AND workspace_id = :ws
                """
            ),
            {"id": entity_id, "ws": principal.workspace_id},
        )
    ).mappings().first()
    if entity is None:
        raise HTTPException(404, "entity not found")

    rows = (
        await session.execute(
            text(
                """
                SELECT ed.relation,
                       CASE WHEN ed.source_id = :id THEN 'out' ELSE 'in' END
                           AS direction,
                       CASE WHEN ed.source_id = :id THEN tgt.name ELSE src.name END
                           AS other_name,
                       ed.chunk_id, c.document_id, doc.title AS document_title,
                       c.page_number, c.char_start, c.char_end, c.text AS excerpt
                FROM entity_edges ed
                JOIN entities src ON src.id = ed.source_id
                JOIN entities tgt ON tgt.id = ed.target_id
                LEFT JOIN chunks c ON c.id = ed.chunk_id
                LEFT JOIN documents doc ON doc.id = c.document_id
                WHERE ed.workspace_id = :ws
                  AND (ed.source_id = :id OR ed.target_id = :id)
                ORDER BY doc.title NULLS LAST, c.ordinal
                """
            ),
            {"id": entity_id, "ws": principal.workspace_id},
        )
    ).mappings().all()

    return EntityDetail(
        id=entity["id"],
        name=entity["name"],
        entity_type=entity["entity_type"],
        evidence=[EntityEvidence(**row) for row in rows],
    )
