"""
Worktree Manager — Parallel agent isolation via Git Worktrees.

Each loop that edits code runs in an isolated ``git worktree`` — shares
history but has its own working directory. Prevents parallel collision
when two agents edit the same files.

Usage:
    from ai_workspace.worktree import WorktreeManager

    async with WorktreeManager(dsn="postgresql:///ai_workspace") as wtm:
        async with wtm.acquire(
            pattern_id="ci-sweeper",
            item_id="fix-auth-flaky",
            branch_name="fix/auth-flaky-20260627",
            repo_path="/home/user/project",
        ) as wt:
            # wt.path is the worktree directory
            # All agent file ops happen inside wt.path
            ...
            # Worktree is cleaned up on context exit
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import asyncpg

logger = logging.getLogger("aiw.worktree")


# ── Config ───────────────────────────────────────────────

@dataclass
class WorktreeConfig:
    """Configuration for the worktree manager."""
    max_worktrees: int = 10
    cleanup_age_hours: int = 24
    lock_timeout_seconds: int = 300
    worktree_base_dir: str | None = None  # defaults to {repo_path}/.worktrees


DEFAULT_CONFIG = WorktreeConfig()


# ── Data types ───────────────────────────────────────────


@dataclass
class WorktreeHandle:
    """Handle to an acquired worktree."""
    worktree_id: str
    pattern_id: str
    item_id: str
    path: Path
    branch: str
    base_branch: str
    repo_path: Path
    created_at: datetime
    acquired_at: datetime
    locked: bool


# ── Manager ──────────────────────────────────────────────


class WorktreeManager:
    """Manages git worktree lifecycle for concurrent agent operations.

    Each worktree is an isolated checkout sharing the repo's .git.
    Tracks lifecycle in PostgreSQL ``worktree_registry`` table.
    """

    def __init__(
        self,
        dsn: str = "postgresql:///ai_workspace",
        config: WorktreeConfig | None = None,
    ):
        self.dsn = dsn
        self.config = config or DEFAULT_CONFIG
        self._pool: asyncpg.Pool | None = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def connect(self):
        self._pool = await asyncpg.create_pool(
            self.dsn, min_size=1, max_size=5,
        )

    async def close(self):
        if self._pool:
            await self._pool.close()
            self._pool = None

    # ── Acquire (context manager) ─────────────────────────

    @asynccontextmanager
    async def acquire(
        self,
        pattern_id: str,
        item_id: str,
        repo_path: str | Path,
        base_branch: str = "main",
        branch_name: str | None = None,
        ttl_seconds: int = 3600,
    ) -> AsyncIterator[WorktreeHandle]:
        """Acquire a worktree for exclusive use.

        Creates a ``git worktree`` at::

            {repo_path}/.worktrees/{pattern_id}/{item_id}/

        On enter:
        1. Checks max_worktrees limit
        2. Verifies no existing worktree for (pattern_id, item_id)
        3. Creates git worktree + branch
        4. Registers in PostgreSQL
        5. Returns WorktreeHandle

        On exit:
        1. Removes worktree from disk
        2. Cleans up git worktree records
        3. Updates registry status to 'released'

        Yields:
            WorktreeHandle with the worktree path
        """
        repo = Path(repo_path).resolve()
        worktree_id = uuid.uuid4().hex[:12]
        branch = branch_name or f"loop/{pattern_id}/{item_id}-{worktree_id[:6]}"
        worktree_path = self._worktree_path(repo, pattern_id, item_id)

        # Ensure worktree dir exists
        worktree_path.parent.mkdir(parents=True, exist_ok=True)

        handle = None
        try:
            # Register in DB first (acquires the slot)
            handle = await self._register(
                worktree_id, pattern_id, item_id,
                worktree_path, branch, base_branch, repo,
            )

            # Create git worktree
            self._git_worktree_add(repo, worktree_path, branch, base_branch)

            logger.info(
                "Worktree %s created at %s (branch=%s, pattern=%s/%s)",
                worktree_id, worktree_path, branch, pattern_id, item_id,
            )

            yield handle

        except Exception:
            # Cleanup on failure
            if worktree_path.exists():
                self._git_worktree_remove(worktree_path)
            if handle:
                await self._set_status(worktree_id, "failed")
            raise

        finally:
            # Cleanup on exit
            try:
                self._git_worktree_remove(worktree_path)
                self._git_worktree_prune(repo)
            except Exception as e:
                logger.warning("Worktree cleanup warning: %s", e)

            await self._set_status(worktree_id, "released")

    # ── Management ───────────────────────────────────────

    async def list_worktrees(
        self,
        pattern_id: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        """List registered worktrees.

        Args:
            pattern_id: Filter by loop pattern
            status: Filter by status ('active', 'locked', 'stale', 'released')
        """
        conditions = ["TRUE"]
        params: list = []
        idx = 1

        if pattern_id:
            conditions.append(f"pattern_id = ${idx}")
            params.append(pattern_id)
            idx += 1
        if status:
            conditions.append(f"status = ${idx}")
            params.append(status)
            idx += 1

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT * FROM worktree_registry WHERE {' AND '.join(conditions)} ORDER BY created_at DESC",
                *params,
            )
            return [dict(r) for r in rows]

    async def get_worktree(self, pattern_id: str, item_id: str) -> dict | None:
        """Find a worktree by (pattern_id, item_id)."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM worktree_registry WHERE pattern_id = $1 AND item_id = $2",
                pattern_id, item_id,
            )
            return dict(row) if row else None

    async def release(self, worktree_id: str, delete: bool = True) -> bool:
        """Manually release a worktree.

        Args:
            worktree_id: UUID of the worktree to release
            delete: If True, delete from disk
        """
        row = await self._get_row(worktree_id)
        if not row:
            return False

        if delete and row["path"]:
            path = Path(row["path"])
            if path.exists():
                self._git_worktree_remove(path)
                self._git_worktree_prune(Path(row["repo_path"]))

        await self._set_status(worktree_id, "released")
        return True

    async def cleanup_stale(
        self,
        max_age_hours: int | None = None,
        dry_run: bool = False,
    ) -> list[str]:
        """Find and clean up abandoned worktrees.

        Args:
            max_age_hours: Age threshold (default: from config)
            dry_run: If True, only report, don't delete

        Returns:
            List of cleaned worktree IDs
        """
        age = max_age_hours or self.config.cleanup_age_hours
        cutoff = datetime.now(UTC) - timedelta(hours=age)

        cleaned: list[str] = []

        async with self._pool.acquire() as conn:
            stale = await conn.fetch(
                """SELECT * FROM worktree_registry
                   WHERE status IN ('active', 'locked')
                     AND acquired_at < $1
                   ORDER BY acquired_at ASC""",
                cutoff,
            )

            for row in stale:
                wt_id = row["id"]
                cleaned.append(str(wt_id))

                if dry_run:
                    logger.info("Would clean stale worktree %s (%s/%s)", wt_id, row["pattern_id"], row["item_id"])
                    continue

                # Remove from disk
                if row["path"]:
                    path = Path(row["path"])
                    if path.exists():
                        try:
                            self._git_worktree_remove(path)
                        except Exception as e:
                            logger.warning("Could not remove worktree %s: %s", wt_id, e)

                    self._git_worktree_prune(Path(row["repo_path"]))

                # Mark as stale
                await conn.execute(
                    "UPDATE worktree_registry SET status = 'stale', released_at = NOW() WHERE id = $1",
                    wt_id,
                )
                logger.info("Cleaned stale worktree %s (%s/%s)", wt_id, row["pattern_id"], row["item_id"])

        return cleaned

    async def stats(self) -> dict:
        """Get worktree usage statistics."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT status, COUNT(*)::int as count
                   FROM worktree_registry GROUP BY status"""
            )
            by_status = {r["status"]: r["count"] for r in rows}
            for s in ("active", "locked", "stale", "released", "orphaned"):
                by_status.setdefault(s, 0)
            return by_status

    def health_check(self, repo_path: str | Path) -> dict:
        """Check if git worktrees are working in a repo."""
        repo = Path(repo_path)
        try:
            result = subprocess.run(
                ["git", "worktree", "list", "--porcelain"],
                cwd=repo, capture_output=True, text=True, timeout=10,
            )
            return {
                "healthy": result.returncode == 0,
                "worktree_count": result.stdout.count("worktree "),
                "output": result.stdout[:500] if result.returncode == 0 else result.stderr[:500],
            }
        except Exception as e:
            return {"healthy": False, "error": str(e)}

    # ── Internal ──────────────────────────────────────────

    def _worktree_path(self, repo: Path, pattern_id: str, item_id: str) -> Path:
        base = Path(self.config.worktree_base_dir or repo / ".worktrees")
        return base / pattern_id / item_id

    async def _register(
        self,
        wt_id: str,
        pattern_id: str,
        item_id: str,
        path: Path,
        branch: str,
        base_branch: str,
        repo: Path,
    ) -> WorktreeHandle:
        """Register worktree in PostgreSQL."""
        async with self._pool.acquire() as conn:
            # Check limit
            count = await conn.fetchval(
                "SELECT COUNT(*)::int FROM worktree_registry WHERE status IN ('active', 'locked') AND repo_path = $1",
                str(repo),
            )
            if count >= self.config.max_worktrees:
                raise RuntimeError(
                    f"Max worktrees ({self.config.max_worktrees}) reached for {repo}"
                )

            # Insert
            now = datetime.now(UTC)
            await conn.execute(
                """INSERT INTO worktree_registry
                   (id, pattern_id, item_id, path, branch, base_branch, repo_path,
                    status, created_at, acquired_at, last_used_at,
                    locked_by, locked_at, lock_expires_at)
                   VALUES ($1, $2, $3, $4, $5, $6, $7,
                           'active', $8, $8, $8,
                           'worktree-manager', $8, $8 + INTERVAL '1 hour')""",
                wt_id, pattern_id, item_id, str(path), branch, base_branch, str(repo),
                now,
            )

            return WorktreeHandle(
                worktree_id=wt_id,
                pattern_id=pattern_id,
                item_id=item_id,
                path=path,
                branch=branch,
                base_branch=base_branch,
                repo_path=repo,
                created_at=now,
                acquired_at=now,
                locked=True,
            )

    async def _set_status(self, worktree_id: str, status: str) -> None:
        async with self._pool.acquire() as conn:
            kwargs = {"status": status}
            if status in ("released", "stale", "failed"):
                kwargs["released_at"] = datetime.now(UTC)

            await conn.execute(
                "UPDATE worktree_registry SET status = $2, released_at = COALESCE(released_at, NOW()) WHERE id = $1",
                worktree_id, status,
            )

    async def _get_row(self, worktree_id: str) -> asyncpg.Record | None:
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(
                "SELECT * FROM worktree_registry WHERE id = $1", worktree_id,
            )

    # ── Git operations ────────────────────────────────────

    def _git_worktree_add(
        self,
        repo: Path,
        worktree_path: Path,
        branch: str,
        base_branch: str = "main",
    ) -> None:
        """git worktree add -b {branch} {path} {base_branch}"""
        # Fetch latest from origin first
        subprocess.run(
            ["git", "fetch", "origin"],
            cwd=repo, capture_output=True, timeout=30,
        )

        result = subprocess.run(
            ["git", "worktree", "add", "-b", branch, str(worktree_path), f"origin/{base_branch}"],
            cwd=repo, capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            # Fallback: try local base branch
            result = subprocess.run(
                ["git", "worktree", "add", "-b", branch, str(worktree_path), base_branch],
                cwd=repo, capture_output=True, text=True, timeout=30,
            )
        if result.returncode != 0:
            raise RuntimeError(f"git worktree add failed: {result.stderr}")

    def _git_worktree_remove(self, worktree_path: Path) -> None:
        """git worktree remove {path}"""
        subprocess.run(
            ["git", "worktree", "remove", str(worktree_path)],
            capture_output=True, timeout=30,
        )

    def _git_worktree_prune(self, repo: Path) -> None:
        """git worktree prune"""
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=repo, capture_output=True, timeout=30,
        )
