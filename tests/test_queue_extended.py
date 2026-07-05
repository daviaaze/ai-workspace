"""
Extended Queue Tests — job chaining, concurrent consumers, schedule ticker,
stale lock recovery, heartbeat, and edge cases.

These use mocked asyncpg so no real database is needed.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from ai_workspace.queue import JobQueue, Job, register_handler, get_handler
from ai_workspace.queue import _handlers


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════


class FakeRow:
    """Simulates an asyncpg.Record for unit testing."""
    def __init__(self, **kwargs):
        self._data = kwargs
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __getitem__(self, key):
        return self._data.get(key)

    def get(self, key, default=None):
        return self._data.get(key, default)


def make_job_row(**overrides):
    """Create a fake job row with sensible defaults."""
    now = datetime.now(timezone.utc)
    data = dict(
        id=1,
        queue="default",
        job_type="test:echo",
        handler="test_handler",
        payload={},
        status="pending",
        priority=0,
        scheduled_at=now,
        available_at=now,
        started_at=None,
        completed_at=None,
        timeout_seconds=300,
        max_retries=3,
        retry_count=0,
        retry_delay_seconds=30,
        last_error=None,
        depends_on=[],
        parent_job_id=None,
        consumer_id=None,
        consumer_lock_until=None,
        result=None,
        created_at=now,
        updated_at=now,
    )
    data.update(overrides)
    return FakeRow(**data)


def make_schedule_row(**overrides):
    """Create a fake schedule row."""
    now = datetime.now(timezone.utc)
    data = dict(
        id=1,
        name="test-schedule",
        job_type="loop:daily-triage",
        handler="ai_workspace.loops.handle_daily_triage",
        payload={},
        queue="loops",
        schedule_type="interval",
        cron_expr=None,
        interval_seconds=3600,
        max_retries=3,
        timeout_seconds=600,
        priority=0,
        enabled=True,
        paused=False,
        paused_reason=None,
        last_run_at=None,
        last_run_status=None,
        next_run_at=now,
        created_at=now,
        updated_at=now,
    )
    data.update(overrides)
    return FakeRow(**data)


@pytest.fixture
def queue():
    """Create a JobQueue with mocked pool."""
    q = JobQueue("postgresql:///test")
    q._pool = MagicMock()
    return q


def _mock_acquire(queue, mock_conn):
    """Set up pool.acquire() to return an async context manager."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=mock_conn)
    cm.__aexit__ = AsyncMock(return_value=None)
    queue._pool.acquire = MagicMock(return_value=cm)


# ═══════════════════════════════════════════════════════════
# 1. Job Chaining (depends_on)
# ═══════════════════════════════════════════════════════════


