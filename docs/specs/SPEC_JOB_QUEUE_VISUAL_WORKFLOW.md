# Spec: PostgreSQL Job Queue + Visual Workflow Engine

> **Status:** 📋 Spec | **Data:** 2026-06-27
> **Refs:** PGMQ, pg_boss, graphile-worker, Temporal, Prefect, Dagster, SPEC_LOOP_PATTERNS.md, SPEC_WORKTREE_MANAGER.md

---

## 🎯 The Problem

The current aiw has **two separate execution systems** with fundamental limitations:

| System | Current | Problem |
|--------|---------|---------|
| **Task Queue** | Huey + SQLite | SQLite = no concurrent consumers. No job chaining. No durable scheduling across restarts. No visibility into queue depth. |
| **Workflow Engine** | PostgreSQL + `@step` DAG | Works, but CLI-only. No web UI for visualization, manual retry, or monitoring. Workflow steps can't reference each other's outputs naturally. |

**What we need** is a unified system where:

- Loops (SPEC_LOOP_PATTERNS.md) are scheduled as **recurring jobs**
- Each loop run is a **job** with state, progress, and result
- Complex multi-step operations are **DAG workflows** with parallel steps and retries
- Everything is **visible and controllable** from a web UI
- Everything runs on **PostgreSQL** (no mixed storage backends)

---

## 🏗 System Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│                        Web UI (FastAPI + React SPA)                │
│  ┌────────────┐ ┌──────────────┐ ┌──────────┐ ┌───────────────┐ │
│  │ Queue      │ │ Workflow DAG │ │ Schedule │ │ Run Details   │ │
│  │ Dashboard  │ │ Visualization│ │ Calendar │ │ + Logs + Retry│ │
│  └────────────┘ └──────────────┘ └──────────┘ └───────────────┘ │
└─────────────────────────┬─────────────────────────────────────────┘
                          │ REST API (FastAPI routes)
┌─────────────────────────┴─────────────────────────────────────────┐
│                       Job Queue Service                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │
│  │ Enqueue  │ │ Dequeue  │ │ Schedule │ │ Retry    │ │ Chaining│  │
│  │ (SKIP    │ │ (SKIP    │ │ (cron +  │ │ (backoff)│ │ (depends│  │
│  │ LOCKED)  │ │ LOCKED)  │ │ interval)│ │          │ │  on)   │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘  │
└─────────────────────────┬─────────────────────────────────────────┘
                          │
┌─────────────────────────┴─────────────────────────────────────────┐
│                    Workflow Engine (enhanced)                       │
│  ┌────────────┐ ┌────────────┐ ┌───────────┐ ┌─────────────────┐ │
│  │ DAG Compile│ │ Topo Sort  │ │ Parallel  │ │ Node Handler:   │ │
│  │ (task→DAG) │ │ (levels)   │ │ Executor  │ │ agent_loop call │ │
│  └────────────┘ └────────────┘ └───────────┘ └─────────────────┘ │
└─────────────────────────┬─────────────────────────────────────────┘
                          │
┌─────────────────────────┴─────────────────────────────────────────┐
│                    PostgreSQL (single source of truth)               │
│  ┌────────────┐ ┌────────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ job_queue  │ │ job_schedule│ │workflow_ │ │ loop_state +     │ │
│  │ (messages) │ │ (recurring) │ │ state    │ │ worktree_reg     │ │
│  └────────────┘ └────────────┘ └──────────┘ └──────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
```

---

## 📐 Part 1: PostgreSQL Job Queue

### Schema

```sql
-- ═══════════════════════════════════════════════════════════════
-- Core job queue (inspired by PGMQ + pg_boss)
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE job_queue (
    id              BIGSERIAL PRIMARY KEY,
    
    -- Identity
    queue           VARCHAR(100) NOT NULL DEFAULT 'default',
    -- 'default', 'loops', 'workflows', 'scheduled', 'webhooks'
    
    job_type        VARCHAR(100) NOT NULL,
    -- 'loop:daily-triage', 'loop:pr-babysitter', 'workflow:deep-research',
    -- 'task:agent', 'task:research', 'webhook:github'
    
    handler         VARCHAR(500) NOT NULL,
    -- Python dotted path to the handler function:
    -- 'ai_workspace.loops.daily_triage.run'
    -- 'ai_workspace.workflow.engine.execute_workflow'
    
    payload         JSONB NOT NULL DEFAULT '{}',
    -- Handler-specific data: {project_root, item_id, pattern_params, ...}
    
    -- State machine
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- 'pending' → 'scheduled' | 'available'
    -- 'available' → 'running'
    -- 'running' → 'completed' | 'failed' | 'cancelled'
    -- 'pending' → 'cancelled' (direct)
    
    -- Priority (higher = first)
    priority        INT NOT NULL DEFAULT 0,
    
    -- Scheduling
    scheduled_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    available_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- If scheduled_at > NOW(), job is 'scheduled' until scheduled_at
    -- Then available_at = scheduled_at, status = 'available'
    
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    
    -- Timeout
    timeout_seconds INT NOT NULL DEFAULT 300,
    
    -- Retry
    max_retries     INT NOT NULL DEFAULT 3,
    retry_count     INT NOT NULL DEFAULT 0,
    retry_delay_seconds INT NOT NULL DEFAULT 30,  -- base delay
    last_error      TEXT,
    
    -- Chaining
    depends_on      BIGINT[] DEFAULT '{}',       -- job IDs that must complete first
    parent_job_id   BIGINT,                       -- for sub-jobs spawned by a parent
    
    -- Metadata
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Consumer tracking (SKIP LOCKED)
    consumer_id     VARCHAR(100),                 -- unique consumer identifier
    consumer_lock_until TIMESTAMPTZ               -- auto-release if not updated
);

