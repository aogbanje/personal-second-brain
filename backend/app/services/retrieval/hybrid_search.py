"""Hybrid retrieval: vector similarity fused with Postgres full-text search.

Both halves run in one SQL statement, which is the main reason the vectors live
in Postgres rather than a dedicated vector service. Ranks are combined with
Reciprocal Rank Fusion -- rank-based, so the cosine distances and ts_rank_cd
scores never have to be normalised onto a shared scale, and there is no weight
to hand-tune.

Note: ts_rank_cd is Postgres' own ranking function, not literally BM25. For
true BM25 without leaving Postgres, ParadeDB's pg_search is the upgrade path.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.embeddings.embedder import embed_query
from app.services.ingestion.pipeline import vector_literal

# RRF damping constant. 60 is the value from the original paper and is not
# sensitive enough to be worth tuning before there is an eval set.
_RRF_K = 60

_SEARCH_SQL = text(
    """
    WITH vec AS (
        SELECT id, ROW_NUMBER() OVER (ORDER BY embedding <=> CAST(:qvec AS vector)) AS rank
        FROM chunks
        WHERE workspace_id = :ws
          AND embedding IS NOT NULL
          AND embedding_model = :model
        ORDER BY embedding <=> CAST(:qvec AS vector)
        LIMIT :top_k
    ),
    kw AS (
        SELECT c.id,
               ROW_NUMBER() OVER (ORDER BY ts_rank_cd(c.tsv, q.query) DESC) AS rank
        FROM chunks c, websearch_to_tsquery('english', :question) AS q(query)
        WHERE c.workspace_id = :ws AND c.tsv @@ q.query
        ORDER BY ts_rank_cd(c.tsv, q.query) DESC
        LIMIT :top_k
    )
    SELECT c.id, c.document_id, c.text, c.char_start, c.char_end, c.page_number,
           d.title AS document_title,
           COALESCE(1.0 / (:rrf_k + vec.rank), 0.0)
             + COALESCE(1.0 / (:rrf_k + kw.rank), 0.0) AS score
    FROM chunks c
    JOIN documents d ON d.id = c.document_id
    LEFT JOIN vec ON vec.id = c.id
    LEFT JOIN kw  ON kw.id  = c.id
    WHERE vec.id IS NOT NULL OR kw.id IS NOT NULL
    ORDER BY score DESC
    LIMIT :limit
    """
)


@dataclass(frozen=True)
class RetrievedChunk:
    id: UUID
    document_id: UUID
    document_title: str
    text: str
    char_start: int
    char_end: int
    page_number: int | None
    score: float


async def hybrid_search(
    session: AsyncSession,
    workspace_id: UUID,
    question: str,
    limit: int | None = None,
) -> list[RetrievedChunk]:
    settings = get_settings()
    vector = await embed_query(question)

    rows = (
        await session.execute(
            _SEARCH_SQL,
            {
                "qvec": vector_literal(vector),
                "question": question,
                "ws": workspace_id,
                "model": settings.embedding_model,
                "top_k": settings.retrieval_top_k,
                "limit": limit or settings.retrieval_context_chunks,
                "rrf_k": _RRF_K,
            },
        )
    ).mappings()

    return [RetrievedChunk(**row) for row in rows]
