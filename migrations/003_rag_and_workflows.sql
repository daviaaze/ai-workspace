-- Migration 003: RAG chunks and workflow engine
-- Date: 2026-06-25
-- Description: Vector chunks for RAG and workflow execution logs

-- ═══════════════════════════════════════════════════════════
-- RAG Chunks (multi-engine retrieval)
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS chunks (
    id              SERIAL PRIMARY KEY,
    kb_id           TEXT NOT NULL,
    content         TEXT NOT NULL,
    metadata        JSONB DEFAULT '{}',
    embedding       vector(1792),
    tsvector        tsvector,
    source          TEXT,
    chunk_index     INT DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS chunks_embedding_idx ON chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS chunks_tsvector_idx ON chunks
    USING gin (tsvector);

CREATE INDEX IF NOT EXISTS chunks_source_idx ON chunks(source);

-- ═══════════════════════════════════════════════════════════
-- Workflow Engine
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS workflow_runs (
    id              SERIAL PRIMARY KEY,
    workflow_name   TEXT NOT NULL,
    status          TEXT DEFAULT 'running',
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    metadata        JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_workflow_runs_status ON workflow_runs(status);

CREATE TABLE IF NOT EXISTS workflow_logs (
    id              SERIAL PRIMARY KEY,
    run_id          INT NOT NULL REFERENCES workflow_runs(id),
    step_name       TEXT NOT NULL,
    status          TEXT DEFAULT 'running',
    input           JSONB DEFAULT '{}',
    output          JSONB DEFAULT '{}',
    error           TEXT,
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    finished_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_workflow_logs_run ON workflow_logs(run_id);