-- ═══════════════════════════════════════════════════════════════
-- Indexes for SKIP LOCKED
-- ═══════════════════════════════════════════════════════════════

-- Primary dequeue: available, not locked, not failed too many times
CREATE INDEX idx_job_queue_dequeue
    ON job_queue (priority DESC, available_at ASC, created_at ASC)
    WHERE status = 'available'
      AND consumer_id IS NULL;

-- Scheduled jobs to be made available
CREATE INDEX idx_job_queue_scheduled
    ON job_queue (scheduled_at ASC)
    WHERE status = 'scheduled';

-- Per-queue views
CREATE INDEX idx_job_queue_queue_status
    ON job_queue (queue, status, created_at DESC);

-- Lookup by parent
CREATE INDEX idx_job_queue_parent
    ON job_queue (parent_job_id)
    WHERE parent_job_id IS NOT NULL;

-- ═══════════════════════════════════════════════════════════════
-- Recurring schedules (for loops and periodic tasks)
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE job_schedule (
    id              SERIAL PRIMARY KEY,
    
    -- Identity
    name            VARCHAR(200) NOT NULL UNIQUE,
    -- 'daily-triage', 'morning-briefing', 'continuous-learning'
    
    job_type        VARCHAR(100) NOT NULL,
    handler         VARCHAR(500) NOT NULL,
    payload         JSONB NOT NULL DEFAULT '{}',
    queue           VARCHAR(100) NOT NULL DEFAULT 'scheduled',
    
    -- Schedule
    schedule_type   VARCHAR(20) NOT NULL,
    -- 'cron' | 'interval' | 'daily' | 'hourly'
    
    cron_expr       VARCHAR(100),                  -- '0 7 * * 1-5' (BRT)
    interval_seconds BIGINT,                        -- 3600 for hourly
    
    -- Limits
    max_retries     INT NOT NULL DEFAULT 3,
    timeout_seconds INT NOT NULL DEFAULT 600,
    priority        INT NOT NULL DEFAULT 0,
    
    -- Lifecycle
    enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    paused          BOOLEAN NOT NULL DEFAULT FALSE,
    paused_reason   TEXT,
    
    -- Last run tracking
    last_run_at     TIMESTAMPTZ,
    last_run_status VARCHAR(20),
    next_run_at     TIMESTAMPTZ,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_job_schedule_next_run
    ON job_schedule (next_run_at ASC)
    WHERE enabled AND NOT paused;
```

### SKIP LOCKED Dequeue (Core Algorithm)

```sql
-- Atomic dequeue: one job, one consumer, no race condition
WITH next_job AS (
    SELECT id
    FROM job_queue
    WHERE status = 'available'
      AND consumer_id IS NULL
      AND available_at <= NOW()
      AND retry_count <= max_retries
    ORDER BY priority DESC, available_at ASC, created_at ASC
    LIMIT 1
    FOR UPDATE SKIP LOCKED
)
UPDATE job_queue
SET status = 'running',
    consumer_id = :consumer_id,
    consumer_lock_until = NOW() + INTERVAL '5 minutes',
    started_at = NOW(),
    updated_at = NOW()
FROM next_job
WHERE job_queue.id = next_job.id
RETURNING job_queue.*;
```

### Python Client

```python
"""
PostgreSQL-backed job queue with SKIP LOCKED.
Replaces Huey SQLite. Supports loops, workflows, and ad-hoc tasks.

Usage:
    queue = JobQueue(dsn="postgresql:///ai_workspace")
    
    # Enqueue a one-off job
    job = await queue.enqueue(
        queue="loops",
        job_type="loop:daily-triage",
        handler="ai_workspace.loops.daily_triage.run",
        payload={"project_root": "/home/user/project"},
        priority=10,
    )
    
    # Enqueue with dependency (chaining)
    job2 = await queue.enqueue(
        ...
        depends_on=[job.id],
    )
    
    # Dequeue and process (called by worker)
    job = await queue.dequeue(consumer_id="worker-1")
    if job:
        try:
            result = await call_handler(job.handler, job.payload)
            await queue.complete(job.id, result)
        except Exception as e:
            await queue.fail(job.id, error=str(e))
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
import json
import uuid

import asyncpg


@dataclass
class Job:
    id: int
    queue: str
    job_type: str
    handler: str
    payload: dict
    status: str
    priority: int
    scheduled_at: datetime
    available_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    max_retries: int
    retry_count: int
    last_error: str | None
    depends_on: list[int]
    parent_job_id: int | None
    consumer_id: str | None
    created_at: datetime


class JobQueue:
    """PostgreSQL-backed job queue using SKIP LOCKED."""
    
    def __init__(self, dsn: str = "postgresql:///ai_workspace"):
        self.dsn = dsn
        self._pool: asyncpg.Pool | None = None
    
    async def connect(self):
        self._pool = await asyncpg.create_pool(self.dsn, min_size=2, max_size=10)
    
    async def close(self):
        if self._pool:
            await self._pool.close()
    
    # ── Enqueue ─────────────────────────────────────────────
    
    async def enqueue(
        self,
        queue: str = "default",
        job_type: str = "task",
        handler: str = "",
        payload: dict | None = None,
        priority: int = 0,
        scheduled_at: datetime | None = None,
        available_at: datetime | None = None,
        max_retries: int = 3,
        retry_delay_seconds: int = 30,
        timeout_seconds: int = 300,
        depends_on: list[int] | None = None,
        parent_job_id: int | None = None,
    ) -> Job:
        """Enqueue a new job."""
        now = datetime.now(timezone.utc)
        sched = scheduled_at or now
        avail = available_at or sched
        
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO job_queue
                   (queue, job_type, handler, payload, priority,
                    scheduled_at, available_at, max_retries,
                    retry_delay_seconds, timeout_seconds,
                    depends_on, parent_job_id)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                   RETURNING *""",
                queue, job_type, handler, json.dumps(payload or {}),
                priority, sched, avail, max_retries,
                retry_delay_seconds, timeout_seconds,
                depends_on or [], parent_job_id,
            )
            return self._row_to_job(row)
    
    async def enqueue_recurring(
        self,
        name: str,
        job_type: str,
        handler: str,
        payload: dict | None = None,
        queue: str = "scheduled",
        schedule_type: str = "interval",
        cron_expr: str | None = None,
        interval_seconds: int | None = None,
        max_retries: int = 3,
        timeout_seconds: int = 600,
        priority: int = 0,
    ) -> dict:
        """Register or update a recurring schedule."""
        now = datetime.now(timezone.utc)
        next_run = self._calc_next_run(schedule_type, cron_expr, interval_seconds, now)
        
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO job_schedule
                   (name, job_type, handler, payload, queue,
                    schedule_type, cron_expr, interval_seconds,
                    max_retries, timeout_seconds, priority, next_run_at)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                   ON CONFLICT (name) DO UPDATE SET
                     handler = EXCLUDED.handler,
                     payload = EXCLUDED.payload,
                     schedule_type = EXCLUDED.schedule_type,
                     cron_expr = EXCLUDED.cron_expr,
                     interval_seconds = EXCLUDED.interval_seconds,
                     enabled = TRUE,
                     paused = FALSE,
                     next_run_at = EXCLUDED.next_run_at,
                     updated_at = NOW()
                   RETURNING *""",
                name, job_type, handler, json.dumps(payload or {}),
                queue, schedule_type, cron_expr, interval_seconds,
                max_retries, timeout_seconds, priority, next_run,
            )
            return dict(row)
    
    # ── Dequeue (SKIP LOCKED) ───────────────────────────────
    
    async def dequeue(self, consumer_id: str, queues: list[str] | None = None) -> Job | None:
        """Atomically claim the next available job.
        
        Uses SELECT ... FOR UPDATE SKIP LOCKED to handle
        multiple concurrent consumers safely.
        """
        queue_filter = "AND queue = ANY($2::varchar[])" if queues else ""
        queues_param = queues or []
        
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""WITH next_job AS (
                        SELECT id FROM job_queue
                        WHERE status = 'available'
                          AND consumer_id IS NULL
                          AND available_at <= NOW()
                          AND retry_count <= max_retries
                          {queue_filter}
                        ORDER BY priority DESC, available_at ASC, created_at ASC
                        LIMIT 1
                        FOR UPDATE SKIP LOCKED
                    )
                    UPDATE job_queue
                    SET status = 'running',
                        consumer_id = $1,
                        consumer_lock_until = NOW() + INTERVAL '5 minutes',
                        started_at = NOW(),
                        updated_at = NOW()
                    FROM next_job
                    WHERE job_queue.id = next_job.id
                    RETURNING job_queue.*""",
                consumer_id, *([queues_param] if queues else []),
            )
            return self._row_to_job(row) if row else None
    
    # ── Status updates ──────────────────────────────────────
    
    async def complete(self, job_id: int, result: Any = None) -> None:
        """Mark job as completed."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """UPDATE job_queue
                   SET status = 'completed',
                       completed_at = NOW(),
                       consumer_id = NULL,
                       consumer_lock_until = NULL,
                       updated_at = NOW()
                   WHERE id = $1""",
                job_id,
            )
            # Check if any waiting jobs can be released
            await self._release_dependent_jobs(conn, job_id)
    
    async def fail(self, job_id: int, error: str = "", retry: bool = True) -> None:
        """Mark job as failed. Schedule retry if retries remain."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """UPDATE job_queue
                   SET retry_count = retry_count + 1,
                       last_error = $2,
                       status = CASE
                           WHEN retry_count + 1 <= max_retries THEN 'available'
                           ELSE 'failed'
                       END,
                       available_at = CASE
                           WHEN retry_count + 1 <= max_retries
                           THEN NOW() + (($3 * POWER(2, retry_count)) * INTERVAL '1 second')
                           ELSE available_at
                       END,
                       consumer_id = NULL,
                       consumer_lock_until = NULL,
                       updated_at = NOW()
                   WHERE id = $1
                   RETURNING *""",
                job_id, error, self._retry_delay_for_job(job_id),
            )
            if row and row["status"] == "failed":
                # Release dependent jobs so they can also fail fast
                await self._release_dependent_jobs(conn, job_id, failed=True)
    
    async def cancel(self, job_id: int) -> None:
        """Cancel a pending or running job."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """UPDATE job_queue
                   SET status = 'cancelled',
                       consumer_id = NULL,
                       consumer_lock_until = NULL,
                       updated_at = NOW()
                   WHERE id = $1 AND status IN ('pending', 'available', 'running')""",
                job_id,
            )
    
    async def heartbeat(self, consumer_id: str, job_ids: list[int]) -> None:
        """Extend consumer lock (called periodically by worker)."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """UPDATE job_queue
                   SET consumer_lock_until = NOW() + INTERVAL '5 minutes'
                   WHERE id = ANY($1::bigint[])
                     AND consumer_id = $2""",
                job_ids, consumer_id,
            )
    
    # ── Scheduling (recurring jobs) ─────────────────────────
    
    async def tick_scheduler(self) -> list[Job]:
        """Check all schedules and enqueue due jobs.
        
        Called by the scheduler ticker (every 60s).
        Returns newly enqueued jobs.
        """
        now = datetime.now(timezone.utc)
        new_jobs = []
        
        async with self._pool.acquire() as conn:
            due = await conn.fetch(
                """SELECT * FROM job_schedule
                   WHERE enabled AND NOT paused
                     AND next_run_at <= $1
                   ORDER BY next_run_at ASC
                   FOR UPDATE SKIP LOCKED""",
                now,
            )
            
            for schedule in due:
                # Enqueue the job
                job = await self.enqueue(
                    queue=schedule["queue"],
                    job_type=schedule["job_type"],
                    handler=schedule["handler"],
                    payload=dict(schedule["payload"]),
                    priority=schedule["priority"],
                    max_retries=schedule["max_retries"],
                    timeout_seconds=schedule["timeout_seconds"],
                )
                new_jobs.append(job)
                
                # Update schedule's last_run and next_run
                next_run = self._calc_next_run(
                    schedule["schedule_type"],
                    schedule["cron_expr"],
                    schedule["interval_seconds"],
                    now,
                )
                await conn.execute(
                    """UPDATE job_schedule
                       SET last_run_at = $2,
                           last_run_status = 'enqueued',
                           next_run_at = $3,
                           updated_at = NOW()
                       WHERE id = $1""",
                    schedule["id"], now, next_run,
                )
        
        return new_jobs
    
    # ── Chaining ────────────────────────────────────────────
    
    async def _release_dependent_jobs(
        self, conn, parent_job_id: int, failed: bool = False,
    ) -> None:
        """Release jobs waiting on a completed/failed parent."""
        if failed:
            # If parent failed, dependent jobs also fail
            await conn.execute(
                """UPDATE job_queue
                   SET status = 'failed',
                       last_error = 'Dependency failed (job #' || $1::text || ')',
                       updated_at = NOW()
                   WHERE $1 = ANY(depends_on)
                     AND status = 'pending'""",
                parent_job_id,
            )
        else:
            # Release jobs whose dependencies are all complete
            # (Complex: check all depends_on IDs are 'completed')
            await conn.execute(
                """UPDATE job_queue AS j
                   SET status = 'available',
                       available_at = NOW(),
                       updated_at = NOW()
                   WHERE $1 = ANY(j.depends_on)
                     AND j.status = 'pending'
                     AND NOT EXISTS (
                         SELECT 1 FROM job_queue AS dep
                         WHERE dep.id = ANY(j.depends_on)
                           AND dep.status != 'completed'
                     )""",
                parent_job_id,
            )
    
    # ── Utilities ───────────────────────────────────────────
    
    async def get_job(self, job_id: int) -> Job | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM job_queue WHERE id = $1", job_id
            )
            return self._row_to_job(row) if row else None
    
    async def list_jobs(
        self,
        queue: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Job]:
        """List jobs with optional filters."""
        conditions = []
        params = []
        if queue:
            conditions.append(f"queue = ${len(params) + 1}")
            params.append(queue)
        if status:
            conditions.append(f"status = ${len(params) + 1}")
            params.append(status)
        
        where = " AND ".join(conditions) if conditions else "TRUE"
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT * FROM job_queue WHERE {where} ORDER BY created_at DESC LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}",
                *params, limit, offset,
            )
            return [self._row_to_job(r) for r in rows]
    
    async def queue_stats(self) -> dict[str, int]:
        """Get queue depth by status."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT status, COUNT(*) as count
                   FROM job_queue GROUP BY status"""
            )
            return {row["status"]: row["count"] for row in rows}
    
    def _calc_next_run(
        self,
        schedule_type: str,
        cron_expr: str | None,
        interval_seconds: int | None,
        from_time: datetime,
    ) -> datetime:
        """Calculate the next run time given a schedule definition."""
        if schedule_type == "interval" and interval_seconds:
            return from_time + timedelta(seconds=interval_seconds)
        elif schedule_type == "cron" and cron_expr:
            # Use croniter for proper cron expression parsing
            from croniter import croniter
            cron = croniter(cron_expr, from_time)
            return cron.get_next(datetime)
        elif schedule_type == "daily":
            # Daily at specific time (e.g., "07:00")
            return from_time + timedelta(days=1)
        return from_time + timedelta(hours=1)
    
    def _row_to_job(self, row) -> Job | None:
        if not row:
            return None
        return Job(
            id=row["id"],
            queue=row["queue"],
            job_type=row["job_type"],
            handler=row["handler"],
            payload=row["payload"] if isinstance(row["payload"], dict) else json.loads(row["payload"]),
            status=row["status"],
            priority=row["priority"],
            scheduled_at=row["scheduled_at"],
            available_at=row["available_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            max_retries=row["max_retries"],
            retry_count=row["retry_count"],
            last_error=row.get("last_error"),
            depends_on=row.get("depends_on") or [],
            parent_job_id=row.get("parent_job_id"),
            consumer_id=row.get("consumer_id"),
            created_at=row["created_at"],
        )
```

### Worker Process

```python
"""
Worker daemon that dequeues and processes jobs.

