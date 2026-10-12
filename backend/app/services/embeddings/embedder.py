"""Local sentence-transformers embeddings.

Runs on this machine: no API key, no rate limit, and ingestion stays up even
when the generation provider is unreachable. The model is loaded once and the
encode call is pushed to a worker thread because it is blocking CPU work.
"""

import asyncio
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.core.config import get_settings

# bge models are trained with an asymmetric prefix: queries get this prepended,
# passages do not. Skipping it measurably degrades retrieval.
_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


@lru_cache
def _model() -> SentenceTransformer:
    settings = get_settings()
    model = SentenceTransformer(settings.embedding_model)
    dim = model.get_sentence_embedding_dimension()
    if dim != settings.embedding_dim:
        raise RuntimeError(
            f"{settings.embedding_model} emits {dim}-d vectors but EMBEDDING_DIM "
            f"is {settings.embedding_dim}. The vector(N) column in infra/init.sql "
            "must match; changing models requires a migration."
        )
    return model


def warm_up() -> None:
    _model()


def _encode(texts: list[str]) -> list[list[float]]:
    vectors = _model().encode(texts, normalize_embeddings=True)
    return [v.tolist() for v in vectors]


async def embed_passages(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    return await asyncio.to_thread(_encode, texts)


async def embed_query(text: str) -> list[float]:
    vectors = await asyncio.to_thread(_encode, [_QUERY_PREFIX + text])
    return vectors[0]