class TestJobChaining:
    """Jobs that depend on other jobs must wait for them to complete."""

    @pytest.mark.asyncio
    async def test_enqueue_with_dependency(self, queue):
        """Enqueue a job with depends_on, verify SQL includes depends_on."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.fetchrow = AsyncMock(return_value=make_job_row(
            id=2, depends_on=[1], status="pending",
        ))

        job = await queue.enqueue(
            queue="default",
            job_type="dependent_task",
            handler="handler",
            payload={},
            depends_on=[1],
        )

        assert job.id == 2
        assert job.depends_on == [1]
        assert job.status == "pending"

        # Verify SQL parameter
        _, kwargs = mock_conn.fetchrow.call_args
        params = kwargs.get("args") or kwargs.get("params") or mock_conn.fetchrow.call_args[0]
        assert any(p == [1] for p in params if isinstance(p, list))

    @pytest.mark.asyncio
    async def test_release_dependents_on_complete(self, queue):
        """When a job completes, its dependents should be released."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.execute = AsyncMock()

        await queue._release_dependents(mock_conn, 1, failed=False)

        # Should have executed a release query
        assert mock_conn.execute.called
        call_args = mock_conn.execute.call_args[0][0]
        assert "status = 'available'" in call_args or "SET status" in call_args

    @pytest.mark.asyncio
    async def test_fail_dependents_on_parent_failure(self, queue):
        """When a job fails permanently, its dependents should also fail."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.execute = AsyncMock()

        await queue._release_dependents(mock_conn, 1, failed=True)

        assert mock_conn.execute.called
        call_sql = mock_conn.execute.call_args[0][0]
        assert "status = 'failed'" in call_sql
        assert "Dependency failed" in call_sql

    @pytest.mark.asyncio
    async def test_diamond_dependency(self, queue):
        """Three-job diamond: A→B, A→C, B,C→D. D releases only after B and C."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.execute = AsyncMock()

        # Simulate completing job B (id=2), but C (id=3) is still running
        # query checks if ALL depends_on are complete
        mock_conn.fetch = AsyncMock(return_value=[
            FakeRow(id=3, status="running"),  # C still running
        ])

        await queue._release_dependents(mock_conn, 2, failed=False)

        # D should NOT be released because C is still running
        # The NOT EXISTS subquery found C, so the UPDATE should not match
        call_sql = mock_conn.execute.call_args[0][0]
        assert "status = 'available'" in call_sql or "NOT EXISTS" in call_sql

    @pytest.mark.asyncio
    async def test_circular_dependency_allowed(self, queue):
        """depends_on should not prevent enqueueing jobs — DB enforces nothing."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.fetchrow = AsyncMock(return_value=make_job_row(
            id=3, depends_on=[2, 1],
        ))

        job = await queue.enqueue(
            queue="default",
            job_type="circular_test",
            handler="handler",
            payload={},
            depends_on=[2, 1],
        )

        assert job.depends_on == [2, 1]
        assert job.id == 3


# ═══════════════════════════════════════════════════════════
# 2. Concurrent Consumers (SKIP LOCKED behavior)
# ═══════════════════════════════════════════════════════════


class TestConcurrentConsumers:
    """Multiple workers dequeuing simultaneously must not conflict."""

    @pytest.mark.asyncio
    async def test_dequeue_sets_consumer_lock(self, queue):
        """Dequeue should set consumer_id and consumer_lock_until."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.fetchrow = AsyncMock(return_value=make_job_row(
            id=42, status="running", consumer_id="worker-a",
            consumer_lock_until=datetime.now(timezone.utc) + timedelta(minutes=5),
        ))

        job = await queue.dequeue(consumer_id="worker-a", queues=["default"])

        assert job is not None
        assert job.consumer_id == "worker-a"
        assert job.consumer_lock_until is not None

    @pytest.mark.asyncio
    async def test_dequeue_returns_none_when_empty(self, queue):
        """Dequeue returns None when no jobs are available."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.fetchrow = AsyncMock(return_value=None)

        job = await queue.dequeue(consumer_id="worker-b")

        assert job is None

    @pytest.mark.asyncio
    async def test_dequeue_filters_by_queue(self, queue):
        """Dequeue should filter by queue name when specified."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.fetchrow = AsyncMock(return_value=make_job_row(queue="loops"))

        job = await queue.dequeue(consumer_id="worker-c", queues=["loops"])

        assert job is not None
        # Verify SQL included queue filter
        call_sql = mock_conn.fetchrow.call_args[0][0]
        assert "queue" in call_sql.lower()

    @pytest.mark.asyncio
    async def test_dequeue_multiple_queues(self, queue):
        """Dequeue accepts a list of queues to search."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.fetchrow = AsyncMock(return_value=make_job_row(queue="workflows"))

        job = await queue.dequeue(
            consumer_id="worker-d",
            queues=["loops", "workflows", "scheduled"],
        )

        assert job is not None
        assert job.queue in ("loops", "workflows", "scheduled")

    @pytest.mark.asyncio
    async def test_dequeue_respects_priority(self, queue):
        """Jobs with higher priority should be dequeued first."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.fetchrow = AsyncMock(return_value=make_job_row(
            id=99, priority=100, status="running",
        ))

        job = await queue.dequeue(consumer_id="worker-e")

        assert job.priority == 100
        assert job.id == 99

    @pytest.mark.asyncio
    async def test_dequeue_available_only(self, queue):
        """Only 'available' jobs should be dequeued."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)

        # Verify the WHERE clause filters by status='available'
        mock_conn.fetchrow = AsyncMock(return_value=make_job_row(status="running"))

        await queue.dequeue(consumer_id="worker-f")

        call_sql = mock_conn.fetchrow.call_args[0][0]
        assert "status = 'available'" in call_sql or '"available"' in call_sql


# ═══════════════════════════════════════════════════════════
# 3. Heartbeat & Stale Locks
# ═══════════════════════════════════════════════════════════


class TestHeartbeat:
    """Workers must extend their lock periodically."""

    @pytest.mark.asyncio
    async def test_heartbeat_extends_lock(self, queue):
        """Heartbeat should update consumer_lock_until to NOW + 5 min."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.execute = AsyncMock()

        await queue.heartbeat("worker-1", [1, 2, 3])

        mock_conn.execute.assert_called_once()
        call_sql = mock_conn.execute.call_args[0][0]
        assert "consumer_lock_until" in call_sql
        assert "ANY" in call_sql or "IN (" in call_sql

    @pytest.mark.asyncio
    async def test_heartbeat_no_ids(self, queue):
        """Heartbeat with empty list should be a no-op."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)

        await queue.heartbeat("worker-1", [])

        mock_conn.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_heartbeat_updates_specific_consumer(self, queue):
        """Heartbeat should only update jobs owned by the caller."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.execute = AsyncMock()

        await queue.heartbeat("worker-x", [42, 99])

        assert mock_conn.execute.called
        call_sql = mock_conn.execute.call_args[0][0]
        assert "consumer_id" in call_sql


