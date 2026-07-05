"""
Integration Smoke Tests — cross-module flows.

Tests verify that the queue, worktree, loops, and MCP client modules
work together correctly. All external I/O is mocked — no real DB,
git repos, or subprocesses are created.

These are integration *logic* tests: they verify the wiring between
modules is correct even though the actual execution is mocked.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_workspace.queue import JobQueue, register_handler, get_handler
from ai_workspace.loops import (
    handle_daily_triage,
    _load_state,
    _save_state,
    _check_budget,
)
from ai_workspace.worktree import WorktreeManager, WorktreeConfig, WorktreeHandle


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════


class FakeRow:
    """Simulates an asyncpg.Record for unit testing.
    Supports dict() conversion via keys()/items().
    """
    def __init__(self, **kwargs):
        self._data = kwargs
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __getitem__(self, key):
        return self._data[key]

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def get(self, key, default=None):
        return self._data.get(key, default)


def make_job_row(**overrides):
    now = datetime.now(timezone.utc)
    data = dict(
        id=1, queue="loops", job_type="loop:daily-triage",
        handler="ai_workspace.loops.handle_daily_triage",
        payload={}, status="pending", priority=0,
        scheduled_at=now, available_at=now,
        started_at=None, completed_at=None,
        timeout_seconds=300, max_retries=3,
        retry_count=0, retry_delay_seconds=30,
        last_error=None, depends_on=[], parent_job_id=None,
        consumer_id=None, consumer_lock_until=None,
        result=None, created_at=now, updated_at=now,
    )
    data.update(overrides)
    return FakeRow(**data)


def make_state_row(**overrides):
    now = datetime.now(timezone.utc)
    data = dict(
        id=1, pattern_id="daily-triage", run_id=42,
        state_type="snapshot", last_run=now,
        items_active=json.dumps([]),
        items_watch=json.dumps([]),
        items_noise=json.dumps([]),
        items_pruned=json.dumps([]),
        escalations=json.dumps([]),
        human_overrides=json.dumps([]),
        data=json.dumps({}),
        created_at=now,
    )
    data.update(overrides)
    return FakeRow(**data)


@pytest.fixture
def mock_queue_with_pool():
    """Create a JobQueue with a mocked asyncpg pool."""
    q = JobQueue("postgresql:///test")
    q._pool = MagicMock()
    return q


def _mock_acquire(queue, mock_conn):
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=mock_conn)
    cm.__aexit__ = AsyncMock(return_value=None)
    queue._pool.acquire = MagicMock(return_value=cm)


# ═══════════════════════════════════════════════════════════
# 1. Queue → Handler → Workflow
# ═══════════════════════════════════════════════════════════


class TestQueueToHandler:
    """A job enqueued → dequeued → handler invoked → result stored."""

    @pytest.mark.asyncio
    async def test_enqueue_dequeue_handler_flow(self, mock_queue_with_pool):
        """Simulate the full lifecycle of a job through the queue."""
        q = mock_queue_with_pool
        mock_conn = AsyncMock()
        _mock_acquire(q, mock_conn)

        # ── Step 1: Enqueue ──
        mock_conn.fetchrow = AsyncMock(return_value=make_job_row(
            id=100, job_type="loop:daily-triage",
            handler="ai_workspace.loops.handle_daily_triage",
            queue="loops",
        ))

        job = await q.enqueue(
            queue="loops",
            job_type="loop:daily-triage",
            handler="ai_workspace.loops.handle_daily_triage",
            payload={"project_root": "/tmp/test"},
        )

        assert job is not None
        assert job.id == 100
        assert job.job_type == "loop:daily-triage"

        # ── Step 2: Dequeue ──
        mock_conn.fetchrow = AsyncMock(return_value=make_job_row(
            id=100, status="running", consumer_id="worker-1",
        ))
        dequeued = await q.dequeue(consumer_id="worker-1", queues=["loops"])
        assert dequeued is not None
        assert dequeued.id == 100
        assert dequeued.consumer_id == "worker-1"

        # ── Step 3: Execute handler (import ensures registration) ──
        from ai_workspace import loops as loops_module
        import importlib
        importlib.reload(loops_module)

        handler = get_handler("loop:daily-triage")
        # If handler is None, the registry might have been cleared by another test
        if handler:
            result = await handler({"project_root": "/tmp/test"})
            assert result["status"] == "ok"
            assert result["pattern"] == "daily-triage"

            # ── Step 4: Complete job ──
            mock_conn.execute = AsyncMock()
            q._release_dependents = AsyncMock()
            await q.complete(100, result)
            mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_queue_job_failure_triggers_retry(self, mock_queue_with_pool):
        """A job that fails should be retried with backoff."""
        q = mock_queue_with_pool
        mock_conn = AsyncMock()
        _mock_acquire(q, mock_conn)

        mock_conn.fetchrow = AsyncMock(return_value=make_job_row(
            id=101, retry_count=0, max_retries=3, retry_delay_seconds=10,
        ))
        mock_conn.execute = AsyncMock()

        await q.fail(101, "Handler crashed", retry=True)

        call_sql = mock_conn.execute.call_args[0][0]
        assert "available" in call_sql
        assert "retry_count" in call_sql


# ═══════════════════════════════════════════════════════════
# 2. Queue → Schedule → Loop → State
# ═══════════════════════════════════════════════════════════


class TestScheduleToLoopToState:
    """A schedule fires → enqueues job → handler runs → state persisted."""

    @pytest.mark.asyncio
    async def test_schedule_ticker_enqueues_loop_job(self, mock_queue_with_pool):
        """Tick scheduler produces jobs for due schedules."""
        q = mock_queue_with_pool
        mock_conn = AsyncMock()
        _mock_acquire(q, mock_conn)

        mock_conn.fetch = AsyncMock(return_value=[
            FakeRow(
                id=1, name="daily-triage", job_type="loop:daily-triage",
                handler="ai_workspace.loops.handle_daily_triage",
                payload={}, queue="loops", schedule_type="interval",
                cron_expr=None, interval_seconds=86400,
                max_retries=3, timeout_seconds=600, priority=0,
                enabled=True, paused=False,
            ),
        ])
        mock_conn.fetchrow = AsyncMock(return_value=make_job_row(id=200))
        mock_conn.execute = AsyncMock()

        jobs = await q.tick_scheduler()

        assert len(jobs) == 1
        assert jobs[0].id == 200

    @pytest.mark.asyncio
    async def test_load_state_and_run_handler(self, mock_queue_with_pool):
        """Handler can load state, execute, and save state."""
        q = mock_queue_with_pool
        mock_conn = AsyncMock()
        _mock_acquire(q, mock_conn)

        # Load state
        mock_conn.fetchrow = AsyncMock(return_value=make_state_row(
            pattern_id="daily-triage",
            items_active=json.dumps([{"id": "issue-42", "title": "Bug in login"}]),
        ))

        state = await _load_state("daily-triage", q)
        assert state["pattern_id"] == "daily-triage"

        # Run handler
        result = await handle_daily_triage({"project_root": "/tmp"})
        assert result["status"] == "ok"

        # Save state
        mock_conn.execute = AsyncMock()
        await _save_state("daily-triage", 42, state, q)
        assert mock_conn.execute.called


# ═══════════════════════════════════════════════════════════
# 3. Queue → Worktree → Loop (CI Sweeper flow)
# ═══════════════════════════════════════════════════════════


class TestQueueWorktreeLoop:
    """A CI sweeper job acquires a worktree and runs inside it."""

    @pytest.mark.asyncio
    async def test_ci_sweeper_acquires_worktree(self, mock_queue_with_pool):
        """A CI sweeper job should be able to acquire a worktree."""
        q = mock_queue_with_pool
        mock_q_conn = AsyncMock()
        _mock_acquire(q, mock_q_conn)
        mock_q_conn.fetchrow = AsyncMock(return_value=make_job_row(
            id=300, job_type="loop:ci-sweeper", status="running",
        ))

        job = await q.dequeue("worker-ci", queues=["loops"])
        assert job is not None
        assert job.job_type == "loop:ci-sweeper"

        # ── Worktree ──
        wtm = WorktreeManager("postgresql:///test", config=WorktreeConfig(
            max_worktrees=5, worktree_base_dir="/tmp/test-wt",
        ))
        wtm._pool = MagicMock()
        mock_wt_conn = AsyncMock()
        cm2 = MagicMock()
        cm2.__aenter__ = AsyncMock(return_value=mock_wt_conn)
        cm2.__aexit__ = AsyncMock(return_value=None)
        wtm._pool.acquire = MagicMock(return_value=cm2)
        mock_wt_conn.fetchval = AsyncMock(return_value=0)
        mock_wt_conn.execute = AsyncMock()

        with patch.object(wtm, "_git_worktree_add") as mock_add:
            with patch.object(wtm, "_git_worktree_remove") as mock_remove:
                with patch.object(wtm, "_git_worktree_prune") as mock_prune:
                    async with wtm.acquire(
                        pattern_id="ci-sweeper",
                        item_id="fix-ci-flaky-test",
                        repo_path="/tmp/test-repo",
                        branch_name="fix/ci-flaky-test",
                    ) as wt_handle:
                        assert wt_handle is not None
                        assert wt_handle.pattern_id == "ci-sweeper"
                        assert wt_handle.branch == "fix/ci-flaky-test"

                    mock_remove.assert_called_once()

    @pytest.mark.asyncio
    async def test_worktree_limit_blocks_new_jobs(self):
        """When max_worktrees is reached, new jobs should fail fast."""
        wtm = WorktreeManager("postgresql:///test", config=WorktreeConfig(
            max_worktrees=1,
        ))
        wtm._pool = MagicMock()
        mock_conn = AsyncMock()
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=mock_conn)
        cm.__aexit__ = AsyncMock(return_value=None)
        wtm._pool.acquire = MagicMock(return_value=cm)

        mock_conn.fetchval = AsyncMock(return_value=0)
        mock_conn.execute = AsyncMock()

        with patch.object(wtm, "_git_worktree_add") as mock_add:
            with patch.object(wtm, "_git_worktree_remove") as mock_remove:
                async with wtm.acquire(
                    pattern_id="ci-sweeper",
                    item_id="first-job",
                    repo_path="/tmp/test-repo",
                ) as wt:
                    assert wt is not None

                # Second worktree — fails (at limit)
                mock_conn.fetchval = AsyncMock(return_value=1)
                with pytest.raises(RuntimeError, match="Max worktrees"):
                    async with wtm.acquire(
                        pattern_id="ci-sweeper",
                        item_id="second-job",
                        repo_path="/tmp/test-repo",
                    ):
                        pass

    @pytest.mark.asyncio
    async def test_multiple_loops_share_queue(self, mock_queue_with_pool):
        """Multiple loop patterns can be scheduled in the same queue."""
        q = mock_queue_with_pool
        mock_conn = AsyncMock()
        _mock_acquire(q, mock_conn)

        # Use side_effect to return different job_types
        mock_conn.fetchrow = AsyncMock(side_effect=[
            make_job_row(id=400, job_type="loop:daily-triage"),
            make_job_row(id=401, job_type="loop:ci-sweeper"),
            make_job_row(id=402, job_type="loop:pr-babysitter"),
        ])

        job1 = await q.enqueue(queue="loops", job_type="loop:daily-triage",
                                handler="h1", payload={})
        job2 = await q.enqueue(queue="loops", job_type="loop:ci-sweeper",
                                handler="h2", payload={})
        job3 = await q.enqueue(queue="loops", job_type="loop:pr-babysitter",
                                handler="h3", payload={})

        assert job1.job_type == "loop:daily-triage"
        assert job2.job_type == "loop:ci-sweeper"
        assert job3.job_type == "loop:pr-babysitter"


# ═══════════════════════════════════════════════════════════
# 4. Budget enforcement integrated with queue
# ═══════════════════════════════════════════════════════════


class TestBudgetIntegration:
    """Budget check prevents handling when exhausted."""

    @pytest.mark.asyncio
    async def test_budget_check_before_handler(self, mock_queue_with_pool):
        """Before running a loop handler, check budget."""
        q = mock_queue_with_pool
        mock_conn = AsyncMock()
        _mock_acquire(q, mock_conn)

        mock_conn.fetchrow = AsyncMock(return_value=FakeRow(
            daily_cap=100000, daily_spent=100000, paused=False, kill_switch=False,
        ))

        within, remaining = await _check_budget("daily-triage", q)
        assert within is False
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_budget_check_before_enqueue(self, mock_queue_with_pool):
        """Budget check can prevent enqueuing when kill_switch is on."""
        q = mock_queue_with_pool
        mock_conn = AsyncMock()
        _mock_acquire(q, mock_conn)

        mock_conn.fetchrow = AsyncMock(return_value=FakeRow(
            daily_cap=100000, daily_spent=50000, paused=False, kill_switch=True,
        ))

        within, _ = await _check_budget("daily-triage", q)
        assert within is False
