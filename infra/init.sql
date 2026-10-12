-- PSB schema. Runs once on first Postgres boot (docker-entrypoint-initdb.d).
-- Source of truth for the schema until Alembic is introduced.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    -- Lowercased before insert so uniqueness is case-insensitive without citext.
    email         TEXT NOT NULL UNIQUE,
    -- argon2id, encoded format produced by argon2-cffi (carries its own params
    -- and salt, so rehashing after a parameter change needs no schema change).
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One per user at signup. Kept as its own table rather than folding
-- workspace_id onto users because content is scoped to a workspace, not an
-- owner -- sharing a workspace later means new rows here, not a migration of
-- every document.
CREATE TABLE workspaces (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX workspaces_owner_idx ON workspaces (owner_id);

-- Opaque session tokens rather than JWTs, so logout can actually revoke. Only
-- the SHA-256 of the token is stored: a dump of this table yields nothing that
-- can be replayed as a cookie.
CREATE TABLE sessions (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    token_hash TEXT NOT NULL UNIQUE,
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX sessions_user_idx ON sessions (user_id);

-- Embedding dimension is fixed at the column level, so it must match the model
-- in EMBEDDING_MODEL. bge-small-en-v1.5 -> 384. Changing models means a migration.
CREATE TABLE documents (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id  UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    title         TEXT NOT NULL,
    source_type   TEXT NOT NULL CHECK (source_type IN ('pdf', 'text', 'url')),
    source_ref    TEXT,
    -- Uploaded bytes live on disk; the worker parses them. Set for source_type
    -- 'pdf', null for text and url.
    blob_path     TEXT,
    -- Full extracted text. Citation offsets are meaningless without it. Empty
    -- until the worker has parsed the source.
    raw_text      TEXT NOT NULL DEFAULT '',
    page_count    INTEGER,
    -- [[page_number, char_start, char_end], ...] into raw_text. Stored at parse
    -- time because page text contains blank lines of its own, so the page
    -- separator cannot be scanned for reliably after the fact.
    page_spans    JSONB NOT NULL DEFAULT '[]'::jsonb,
    -- Latest progress event, replayed to SSE clients that connect late.
    progress      JSONB,
    status        TEXT NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending', 'processing', 'ready', 'failed')),
    error         TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX documents_workspace_idx ON documents (workspace_id, created_at DESC);

CREATE TABLE chunks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    ordinal         INTEGER NOT NULL,
    text            TEXT NOT NULL,
    -- Offsets into documents.raw_text. This is what makes passage-level
    -- highlighting possible later; it cannot be reconstructed after the fact.
    char_start      INTEGER NOT NULL,
    char_end        INTEGER NOT NULL,
    page_number     INTEGER,
    -- Vectors are only comparable within the same model. Store which one
    -- produced this row so re-embedding can target what is stale.
    embedding_model TEXT NOT NULL,
    embedding_dim   INTEGER NOT NULL,
    embedding       vector(384),
    tsv             tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (document_id, ordinal)
);

CREATE INDEX chunks_document_idx  ON chunks (document_id, ordinal);
CREATE INDEX chunks_workspace_idx ON chunks (workspace_id);
CREATE INDEX chunks_tsv_idx       ON chunks USING GIN (tsv);
CREATE INDEX chunks_embedding_idx ON chunks
    USING hnsw (embedding vector_cosine_ops);

-- Knowledge graph, modelled relationally. Entities are deduplicated per
-- workspace by normalized name; edges carry the chunk they were extracted from
-- so every graph claim traces back to a citable passage.
CREATE TABLE entities (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    entity_type     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (workspace_id, normalized_name)
);

CREATE TABLE entity_edges (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id  UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    source_id     UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    target_id     UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    relation      TEXT NOT NULL,
    chunk_id      UUID REFERENCES chunks(id) ON DELETE SET NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX entity_edges_source_idx    ON entity_edges (workspace_id, source_id);
CREATE INDEX entity_edges_target_idx    ON entity_edges (workspace_id, target_id);
