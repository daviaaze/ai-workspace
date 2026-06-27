"""Tests for the PostgreSQL Job Queue module."""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from ai_workspace.queue import JobQueue, Job, register_handler, get_handler


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
    """Create a fake job row for testing."""
    now = datetime.now(timezone.utc)
    data = dict(
        id=1,
        queue="default",
        job_type="test",
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


class TestHandler:
    """Test handler registration and lookup."""

    def teardown_method(self):
        # Clean up test handlers
        from ai_workspace.queue import _handlers
        _handlers.pop("test:handler", None)

    def test_register_and_get_handler(self):
        @register_handler("test:handler")
        async def my_handler(payload):
            return {"ok": True}

        handler = get_handler("test:handler")
        assert handler is not None
        assert handler is my_handler

    def test_get_handler_unknown(self):
        assert get_handler("nonexistent") is None


class TestJobQueueUnit:
    """Unit tests for JobQueue with mocked asyncpg."""

    @pytest.fixture
    def queue(self):
        q = JobQueue("postgresql:///test")
        q._pool = MagicMock()
        return q

    def _mock_acquire(self, queue, mock_conn):
        """Set up pool.acquire() to return an async context manager."""
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=mock_conn)
        cm.__aexit__ = AsyncMock(return_value=None)
        queue._pool.acquire = MagicMock(return_value=cm)

    @pytest.mark.asyncio
    async def test_enqueue(self, queue):
        mock_conn = AsyncMock()
        self._mock_acquire(queue, mock_conn)
        mock_conn.fetchrow = AsyncMock(return_value=make_job_row(
            id=42, job_type="test:enqueue", payload={"key": "value"}, priority=5,
        ))

        job = await queue.enqueue(
            queue="test",
            job_type="test:enqueue",
            handler="handler",
            payload={"key": "value"},
            priority=5,
        )

        assert job.id == 42
        assert job.job_type == "test:enqueue"
        assert job.payload == {"key": "value"}
        assert job.priority == 5
        assert job.status == "pending"
        mock_conn.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_dequeue_returns_job(self, queue):
        mock_conn = AsyncMock()
        self._mock_acquire(queue, mock_conn)
        mock_conn.fetchrow = AsyncMock(return_value=make_job_row(
            id=7, status="running", consumer_id="worker-1",
        ))

        job = await queue.dequeue(consumer_id="worker-1", queues=["default"])

        assert job is not None
        assert job.id == 7
        assert job.consumer_id == "worker-1"

    @pytest.mark.asyncio
    async def test_dequeue_no_jobs(self, queue):
        mock_conn = AsyncMock()
        self._mock_acquire(queue, mock_conn)
        mock_conn.fetchrow = AsyncMock(return_value=None)

        job = await queue.dequeue(consumer_id="worker-1")

        assert job is None

    @pytest.mark.asyncio
    async def test_complete(self, queue):
        mock_conn = AsyncMock()
        self._mock_acquire(queue, mock_conn)
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")
        queue._release_dependents = AsyncMock()

        await queue.complete(42, {"result": "done"})

        mock_conn.execute.assert_called_once()
        queue._release_dependents.assert_called_once()

    @pytest.mark.asyncio
    async def test_fail_with_retry(self, queue):
        mock_conn = AsyncMock()
        self._mock_acquire(queue, mock_conn)
        mock_conn.fetchrow = AsyncMock(return_value=make_job_row(
            retry_count=0, max_retries=3, retry_delay_seconds=30,
        ))
        mock_conn.execute = AsyncMock()

        await queue.fail(42, "Timeout", retry=True)

        assert mock_conn.execute.called

    @pytest.mark.asyncio
    async def test_fail_no_retry(self, queue):
        mock_conn = AsyncMock()
        self._mock_acquire(queue, mock_conn)
        mock_conn.fetchrow = AsyncMock(return_value=make_job_row(
            retry_count=3, max_retries=3, retry_delay_seconds=30,
        ))
        mock_conn.execute = AsyncMock()

        await queue.fail(42, "Final error", retry=True)

        # Should go to fail path (not retry) — assert retry_count is NOT in SQL
        call_sql = mock_conn.execute.call_args[0][0]
        assert "status = 'failed'" in call_sql
        assert "available_at" not in call_sql

    @pytest.mark.asyncio
    async def test_fail_retry_false_does_not_increment(self, queue):
        """fail(retry=False) should NOT increment retry_count."""
        mock_conn = AsyncMock()
        self._mock_acquire(queue, mock_conn)
        mock_conn.fetchrow = AsyncMock(return_value=make_job_row(
            retry_count=0, max_retries=3, retry_delay_seconds=30,
        ))
        mock_conn.execute = AsyncMock()

        await queue.fail(42, "Manual fail", retry=False)

        call_sql = mock_conn.execute.call_args[0][0]
        assert "status = 'failed'" in call_sql
        # retry_count should NOT be set when retry=False
        assert "retry_count" not in call_sql.split("SET")[1].split(",")[0]

    @pytest.mark.asyncio
    async def test_cancel(self, queue):
        mock_conn = AsyncMock()
        self._mock_acquire(queue, mock_conn)
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")

        ok = await queue.cancel(42)

        assert ok is True

    @pytest.mark.asyncio
    async def test_queue_stats(self, queue):
        mock_conn = AsyncMock()
        self._mock_acquire(queue, mock_conn)
        mock_conn.fetch = AsyncMock(return_value=[
            FakeRow(status="running", count=2),
            FakeRow(status="pending", count=5),
            FakeRow(status="completed", count=100),
        ])

        stats = await queue.queue_stats()

        assert stats["running"] == 2
        assert stats["pending"] == 5
        assert stats["completed"] == 100
        assert stats["failed"] == 0  # default

    @pytest.mark.asyncio
    async def test_retry_job(self, queue):
        mock_conn = AsyncMock()
        self._mock_acquire(queue, mock_conn)
        mock_conn.execute = AsyncMock(return_value="UPDATE 1")

        ok = await queue.retry_job(42)

        assert ok is True

    def test_calc_next_run_interval(self, queue):
        now = datetime.now(timezone.utc)
        next_run = queue._calc_next_run("interval", None, 3600, now)
        assert next_run == now + timedelta(seconds=3600)

    def test_calc_next_run_cron(self, queue):
        now = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
        next_run = queue._calc_next_run("cron", "0 11 * * *", None, now)
        assert next_run is not None
        assert next_run > now

    def test_calc_next_run_daily(self, queue):
        now = datetime.now(timezone.utc)
        next_run = queue._calc_next_run("daily", None, None, now)
        assert next_run == now + timedelta(days=1)

    def test_calc_next_run_default(self, queue):
        now = datetime.now(timezone.utc)
        next_run = queue._calc_next_run("unknown", None, None, now)
        assert next_run == now + timedelta(hours=1)