Replaces: `aiw worker` (Huey consumer)
New:      `aiw worker start --concurrency 4`

Architecture:
  - Main process: scheduler ticker (every 60s) + HTTP health endpoint
  - Worker pool: N async workers, each running dequeue→process→complete loop
  - Job handlers are Python callables registered in a handler registry
"""

import asyncio
import logging
import signal
from typing import Any, Callable
from datetime import datetime, timezone

logger = logging.getLogger("aiw.worker")


# ── Handler Registry ────────────────────────────────────

_handlers: dict[str, Callable] = {}

def register_handler(job_type: str, fn: Callable):
    """Register a handler function for a job type.
    
    Usage:
        @register_handler("loop:daily-triage")
        async def handle_daily_triage(payload: dict) -> dict:
            ...
    """
    _handlers[job_type] = fn

def get_handler(job_type: str) -> Callable | None:
    return _handlers.get(job_type)


# ── Worker ──────────────────────────────────────────────

class Worker:
    """Dequeues jobs from PostgreSQL and dispatches to handlers.
    
    Usage:
        worker = Worker(dsn="postgresql:///ai_workspace")
        await worker.start(concurrency=4)
    """
    
    def __init__(self, dsn: str, consumer_id: str | None = None):
        self.queue = JobQueue(dsn)
        self.consumer_id = consumer_id or f"worker-{uuid.uuid4().hex[:8]}"
        self._running = False
        self._active_jobs: dict[int, asyncio.Task] = {}
    
    async def start(self, concurrency: int = 4):
        """Start the worker pool."""
        self._running = True
        await self.queue.connect()
        
        # Start scheduler ticker
        scheduler_task = asyncio.create_task(self._scheduler_loop())
        
        # Start worker pool
        workers = [
            asyncio.create_task(self._worker_loop(i))
            for i in range(concurrency)
        ]
        
        logger.info(
            "Worker %s started with %d concurrent slots",
            self.consumer_id, concurrency,
        )
        
        # Wait for shutdown
        await asyncio.gather(scheduler_task, *workers)
    
    async def _worker_loop(self, worker_id: int):
        """Single worker: dequeue → process → repeat."""
        while self._running:
            try:
                job = await self.queue.dequeue(
                    consumer_id=f"{self.consumer_id}-{worker_id}",
                    queues=["default", "loops", "workflows", "scheduled"],
                )
                
                if job is None:
                    await asyncio.sleep(1)
                    continue
                
                # Process in a task so heartbeat can run concurrently
                task = asyncio.create_task(self._process_job(job))
                self._active_jobs[job.id] = task
                task.add_done_callback(lambda _, jid=job.id: self._active_jobs.pop(jid, None))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Worker loop error")
                await asyncio.sleep(5)
    
    async def _process_job(self, job: Job):
        """Process a single job with timeout."""
        handler = get_handler(job.job_type)
        if handler is None:
            await self.queue.fail(job.id, f"No handler for {job.job_type}")
            return
        
        try:
            result = await asyncio.wait_for(
                handler(job.payload),
                timeout=job.timeout_seconds,
            )
            await self.queue.complete(job.id, result)
            logger.info("Job %d (%s) completed", job.id, job.job_type)
        except asyncio.TimeoutError:
            await self.queue.fail(job.id, "Timeout", retry=True)
            logger.warning("Job %d (%s) timed out", job.id, job.job_type)
        except Exception as e:
            await self.queue.fail(job.id, str(e), retry=True)
            logger.error("Job %d (%s) failed: %s", job.id, job.job_type, e)
    
    async def _scheduler_loop(self):
        """Tick the scheduler every 60 seconds."""
        while self._running:
            try:
                jobs = await self.queue.tick_scheduler()
                if jobs:
                    logger.info("Scheduler enqueued %d jobs", len(jobs))
            except Exception as e:
                logger.error("Scheduler tick failed: %s", e)
            await asyncio.sleep(60)
    
    async def stop(self):
        """Graceful shutdown."""
        self._running = False
        # Cancel active jobs
        for task in self._active_jobs.values():
            task.cancel()
        await self.queue.close()
```

---

## 📐 Part 2: Enhanced Workflow Engine

The existing `engine.py` already has `BaseWorkflow`, `@step`, `WorkflowRegistry`, topological sort, retries, and PostgreSQL persistence.  What it needs:

### Enhancements

```python
# New features added to BaseWorkflow:

class BaseWorkflow:
    # 1. Job queue integration — workflows are enqueued as jobs
    #    The queue fires the workflow, not a manual CLI call.
    
    # 2. DAG visualization data — expose structure for web UI
    def get_dag_structure(self) -> dict:
        """Return the DAG as {nodes: [...], edges: [...]}.
        
        Each node: {id, label, status, duration_ms, error, output_preview}
        Each edge: {source, target}
        
        Used by the web UI to render the DAG graph.
        """
        deps = self._infer_dependencies()
        levels = self._topological_sort(deps)
        steps = self._get_step_methods()
        
        nodes = []
        for step_name in steps:
            method = getattr(self, step_name)
            doc = method.__doc__ or ""
            nodes.append({
                "id": step_name,
                "label": step_name.removeprefix("step_").replace("_", " ").title(),
                "description": doc.strip()[:200],
            })
        
        edges = []
        for step, depends in deps.items():
            for dep in depends:
                edges.append({"source": dep, "target": step})
        
        return {"nodes": nodes, "edges": edges}
    
    # 3. Step-level output references — steps can read outputs
    #    from completed steps by name (not just ctx.get())
    #    Already works via ctx.get(step_name).
    
    # 4. Webhook triggers — workflows can be triggered by
    #    external events (GitHub webhook, Slack command)
    
    # 5. Parallel sub-workflows — a step can spawn sub-workflows
    #    and wait for them to complete (fan-out)
```

### Workflow → Job Queue Integration

```python
# When a workflow is triggered via the queue:
@register_handler("workflow:run")
async def handle_workflow_run(payload: dict) -> dict:
    """Handler for workflow job type."""
    wf_name = payload["workflow_name"]
    inputs = payload.get("inputs", {})
    db_url = payload.get("db_url")
    
    wf_cls = WorkflowRegistry.get(wf_name)
    if not wf_cls:
        raise ValueError(f"Unknown workflow: {wf_name}")
    
    wf = wf_cls(db_url=db_url)
    
    # Run and return results (stored as job result)
    result = await wf.run(**inputs)
    return {
        "run_id": result.run_id,
        "status": result.status.value,
        "steps": {
            name: {
                "status": s.status.value,
                "duration_ms": s.duration_ms,
                "error": s.error,
            }
            for name, s in result.steps.items()
        },
    }
```

---

## 📐 Part 3: Visual Work Engine (Web UI)

### REST API (FastAPI routes)

```
GET    /api/v1/queue/stats              — Queue depth by status
GET    /api/v1/queue/jobs               — List jobs (?queue=&status=&limit=)
GET    /api/v1/queue/jobs/:id           — Job detail
POST   /api/v1/queue/jobs              — Enqueue new job
POST   /api/v1/queue/jobs/:id/cancel   — Cancel job
POST   /api/v1/queue/jobs/:id/retry    — Retry failed job

GET    /api/v1/schedules                — List schedules
POST   /api/v1/schedules               — Create schedule
PUT    /api/v1/schedules/:id            — Update schedule
POST   /api/v1/schedules/:id/pause     — Pause schedule
POST   /api/v1/schedules/:id/resume    — Resume schedule
POST   /api/v1/schedules/:id/trigger   — Trigger immediate run

GET    /api/v1/workflows                — List registered workflows
GET    /api/v1/workflows/:name          — Workflow detail + DAG structure
POST   /api/v1/workflows/:name/run     — Trigger workflow run
GET    /api/v1/workflows/runs           — List workflow runs
GET    /api/v1/workflows/runs/:id       — Run detail + step status
POST   /api/v1/workflows/runs/:id/retry — Retry failed run

GET    /api/v1/loops                    — List loop patterns (from loop_state)
GET    /api/v1/loops/:id                — Loop detail + state
POST   /api/v1/loops/:id/enable        — Enable at level
POST   /api/v1/loops/:id/disable       — Disable
POST   /api/v1/loops/:id/run           — Trigger immediate run
```

### Web UI Pages

```
┌─────────────────────────────────────────────────────┐
│  ⚡ aiw Work Engine                                   │
│  ┌─────┬──────┬────────┬──────┬────────────┐        │
│  │Queue│Workflows│Loops│Schedules│  History   │        │
│  └─────┴──────┴────────┴──────┴────────────┘        │
│                                                       │
│  ┌─ Queue Dashboard ─────────────────────────────┐   │
│  │  ● running: 3    ● pending: 12   ● failed: 1   │   │
│  │  ● scheduled: 5  ● completed: 342 (today)     │   │
│  │                                                │   │
│  │  ┌──────┬────────┬─────────┬──────┬────────┐  │   │
│  │  │ ID   │ Type   │ Status  │ Queue│ Age    │  │   │
│  │  ├──────┼────────┼─────────┼──────┼────────┤  │   │
│  │  │ 1423 │ loop:  │ ● runn. │ loops│ 2m    │  │   │
│  │  │ 1422 │ wf:    │ ● runn. │ wf   │ 5m    │  │   │
│  │  │ 1421 │ loop:  │ ○ pend. │ loops│ 1s    │  │   │
│  │  │ 1420 │ task   │ ✕ failed│ def  │ 10m   │  │   │
│  │  └──────┴────────┴─────────┴──────┴────────┘  │   │
│  └────────────────────────────────────────────────┘   │
│                                                       │
│  ┌─ Workflow: Deep Research (run #87) ───────────┐   │
│  │                                                │   │
│  │  ╭─────────╮                                   │   │
│  │  │  Plan   │  ✅ 2.3s                          │   │
│  │  ╰────┬────╯                                   │   │
│  │       │                                         │   │
│  │  ┌────┼────┐                                   │   │
│  │  ▼    ▼    ▼                                   │   │
│  │ ╭───╮ ╭───╮ ╭───╮                             │   │
│  │ │ A │ │ B │ │ C │  ✅ All parallel 1.5s       │   │
│  │ ╰──┬╯ ╰──┬╯ ╰──┬╯                             │   │
│  │    │     │     │                                │   │
│  │    ▼     ▼     │                                │   │
│  │ ╭────╮ ╭────╮ │                                │   │
│  │ │ D  │ │ E  │◄╯  ● running (12s)              │   │
│  │ ╰──┬─╯ ╰────╯                                  │   │
│  │    │                                            │   │
│  │    ▼                                            │   │
│  │ ╭─────╮                                         │   │
│  │ │  F  │  ◌ pending                              │   │
│  │ ╰─────╯                                         │   │
│  │                                                │   │
│  │ [Retry Step D] [Cancel] [View Logs]           │   │
│  └────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### React Component Tree

```
<WorkEngine>
  <Sidebar>
    <QueueStats />          — depth by status, with sparklines
    <SchedulerList />       — recurring schedules, on/off toggle
  </Sidebar>
  <MainPanel>
    <TabBar tabs={[Queue, Workflows, Loops, History]} />
    <Routes>
      <QueueDashboard>
        <JobFilter />         — queue, status, type, date range
        <JobTable />          — sortable, with action buttons
        <JobDetail />         — payload, retries, error, logs
      </QueueDashboard>
      <WorkflowView>
        <WorkflowSelector />  — pick from registered workflows
        <DAGGraph />          — react-flow DAG visualization
        <StepDetail />        — click node → step info
        <RunControls />       — retry, cancel, re-run
      </WorkflowView>
      <LoopsView>
        <LoopCard />          — per-pattern status card
        <LoopState />         — active/watch items
        <LoopControls />      — run, pause, level change
      </LoopsView>
      <History>
        <Timeline />          — chronological run log
        <RunDetail />         — job + workflow + loop all in one
      </History>
    </Routes>
  </MainPanel>
</WorkEngine>
```

---

## 🔗 Integration: Four Systems as One

```
┌─────────────────────────────────────────────────────────────┐
│                    Web UI (Single Page)                       │
│  Shows: queue depth, workflow DAGs, loop states, run logs    │
│  Controls: retry, cancel, pause, trigger, schedule            │
└─────────────────────┬───────────────────────────────────────┘
                      │ REST API
┌─────────────────────┴───────────────────────────────────────┐
│                  Unified Service Layer                        │
│                                                               │
│  JobQueue          Scheduler         WorkflowEngine           │
│  ┌──────────────┐  ┌─────────────┐  ┌────────────────────┐  │
│  │ SKIP LOCKED  │  │ tick_sched  │  │ BaseWorkflow       │  │
│  │ enqueue/deq  │  │ → enqueue   │  │ @step, topo sort   │  │
│  │ complete/fail│  │ recurring   │  │ run, retry         │  │
│  │ chaining     │  │ jobs        │  │ get_dag_structure  │  │
│  │ heartbeat    │  │             │  │                    │  │
│  └──────┬───────┘  └──────┬──────┘  └────────┬───────────┘  │
└─────────┼─────────────────┼───────────────────┼────────────┘
          │                 │                   │
          ▼                 ▼                   ▼
    ┌──────────────────────────────────────────────────────┐
    │                   PostgreSQL                            │
    │  job_queue | job_schedule | workflow_runs | loop_state │
    │  worktree_registry | loop_patterns | loop_run_log     │
    └──────────────────────────────────────────────────────┘
```

**Key integration points:**

1. **Loop patterns** register their run function as a handler, and create a recurring schedule via `enqueue_recurring()`
2. **Workflows** are triggered by enqueuing a `workflow:run` job — the handler calls `BaseWorkflow.run()`
3. **Worktree operations** are tracked in `worktree_registry` alongside the job that created them
4. **Everything is visible** in the web UI via the same REST API

---

## ⚡ CLI Interface

```bash
# Queue
aiw queue list
aiw queue list --queue loops --status running
aiw queue stats
aiw queue inspect 1423        # show full job detail
aiw queue cancel 1423
aiw queue retry 1423

# Scheduler
aiw schedule list
aiw schedule show daily-triage
aiw schedule pause daily-triage
aiw schedule resume daily-triage
aiw schedule trigger daily-triage   # immediate run

# Worker
aiw worker start --concurrency 4
aiw worker status                # running jobs, uptime
aiw worker stop

# Web UI
aiw web start --port 3000        # start the visual work engine
aiw web open                      # open in browser
```

---

## ✅ Acceptance Criteria

### Job Queue
- [ ] `job_queue` table with SKIP LOCKED dequeue
- [ ] `job_schedule` table for recurring schedules (cron + interval)
- [ ] `JobQueue` Python class with `enqueue`, `dequeue`, `complete`, `fail`, `cancel`, `heartbeat`
- [ ] `tick_scheduler()` enqueues due recurring jobs
- [ ] Job chaining via `depends_on` — jobs wait for dependencies
- [ ] Retry with exponential backoff, max retries
- [ ] Concurrent consumers via SKIP LOCKED (no double-processing)
- [ ] Worker process with configurable concurrency
- [ ] Handler registry (`@register_handler`)
- [ ] Graceful shutdown (SIGTERM → cancel active jobs)
- [ ] `aiw queue list/stats/inspect/cancel/retry` commands
- [ ] `aiw schedule list/show/pause/resume/trigger` commands
- [ ] `aiw worker start/status/stop` commands

### Workflow Engine Enhancements
- [ ] `get_dag_structure()` returns {nodes, edges} for visualization
- [ ] Workflows are triggerable via job queue
- [ ] Workflow steps log structured output for web UI

### Visual Web UI
- [ ] FastAPI REST API with all endpoints
- [ ] Queue dashboard showing depth, jobs, controls
- [ ] DAG visualization using react-flow or cytoscape
- [ ] Per-workflow run history with step details
- [ ] Loop state view (active/watch items per pattern)
- [ ] Schedule management (create, pause, trigger)
- [ ] Real-time updates (WebSocket or polling)
- [ ] `aiw web start --port` command
- [ ] Responsive layout, dark mode

---

## 📚 References

- [PGMQ](https://github.com/tembo-io/pgmq) — PostgreSQL message queue (SKIP LOCKED pattern)
- [pg_boss](https://github.com/timgit/pg-boss) — job queue for Node.js on PostgreSQL
- [graphile-worker](https://github.com/graphile/worker) — PostgreSQL job queue, very fast
- [Prefect](https://github.com/PrefectHQ/prefect) — Python workflow engine with web UI
- [Dagster](https://github.com/dagster-io/dagster) — asset-oriented orchestrator
- [Temporal](https://github.com/temporalio/temporal) — durable execution (architecture reference)
- [SQLMesh](https://github.com/SQLMesh/sqlmesh) — DAG-based data transformation, plan/apply cycle
- [Windmill](https://github.com/windmill-labs/windmill) — low-code workflow engine
- [react-flow](https://reactflow.dev/) — DAG visualization component
- SPEC_LOOP_PATTERNS.md — loop scheduling uses this queue
- SPEC_WORKTREE_MANAGER.md — worktree lifecycle tracked alongside jobs