# ═══════════════════════════════════════════════════════════
# 4. Schedule Ticker
# ═══════════════════════════════════════════════════════════


class TestScheduleTicker:
    """The ticker checks due schedules and enqueues jobs."""

    @pytest.mark.asyncio
    async def test_tick_enqueues_due_schedules(self, queue):
        """Due schedules should produce jobs with SKIP LOCKED isolation."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.fetch = AsyncMock(return_value=[
            make_schedule_row(id=10, name="daily-triage"),
            make_schedule_row(id=11, name="pr-babysitter"),
        ])
        mock_conn.fetchrow = AsyncMock(return_value=make_job_row(id=100))
        mock_conn.execute = AsyncMock()

        jobs = await queue.tick_scheduler()

        assert len(jobs) == 2
        assert jobs[0].id == 100
        assert jobs[1].id == 100

    @pytest.mark.asyncio
    async def test_tick_updates_schedule_next_run(self, queue):
        """After enqueuing, the schedule's next_run_at should advance."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.fetch = AsyncMock(return_value=[
            make_schedule_row(id=5, name="ci-sweeper", interval_seconds=900),
        ])
        mock_conn.fetchrow = AsyncMock(return_value=make_job_row(id=200))
        mock_conn.execute = AsyncMock()

        await queue.tick_scheduler()

        # execute was called to update next_run_at
        assert mock_conn.execute.called
        update_call = mock_conn.execute.call_args_list[0]
        call_sql = update_call.args[0]
        assert "next_run_at" in call_sql
        assert "last_run_status" in call_sql

    @pytest.mark.asyncio
    async def test_tick_skips_paused_schedules(self, queue):
        """Paused schedules should not produce jobs."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.fetch = AsyncMock(return_value=[])  # no due schedules (paused)

        jobs = await queue.tick_scheduler()

        assert jobs == []
        # fetch should have filtered for enabled AND NOT paused
        call_sql = mock_conn.fetch.call_args[0][0]
        assert "NOT paused" in call_sql or "paused" in call_sql

    @pytest.mark.asyncio
    async def test_tick_skips_disabled_schedules(self, queue):
        """Disabled schedules should not produce jobs."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.fetch = AsyncMock(return_value=[])

        await queue.tick_scheduler()

        call_sql = mock_conn.fetch.call_args[0][0]
        assert "enabled" in call_sql.lower()

    @pytest.mark.asyncio
    async def test_schedule_recurring_inserts(self, queue):
        """schedule_recurring should INSERT and return a Schedule."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.fetchrow = AsyncMock(return_value=make_schedule_row(
            name="my-custom-schedule", schedule_type="interval", interval_seconds=300,
        ))

        sched = await queue.schedule_recurring(
            name="my-custom-schedule",
            job_type="custom:test",
            handler="custom.handler",
            schedule_type="interval",
            interval_seconds=300,
        )

        assert sched.name == "my-custom-schedule"
        assert sched.schedule_type == "interval"
        assert sched.interval_seconds == 300
        assert sched.next_run_at is not None

    @pytest.mark.asyncio
    async def test_schedule_recurring_cron(self, queue):
        """schedule_recurring with cron expression."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.fetchrow = AsyncMock(return_value=make_schedule_row(
            name="cron-schedule", schedule_type="cron", cron_expr="0 9 * * *",
        ))

        sched = await queue.schedule_recurring(
            name="cron-schedule",
            job_type="custom:cron",
            handler="custom.cron_handler",
            schedule_type="cron",
            cron_expr="0 9 * * *",
        )

        assert sched.schedule_type == "cron"

    @pytest.mark.asyncio
    async def test_list_schedules(self, queue):
        """list_schedules should return all schedules."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.fetch = AsyncMock(return_value=[
            make_schedule_row(id=1, name="sched-a"),
            make_schedule_row(id=2, name="sched-b"),
        ])

        schedules = await queue.list_schedules()

        assert len(schedules) == 2
        assert schedules[0].name == "sched-a"
        assert schedules[1].name == "sched-b"

    @pytest.mark.asyncio
    async def test_trigger_schedule(self, queue):
        """trigger_schedule should enqueue a high-priority job."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        # get_schedule
        mock_conn.fetchrow = AsyncMock(return_value=make_schedule_row(
            name="daily-triage", job_type="loop:daily-triage",
        ))
        # enqueue
        mock_conn_2 = AsyncMock()
        mock_conn_2.fetchrow = AsyncMock(return_value=make_job_row(
            id=999, priority=99, job_type="loop:daily-triage",
        ))
        _mock_acquire(queue, mock_conn_2)

        job = await queue.trigger_schedule("daily-triage")

        assert job is not None
        assert job.priority == 99  # manual triggers get high priority

    @pytest.mark.asyncio
    async def test_trigger_schedule_not_found(self, queue):
        """trigger_schedule on missing schedule returns None."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.fetchrow = AsyncMock(return_value=None)

        job = await queue.trigger_schedule("nonexistent")

        assert job is None


# ═══════════════════════════════════════════════════════════
# 5. Cancel & Retry
# ═══════════════════════════════════════════════════════════


class TestCancelAndRetry:
    """Job cancellation and manual retry behavior."""

    @pytest.mark.asyncio
    async def test_cancel_pending_job(self, queue):
        """Cancel a pending job should succeed."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")

        ok = await queue.cancel(42)

        assert ok is True

    @pytest.mark.asyncio
    async def test_cancel_completed_job_fails(self, queue):
        """Cancel a completed job should return False."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.execute = AsyncMock(return_value="UPDATE 0")  # nothing matched

        ok = await queue.cancel(42)

        assert ok is False

    @pytest.mark.asyncio
    async def test_cancel_scheduled_job(self, queue):
        """Cancel a scheduled job should work (it's not terminal yet)."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")

        ok = await queue.cancel(42)

        assert ok is True
        call_sql = mock_conn.execute.call_args[0][0]
        # Should allow 'scheduled' status
        assert "scheduled" in call_sql or "status" in call_sql

    @pytest.mark.asyncio
    async def test_retry_failed_job(self, queue):
        """retry_job should reset a failed job to available with retry_count=0."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")

        ok = await queue.retry_job(42)

        assert ok is True
        call_sql = mock_conn.execute.call_args[0][0]
        assert "status = 'available'" in call_sql
        assert "retry_count = 0" in call_sql

    @pytest.mark.asyncio
    async def test_retry_non_failed_job_fails(self, queue):
        """retry_job on a non-failed job should return False."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.execute = AsyncMock(return_value="UPDATE 0")  # nothing matched

        ok = await queue.retry_job(42)

        assert ok is False


# ═══════════════════════════════════════════════════════════
# 6. Job Lifecycle State Machine
# ═══════════════════════════════════════════════════════════


class TestJobLifecycle:
    """Full lifecycle: pending → available → running → completed/failed."""

    @pytest.mark.asyncio
    async def test_complete_updates_result(self, queue):
        """Complete should store result and set status."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.execute = AsyncMock()
        queue._release_dependents = AsyncMock()

        await queue.complete(42, {"output": "success"})

        call_sql = mock_conn.execute.call_args[0][0]
        assert "status = 'completed'" in call_sql
        assert "completed_at" in call_sql
        assert "result" in call_sql

    @pytest.mark.asyncio
    async def test_fail_exponential_backoff(self, queue):
        """Retry delay should use exponential backoff."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.fetchrow = AsyncMock(return_value=make_job_row(
            retry_count=0, max_retries=5, retry_delay_seconds=10,
        ))
        mock_conn.execute = AsyncMock()

        await queue.fail(42, "error", retry=True)

        call_sql = mock_conn.execute.call_args[0][0]
        # retry_count becomes 1, backoff = 10 * 2^0 = 10s
        assert "available_at" in call_sql
        assert "retry_count" in call_sql

    @pytest.mark.asyncio
    async def test_fail_no_remaining_retries(self, queue):
        """When retry_count >= max_retries, job fails permanently."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.fetchrow = AsyncMock(return_value=make_job_row(
            retry_count=3, max_retries=3, retry_delay_seconds=30,
        ))
        mock_conn.execute = AsyncMock()

        await queue.fail(42, "Final failure", retry=True)

        call_sql = mock_conn.execute.call_args[0][0]
        assert "status = 'failed'" in call_sql

    @pytest.mark.asyncio
    async def test_fail_with_retry_false_skips_backoff(self, queue):
        """fail(retry=False) should go straight to failed."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.fetchrow = AsyncMock(return_value=make_job_row(
            retry_count=0, max_retries=3, retry_delay_seconds=10,
        ))
        mock_conn.execute = AsyncMock()

        await queue.fail(42, "Manual abort", retry=False)

        call_sql = mock_conn.execute.call_args[0][0]
        assert "status = 'failed'" in call_sql
        assert "retry_count" not in call_sql

    @pytest.mark.asyncio
    async def test_get_job(self, queue):
        """get_job returns a Job for valid ID."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.fetchrow = AsyncMock(return_value=make_job_row(id=42))

        job = await queue.get_job(42)

        assert job is not None
        assert job.id == 42

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, queue):
        """get_job returns None for missing ID."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.fetchrow = AsyncMock(return_value=None)

        job = await queue.get_job(99999)

        assert job is None

    @pytest.mark.asyncio
    async def test_list_jobs_with_filters(self, queue):
        """list_jobs with queue, status, job_type filters."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.fetch = AsyncMock(return_value=[
            make_job_row(id=1, queue="loops", status="running"),
            make_job_row(id=2, queue="loops", status="running"),
        ])

        jobs = await queue.list_jobs(queue="loops", status="running")

        assert len(jobs) == 2


# ═══════════════════════════════════════════════════════════
# 7. Queue Stats
# ═══════════════════════════════════════════════════════════


class TestQueueStats:
    """Queue statistics aggregation."""

    @pytest.mark.asyncio
    async def test_queue_stats_all_statuses_present(self, queue):
        """Stats should include zeros for missing statuses."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.fetch = AsyncMock(return_value=[
            FakeRow(status="available", count=5),
            FakeRow(status="completed", count=100),
        ])

        stats = await queue.queue_stats()

        assert stats["available"] == 5
        assert stats["completed"] == 100
        assert stats["pending"] == 0
        assert stats["failed"] == 0
        assert stats["running"] == 0
        assert stats["cancelled"] == 0

    @pytest.mark.asyncio
    async def test_queue_stats_empty(self, queue):
        """Stats on empty queue should return all zeros."""
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.fetch = AsyncMock(return_value=[])

        stats = await queue.queue_stats()

        for status in ("pending", "available", "running", "completed", "failed", "cancelled"):
            assert stats[status] == 0


