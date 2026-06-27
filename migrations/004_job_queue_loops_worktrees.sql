-- Migration 004: Job Queue, Loop Patterns, and Worktree Registry
-- Date: 2026-06-27
-- Description: PostgreSQL-backed job queue (SKIP LOCKED), production loop patterns,
--              loop state/run-log/budget, and worktree isolation tracking.

-- ═══════════════════════════════════════════════════════════════
-- Part 1: Job Queue (replaces Huey SQLite)
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS job_queue (
    id                  BIGSERIAL PRIMARY KEY,

    -- Identity
    queue               VARCHAR(100) NOT NULL DEFAULT 'default',
    job_type            VARCHAR(100) NOT NULL,
    handler             VARCHAR(500) NOT NULL,
    payload             JSONB NOT NULL DEFAULT '{}',

    -- State machine
    status              VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- 'pending' | 'scheduled' | 'available' | 'running' | 'completed' | 'failed' | 'cancelled'

    priority            INT NOT NULL DEFAULT 0,

    -- Scheduling
    scheduled_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    available_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Timing
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    timeout_seconds     INT NOT NULL DEFAULT 300,

    -- Retry
    max_retries         INT NOT NULL DEFAULT 3,
    retry_count         INT NOT NULL DEFAULT 0,
    retry_delay_seconds INT NOT NULL DEFAULT 30,
    last_error          TEXT,

    -- Chaining
    depends_on          BIGINT[] DEFAULT '{}',
    parent_job_id       BIGINT,

    -- Consumer tracking (SKIP LOCKED)
    consumer_id         VARCHAR(100),
    consumer_lock_until TIMESTAMPTZ,

    -- Result
    result              JSONB,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for SKIP LOCKED dequeue performance
CREATE INDEX IF NOT EXISTS idx_job_queue_dequeue
    ON job_queue (priority DESC, available_at ASC, created_at ASC)
    WHERE status = 'available' AND consumer_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_job_queue_scheduled
    ON job_queue (scheduled_at ASC)
    WHERE status = 'scheduled';

CREATE INDEX IF NOT EXISTS idx_job_queue_queue_status
    ON job_queue (queue, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_job_queue_parent
    ON job_queue (parent_job_id)
    WHERE parent_job_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_job_queue_consumer
    ON job_queue (consumer_id)
    WHERE consumer_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_job_queue_stale_locks
    ON job_queue (consumer_lock_until)
    WHERE consumer_lock_until IS NOT NULL;

-- ═══════════════════════════════════════════════════════════════
-- Part 2: Recurring Schedules
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS job_schedule (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(200) NOT NULL UNIQUE,
    job_type            VARCHAR(100) NOT NULL,
    handler             VARCHAR(500) NOT NULL,
    payload             JSONB NOT NULL DEFAULT '{}',
    queue               VARCHAR(100) NOT NULL DEFAULT 'scheduled',

    schedule_type       VARCHAR(20) NOT NULL,
    -- 'cron' | 'interval' | 'daily' | 'hourly'

    cron_expr           VARCHAR(100),
    interval_seconds    BIGINT,

    max_retries         INT NOT NULL DEFAULT 3,
    timeout_seconds     INT NOT NULL DEFAULT 600,
    priority            INT NOT NULL DEFAULT 0,

    enabled             BOOLEAN NOT NULL DEFAULT TRUE,
    paused              BOOLEAN NOT NULL DEFAULT FALSE,
    paused_reason       TEXT,

    last_run_at         TIMESTAMPTZ,
    last_run_status     VARCHAR(20),
    next_run_at         TIMESTAMPTZ,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_job_schedule_next_run
    ON job_schedule (next_run_at ASC)
    WHERE enabled AND NOT paused;

-- ═══════════════════════════════════════════════════════════════
-- Part 3: Loop Pattern Registry
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS loop_patterns (
    id                  VARCHAR(100) PRIMARY KEY,
    title               VARCHAR(200) NOT NULL,
    description         TEXT NOT NULL,
    cadence             BIGINT NOT NULL,            -- seconds between runs
    max_turns           INT NOT NULL DEFAULT 20,
    max_tokens          BIGINT NOT NULL DEFAULT 100000,
    verifier            BOOLEAN NOT NULL DEFAULT FALSE,
    worktree            BOOLEAN NOT NULL DEFAULT FALSE,
    requires_mcp        TEXT[] DEFAULT '{}',
    requires_skills     TEXT[] DEFAULT '{}',
    readiness           VARCHAR(10) DEFAULT 'L0',
    enabled             BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Seed the 7 canonical patterns
INSERT INTO loop_patterns (id, title, description, cadence, max_turns, max_tokens, verifier, worktree, readiness) VALUES
    ('daily-triage',        'Daily Triage',         'Morning scan of CI, issues, commits. Report-only week one.',                       86400,  10,  50000,  FALSE, FALSE, 'L0'),
    ('pr-babysitter',       'PR Babysitter',        'Shepherd PRs through review, CI, rebase, and merge.',                             900,    20,  200000, TRUE,  TRUE,  'L0'),
    ('ci-sweeper',          'CI Sweeper',           'React to failing checks with minimal fixes in isolated worktrees.',                 900,    15,  150000, TRUE,  TRUE,  'L0'),
    ('dependency-sweeper',  'Dependency Sweeper',   'Patch CVEs and stale deps in worktrees. Majors and denylist stay human-gated.',    21600,  15,  100000, TRUE,  TRUE,  'L0'),
    ('post-merge-cleanup',  'Post-Merge Cleanup',   'TODOs, deprecations, and tech debt after merges. Small PRs overnight.',            21600,  10,   80000, FALSE, TRUE,  'L0'),
    ('issue-triage',        'Issue Triage',         'Dedupe, score, and label incoming issues. Propose-only week one.',                 7200,   10,   50000, FALSE, FALSE, 'L0'),
    ('changelog-drafter',   'Changelog Drafter',    'Scan merges & commits, produce polished categorized release notes drafts.',        86400,  5,    60000, FALSE, FALSE, 'L0')
ON CONFLICT (id) DO NOTHING;

-- ═══════════════════════════════════════════════════════════════
-- Part 4: Loop State (per-pattern durable memory)
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS loop_state (
    id                  SERIAL PRIMARY KEY,
    pattern_id          VARCHAR(100) NOT NULL REFERENCES loop_patterns(id),
    run_id              BIGINT,                         -- FK to job_queue
    state_type          VARCHAR(20) DEFAULT 'snapshot',

    -- Standard sections (mirrors the STATE.md concept)
    last_run            TIMESTAMPTZ,
    items_active        JSONB DEFAULT '[]',   -- [{id, title, status, attempts, worktree_id}]
    items_watch         JSONB DEFAULT '[]',   -- [{id, title, status, last_seen}]
    items_noise         JSONB DEFAULT '[]',   -- [{id, title, reason, ignored_since}]
    items_pruned        JSONB DEFAULT '[]',   -- resolved this run
    escalations         JSONB DEFAULT '[]',   -- [{item_id, reason, context, escalated_at}]
    human_overrides     JSONB DEFAULT '[]',   -- [{item_id, decision, by, at}]

    data                JSONB,                          -- full custom state payload

    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_loop_state_pattern
    ON loop_state (pattern_id, created_at DESC);

-- ═══════════════════════════════════════════════════════════════
-- Part 5: Loop Run Log (per-run metrics + budget tracking)
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS loop_run_log (
    id                  BIGSERIAL PRIMARY KEY,
    pattern_id          VARCHAR(100) NOT NULL REFERENCES loop_patterns(id),
    run_id              BIGINT,                         -- FK to job_queue
    started_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at         TIMESTAMPTZ,
    duration_ms         INT,
    items_found         INT DEFAULT 0,
    actions_taken       INT DEFAULT 0,
    escalations         INT DEFAULT 0,
    tokens_estimate     BIGINT DEFAULT 0,
    outcome             VARCHAR(20),                    -- 'success', 'failed', 'escalated', 'noop', 'error'
    error               TEXT,

    token_budget        BIGINT,
    tokens_remaining    BIGINT,

    schedule_name       VARCHAR(200),

    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_loop_run_log_pattern
    ON loop_run_log (pattern_id, started_at DESC);

-- ═══════════════════════════════════════════════════════════════
-- Part 6: Loop Budget (daily token caps with auto-pause)
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS loop_budget (
    id                  SERIAL PRIMARY KEY,
    pattern_id          VARCHAR(100) NOT NULL REFERENCES loop_patterns(id),
    daily_cap           BIGINT NOT NULL DEFAULT 100000,
    daily_spent         BIGINT DEFAULT 0,
    budget_date         DATE NOT NULL DEFAULT CURRENT_DATE,
    paused              BOOLEAN DEFAULT FALSE,
    pause_reason        TEXT,
    kill_switch         BOOLEAN DEFAULT FALSE,
    notify_at_pct       INT DEFAULT 80,

    UNIQUE (pattern_id, budget_date)
);

-- Seed budgets for all patterns
INSERT INTO loop_budget (pattern_id, daily_cap) VALUES
    ('daily-triage',        50000),
    ('pr-babysitter',      200000),
    ('ci-sweeper',         150000),
    ('dependency-sweeper',  50000),
    ('post-merge-cleanup',  50000),
    ('issue-triage',        50000),
    ('changelog-drafter',   50000)
ON CONFLICT (pattern_id, budget_date) DO NOTHING;

-- ═══════════════════════════════════════════════════════════════
-- Part 7: Worktree Registry
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS worktree_registry (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_id          VARCHAR(100) NOT NULL,
    item_id             VARCHAR(200) NOT NULL,          -- PR#1234, issue#456, fix-auth
    path                TEXT NOT NULL,                   -- absolute path to worktree
    branch              VARCHAR(200) NOT NULL,           -- git branch name
    base_branch         VARCHAR(200) NOT NULL DEFAULT 'main',
    repo_path           TEXT NOT NULL,                   -- main repo path

    status              VARCHAR(20) NOT NULL DEFAULT 'active',
    -- 'active', 'locked', 'stale', 'released', 'orphaned'

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acquired_at         TIMESTAMPTZ,
    released_at         TIMESTAMPTZ,
    last_used_at        TIMESTAMPTZ,

    locked_by           VARCHAR(200),                   -- agent/process ID
    locked_at           TIMESTAMPTZ,
    lock_expires_at     TIMESTAMPTZ,

    total_edits         INT DEFAULT 0,
    total_tool_calls    INT DEFAULT 0,
    outcome             VARCHAR(50),                    -- 'committed', 'abandoned', 'merged'
    error               TEXT,

    UNIQUE (pattern_id, item_id),
    UNIQUE (path)
);

CREATE INDEX IF NOT EXISTS idx_worktree_status
    ON worktree_registry (status);

CREATE INDEX IF NOT EXISTS idx_worktree_pattern
    ON worktree_registry (pattern_id, status);

CREATE INDEX IF NOT EXISTS idx_worktree_stale
    ON worktree_registry (status, acquired_at)
    WHERE status IN ('active', 'locked');

CREATE INDEX IF NOT EXISTS idx_worktree_repo
    ON worktree_registry (repo_path);

-- ═══════════════════════════════════════════════════════════════
-- Part 8: Cron expression helper (for PostgreSQL-based cron eval)
-- ═══════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION cron_next(
    cron_expr TEXT,
    from_time TIMESTAMPTZ
) RETURNS TIMESTAMPTZ AS $$
-- Placeholder: Python-side croniter handles actual parsing.
-- This is used for DB-level next_run_at calculation fallback.
BEGIN
    RETURN from_time + INTERVAL '1 day';
END;
$$ LANGUAGE plpgsql IMMUTABLE;
