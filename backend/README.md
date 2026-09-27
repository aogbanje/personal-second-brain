# PSB backend

FastAPI + Postgres (pgvector) + local embeddings + Claude for grounded answers.

## Run it

```bash
# 1. Services
docker compose -f ../infra/docker-compose.yml up -d

# 2. Python deps  (this machine has no pip yet -- see Troubleshooting)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Config
cp .env.example .env    # set ANTHROPIC_API_KEY

# 4. Serve
uvicorn app.main:app --reload
```

First boot downloads the embedding model (~130 MB) into the HuggingFace cache.

## Try the slice

```bash
curl -F "file=@some.pdf" localhost:8000/api/v1/documents

curl -s localhost:8000/api/v1/chat \
  -H 'content-type: application/json' \
  -d '{"question":"What does the document say about X?"}' | jq
```

`/chat` returns the answer split into `segments`. Each segment carries the
citations for that span, and every citation's `char_start`/`char_end` are
offsets into `GET /documents/{id}/text` — so the frontend can highlight the
exact passage in the source rather than string-matching for it.

## Tests

```bash
pytest tests/
```

`test_chunker_offsets.py` pins the invariant the whole citation feature rests
on: `raw_text[chunk.char_start:chunk.char_end] == chunk.text`. If that breaks,
highlights land on the wrong passage silently, so treat a failure there as a
release blocker.

## Layout

| Path | Role |
|---|---|
| `app/services/ingestion/` | parse → chunk, offsets preserved throughout |
| `app/services/embeddings/` | local `bge-small-en-v1.5`, no API dependency |
| `app/services/retrieval/` | vector + full-text fused with RRF, one SQL query |
| `app/services/rag/` | Claude call with native citations, offsets rebased |
| `app/workers/` | empty; the Arq seam is `pipeline.ingest(doc_id)` |
| `../infra/init.sql` | schema source of truth (no Alembic yet) |

## Things that will bite

- **Embedding dim is fixed in SQL.** `chunks.embedding` is `vector(384)`.
  Changing `EMBEDDING_MODEL` to one with a different width needs a migration;
  `embedder.warm_up()` fails at boot rather than letting them drift apart.
- **Re-embedding.** `chunks.embedding_model` records what produced each vector,
  so a model change can target exactly what is stale.
- **Ingestion is synchronous.** A large PDF blocks its request. `ingest` takes
  only a `doc_id` and opens its own session specifically so moving it to Arq is
  a registration, not a refactor.
- **No OCR.** A scanned PDF extracts no text and the document lands in `failed`
  with that message.
- **Citations and structured outputs are mutually exclusive** in the API, so
  `/chat` assembles its response shape here rather than asking the model for
  JSON.

## Troubleshooting

This machine's Python has no `pip`, `venv` bootstrap, or `ensurepip`, so step 2
fails as written. Fix with either:

```bash
sudo apt install python3-pip python3-venv     # then retry step 2
curl -LsSf https://astral.sh/uv/install.sh | sh && uv sync   # or use uv
```
