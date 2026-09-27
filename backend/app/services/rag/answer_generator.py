"""Grounded answer generation with native citations.

Each retrieved chunk is handed to the model as its own `document` block with
citations enabled, so the API returns the answer already split into cited and
uncited spans -- including the exact character range of the quoted text within
the chunk. Those ranges are rebased onto `documents.raw_text` here, which is
what lets the frontend highlight the passage inside the original document
instead of guessing at it with substring matching.

Citations are incompatible with structured outputs (`output_config.format`);
the answer comes back as prose plus citation metadata, so the response shape is
assembled on this side.
"""

import logging
from functools import lru_cache

from anthropic import AsyncAnthropic

from app.core.config import get_settings
from app.models.schemas import AnswerSegment, ChatResponse, Citation
from app.services.retrieval.hybrid_search import RetrievedChunk

logger = logging.getLogger(__name__)

_SYSTEM = """You answer questions strictly from the attached documents.

Rules:
- Ground every factual claim in the documents and cite the passage it came from.
- If the documents do not contain the answer, say so plainly. Do not fill the \
gap from general knowledge.
- If the documents disagree, say that and cite both sides.
- Be concise. No preamble, no restating the question."""


class NoContextError(RuntimeError):
    """Retrieval returned nothing, so there is nothing to ground an answer in."""


class RefusedError(RuntimeError):
    """The model declined the request (stop_reason == "refusal")."""


@lru_cache
def _client() -> AsyncAnthropic:
    settings = get_settings()
    # Passing base_url=None lets the SDK use its default; set ANTHROPIC_BASE_URL
    # to route through a gateway instead.
    return AsyncAnthropic(
        api_key=settings.anthropic_api_key,
        base_url=settings.anthropic_base_url,
    )


def _document_blocks(chunks: list[RetrievedChunk]) -> list[dict]:
    blocks = []
    for chunk in chunks:
        title = chunk.document_title
        if chunk.page_number is not None:
            title = f"{title} (p. {chunk.page_number})"
        blocks.append(
            {
                "type": "document",
                "source": {
                    "type": "text",
                    "media_type": "text/plain",
                    "data": chunk.text,
                },
                "title": title,
                "citations": {"enabled": True},
            }
        )
    return blocks


def _to_citation(raw, chunks: list[RetrievedChunk]) -> Citation | None:
    """Map one API citation onto a source chunk, rebasing offsets."""
    index = getattr(raw, "document_index", None)
    if index is None or not (0 <= index < len(chunks)):
        logger.warning("citation referenced unknown document_index %r", index)
        return None

    chunk = chunks[index]
    cited_text = getattr(raw, "cited_text", "") or ""

    # char_location is what a plain-text document source yields. Other location
    # types (page_location, content_block_location) would mean the source type
    # changed; fall back to the chunk's own span rather than dropping the cite.
    start = getattr(raw, "start_char_index", None)
    end = getattr(raw, "end_char_index", None)
    if start is None or end is None:
        char_start, char_end = chunk.char_start, chunk.char_end
    else:
        char_start = min(chunk.char_start + start, chunk.char_end)
        char_end = min(chunk.char_start + end, chunk.char_end)

    return Citation(
        document_id=chunk.document_id,
        document_title=chunk.document_title,
        chunk_id=chunk.id,
        page_number=chunk.page_number,
        cited_text=cited_text,
        char_start=char_start,
        char_end=char_end,
    )


async def generate_answer(question: str, chunks: list[RetrievedChunk]) -> ChatResponse:
    if not chunks:
        raise NoContextError("no chunks matched the question")

    settings = get_settings()
    content = _document_blocks(chunks)
    content.append({"type": "text", "text": question})

    response = await _client().beta.messages.create(
        model=settings.answer_model,
        max_tokens=16000,
        system=_SYSTEM,
        thinking={"type": "adaptive"},
        # Routes around a safety-classifier refusal instead of failing the
        # request outright; the category decides the substitute model.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": content}],
    )

    if response.stop_reason == "refusal":
        details = getattr(response, "stop_details", None)
        raise RefusedError(getattr(details, "explanation", None) or "request declined")

    segments: list[AnswerSegment] = []
    all_citations: list[Citation] = []

    for block in response.content:
        if block.type != "text":
            continue  # thinking blocks and anything else are not answer text
        cites = [
            c
            for c in (_to_citation(raw, chunks) for raw in (block.citations or []))
            if c is not None
        ]
        segments.append(AnswerSegment(text=block.text, citations=cites))
        all_citations.extend(cites)

    return ChatResponse(
        answer="".join(s.text for s in segments),
        segments=segments,
        citations=all_citations,
        retrieved_chunk_ids=[c.id for c in chunks],
    )
