"""
Worktree Manager Tests — lifecycle, limits, cleanup, git operations.

Uses mocked asyncpg and subprocess so no real git or DB is needed.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_workspace.worktree import (
    WorktreeManager,
    WorktreeConfig,
    WorktreeHandle,
)


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════


class FakeRow:
    """Simulates an asyncpg.Record for unit testing.
    Supports dict() conversion by providing keys().
    """
    def __init__(self, **kwargs):
        self._data = kwargs

    def __getitem__(self, key):
        if isinstance(key, (int, str)):
            return self._data[key]
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

    def __setitem__(self, key, value):
        self._data[key] = value


def make_wt_row(**overrides):
    now = datetime.now(timezone.utc)
    data = dict(
        id="abc123def456",
        pattern_id="ci-sweeper",
        item_id="fix-auth",
        path="/tmp/worktrees/ci-sweeper/fix-auth",
        branch="loop/ci-sweeper/fix-auth-abc123",
        base_branch="main",
        repo_path="/home/user/project",
        status="active",
        created_at=now,
        acquired_at=now,
        released_at=None,
        last_used_at=now,
        locked_by="worktree-manager",
        locked_at=now,
        lock_expires_at=now + timedelta(hours=1),
        total_edits=0,
        total_tool_calls=0,
        outcome=None,
        error=None,
    )
    data.update(overrides)
    return FakeRow(**data)


@pytest.fixture
def wtm():
    """Create a WorktreeManager with mocked pool."""
    config = WorktreeConfig(
        max_worktrees=3,
        cleanup_age_hours=24,
        worktree_base_dir="/tmp/test-worktrees",
    )
    wm = WorktreeManager("postgresql:///test", config=config)
    wm._pool = MagicMock()
    return wm


def _mock_acquire(wtm, mock_conn):
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=mock_conn)
    cm.__aexit__ = AsyncMock(return_value=None)
    wtm._pool.acquire = MagicMock(return_value=cm)


# ═══════════════════════════════════════════════════════════
# 1. Registration & Acquire
# ═══════════════════════════════════════════════════════════


class TestRegistration:
    """Worktree registration in PostgreSQL."""

    @pytest.mark.asyncio
    async def test_register_inserts_row(self, wtm):
        """_register should insert a worktree record."""
        mock_conn = AsyncMock()
        _mock_acquire(wtm, mock_conn)
        mock_conn.fetchval = AsyncMock(return_value=0)  # count < max
        mock_conn.execute = AsyncMock()

        handle = await wtm._register(
            wt_id="test-id-1",
            pattern_id="ci-sweeper",
            item_id="fix-issue-42",
            path=Path("/tmp/worktrees/ci-sweeper/fix-issue-42"),
            branch="loop/fix-42",
            base_branch="main",
            repo=Path("/home/user/project"),
        )

        assert handle.worktree_id == "test-id-1"
        assert handle.pattern_id == "ci-sweeper"
        assert handle.item_id == "fix-issue-42"
        assert handle.locked is True
        mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_enforces_max(self, wtm):
        """Register should raise when max_worktrees reached."""
        mock_conn = AsyncMock()
        _mock_acquire(wtm, mock_conn)
        mock_conn.fetchval = AsyncMock(return_value=3)  # at limit

        with pytest.raises(RuntimeError, match="Max worktrees"):
            await wtm._register(
                wt_id="overflow",
                pattern_id="ci-sweeper",
                item_id="overflow-item",
                path=Path("/tmp/overflow"),
                branch="loop/overflow",
                base_branch="main",
                repo=Path("/home/user/project"),
            )

    @pytest.mark.asyncio
    async def test_register_tracks_repo_path(self, wtm):
        """Registration should be per-repo, so limits are per-repo."""
        mock_conn = AsyncMock()
        _mock_acquire(wtm, mock_conn)
        mock_conn.fetchval = AsyncMock(return_value=0)  # other repo has room
        mock_conn.execute = AsyncMock()

        handle = await wtm._register(
            wt_id="different-repo",
            pattern_id="ci-sweeper",
            item_id="fix-other",
            path=Path("/tmp/other"),
            branch="loop/other",
            base_branch="main",
            repo=Path("/different/repo"),
        )

        assert handle is not None
        # fetchval should have been called with the correct repo_path
        call_args = mock_conn.fetchval.call_args[0]
        assert len(call_args) >= 2
        assert "worktree_registry" in call_args[0]
        # The repo_path should be in the parameters
        assert any("/different/repo" in str(p) for p in call_args)

    @pytest.mark.asyncio
    async def test_worktree_path_resolution(self, wtm):
        """_worktree_path should resolve to the right directory."""
        repo = Path("/home/user/project")
        path = wtm._worktree_path(repo, "ci-sweeper", "fix-auth")
        assert str(path) == "/tmp/test-worktrees/ci-sweeper/fix-auth"


# ═══════════════════════════════════════════════════════════
# 2. Acquire → Release lifecycle
# ═══════════════════════════════════════════════════════════


class TestAcquireRelease:
    """Acquire with context manager and cleanup."""

    @pytest.mark.asyncio
    async def test_acquire_context_manager(self, wtm):
        """acquire() should register, yield, then release."""
        mock_conn = AsyncMock()
        _mock_acquire(wtm, mock_conn)
        mock_conn.fetchval = AsyncMock(return_value=0)  # within limit
        mock_conn.execute = AsyncMock()

        with patch.object(wtm, "_git_worktree_add") as mock_add:
            with patch.object(wtm, "_git_worktree_remove") as mock_remove:
                with patch.object(wtm, "_git_worktree_prune") as mock_prune:
                    async with wtm.acquire(
                        pattern_id="ci-sweeper",
                        item_id="test-acquire",
                        repo_path="/home/user/project",
                    ) as handle:
                        assert handle is not None
                        assert handle.pattern_id == "ci-sweeper"
                        assert handle.item_id == "test-acquire"
                        # git worktree add should have been called
                        mock_add.assert_called_once()

                    # After exit, git worktree remove should have been called
                    mock_remove.assert_called_once()
                    # Status should be set to 'released'
                    last_status_call = mock_conn.execute.call_args_list[-1]
                    status_sql = last_status_call.args[0]
                    assert "released" in status_sql

    @pytest.mark.asyncio
    async def test_acquire_cleanup_on_failure(self, wtm):
        """If worktree creation fails, registration should be cleaned up."""
        mock_conn = AsyncMock()
        _mock_acquire(wtm, mock_conn)
        mock_conn.fetchval = AsyncMock(return_value=0)
        mock_conn.execute = AsyncMock()

        with patch.object(wtm, "_git_worktree_add", side_effect=RuntimeError("git failed")):
            with patch.object(wtm, "_git_worktree_remove") as mock_remove:
                with pytest.raises(RuntimeError, match="git failed"):
                    async with wtm.acquire(
                        pattern_id="ci-sweeper",
                        item_id="fail-test",
                        repo_path="/home/user/project",
                    ):
                        pass  # should not reach here

                # Should try to clean up the worktree
                mock_remove.assert_called_once()


# ═══════════════════════════════════════════════════════════
# 3. Query & Management
# ═══════════════════════════════════════════════════════════


class TestWorktreeQuery:
    """Querying the worktree registry."""

    @pytest.mark.asyncio
    async def test_list_worktrees(self, wtm):
        mock_conn = AsyncMock()
        _mock_acquire(wtm, mock_conn)
        mock_conn.fetch = AsyncMock(return_value=[
            make_wt_row(pattern_id="ci-sweeper"),
            make_wt_row(pattern_id="pr-babysitter"),
        ])

        result = await wtm.list_worktrees()

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_worktrees_filter_by_pattern(self, wtm):
        mock_conn = AsyncMock()
        _mock_acquire(wtm, mock_conn)
        mock_conn.fetch = AsyncMock(return_value=[
            make_wt_row(pattern_id="ci-sweeper"),
        ])

        result = await wtm.list_worktrees(pattern_id="ci-sweeper")

        assert len(result) == 1
        assert result[0]["pattern_id"] == "ci-sweeper"

    @pytest.mark.asyncio
    async def test_list_worktrees_filter_by_status(self, wtm):
        mock_conn = AsyncMock()
        _mock_acquire(wtm, mock_conn)
        mock_conn.fetch = AsyncMock(return_value=[
            make_wt_row(status="active"),
        ])

        result = await wtm.list_worktrees(status="active")

        assert len(result) == 1
        assert result[0]["status"] == "active"

    @pytest.mark.asyncio
    async def test_get_worktree(self, wtm):
        mock_conn = AsyncMock()
        _mock_acquire(wtm, mock_conn)
        mock_conn.fetchrow = AsyncMock(return_value=make_wt_row(
            pattern_id="ci-sweeper", item_id="fix-auth",
        ))

        result = await wtm.get_worktree("ci-sweeper", "fix-auth")

        assert result is not None
        assert result["pattern_id"] == "ci-sweeper"
        assert result["item_id"] == "fix-auth"

    @pytest.mark.asyncio
    async def test_get_worktree_not_found(self, wtm):
        mock_conn = AsyncMock()
        _mock_acquire(wtm, mock_conn)
        mock_conn.fetchrow = AsyncMock(return_value=None)

        result = await wtm.get_worktree("nonexistent", "nope")

        assert result is None


# ═══════════════════════════════════════════════════════════
# 4. Cleanup
# ═══════════════════════════════════════════════════════════


class TestCleanup:
    """Stale worktree cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_stale_worktrees(self, wtm):
        """cleanup_stale should find and release old worktrees."""
        mock_conn = AsyncMock()
        _mock_acquire(wtm, mock_conn)
        mock_conn.fetch = AsyncMock(return_value=[
            make_wt_row(
                id="stale-1",
                pattern_id="ci-sweeper",
                path="/tmp/stale/worktree",
                repo_path="/home/user/project",
            ),
        ])

        with patch.object(wtm, "_git_worktree_remove") as mock_remove:
            with patch.object(wtm, "_git_worktree_prune") as mock_prune:
                cleaned = await wtm.cleanup_stale(max_age_hours=1)

                assert len(cleaned) == 1
                assert "stale-1" in cleaned

    @pytest.mark.asyncio
    async def test_cleanup_stale_dry_run(self, wtm):
        """Dry run should not delete."""
        mock_conn = AsyncMock()
        _mock_acquire(wtm, mock_conn)
        mock_conn.fetch = AsyncMock(return_value=[
            make_wt_row(id="stale-dry", repo_path="/home/user/project"),
        ])

        with patch.object(wtm, "_git_worktree_remove") as mock_remove:
            cleaned = await wtm.cleanup_stale(max_age_hours=1, dry_run=True)

            assert len(cleaned) == 1
            mock_remove.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_no_stale(self, wtm):
        """No stale worktrees should return empty list."""
        mock_conn = AsyncMock()
        _mock_acquire(wtm, mock_conn)
        mock_conn.fetch = AsyncMock(return_value=[])  # no stale

        cleaned = await wtm.cleanup_stale()

        assert cleaned == []

    @pytest.mark.asyncio
    async def test_stats_returns_defaults(self, wtm):
        """stats should return zeros for missing statuses."""
        mock_conn = AsyncMock()
        _mock_acquire(wtm, mock_conn)
        mock_conn.fetch = AsyncMock(return_value=[])

        stats = await wtm.stats()

        assert stats["active"] == 0
        assert stats["locked"] == 0
        assert stats["stale"] == 0
        assert stats["released"] == 0
        assert stats["orphaned"] == 0

    @pytest.mark.asyncio
    async def test_stats_with_data(self, wtm):
        mock_conn = AsyncMock()
        _mock_acquire(wtm, mock_conn)
        mock_conn.fetch = AsyncMock(return_value=[
            FakeRow(status="active", count=3),
            FakeRow(status="released", count=10),
        ])

        stats = await wtm.stats()

        assert stats["active"] == 3
        assert stats["released"] == 10
        assert stats["stale"] == 0


