from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://psb:psb@localhost:5432/psb"
    redis_url: str = "redis://localhost:6379/0"

    anthropic_api_key: str | None = None
    anthropic_base_url: str | None = None
    answer_model: str = "claude-opus-5"
    # Entity extraction runs over every chunk of every document, so it is the
    # cost-dominant call. Drop it to claude-haiku-4-5 if that matters more than
    # extraction quality.
    extraction_model: str = "claude-opus-5"

    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384

    # Sessions are opaque tokens in an httpOnly cookie. The cookie is the only
    # transport that works for the SSE progress stream, since EventSource cannot
    # set an Authorization header.
    session_cookie_name: str = "psb_session"
    session_ttl_days: int = 30
    # Must be True anywhere the frontend is served over HTTPS. False here only
    # because local dev is http://localhost.
    cookie_secure: bool = False

    upload_dir: str = "uploads"

    chunk_target_chars: int = 1200
    chunk_overlap_chars: int = 150
    retrieval_top_k: int = 20
    retrieval_context_chunks: int = 8

    # OCR fallback. Triggered per page, not per document, so a PDF with a
    # scanned figure among digital text only rasterises the page that needs it.
    enable_ocr: bool = True
    ocr_min_chars_per_page: int = 40
    ocr_dpi: int = 200

    scrape_timeout_seconds: float = 20.0
    scrape_user_agent: str = "psb/0.1 (+personal second brain)"

    enable_graph_extraction: bool = True
    graph_chunks_per_call: int = 4
    graph_max_concurrency: int = 4
    # Bounds worst-case cost for one absurdly long document.
    graph_max_chunks_per_document: int = 120


@lru_cache
def get_settings() -> Settings:
    return Settings()
