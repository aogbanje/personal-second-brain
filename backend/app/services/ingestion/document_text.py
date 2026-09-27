"""Document text plus page offsets -- the shared shape every parser produces.

Kept separate from the PDF parser so chunking and offset arithmetic can be
tested without PyMuPDF installed.
"""

from dataclasses import dataclass

# Appended after every page by the PDF parser. Fixed width matters:
# pipeline._reconstruct recovers page spans from stored text by scanning for it.
PAGE_SEPARATOR = "\n\n"


@dataclass(frozen=True)
class PageSpan:
    page_number: int  # 1-indexed, matching how PDFs are cited
    char_start: int
    char_end: int


@dataclass(frozen=True)
class ParsedDocument:
    text: str
    pages: list[PageSpan]

    @property
    def page_count(self) -> int:
        return len(self.pages)

    def page_for_offset(self, offset: int) -> int | None:
        for page in self.pages:
            if page.char_start <= offset < page.char_end:
                return page.page_number
        return self.pages[-1].page_number if self.pages else None


def parse_plain_text(text: str) -> ParsedDocument:
    return ParsedDocument(text=text, pages=[PageSpan(1, 0, len(text))])
