-- Migration 002: Semantic cache
-- Date: 2026-06-25
-- Description: pgvector HNSW semantic cache with dual embedding

CREATE TABLE IF NOT EXISTS semantic_cache (
    id              SERIAL PRIMARY KEY,
    query_hash      TEXT UNIQUE NOT NULL,
    query_text      TEXT NOT NULL,
    embedding       vector(1792) NOT NULL,
    response_text   TEXT NOT NULL,
    response_type   TEXT NOT NULL DEFAULT 'chat',
    tokens_saved    INT DEFAULT 0,
    cost_saved      REAL DEFAULT 0.0,
    model_used      TEXT,
    similarity      REAL DEFAULT 1.0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    last_hit        TIMESTAMPTZ DEFAULT NOW(),
    hit_count       INT DEFAULT 1,
    metadata        JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_semantic_cache_embedding
    ON semantic_cache USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE UNIQUE INDEX IF NOT EXISTS idx_semantic_cache_hash
    ON semantic_cache(query_hash);
