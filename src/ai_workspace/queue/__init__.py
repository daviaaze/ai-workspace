"""
Job Queue — PostgreSQL-backed task queue with SKIP LOCKED.

Replaces Huey SQLite. Provides:
- Concurrent consumer safety via SELECT … FOR UPDATE SKIP LOCKED
- Job chaining (depends_on)
- Retry with exponential backoff
- Recurring schedules (cron + interval)
- Full lifecycle visibility

Usage:
    from ai_workspace.queue import JobQueue

    # DSN from environment or default (set AIW_DB_URL env var)
    queue = JobQueue()
    await queue.connect()

    job = await queue.enqueue(
        queue="loops",
        job_type="loop:daily-triage",
        handler="ai_workspace.loops.handle_daily_triage",
        payload={"project_root": "/home/user/project"},
    )

    # In worker:
    job = await queue.dequeue(consumer_id="worker-1")
    if job:
        try:
            result = await handle(job)
            await queue.complete(job.id, result)
        except Exception as e:
            await queue.fail(job.id, str(e))
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

try:
    from croniter import croniter
    HAS_CRONITER = True
except ImportError:
    HAS_CRONITER = False

import asyncpg

# ── Data types ────────────────────────────────────────────


@dataclass
class Job:
    """A single job in the queue."""
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
    timeout_seconds: int
    max_retries: int
    retry_count: int
    retry_delay_seconds: int
    last_error: str | None
    depends_on: list[int]
    parent_job_id: int | None
    consumer_id: str | None
    consumer_lock_until: datetime | None
    result: Any
    created_at: datetime
    updated_at: datetime


@dataclass
class Schedule:
    """A recurring schedule definition."""
    id: int
    name: str
    job_type: str
    handler: str
    payload: dict
    queue: str
    schedule_type: str
    cron_expr: str | None
    interval_seconds: int | None
    max_retries: int
    timeout_seconds: int
    priority: int
    enabled: bool
    paused: bool
    paused_reason: str | None
    last_run_at: datetime | None
    last_run_status: str | None
    next_run_at: datetime | None
    created_at: datetime
    updated_at: datetime


# ── Handler Registry ────────────────────────────────────

_handlers: dict[str, Callable] = {}


def register_handler(job_type: str):
    """Decorator: register a handler function for a job type.

    Usage:
        @register_handler("loop:daily-triage")
        async def handle_daily_triage(payload: dict) -> dict:
            ...
    """
    def decorator(fn: Callable):
        _handlers[job_type] = fn
        return fn
    return decorator


def get_handler(job_type: str) -> Callable | None:
    return _handlers.get(job_type)


# ── Job Queue ────────────────────────────────────────────


class JobQueue:
    """PostgreSQL-backed job queue using SKIP LOCKED.

    Thread-safe for multiple consumers via PostgreSQL row-level locking.
    """

    def __init__(self, dsn: str = "postgresql:///ai_workspace"):
        self.dsn = dsn
        self._pool: asyncpg.Pool | None = None

    async def connect(self):
        """Create connection pool."""
        self._pool = await asyncpg.create_pool(
            self.dsn,
            min_size=2,
            max_size=10,
            command_timeout=30,
        )

    async def close(self):
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    # ── Enqueue ───────────────────────────────────────────

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
        """Enqueue a new job.

        Args:
            queue: Queue name ('default', 'loops', 'workflows', 'scheduled')
            job_type: Handler type for routing (e.g. 'loop:daily-triage')
            handler: Python dotted path to handler function
            payload: JSON-serializable data for the handler
            priority: Higher = processed first
            scheduled_at: Don't make available before this time
            available_at: Override for when job becomes available
            max_retries: Max retry attempts on failure
            retry_delay_seconds: Base delay before retry (exponential backoff)
            timeout_seconds: Max execution time before considered failed
            depends_on: List of job IDs that must complete first
            parent_job_id: If this is a sub-job of another job
        """
        now = datetime.now(UTC)
        sched = scheduled_at or now
        avail = available_at or sched

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO job_queue
                   (queue, job_type, handler, payload, priority,
                    scheduled_at, available_at, max_retries,
                    retry_delay_seconds, timeout_seconds,
                    depends_on, parent_job_id)
                   VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9, $10, $11, $12)
                   RETURNING *""",
                queue, job_type, handler,
                json.dumps(payload or {}),
                priority, sched, avail,
                max_retries, retry_delay_seconds, timeout_seconds,
                depends_on or [], parent_job_id,
            )
            return self._row_to_job(row)

    # ── Dequeue (SKIP LOCKED) ─────────────────────────────

    async def dequeue(
        self,
        consumer_id: str,
        queues: list[str] | None = None,
    ) -> Job | None:
        """Atomically claim the next available job.

        Uses SELECT … FOR UPDATE SKIP LOCKED so multiple workers
        can dequeue concurrently without conflicts.

        Args:
            consumer_id: Unique identifier for this worker
            queues: If set, only dequeue from these queues

        Returns:
            Job if one was available, None otherwise
        """
        queue_filter = "AND queue = ANY($2::varchar[])" if queues else ""
        params: list = [consumer_id]
        if queues:
            params.append(queues)

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                WITH next_job AS (
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
                RETURNING job_queue.*
                """,
                *params,
            )
            return self._row_to_job(row) if row else None

    # ── Status updates ─────────────────────────────────────

    async def complete(self, job_id: int, result: Any = None) -> None:
        """Mark job as completed. Releases dependent jobs."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """UPDATE job_queue
                   SET status = 'completed',
                       completed_at = NOW(),
                       consumer_id = NULL,
                       consumer_lock_until = NULL,
                       result = $2::jsonb,
                       updated_at = NOW()
                   WHERE id = $1""",
                job_id,
                json.dumps(result) if result is not None else None,
            )
            await self._release_dependents(conn, job_id)

    async def fail(
        self,
        job_id: int,
        error: str = "",
        retry: bool = True,
    ) -> None:
        """Mark job as failed. Schedules retry if retries remain.

        Args:
            job_id: Job to fail
            error: Error description
            retry: If True, retry up to max_retries. If False, fail immediately.
        """
        async with self._pool.acquire() as conn:
            # Get current retry info
            current = await conn.fetchrow(
                "SELECT retry_count, max_retries, retry_delay_seconds FROM job_queue WHERE id = $1",
                job_id,
            )
            if not current:
                return

            max_retries = current["max_retries"]
            delay = current["retry_delay_seconds"]

            if retry and current["retry_count"] < max_retries:
                retry_count = current["retry_count"] + 1
                # Exponential backoff: delay * 2^attempt
                backoff = delay * (2 ** (retry_count - 1))
                await conn.execute(
                    """UPDATE job_queue
                       SET retry_count = $2,
                           last_error = $3,
                           status = 'available',
                           available_at = NOW() + ($4 * INTERVAL '1 second'),
                           consumer_id = NULL,
                           consumer_lock_until = NULL,
                           updated_at = NOW()
                       WHERE id = $1""",
                    job_id, retry_count, error, backoff,
                )
            else:
                await conn.execute(
                    """UPDATE job_queue
                       SET last_error = $2,
                           status = 'failed',
                           completed_at = NOW(),
                           consumer_id = NULL,
                           consumer_lock_until = NULL,
                           updated_at = NOW()
                       WHERE id = $1""",
                    job_id, error,
                )
                # Fail dependent jobs
                await self._release_dependents(conn, job_id, failed=True)

    async def cancel(self, job_id: int) -> bool:
        """Cancel a pending, scheduled, or running job.

        Returns:
            True if cancelled, False if job was already in terminal state
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """UPDATE job_queue
                   SET status = 'cancelled',
                       consumer_id = NULL,
                       consumer_lock_until = NULL,
                       completed_at = NOW(),
                       updated_at = NOW()
                   WHERE id = $1
                     AND status IN ('pending', 'scheduled', 'available', 'running')""",
                job_id,
            )
            return result == "UPDATE 1"

    async def heartbeat(self, consumer_id: str, job_ids: list[int]) -> None:
        """Extend consumer lock for active jobs.

        Called periodically by the worker to prevent lock expiry
        while a job is still processing.
        """
        if not job_ids:
            return
        async with self._pool.acquire() as conn:
            await conn.execute(
                """UPDATE job_queue
                   SET consumer_lock_until = NOW() + INTERVAL '5 minutes'
                   WHERE id = ANY($1::bigint[])
                     AND consumer_id = $2""",
                job_ids, consumer_id,
            )

    # ── Recurring schedules ────────────────────────────────

    async def schedule_recurring(
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
    ) -> Schedule:
        """Register or update a recurring schedule.

        Args:
            name: Unique schedule name (e.g. 'daily-triage')
            schedule_type: 'cron', 'interval', 'daily', 'hourly'
            cron_expr: Cron expression (for 'cron' type)
            interval_seconds: Interval in seconds (for 'interval' type)
        """
        now = datetime.now(UTC)
        next_run = self._calc_next_run(schedule_type, cron_expr, interval_seconds, now)

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO job_schedule
                   (name, job_type, handler, payload, queue,
                    schedule_type, cron_expr, interval_seconds,
                    max_retries, timeout_seconds, priority,
                    next_run_at)
                   VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9, $10, $11, $12)
                   ON CONFLICT (name) DO UPDATE SET
                     handler = EXCLUDED.handler,
                     payload = EXCLUDED.payload,
                     schedule_type = EXCLUDED.schedule_type,
                     cron_expr = EXCLUDED.cron_expr,
                     interval_seconds = EXCLUDED.interval_seconds,
                     max_retries = EXCLUDED.max_retries,
                     timeout_seconds = EXCLUDED.timeout_seconds,
                     priority = EXCLUDED.priority,
                     enabled = TRUE,
                     paused = FALSE,
                     next_run_at = EXCLUDED.next_run_at,
                     updated_at = NOW()
                   RETURNING *""",
                name, job_type, handler,
                json.dumps(payload or {}),
                queue,
                schedule_type, cron_expr, interval_seconds,
                max_retries, timeout_seconds, priority,
                next_run,
            )
            return self._row_to_schedule(row)

    async def tick_scheduler(self) -> list[Job]:
        """Check all schedules and enqueue due jobs.

        Called by the scheduler ticker (every 60s). Returns newly
        enqueued jobs.

        Uses SKIP LOCKED so only one worker processes each schedule.
        """
        now = datetime.now(UTC)
        new_jobs: list[Job] = []

        async with self._pool.acquire() as conn:
            due = await conn.fetch(
                """SELECT * FROM job_schedule
                   WHERE enabled AND NOT paused
                     AND next_run_at <= $1
                   ORDER BY next_run_at ASC
                   FOR UPDATE SKIP LOCKED""",
                now,
            )

            for sched in due:
                # Enqueue a job for this schedule
                job = await self.enqueue(
                    queue=sched["queue"],
                    job_type=sched["job_type"],
                    handler=sched["handler"],
                    payload=dict(sched["payload"]) if sched["payload"] else {},
                    priority=sched["priority"],
                    max_retries=sched["max_retries"],
                    timeout_seconds=sched["timeout_seconds"],
                )
                new_jobs.append(job)

                # Calculate next run
                next_run = self._calc_next_run(
                    sched["schedule_type"],
                    sched["cron_expr"],
                    sched["interval_seconds"],
                    now,
                )
                await conn.execute(
                    """UPDATE job_schedule
                       SET last_run_at = $2,
                           last_run_status = 'enqueued',
                           next_run_at = $3,
                           updated_at = NOW()
                       WHERE id = $1""",
                    sched["id"], now, next_run,
                )

        return new_jobs

    # ── Schedule management ────────────────────────────────

    async def list_schedules(self) -> list[Schedule]:
        """List all registered schedules."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM job_schedule ORDER BY name"
            )
            return [self._row_to_schedule(r) for r in rows]

    async def get_schedule(self, name: str) -> Schedule | None:
        """Get a schedule by name."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM job_schedule WHERE name = $1", name
            )
            return self._row_to_schedule(row) if row else None

    async def pause_schedule(self, name: str, reason: str = "") -> bool:
        """Pause a recurring schedule."""
        async with self._pool.acquire() as conn:
            r = await conn.execute(
                "UPDATE job_schedule SET paused = TRUE, paused_reason = $2, updated_at = NOW() WHERE name = $1",
                name, reason,
            )
            return r == "UPDATE 1"

    async def resume_schedule(self, name: str) -> bool:
        """Resume a paused schedule."""
        async with self._pool.acquire() as conn:
            r = await conn.execute(
                "UPDATE job_schedule SET paused = FALSE, paused_reason = NULL, updated_at = NOW() WHERE name = $1",
                name,
            )
            return r == "UPDATE 1"

    async def trigger_schedule(self, name: str) -> Job | None:
        """Trigger an immediate run of a schedule (outside normal cadence)."""
        sched = await self.get_schedule(name)
        if not sched:
            return None
        return await self.enqueue(
            queue=sched.queue,
            job_type=sched.job_type,
            handler=sched.handler,
            payload=dict(sched.payload) if sched.payload else {},
            priority=99,  # high priority for manual triggers
            max_retries=sched.max_retries,
            timeout_seconds=sched.timeout_seconds,
        )

    # ── Query ──────────────────────────────────────────────

    async def get_job(self, job_id: int) -> Job | None:
        """Get a single job by ID."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM job_queue WHERE id = $1", job_id
            )
            return self._row_to_job(row) if row else None

    async def list_jobs(
        self,
        queue: str | None = None,
        status: str | None = None,
        job_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Job]:
        """List jobs with optional filters."""
        conditions = ["TRUE"]
        params: list = []
        idx = 1

        if queue:
            conditions.append(f"queue = ${idx}")
            params.append(queue)
            idx += 1
        if status:
            conditions.append(f"status = ${idx}")
            params.append(status)
            idx += 1
        if job_type:
            conditions.append(f"job_type = ${idx}")
            params.append(job_type)
            idx += 1

        where = " AND ".join(conditions)

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT * FROM job_queue WHERE {where} ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}",
                *params, limit, offset,
            )
            return [self._row_to_job(r) for r in rows]

    async def queue_stats(self) -> dict[str, int]:
        """Get queue depth by status."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT status, COUNT(*)::int as count FROM job_queue GROUP BY status"
            )
            stats = {r["status"]: r["count"] for r in rows}
            for s in ("pending", "scheduled", "available", "running", "completed", "failed", "cancelled"):
                stats.setdefault(s, 0)
            return stats

    async def retry_job(self, job_id: int) -> bool:
        """Manually retry a failed job. Resets retry count."""
        async with self._pool.acquire() as conn:
            r = await conn.execute(
                """UPDATE job_queue
                   SET status = 'available',
                       retry_count = 0,
                       last_error = NULL,
                       available_at = NOW(),
                       consumer_id = NULL,
                       updated_at = NOW()
                   WHERE id = $1 AND status = 'failed'""",
                job_id,
            )
            return r == "UPDATE 1"

    # ── Internal ───────────────────────────────────────────

    async def _release_dependents(
        self,
        conn: asyncpg.Connection,
        parent_job_id: int,
        failed: bool = False,
    ) -> None:
        """Release or fail jobs waiting on a completed/failed parent."""
        if failed:
            await conn.execute(
                """UPDATE job_queue
                   SET status = 'failed',
                       last_error = 'Dependency failed (job #' || $1::text || ')',
                       updated_at = NOW()
                   WHERE $1 = ANY(depends_on) AND status = 'pending'""",
                parent_job_id,
            )
        else:
            # Release jobs whose all dependencies are complete
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

    def _calc_next_run(
        self,
        schedule_type: str,
        cron_expr: str | None,
        interval_seconds: int | None,
        from_time: datetime,
    ) -> datetime:
        """Calculate the next run time."""
        if schedule_type == "interval" and interval_seconds:
            return from_time + timedelta(seconds=interval_seconds)
        elif schedule_type == "cron" and cron_expr:
            if HAS_CRONITER:
                cron = croniter(cron_expr, from_time)
                return cron.get_next(datetime)
        elif schedule_type == "daily":
            return from_time + timedelta(days=1)
        elif schedule_type == "hourly":
            return from_time + timedelta(hours=1)
        return from_time + timedelta(hours=1)

    def _row_to_job(self, row: asyncpg.Record | None) -> Job | None:
        if row is None:
            return None
        return Job(
            id=row["id"],
            queue=row["queue"],
            job_type=row["job_type"],
            handler=row["handler"],
            payload=row["payload"] if isinstance(row["payload"], dict) else {},
            status=row["status"],
            priority=row["priority"],
            scheduled_at=row["scheduled_at"],
            available_at=row["available_at"],
            started_at=row.get("started_at"),
            completed_at=row.get("completed_at"),
            timeout_seconds=row["timeout_seconds"],
            max_retries=row["max_retries"],
            retry_count=row["retry_count"],
            retry_delay_seconds=row["retry_delay_seconds"],
            last_error=row.get("last_error"),
            depends_on=row.get("depends_on") or [],
            parent_job_id=row.get("parent_job_id"),
            consumer_id=row.get("consumer_id"),
            consumer_lock_until=row.get("consumer_lock_until"),
            result=row.get("result"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _row_to_schedule(self, row: asyncpg.Record | None) -> Schedule | None:
        if row is None:
            return None
        return Schedule(
            id=row["id"],
            name=row["name"],
            job_type=row["job_type"],
            handler=row["handler"],
            payload=row["payload"] if isinstance(row["payload"], dict) else {},
            queue=row["queue"],
            schedule_type=row["schedule_type"],
            cron_expr=row.get("cron_expr"),
            interval_seconds=row.get("interval_seconds"),
            max_retries=row["max_retries"],
            timeout_seconds=row["timeout_seconds"],
            priority=row["priority"],
            enabled=row["enabled"],
            paused=row["paused"],
            paused_reason=row.get("paused_reason"),
            last_run_at=row.get("last_run_at"),
            last_run_status=row.get("last_run_status"),
            next_run_at=row.get("next_run_at"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


# ── Convenience ──────────────────────────────────────────

_default_queue: JobQueue | None = None


async def get_queue(dsn: str | None = None) -> JobQueue:
    """Get or create the default JobQueue singleton."""
    global _default_queue
    if _default_queue is None:
        from ai_workspace.core.db import get_db_url
        _default_queue = JobQueue(dsn or get_db_url())
        await _default_queue.connect()
    return _default_queue
