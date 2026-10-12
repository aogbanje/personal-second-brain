"""Search snippets, highlighted by Postgres' own stemmer.

Why this is a second query rather than more columns on the ranking query:
`hybrid_search` is shared with `/chat`, and snippets are useless there. Keeping
them separate means the retrieval SQL that chat depends on is untouched, at the
cost of one extra round trip on the search path only.

Why `ts_headline` rather than finding the terms in Python: it stems the same way
the index does, so a search for "running" highlights "ran". Reimplementing that
client-side would drift from what actually matched.

Why control characters rather than `<mark>`: **ts_headline does not escape the
source text.** Asking it for HTML tags and rendering the result as HTML would
inject whatever markup happens to be in an ingested document -- a stored XSS
whose payload is any scraped page containing a `<script>`. These sentinels carry
no meaning to a browser, so the frontend splits on them and builds real elements
instead. The worst a document containing a literal STX can do is produce one
stray highlight.
"""

from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

# STX / ETX. Chosen because extracted document text effectively never contains
# them, and because neither means anything to an HTML parser. The frontend has
# the same two constants -- they must stay in sync.
MARK_START = "\x02"
MARK_END = "\x03"

_HEADLINE_OPTIONS = (
    f"StartSel={MARK_START}, StopSel={MARK_END}, "
    "MaxFragments=2, FragmentDelimiter= … , MaxWords=30, MinWords=12, "
    "HighlightAll=FALSE"
)

_SNIPPET_SQL = text(
    """
    SELECT c.id,
           ts_headline(CAST('english' AS regconfig), c.text,
                       websearch_to_tsquery(CAST('english' AS regconfig),
                                            CAST(:q AS text)),
                       CAST(:opts AS text)) AS snippet
    FROM chunks c
    WHERE c.workspace_id = :ws AND c.id IN :ids
    """
).bindparams(bindparam("ids", expanding=True))


async def snippets_for(
    session: AsyncSession,
    workspace_id: UUID,
    chunk_ids: list[UUID],
    query: str,
) -> dict[UUID, str]:
    """Map chunk id -> highlighted excerpt.

    Unordered: the caller already has the ranking and uses this to decorate it.
    A chunk matched by vector similarity alone has no matching lexemes, so
    ts_headline falls back to the opening fragment -- which is the right thing to
    show for a semantic hit, just without highlights.
    """
    if not chunk_ids:
        return {}

    rows = (
        await session.execute(
            _SNIPPET_SQL,
            {
                "q": query,
                "opts": _HEADLINE_OPTIONS,
                "ws": workspace_id,
                "ids": chunk_ids,
            },
        )
    ).mappings()

    return {row["id"]: row["snippet"] for row in rows}
