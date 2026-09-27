"""PDF text extraction that preserves character offsets.

Page boundaries are recorded as offset ranges into the concatenated text so a
chunk (or a citation) can be resolved back to a page number without re-parsing.
"""

import logging

import fitz

from app.core.config import get_settings
from app.services.ingestion.document_text import (
    PAGE_SEPARATOR,
    PageSpan,
    ParsedDocument,
)
from app.services.ingestion.ocr import ocr_page

logger = logging.getLogger(__name__)


def parse_pdf(data: bytes) -> ParsedDocument:
    settings = get_settings()
    parts: list[str] = []
    pages: list[PageSpan] = []
    cursor = 0
    ocr_pages = 0

    with fitz.open(stream=data, filetype="pdf") as doc:
        for index, page in enumerate(doc, start=1):
            body = page.get_text("text")

            # A page whose text layer is empty or near-empty is either blank or
            # a scan. OCR distinguishes them; a genuinely blank page just
            # returns nothing again.
            if (
                settings.enable_ocr
                and len(body.strip()) < settings.ocr_min_chars_per_page
            ):
                recognised = ocr_page(page, settings.ocr_dpi)
                if len(recognised.strip()) > len(body.strip()):
                    body = recognised
                    ocr_pages += 1

            # The separator also stops the last word of one page from fusing
            # with the first word of the next.
            block = body + PAGE_SEPARATOR
            parts.append(block)
            pages.append(PageSpan(index, cursor, cursor + len(block)))
            cursor += len(block)

    if ocr_pages:
        logger.info("OCR recovered text for %d page(s)", ocr_pages)

    return ParsedDocument(text="".join(parts), pages=pages)