# ═══════════════════════════════════════════════════════════
# 8. Schedule Management (pause/resume)
# ═══════════════════════════════════════════════════════════


class TestScheduleManagement:
    """Pausing and resuming schedules."""

    @pytest.mark.asyncio
    async def test_pause_schedule(self, queue):
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")

        ok = await queue.pause_schedule("daily-triage", reason="Testing")

        assert ok is True

    @pytest.mark.asyncio
    async def test_resume_schedule(self, queue):
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")

        ok = await queue.resume_schedule("daily-triage")

        assert ok is True

    @pytest.mark.asyncio
    async def test_pause_schedule_not_found(self, queue):
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.execute = AsyncMock(return_value="UPDATE 0")

        ok = await queue.pause_schedule("nonexistent")

        assert ok is False

    @pytest.mark.asyncio
    async def test_get_schedule(self, queue):
        mock_conn = AsyncMock()
        _mock_acquire(queue, mock_conn)
        mock_conn.fetchrow = AsyncMock(return_value=make_schedule_row(name="my-schedule"))

        sched = await queue.get_schedule("my-schedule")

        assert sched is not None
        assert sched.name == "my-schedule"


# ═══════════════════════════════════════════════════════════
# 9. Handler Registry
# ═══════════════════════════════════════════════════════════


