"""
Loop Pattern Tests — handler registration, return values, state persistence,
budget check/spend, run log writing, and seed defaults.

Tests use mocked asyncpg so no real database is needed.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_workspace.loops import (
    handle_daily_triage,
    handle_pr_babysitter,
    handle_ci_sweeper,
    handle_dependency_sweeper,
    handle_post_merge_cleanup,
    handle_issue_triage,
    handle_changelog_drafter,
    _load_state,
    _save_state,
    _write_run_log,
    _check_budget,
    _spend_budget,
    seed_default_schedules,
)
from ai_workspace.queue import register_handler, get_handler, _handlers, JobQueue


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


def make_state_row(**overrides):
    now = datetime.now(timezone.utc)
    data = dict(
        id=1, pattern_id="daily-triage", run_id=42,
        state_type="snapshot", last_run=now,
        items_active=json.dumps([{"id": "item-1", "title": "Test Item", "status": "active"}]),
        items_watch=json.dumps([]), items_noise=json.dumps([]),
        items_pruned=json.dumps([]), escalations=json.dumps([]),
        human_overrides=json.dumps([]), data=json.dumps({}), created_at=now,
    )
    data.update(overrides)
    return FakeRow(**data)


def make_budget_row(**overrides):
    data = dict(
        pattern_id="daily-triage", daily_cap=100000, daily_spent=25000,
        pause_reason=None, paused=False, kill_switch=False,
    )
    data.update(overrides)
    return FakeRow(**data)


@pytest.fixture
def mock_pool_and_queue():
    """Create a mock JobQueue with a mocked asyncpg pool and connection."""
    mock_conn = AsyncMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=mock_conn)
    cm.__aexit__ = AsyncMock(return_value=None)

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=cm)

    queue = JobQueue("postgresql:///test")
    queue._pool = mock_pool
    return queue, mock_conn


# ═══════════════════════════════════════════════════════════
# 1. Handler Registration
# ═══════════════════════════════════════════════════════════


class TestHandlerRegistration:
    """All 7 loop handlers should be registered with the queue."""

    def test_daily_triage_registered(self):
        handler = get_handler("loop:daily-triage")
        assert handler is not None
        assert handler.__name__ == "handle_daily_triage"

    def test_pr_babysitter_registered(self):
        handler = get_handler("loop:pr-babysitter")
        assert handler is not None
        assert handler.__name__ == "handle_pr_babysitter"

    def test_ci_sweeper_registered(self):
        handler = get_handler("loop:ci-sweeper")
        assert handler is not None
        assert handler.__name__ == "handle_ci_sweeper"

    def test_dependency_sweeper_registered(self):
        handler = get_handler("loop:dependency-sweeper")
        assert handler is not None
        assert handler.__name__ == "handle_dependency_sweeper"

    def test_post_merge_cleanup_registered(self):
        handler = get_handler("loop:post-merge-cleanup")
        assert handler is not None
        assert handler.__name__ == "handle_post_merge_cleanup"

    def test_issue_triage_registered(self):
        handler = get_handler("loop:issue-triage")
        assert handler is not None
        assert handler.__name__ == "handle_issue_triage"

    def test_changelog_drafter_registered(self):
        handler = get_handler("loop:changelog-drafter")
        assert handler is not None
        assert handler.__name__ == "handle_changelog_drafter"


# ═══════════════════════════════════════════════════════════
# 2. Handler Returns
# ═══════════════════════════════════════════════════════════


class TestHandlerReturns:
    """Each handler should return a meaningful result structure."""

    @pytest.mark.asyncio
    async def test_daily_triage_returns_ok(self):
        """Daily triage should return status ok even outside a git repo."""
        result = await handle_daily_triage({"project_root": "/tmp"})
        assert result["status"] == "ok"
        assert result["pattern"] == "daily-triage"

    @pytest.mark.asyncio
    async def test_daily_triage_returns_error_for_non_repo(self):
        """Daily triage should report not-a-repo gracefully."""
        result = await handle_daily_triage({"project_root": "/tmp"})
        assert "error" in result
        assert result["items_found"] == 0

    @pytest.mark.asyncio
    async def test_pr_babysitter_returns_ok(self):
        result = await handle_pr_babysitter({"project_root": "/tmp"})
        assert result["status"] == "ok"
        assert result["pattern"] == "pr-babysitter"

    @pytest.mark.asyncio
    async def test_ci_sweeper_returns_data(self):
        result = await handle_ci_sweeper({"project_root": "/tmp"})
        assert result["pattern"] == "ci-sweeper"
        # Outside git repo, ci_sweeper may not populate data; just check it exists
        assert "failures_found" in result

    @pytest.mark.asyncio
    async def test_dependency_sweeper_parses_deps(self):
        """Should parse dependencies even from /tmp (no pyproject.toml)."""
        result = await handle_dependency_sweeper({"project_root": "/tmp"})
        assert isinstance(result.get("data"), dict)
        assert "total_deps" in result["data"]

    @pytest.mark.asyncio
    async def test_post_merge_cleanup_returns_items(self):
        result = await handle_post_merge_cleanup({"project_root": "/tmp"})
        assert result["pattern"] == "post-merge-cleanup"
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_issue_triage_returns_issues_scanned(self):
        result = await handle_issue_triage({"project_root": "/tmp"})
        assert result["pattern"] == "issue-triage"
        assert "issues_scanned" in result

    @pytest.mark.asyncio
    async def test_changelog_drafter_merges_found(self):
        result = await handle_changelog_drafter({"project_root": "/tmp"})
        assert result["pattern"] == "changelog-drafter"
        assert "merges_found" in result
        assert isinstance(result.get("draft_path"), str)

    @pytest.mark.asyncio
    async def test_handlers_in_git_repo(self):
        """When run in the aiw repo itself, handlers should find real data."""
        repo_root = __file__.rsplit("/tests/", 1)[0]  # workspace root

        # Daily triage on the real repo
        result = await handle_daily_triage({"project_root": repo_root})
        assert result["items_found"] > 0, "Should find commits in own repo"
        assert "data" in result
        assert result["data"]["total_commits"] > 0

        # CI sweeper should find .github/workflows
        ci_result = await handle_ci_sweeper({"project_root": repo_root})
        assert isinstance(ci_result.get("data", {}).get("ci_files"), list)

        # Dep sweeper should parse pyproject.toml
        dep_result = await handle_dependency_sweeper({"project_root": repo_root})
        assert dep_result["data"]["total_deps"] > 0

        # Issue triage should find TODO/FIXME
        issue_result = await handle_issue_triage({"project_root": repo_root})
        assert issue_result["issues_scanned"] > 0

        # Changelog drafter should produce a draft
        cl_result = await handle_changelog_drafter({"project_root": repo_root})
        assert cl_result["merges_found"] > 0

        # Post-merge cleanup should find TODOs
        pm_result = await handle_post_merge_cleanup({"project_root": repo_root})
        assert pm_result["items_found"] > 0


# ═══════════════════════════════════════════════════════════
# 3. State Persistence Helpers
# ═══════════════════════════════════════════════════════════


class TestStateHelpers:
    """_load_state and _save_state should work with PostgreSQL."""

    @pytest.mark.asyncio
    async def test_load_state_existing(self, mock_pool_and_queue):
        queue, mock_conn = mock_pool_and_queue
        mock_conn.fetchrow = AsyncMock(return_value=make_state_row(
            pattern_id="daily-triage",
            items_active=json.dumps([{"id": "pr-42", "title": "Fix auth"}]),
        ))
        state = await _load_state("daily-triage", queue)
        assert state is not None
        assert "pattern_id" in state

    @pytest.mark.asyncio
    async def test_load_state_empty(self, mock_pool_and_queue):
        queue, mock_conn = mock_pool_and_queue
        mock_conn.fetchrow = AsyncMock(return_value=None)
        state = await _load_state("daily-triage", queue)
        assert state is not None
        assert state["pattern_id"] == "daily-triage"
        assert state["items_active"] == []

    @pytest.mark.asyncio
    async def test_save_state_calls_insert(self, mock_pool_and_queue):
        queue, mock_conn = mock_pool_and_queue
        mock_conn.execute = AsyncMock()
        state = {
            "pattern_id": "ci-sweeper",
            "items_active": [{"id": "ci-1", "status": "active"}],
            "items_watch": [], "items_noise": [], "items_pruned": [],
            "escalations": [], "data": {"failures": 3},
        }
        await _save_state("ci-sweeper", 42, state, queue)
        assert mock_conn.execute.called


# ═══════════════════════════════════════════════════════════
# 4. Run Log Writing
# ═══════════════════════════════════════════════════════════


class TestRunLog:
    """Loop run log entries."""

    @pytest.mark.asyncio
    async def test_write_run_log(self, mock_pool_and_queue):
        queue, mock_conn = mock_pool_and_queue
        mock_conn.execute = AsyncMock()
        await _write_run_log(
            pattern_id="daily-triage", run_id=42, outcome="success",
            items_found=5, actions_taken=2, tokens_estimate=1500, queue=queue,
        )
        assert mock_conn.execute.called

    @pytest.mark.asyncio
    async def test_write_run_log_with_error(self, mock_pool_and_queue):
        queue, mock_conn = mock_pool_and_queue
        mock_conn.execute = AsyncMock()
        await _write_run_log(
            pattern_id="ci-sweeper", run_id=43, outcome="failed",
            error="Connection timeout", tokens_estimate=0, queue=queue,
        )
        assert mock_conn.execute.called
        call_sql = mock_conn.execute.call_args[0][0]
        assert "loop_run_log" in call_sql


# ═══════════════════════════════════════════════════════════
# 5. Budget Check & Spend
# ═══════════════════════════════════════════════════════════


class TestBudget:
    """Daily token budget enforcement for loop patterns."""

    @pytest.mark.asyncio
    async def test_check_budget_within_limits(self, mock_pool_and_queue):
        queue, mock_conn = mock_pool_and_queue
        mock_conn.fetchrow = AsyncMock(return_value=make_budget_row(daily_cap=100000, daily_spent=25000))
        ok, remaining = await _check_budget("daily-triage", queue)
        assert ok is True
        assert remaining == 75000

    @pytest.mark.asyncio
    async def test_check_budget_exceeded(self, mock_pool_and_queue):
        queue, mock_conn = mock_pool_and_queue
        mock_conn.fetchrow = AsyncMock(return_value=make_budget_row(daily_cap=100000, daily_spent=150000))
        ok, remaining = await _check_budget("daily-triage", queue)
        assert ok is False
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_check_budget_no_row(self, mock_pool_and_queue):
        queue, mock_conn = mock_pool_and_queue
        mock_conn.fetchrow = AsyncMock(return_value=None)
        ok, remaining = await _check_budget("daily-triage", queue)
        assert ok is True
        assert remaining == 100000

    @pytest.mark.asyncio
    async def test_check_budget_kill_switch(self, mock_pool_and_queue):
        queue, mock_conn = mock_pool_and_queue
        mock_conn.fetchrow = AsyncMock(return_value=make_budget_row(daily_cap=100000, daily_spent=10000, kill_switch=True))
        ok, remaining = await _check_budget("daily-triage", queue)
        assert ok is False
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_check_budget_paused(self, mock_pool_and_queue):
        queue, mock_conn = mock_pool_and_queue
        mock_conn.fetchrow = AsyncMock(return_value=make_budget_row(daily_cap=100000, daily_spent=50000, paused=True))
        ok, remaining = await _check_budget("daily-triage", queue)
        assert ok is False
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_spend_budget_upserts(self, mock_pool_and_queue):
        queue, mock_conn = mock_pool_and_queue
        mock_conn.execute = AsyncMock()
        await _spend_budget("daily-triage", 5000, queue)
        assert mock_conn.execute.called
        call_sql = mock_conn.execute.call_args[0][0]
        assert "ON CONFLICT" in call_sql or "DO UPDATE" in call_sql


# ═══════════════════════════════════════════════════════════
# 6. Seed Default Schedules
# ═══════════════════════════════════════════════════════════


class TestSeedDefaults:
    """Seeding default schedules for all 7 loop patterns."""

    @pytest.mark.asyncio
    async def test_seed_default_schedules_returns_list(self):
        with patch("ai_workspace.queue.JobQueue") as MockQueue:
            instance = MagicMock()
            instance.connect = AsyncMock()
            MockQueue.return_value = instance

            def make_sched(name):
                s = MagicMock()
                s.name = name
                s.enabled = True
                s.paused = False
                return s

            names = ["daily-triage", "pr-babysitter", "ci-sweeper",
                     "dependency-sweeper", "post-merge-cleanup",
                     "issue-triage", "changelog-drafter"]
            instance.schedule_recurring = AsyncMock(side_effect=[make_sched(n) for n in names])
            instance.close = AsyncMock()

            results = await seed_default_schedules("postgresql:///test")
            assert len(results) == 7
            assert all(r["name"] in names for r in results)

    @pytest.mark.asyncio
    async def test_seed_schedules_calls_schedule_recurring(self):
        with patch("ai_workspace.queue.JobQueue") as MockQueue:
            instance = MagicMock()
            instance.connect = AsyncMock()
            MockQueue.return_value = instance
            sched_mock = MagicMock()
            sched_mock.name = "test-schedule"
            sched_mock.enabled = True
            sched_mock.paused = False
            instance.schedule_recurring = AsyncMock(return_value=sched_mock)
            instance.close = AsyncMock()
            await seed_default_schedules("postgresql:///test")
            assert instance.schedule_recurring.call_count == 7

    @pytest.mark.asyncio
    async def test_seed_schedules_closes_queue(self):
        with patch("ai_workspace.queue.JobQueue") as MockQueue:
            instance = MagicMock()
            instance.connect = AsyncMock()
            MockQueue.return_value = instance
            sched_mock = MagicMock()
            sched_mock.name = "test"
            sched_mock.enabled = True
            sched_mock.paused = False
            instance.schedule_recurring = AsyncMock(return_value=sched_mock)
            instance.close = AsyncMock()
            await seed_default_schedules("postgresql:///test")
            instance.close.assert_called_once()
