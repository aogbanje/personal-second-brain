# PSB — AI-Powered Document Intelligence Platform

## What This Project Is

An app that takes messy, scattered inputs — PDFs, web links, maybe raw text — and turns them into a **structured, queryable knowledge graph** you can search and chat with. Under the hood it's a RAG (Retrieval-Augmented Generation) pipeline: documents get parsed, chunked, embedded, and linked by extracted entities/relationships, so a user can ask a question in natural language and get an answer grounded in _their_ documents, with the graph showing how concepts connect across sources.

Stack: **Python** (backend/AI/data pipeline) + **Next.js** (frontend/UX).

---

## Core Feature Set (the MVP backbone)

- Multi-source ingestion: PDF upload, URL scraping, plain text/.docx
- Parsing + chunking (with OCR fallback for scanned PDFs)
- Embedding generation → vector store
- Entity & relationship extraction → knowledge graph store
- Hybrid retrieval (vector similarity + keyword/BM25)
- RAG chat interface with **source citations** (not just answers — show _where_ it came from)
- Interactive graph visualization (explore nodes/edges, click to drill into source doc)
- Async background processing for ingestion (documents shouldn't block the UI)
- Real-time status updates while a doc is being processed
- Auth + per-user/workspace document organization

## Features Worth Considering (not required, but valuable)

- Auto-tagging / semantic clustering of documents
- Passage-level highlighting in the source doc when a chat answer cites it
- Export: graph as JSON/GraphML, summaries as Markdown/PDF
- Document versioning + re-indexing on update
- Collaborative annotations/comments on documents or graph nodes
- Rate limiting + a basic usage dashboard
- Webhook/plugin hooks for external tools to push documents in

---

## Architecture Decisions to Reason Through Before You Lock In

Don't treat these as solved — they shape a lot of what follows, so it's worth sitting with each one for a bit:

1. **Vector store** — pgvector (Postgres extension, one less service to run) vs. Qdrant/Weaviate (self-hosted, built for this) vs. Pinecone (managed, no ops). What does _your_ deployment budget and ops appetite look like?
2. **Graph store** — Neo4j (real graph DB, Cypher queries, built-in viz tooling) vs. modeling edges relationally in Postgres vs. an in-memory networkx graph rebuilt on read. At what scale does "knowledge graph" actually need a dedicated graph engine vs. just... a table?
3. **RAG orchestration** — raw API calls you control end-to-end vs. LangChain/LlamaIndex abstractions that save boilerplate but hide what's happening. Given you're still building instincts here, which serves your learning better _right now_?
4. **Background jobs** — Celery (mature, heavier) vs. RQ (simpler) vs. Arq (async-native, pairs naturally with FastAPI). Since your API layer is likely async, does a sync-first queue fight that?

Worth sketching out your reasoning for each before writing a line of code — it'll save you a rewrite later.

---

## File Structure

```
psb(personal-second-brain)/
├── backend/                          # Python backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app entrypoint
│   │   ├── core/
│   │   │   ├── config.py             # env-driven settings
│   │   │   ├── security.py           # auth/JWT logic
│   │   │   └── logging.py
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── routes_documents.py
│   │   │   │   ├── routes_search.py
│   │   │   │   ├── routes_chat.py
│   │   │   │   ├── routes_graph.py
│   │   │   │   └── routes_auth.py
│   │   │   └── deps.py               # shared FastAPI dependencies
│   │   ├── services/
│   │   │   ├── ingestion/
│   │   │   │   ├── pdf_parser.py
│   │   │   │   ├── web_scraper.py
│   │   │   │   └── chunker.py
│   │   │   ├── embeddings/
│   │   │   │   └── embedder.py
│   │   │   ├── graph/
│   │   │   │   ├── entity_extractor.py
│   │   │   │   └── graph_builder.py
│   │   │   ├── retrieval/
│   │   │   │   ├── vector_search.py
│   │   │   │   └── hybrid_search.py
│   │   │   └── rag/
│   │   │       └── answer_generator.py
│   │   ├── models/
│   │   │   ├── schemas.py            # Pydantic request/response models
│   │   │   └── db_models.py          # ORM models
│   │   ├── db/
│   │   │   ├── postgres.py
│   │   │   ├── vector_store.py
│   │   │   └── graph_store.py
│   │   ├── workers/
│   │   │   ├── celery_app.py         # or arq/rq equivalent
│   │   │   └── tasks.py
│   │   └── utils/
│   │       └── helpers.py
│   ├── tests/
│   │   ├── test_ingestion.py
│   │   ├── test_retrieval.py
│   │   └── test_api.py
│   ├── alembic/                      # DB migrations (if using Postgres)
│   ├── requirements.txt              # or pyproject.toml
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/                         # Next.js frontend
│   ├── app/
│   │   ├── (auth)/
│   │   │   ├── login/page.tsx
│   │   │   └── signup/page.tsx
│   │   ├── dashboard/
│   │   │   ├── page.tsx              # document library
│   │   │   └── [docId]/page.tsx
│   │   ├── graph/
│   │   │   └── page.tsx              # interactive graph explorer
│   │   ├── chat/
│   │   │   └── page.tsx              # RAG chat interface
│   │   ├── layout.tsx
│   │   └── page.tsx                  # landing/home
│   ├── components/
│   │   ├── ui/                       # buttons, inputs, modals, etc.
│   │   ├── graph/
│   │   │   └── GraphCanvas.tsx       # e.g. react-flow / d3 based viz
│   │   ├── chat/
│   │   │   ├── ChatWindow.tsx
│   │   │   └── CitationCard.tsx
│   │   └── documents/
│   │       ├── UploadDropzone.tsx
│   │       └── DocumentCard.tsx
│   ├── lib/
│   │   ├── api-client.ts             # typed fetch wrapper to backend
│   │   └── auth.ts
│   ├── hooks/
│   │   ├── useDocuments.ts
│   │   └── useGraphData.ts
│   ├── styles/
│   │   └── globals.css
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   └── next.config.js
│
├── infra/
│   ├── docker-compose.yml            # spins up backend, frontend, db, vector store, graph store, redis
│   └── k8s/                          # optional, for later
│
├── docs/
│   ├── architecture.md
│   └── api-spec.md
│
├── .gitignore
└── README.md
```

---

## A Note on Sequencing

Ingestion → embedding → retrieval → graph → chat is roughly the dependency order — each layer needs the one before it working. Worth deciding: are you building this vertically (one document type, end-to-end, working) or horizontally (all ingestion types, then all retrieval, etc.)? Given your 20-minute-stuck rule and daily build rhythm, which of those two gets you a demoable slice fastest?