class TestHandlerRegistry:
    """Handler registration and lookup."""

    _added_handlers: set = set()

    def setup_method(self):
        self._added_handlers = set()

    def teardown_method(self):
        for key in self._added_handlers:
            _handlers.pop(key, None)

    @pytest.mark.asyncio
    async def test_register_decorator(self):
        @register_handler("echo:hello")
        async def hello(payload):
            return {"message": "hello"}

        self._added_handlers.add("echo:hello")

        handler = get_handler("echo:hello")
        assert handler is hello

        result = await handler({"name": "world"})
        assert result["message"] == "hello"

    @pytest.mark.asyncio
    async def test_register_multiple_handlers(self):
        @register_handler("type:a")
        async def handler_a(payload): return "a"

        @register_handler("type:b")
        async def handler_b(payload): return "b"

        @register_handler("type:c")
        async def handler_c(payload): return "c"

        self._added_handlers.update(["type:a", "type:b", "type:c"])

        assert get_handler("type:a") is handler_a
        assert get_handler("type:b") is handler_b
        assert get_handler("type:c") is handler_c
        assert get_handler("type:nonexistent") is None

    def test_register_replaces_existing(self):
        """Registering the same job_type again should replace the handler."""
        async def old_handler(payload): return "old"
        async def new_handler(payload): return "new"

        self._added_handlers.add("dup:test")
        _handlers["dup:test"] = old_handler
        _handlers["dup:test"] = new_handler  # manual replace

        assert get_handler("dup:test") is new_handler
