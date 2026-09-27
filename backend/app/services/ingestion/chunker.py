"""Offset-preserving chunker.

Every chunk records where it came from in the source text. That is the whole
point: citation offsets the model reports are chunk-relative, and rebasing them
onto the document requires char_start to be exact, not approximate.
"""

import re
from dataclasses import dataclass

from app.services.ingestion.document_text import ParsedDocument

# Split on blank lines first, then sentence ends -- coarse to fine, so chunks
# break at the most semantically meaningful boundary that fits.
_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class TextChunk:
    ordinal: int
    text: str
    char_start: int
    char_end: int
    page_number: int | None


def _segments(text: str) -> list[tuple[int, int]]:
    """Split text into (start, end) spans at paragraph then sentence breaks."""
    spans: list[tuple[int, int]] = []
    cursor = 0
    for para in _PARAGRAPH_BREAK.split(text):
        if not para:
            cursor += 2
            continue
        start = text.index(para, cursor)
        for sentence in _SENTENCE_END.split(para):
            if not sentence.strip():
                continue
            s_start = text.index(sentence, start)
            spans.append((s_start, s_start + len(sentence)))
            start = s_start + len(sentence)
        cursor = start
    return spans


def _split_oversized(
    text: str, spans: list[tuple[int, int]], limit: int
) -> list[tuple[int, int]]:
    """Break spans longer than `limit` at whitespace, or mid-token if need be.

    Tables, OCR output and code blocks routinely arrive with no sentence or
    paragraph punctuation at all. Without this, such a run stays a single
    segment and becomes one enormous chunk whose embedding is too diffuse to
    retrieve accurately.
    """
    out: list[tuple[int, int]] = []
    for start, end in spans:
        while end - start > limit:
            window_end = start + limit
            # Prefer the last whitespace in the window so words stay intact.
            split = text.rfind(" ", start, window_end)
            if split <= start:
                split = window_end  # one unbroken token; cut it
            else:
                split += 1  # keep the space with the left piece
            out.append((start, split))
            start = split
        if end > start:
            out.append((start, end))
    return out


def chunk_document(
    parsed: ParsedDocument,
    target_chars: int,
    overlap_chars: int,
) -> list[TextChunk]:
    text = parsed.text
    # An overlap at or above the target makes each chunk carry forward nearly
    # all of its predecessor, which explodes the chunk count and stores the same
    # passage many times over.
    overlap_chars = max(0, min(overlap_chars, target_chars // 2))
    spans = _split_oversized(text, _segments(text), target_chars)
    if not spans:
        return []

    chunks: list[TextChunk] = []
    current: list[tuple[int, int]] = []

    def flush() -> None:
        if not current:
            return
        start, end = current[0][0], current[-1][1]
        body = text[start:end]
        if body.strip():
            chunks.append(
                TextChunk(
                    ordinal=len(chunks),
                    text=body,
                    char_start=start,
                    char_end=end,
                    page_number=parsed.page_for_offset(start),
                )
            )

    for span in spans:
        current.append(span)
        if current[-1][1] - current[0][0] < target_chars:
            continue

        flush()

        # Carry trailing segments forward so a passage split across a chunk
        # boundary still appears whole in one of them.
        carried: list[tuple[int, int]] = []
        carried_len = 0
        for prev in reversed(current):
            length = prev[1] - prev[0]
            if carried_len + length > overlap_chars:
                break
            carried.insert(0, prev)
            carried_len += length
        current = carried

    # Avoid emitting a near-duplicate tail that the overlap already covered.
    if current and (current[-1][1] - current[0][0]) > overlap_chars:
        flush()
    elif current and not chunks:
        flush()

    return chunks
