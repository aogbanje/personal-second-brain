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

# 5. Worker, in a second shell (skip it and ingestion runs in-request instead)
arq app.workers.arq_app.WorkerSettings
```

First boot downloads the embedding model (~130 MB) into the HuggingFace cache.
Scanned PDFs also need `tesseract` on PATH — without it those pages extract
nothing, but ingestion still succeeds.

## Try the slice

Every content route is scoped to the caller's workspace, so the first step is
getting a session cookie. `-c/-b` keeps it in a jar; a browser does this for
you.

```bash
curl -c jar -s localhost:8000/api/v1/auth/signup \
  -H 'content-type: application/json' \
  -d '{"email":"me@example.com","password":"a-long-enough-password"}'

curl -b jar -F "file=@some.pdf" localhost:8000/api/v1/documents

curl -b jar -s localhost:8000/api/v1/chat \
  -H 'content-type: application/json' \
  -d '{"question":"What does the document say about X?"}' | jq

# Retrieval without generation: where did I read that?
curl -b jar -s 'localhost:8000/api/v1/search?q=some%20phrase' | jq
```

`/chat` returns the answer split into `segments`. Each segment carries the
citations for that span, and every citation's `char_start`/`char_end` are
offsets into `GET /documents/{id}/text` — so the frontend can highlight the
exact passage in the source rather than string-matching for it.

`/search` runs the same `hybrid_search` the chat path uses, without the model
call, so its ranking is exactly the context chat would have been handed — which
makes it the way to see *why* chat cited what it cited. Each hit carries a
`snippet` with matched terms wrapped in `\x02`/`\x03`, not `<mark>` tags: see
`services/retrieval/snippets.py` for why the highlighted excerpt is never HTML.

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
| `app/api/deps.py` | `current_user`: the one place a cookie becomes a workspace |
| `app/services/ingestion/` | parse → chunk, offsets preserved throughout |
| `app/services/embeddings/` | local `bge-small-en-v1.5`, no API dependency |
| `app/services/retrieval/` | vector + full-text fused with RRF, one SQL query; `snippets.py` adds `ts_headline` excerpts for `/search` |
| `app/services/rag/` | Claude call with native citations, offsets rebased |
| `app/workers/` | Arq worker + enqueue side; falls back to inline ingestion |
| `../infra/init.sql` | schema source of truth (no Alembic yet) |

## Things that will bite

- **The session cookie only works because dev is all on localhost.** SameSite
  ignores the port, so `localhost:3000` → `localhost:8000` counts as same-site
  and `SameSite=Lax` is enough. Split the API onto its own domain and you need
  `SameSite=None; Secure`, an explicit `Domain=`, and real CSRF tokens — set
  `COOKIE_SECURE=true` and treat the Lax assumption in `routes_auth.py` as
  no longer holding.
- **Embedding dim is fixed in SQL.** `chunks.embedding` is `vector(384)`.
  Changing `EMBEDDING_MODEL` to one with a different width needs a migration;
  `embedder.warm_up()` fails at boot rather than letting them drift apart.
- **Re-embedding.** `chunks.embedding_model` records what produced each vector,
  so a model change can target exactly what is stale.
- **Ingestion runs in a worker, or inline if it can't.** `enqueue_ingest`
  returns `False` and processes the document in-request when Redis is
  unreachable, so a large PDF blocks that request. The upload response says
  which path it took. Start a worker with
  `arq app.workers.arq_app.WorkerSettings`.
- **OCR is per page, not per document.** A PDF that is half digital and half
  scanned recovers the scanned pages only. It needs the `tesseract` binary on
  PATH; without it OCR reports itself unavailable and those pages extract
  nothing rather than the request failing.
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
