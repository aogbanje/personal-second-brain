"""Library search: the retrieval layer without the generation layer.

`/chat` answers questions; this answers "where did I read that?". It is the same
`hybrid_search` call, so results rank identically to the context chat would have
been given -- which also makes this the tool for seeing *why* chat cited what it
cited, without paying for a model call.

GET rather than POST: a search is idempotent and a search URL should be
shareable and back-button-able, which the frontend relies on by driving the page
straight off `?q=`.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Principal, current_user
from app.db.postgres import get_session
from app.models.schemas import SearchHit, SearchResponse
from app.services.retrieval.hybrid_search import hybrid_search
from app.services.retrieval.snippets import snippets_for

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def search(
    q: str = Query(min_length=1, max_length=500, description="Search query"),
    limit: int = Query(default=20, ge=1, le=100),
    principal: Principal = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> SearchResponse:
    query = q.strip()
    if not query:
        # A whitespace-only query is not an error, it just has no results.
        # websearch_to_tsquery would return an empty tsquery that matches
        # nothing, and embedding blank text wastes a model call.
        return SearchResponse(query=q, results=[])

    chunks = await hybrid_search(
        session, principal.workspace_id, query, limit=limit
    )
    snippets = await snippets_for(
        session, principal.workspace_id, [c.id for c in chunks], query
    )

    return SearchResponse(
        query=query,
        results=[
            SearchHit(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                document_title=chunk.document_title,
                page_number=chunk.page_number,
                text=chunk.text,
                # Falls back to the raw chunk text if the snippet query somehow
                # missed this id, so a hit is never rendered blank.
                snippet=snippets.get(chunk.id, chunk.text),
                char_start=chunk.char_start,
                char_end=chunk.char_end,
                score=chunk.score,
            )
            for chunk in chunks
        ],
    )