# ═══════════════════════════════════════════════════════════
# 5. Git Operations
# ═══════════════════════════════════════════════════════════


class TestGitOperations:
    """Git worktree command generation (mocked subprocess)."""

    @pytest.fixture
    def wtm_clean(self):
        """WorktreeManager without pool (for git-only tests)."""
        return WorktreeManager("postgresql:///test")

    def test_git_worktree_add(self, wtm_clean):
        """_git_worktree_add should call git worktree add -b."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            wtm_clean._git_worktree_add(
                repo=Path("/home/user/project"),
                worktree_path=Path("/tmp/worktrees/fix-auth"),
                branch="loop/fix-auth",
                base_branch="main",
            )

            # First call: git fetch origin
            assert mock_run.call_args_list[0].args[0] == [
                "git", "fetch", "origin",
            ]
            # Second call: git worktree add -b
            add_call = mock_run.call_args_list[1].args[0]
            assert add_call[:5] == ["git", "worktree", "add", "-b", "loop/fix-auth"]
            assert add_call[5] == str(Path("/tmp/worktrees/fix-auth"))

    def test_git_worktree_add_fallback_to_local(self, wtm_clean):
        """If origin/ doesn't exist, fallback to local base_branch."""
        with patch("subprocess.run") as mock_run:
            # First call (fetch): ok
            # Second call (origin add): fails
            # Third call (local add): ok
            mock_run.side_effect = [
                MagicMock(returncode=0),                                     # fetch ok
                MagicMock(returncode=1, stderr="fatal: invalid refspec"),    # origin fail
                MagicMock(returncode=0),                                     # local ok
            ]

            wtm_clean._git_worktree_add(
                repo=Path("/home/user/project"),
                worktree_path=Path("/tmp/fix-auth"),
                branch="loop/fix-auth",
                base_branch="main",
            )

            # Check fallback call used local base_branch
            fallback_call = mock_run.call_args_list[2].args[0]
            assert fallback_call[-1] == "main"  # base_branch (no origin/ prefix)

    def test_git_worktree_add_total_failure(self, wtm_clean):
        """If all git worktree add attempts fail, raise RuntimeError."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),                                     # fetch ok
                MagicMock(returncode=1, stderr="fatal: invalid refspec"),    # origin fail
                MagicMock(returncode=1, stderr="fatal: another error"),      # local fail
            ]

            with pytest.raises(RuntimeError, match="git worktree add failed"):
                wtm_clean._git_worktree_add(
                    repo=Path("/home/user/project"),
                    worktree_path=Path("/tmp/fail-path"),
                    branch="loop/fail",
                    base_branch="main",
                )

    def test_git_worktree_remove(self, wtm_clean):
        """_git_worktree_remove should call git worktree remove."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            wtm_clean._git_worktree_remove(Path("/tmp/worktrees/to-remove"))

            mock_run.assert_called_once_with(
                ["git", "worktree", "remove", str(Path("/tmp/worktrees/to-remove"))],
                capture_output=True, timeout=30,
            )

    def test_git_worktree_prune(self, wtm_clean):
        """_git_worktree_prune should call git worktree prune."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            wtm_clean._git_worktree_prune(Path("/home/user/project"))

            mock_run.assert_called_once_with(
                ["git", "worktree", "prune"],
                cwd=Path("/home/user/project"), capture_output=True, timeout=30,
            )

    def test_health_check_success(self, wtm_clean):
        """health_check should return healthy=True when git worktree works."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="worktree /home/user/project abc123\nworktree /tmp/wt abc456\n",
            )

            result = wtm_clean.health_check("/home/user/project")

            assert result["healthy"] is True
            assert result["worktree_count"] == 2

    def test_health_check_failure(self, wtm_clean):
        """health_check should return healthy=False on error."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("git not found")

            result = wtm_clean.health_check("/home/user/project")

            assert result["healthy"] is False
            assert "error" in result


# ═══════════════════════════════════════════════════════════
# 6. Release
# ═══════════════════════════════════════════════════════════


class TestRelease:
    """Manual worktree release."""

    @pytest.mark.asyncio
    async def test_release_with_delete(self, wtm):
        mock_conn = AsyncMock()
        _mock_acquire(wtm, mock_conn)
        row = make_wt_row(
            id="release-me", path="/tmp/worktrees/release-me", repo_path="/home/user/project",
        )
        mock_conn.fetchrow = AsyncMock(return_value=row)
        mock_conn.execute = AsyncMock()

        # The release method calls _git_worktree_remove and _git_worktree_prune
        # via the _get_row + path lookup path
        with patch.object(wtm, "_git_worktree_remove") as mock_remove:
            with patch.object(wtm, "_git_worktree_prune") as mock_prune:
                ok = await wtm.release("release-me", delete=True)

                assert ok is True

    @pytest.mark.asyncio
    async def test_release_not_found(self, wtm):
        mock_conn = AsyncMock()
        _mock_acquire(wtm, mock_conn)
        mock_conn.fetchrow = AsyncMock(return_value=None)

        ok = await wtm.release("nonexistent")

        assert ok is False


# ═══════════════════════════════════════════════════════════
# 7. Config
# ═══════════════════════════════════════════════════════════


class TestConfig:
    """WorktreeConfig defaults and customization."""

    def test_default_config(self):
        config = WorktreeConfig()
        assert config.max_worktrees == 10
        assert config.cleanup_age_hours == 24
        assert config.lock_timeout_seconds == 300

    def test_custom_config(self):
        config = WorktreeConfig(
            max_worktrees=5,
            cleanup_age_hours=48,
            worktree_base_dir="/custom/path",
        )
        assert config.max_worktrees == 5
        assert config.cleanup_age_hours == 48
        assert config.worktree_base_dir == "/custom/path"
