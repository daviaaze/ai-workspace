-- Migration 001: Initial schema
-- Date: 2026-06-25
-- Description: Core tables for knowledge, cost, source reputation, sessions

-- ═══════════════════════════════════════════════════════════
-- Knowledge Store
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS knowledge_entries (
    id              SERIAL PRIMARY KEY,
    title           TEXT NOT NULL,
    content         TEXT NOT NULL,
    category        TEXT DEFAULT 'general',
    source          TEXT,
    embedding       vector(1792),
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_embedding
    ON knowledge_entries USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE TABLE IF NOT EXISTS research_entries (
    id              SERIAL PRIMARY KEY,
    query           TEXT NOT NULL,
    result          TEXT NOT NULL,
    sources         JSONB DEFAULT '[]',
    tokens_used     INT DEFAULT 0,
    model_used      TEXT,
    embedding       vector(1792),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tasks (
    id              SERIAL PRIMARY KEY,
    title           TEXT NOT NULL,
    description     TEXT,
    status          TEXT DEFAULT 'pending',
    priority        INT DEFAULT 0,
    cron_expression TEXT,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_memory (
    id              SERIAL PRIMARY KEY,
    key             TEXT UNIQUE NOT NULL,
    value           TEXT NOT NULL,
    category        TEXT DEFAULT 'general',
    embedding       vector(1792),
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ═══════════════════════════════════════════════════════════
-- Cost Tracking
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS cost_log (
    id              SERIAL PRIMARY KEY,
    model           TEXT NOT NULL,
    provider        TEXT NOT NULL,
    tokens_in       INT DEFAULT 0,
    tokens_out      INT DEFAULT 0,
    cost            REAL DEFAULT 0.0,
    cached          BOOLEAN DEFAULT FALSE,
    timestamp       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cost_timestamp ON cost_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_cost_provider ON cost_log(provider);

-- ═══════════════════════════════════════════════════════════
-- Source Reputation
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS source_tracking (
    id              SERIAL PRIMARY KEY,
    url             TEXT NOT NULL UNIQUE,
    domain          TEXT NOT NULL,
    title           TEXT DEFAULT '',
    snippet         TEXT DEFAULT '',
    cred1_score     REAL,
    credinet_credible BOOLEAN,
    credinet_last_checked TIMESTAMPTZ,
    our_score       REAL DEFAULT 0.5,
    cross_ref_score REAL,
    cross_ref_samples INT DEFAULT 0,
    composite_score REAL DEFAULT 0.5,
    composite_updated TIMESTAMPTZ,
    first_seen      TIMESTAMPTZ DEFAULT NOW(),
    last_seen       TIMESTAMPTZ DEFAULT NOW(),
    times_used      INT DEFAULT 1,
    times_accurate  INT DEFAULT 0,
    times_inaccurate INT DEFAULT 0,
    user_rating     REAL,
    category        TEXT,
    sources_flagging INT DEFAULT 0,
    is_flagged      BOOLEAN DEFAULT FALSE,
    metadata        JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_source_domain ON source_tracking(domain);
CREATE INDEX IF NOT EXISTS idx_source_composite ON source_tracking(composite_score);
CREATE INDEX IF NOT EXISTS idx_source_cred1 ON source_tracking(cred1_score);

CREATE TABLE IF NOT EXISTS domain_reputation (
    id              SERIAL PRIMARY KEY,
    domain          TEXT UNIQUE NOT NULL,
    cred1_score     REAL,
    cred1_category  TEXT,
    cred1_sources   INT DEFAULT 0,
    cred1_last_updated TIMESTAMPTZ,
    credinet_credible BOOLEAN,
    credinet_last_checked TIMESTAMPTZ,
    times_used      INT DEFAULT 0,
    times_accurate  INT DEFAULT 0,
    times_inaccurate INT DEFAULT 0,
    accuracy_rate   REAL,
    user_rating     REAL,
    user_flags      INT DEFAULT 0,
    composite_score REAL DEFAULT 0.5,
    composite_updated TIMESTAMPTZ,
    cross_ref_score REAL,
    cross_ref_samples INT DEFAULT 0,
    first_seen      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_domain_composite ON domain_reputation(composite_score);
CREATE INDEX IF NOT EXISTS idx_domain_cred1 ON domain_reputation(cred1_score);

CREATE TABLE IF NOT EXISTS cross_reference_log (
    id              SERIAL PRIMARY KEY,
    research_id     INT,
    claim_hash      TEXT NOT NULL,
    claim_summary   TEXT,
    sources_agreeing INT DEFAULT 0,
    sources_disagreeing INT DEFAULT 0,
    total_sources   INT DEFAULT 0,
    agreement_ratio REAL DEFAULT 0.0,
    consensus       TEXT DEFAULT 'inconclusive',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crossref_claim ON cross_reference_log(claim_hash);

-- ═══════════════════════════════════════════════════════════
-- Sessions
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS sessions (
    id              SERIAL PRIMARY KEY,
    session_id      TEXT UNIQUE NOT NULL,
    title           TEXT,
    model           TEXT,
    provider        TEXT,
    pattern         TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS session_entries (
    id              SERIAL PRIMARY KEY,
    session_id      TEXT NOT NULL REFERENCES sessions(session_id),
    parent_id       INT REFERENCES session_entries(id),
    role            TEXT NOT NULL,
    content         TEXT,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_session_entries_created ON session_entries(created_at);
CREATE INDEX IF NOT EXISTS idx_session_entries_parent ON session_entries(parent_id);
