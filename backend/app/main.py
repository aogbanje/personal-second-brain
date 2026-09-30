import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import routes_auth, routes_chat, routes_documents, routes_graph
from app.services.embeddings.embedder import warm_up
from app.workers.queue import close_pool

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the embedding model at boot rather than on the first query, and fail
    # fast if its dimension disagrees with the vector column.
    warm_up()
    yield
    await close_pool()


app = FastAPI(title="PSB", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    # Must stay an explicit origin rather than "*": credentialed requests are
    # rejected against a wildcard, and the session cookie makes every request
    # credentialed.
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_auth.router, prefix="/api/v1")
app.include_router(routes_documents.router, prefix="/api/v1")
app.include_router(routes_chat.router, prefix="/api/v1")
app.include_router(routes_graph.router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
