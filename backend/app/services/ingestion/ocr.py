"""OCR fallback for pages a PDF has no text layer for.

Applied per page rather than per document: a report that is mostly digital text
with two scanned appendix pages only rasterises those two.

Requires the tesseract binary (`apt install tesseract-ocr`). If it is missing,
`available()` returns False and ingestion proceeds with whatever text layer
exists rather than failing the document.
"""

import logging
import shutil
from functools import lru_cache

logger = logging.getLogger(__name__)


@lru_cache
def available() -> bool:
    if shutil.which("tesseract") is None:
        logger.warning("tesseract not on PATH; OCR fallback disabled")
        return False
    try:
        import pytesseract  # noqa: F401
    except ImportError:
        logger.warning("pytesseract not installed; OCR fallback disabled")
        return False
    return True


def ocr_page(page, dpi: int) -> str:
    """Rasterise a PyMuPDF page and return recognised text ('' on failure)."""
    if not available():
        return ""

    import io

    import pytesseract
    from PIL import Image

    try:
        pixmap = page.get_pixmap(dpi=dpi)
        image = Image.open(io.BytesIO(pixmap.tobytes("png")))
        return pytesseract.image_to_string(image) or ""
    except Exception:
        logger.exception("OCR failed on page %s", getattr(page, "number", "?"))
        return ""
