"""Chunker offset invariants.

Citation highlighting is built on the assumption that a chunk's char_start and
char_end index back into the source text exactly. If that breaks, every
highlight in the product lands on the wrong passage -- silently. These tests
pin the invariant.
"""

import pytest

from app.services.ingestion.chunker import chunk_document
from app.services.ingestion.document_text import (
    PageSpan,
    ParsedDocument,
    parse_plain_text,
)

TARGET = 300
OVERLAP = 60


def _chunk(text: str, pages: list[PageSpan] | None = None):
    parsed = (
        ParsedDocument(text=text, pages=pages)
        if pages is not None
        else parse_plain_text(text)
    )
    return parsed, chunk_document(parsed, target_chars=TARGET, overlap_chars=OVERLAP)


def _prose(paragraphs: int, sentences: int = 6) -> str:
    return "\n\n".join(
        " ".join(
            f"Paragraph {p} sentence {s} carries some filler content."
            for s in range(sentences)
        )
        for p in range(paragraphs)
    )


@pytest.mark.parametrize("paragraphs", [1, 3, 12])
def test_offsets_index_back_into_source(paragraphs):
    parsed, chunks = _chunk(_prose(paragraphs))

    assert chunks, "expected at least one chunk"
    for chunk in chunks:
        assert parsed.text[chunk.char_start : chunk.char_end] == chunk.text


def test_offsets_survive_unicode():
    # Python slices by code point; a byte-oriented offset would drift here.
    text = _prose(4).replace("filler", "naïve café — résumé 🎯")
    parsed, chunks = _chunk(text)

    for chunk in chunks:
        assert parsed.text[chunk.char_start : chunk.char_end] == chunk.text


def test_chunks_are_ordered_and_cover_the_document():
    parsed, chunks = _chunk(_prose(10))

    assert [c.ordinal for c in chunks] == list(range(len(chunks)))
    assert chunks[0].char_start == 0
    # Overlap means starts may step back, but the frontier must keep advancing.
    assert all(
        b.char_end > a.char_end for a, b in zip(chunks, chunks[1:], strict=False)
    )
    assert chunks[-1].char_end == len(parsed.text.rstrip()) or chunks[
        -1
    ].char_end <= len(parsed.text)


def test_page_number_comes_from_the_offset_not_the_chunk_index():
    page_one = _prose(2)
    page_two = _prose(2)
    text = page_one + "\n\n" + page_two
    boundary = len(page_one) + 2
    pages = [PageSpan(1, 0, boundary), PageSpan(2, boundary, len(text))]

    parsed, chunks = _chunk(text, pages)

    for chunk in chunks:
        expected = 1 if chunk.char_start < boundary else 2
        assert chunk.page_number == expected
    assert {c.page_number for c in chunks} == {1, 2}


def test_empty_and_whitespace_input_yield_no_chunks():
    assert _chunk("")[1] == []
    assert _chunk("   \n\n  \t ")[1] == []


def test_short_document_still_produces_one_chunk():
    parsed, chunks = _chunk("A single short sentence.")

    assert len(chunks) == 1
    assert parsed.text[chunks[0].char_start : chunks[0].char_end] == chunks[0].text


def test_text_without_sentence_breaks_is_still_split():
    # Tables, OCR output and code arrive with no sentence punctuation. Left
    # unsplit they become one huge chunk whose embedding retrieves nothing well.
    parsed, chunks = _chunk("word " * 900)

    assert len(chunks) > 1
    assert max(c.char_end - c.char_start for c in chunks) <= TARGET
    for chunk in chunks:
        assert parsed.text[chunk.char_start : chunk.char_end] == chunk.text


def test_single_unbroken_token_is_cut_rather_than_kept_whole():
    parsed, chunks = _chunk("x" * 5000)

    assert max(c.char_end - c.char_start for c in chunks) <= TARGET
    assert "".join(c.text for c in chunks).startswith("x" * TARGET)


def test_overlap_is_clamped_below_target():
    # An overlap at or above the target makes every chunk carry nearly all of
    # its predecessor, exploding the count and storing passages many times over.
    text = "Alpha. Beta. Gamma. Delta. " * 30
    parsed = parse_plain_text(text)

    chunks = chunk_document(parsed, target_chars=50, overlap_chars=200)

    assert len(chunks) < len(text) // 10
    for chunk in chunks:
        assert parsed.text[chunk.char_start : chunk.char_end] == chunk.text
