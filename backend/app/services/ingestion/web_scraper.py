"""URL ingestion.

trafilatura strips navigation, footers and boilerplate, which matters more here
than it might elsewhere: chrome text embeds and retrieves as readily as body
text, so leaving it in pollutes every search over the document.
"""

import logging
from dataclasses import dataclass

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ScrapeError(RuntimeError):
    pass


@dataclass(frozen=True)
class ScrapedPage:
    title: str
    text: str
    url: str


async def scrape_url(url: str) -> ScrapedPage:
    settings = get_settings()

    if not url.lower().startswith(("http://", "https://")):
        raise ScrapeError("only http(s) URLs are supported")

    try:
        async with httpx.AsyncClient(
            timeout=settings.scrape_timeout_seconds,
            follow_redirects=True,
            headers={"user-agent": settings.scrape_user_agent},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ScrapeError(f"could not fetch {url}: {exc}") from exc

    content_type = response.headers.get("content-type", "")
    if "html" not in content_type and "text" not in content_type:
        raise ScrapeError(f"unsupported content-type {content_type!r}")

    import trafilatura

    html = response.text
    text = trafilatura.extract(
        html, include_comments=False, include_tables=True, no_fallback=False
    )
    if not text or not text.strip():
        raise ScrapeError("no article text found at that URL")

    title = url
    metadata = trafilatura.extract_metadata(html)
    if metadata is not None and metadata.title:
        title = metadata.title

    return ScrapedPage(title=title.strip(), text=text.strip(), url=str(response.url))
