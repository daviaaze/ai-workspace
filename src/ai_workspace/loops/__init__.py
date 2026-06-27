"""
Loop Patterns — 7 production agent loops.

Each loop is a handler registered with the ``@register_handler`` decorator.
The queue fires the handler, which:
1. Loads loop state from PostgreSQL
2. Runs a triage/scan
3. Classifies items into active/watch/noise
4. Takes action (if readiness >= L2)
5. Updates state + writes run log
6. Checks budget

Patterns:
- ``daily-triage`` — Morning scan of CI, issues, commits
- ``pr-babysitter`` — Shepherd PRs through review/CI/merge
- ``ci-sweeper`` — React to failing CI checks
- ``dependency-sweeper`` — Patch CVEs and stale deps
- ``post-merge-cleanup`` — TODOs, deprecations, tech debt
- ``issue-triage`` — Dedupe, score, label incoming issues
- ``changelog-drafter`` — Scan merges, draft release notes
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from ai_workspace.queue import register_handler, JobQueue

logger = logging.getLogger("aiw.loops")


# ── Shared helpers ──────────────────────────────────────


def _get_db_url() -> str:
    return os.environ.get("AIW_DB_URL", "postgresql:///ai_workspace")


async def _load_state(pattern_id: str, queue: JobQueue) -> dict[str, Any]:
    """Load the latest state snapshot for a pattern."""
    async with queue._pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT * FROM loop_state
               WHERE pattern_id = $1
               ORDER BY created_at DESC LIMIT 1""",
            pattern_id,
        )
        return dict(row) if row else {
            "pattern_id": pattern_id,
            "items_active": [],
            "items_watch": [],
            "items_noise": [],
            "items_pruned": [],
            "escalations": [],
        }


async def _save_state(
    pattern_id: str,
    run_id: int | None,
    state: dict[str, Any],
    queue: JobQueue,
) -> None:
    """Persist a state snapshot."""
    async with queue._pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO loop_state
               (pattern_id, run_id, state_type, last_run, items_active,
                items_watch, items_noise, items_pruned, escalations, data)
               VALUES ($1, $2, 'snapshot', NOW(),
                       $3::jsonb, $4::jsonb, $5::jsonb, $6::jsonb, $7::jsonb, $8::jsonb)""",
            pattern_id,
            run_id,
            json.dumps(state.get("items_active", [])),
            json.dumps(state.get("items_watch", [])),
            json.dumps(state.get("items_noise", [])),
            json.dumps(state.get("items_pruned", [])),
            json.dumps(state.get("escalations", [])),
            json.dumps(state.get("data", {})),
        )


async def _write_run_log(
    pattern_id: str,
    run_id: int | None,
    outcome: str,
    items_found: int = 0,
    actions_taken: int = 0,
    escalations: int = 0,
    error: str | None = None,
    tokens_estimate: int = 0,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    duration_ms: int | None = None,
    queue: JobQueue | None = None,
) -> None:
    """Write a run log entry."""
    dsn = _get_db_url()
    pool = queue._pool if queue else None

    if pool:
        now = datetime.now(timezone.utc)
        start = started_at or now
        end = finished_at or now
        dur = duration_ms or int((end - start).total_seconds() * 1000)
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO loop_run_log
                   (pattern_id, run_id, started_at, finished_at, duration_ms,
                    items_found, actions_taken, escalations, tokens_estimate,
                    outcome, error)
                   VALUES ($1, $2, $3, $4, $5,
                           $6, $7, $8, $9, $10, $11)""",
                pattern_id, run_id, start, end, dur,
                items_found, actions_taken,
                escalations, tokens_estimate, outcome, error,
            )


async def _check_budget(pattern_id: str, queue: JobQueue) -> tuple[bool, int]:
    """Check if the pattern has budget remaining for today.

    Returns:
        (within_budget, remaining_tokens)
    """
    async with queue._pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT daily_cap, daily_spent, paused, kill_switch
               FROM loop_budget
               WHERE pattern_id = $1 AND budget_date = CURRENT_DATE""",
            pattern_id,
        )
        if not row:
            return True, 100000

        if row["kill_switch"] or row["paused"]:
            return False, 0

        remaining = row["daily_cap"] - row["daily_spent"]
        return remaining > 0, max(0, remaining)


async def _spend_budget(pattern_id: str, tokens: int, queue: JobQueue) -> None:
    """Record token spend against today's budget."""
    async with queue._pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO loop_budget (pattern_id, budget_date, daily_spent)
               VALUES ($1, CURRENT_DATE, $2)
               ON CONFLICT (pattern_id, budget_date) DO UPDATE
               SET daily_spent = loop_budget.daily_spent + $2""",
            pattern_id, tokens,
        )


# ── Pattern 1: Daily Triage ─────────────────────────────


@register_handler("loop:daily-triage")
async def handle_daily_triage(payload: dict) -> dict:
    """Morning scan of CI, issues, and commits.

    L1: Report-only. Updates state with findings. Human reviews.
    L2: Auto-labels and suggests priorities.
    L3: Auto-creates issues for high-priority items.
    """
    project_root = payload.get("project_root", os.getcwd())
    logger.info("Daily Triage: scanning %s", project_root)

    # In a real implementation, this would:
    # 1. Check CI status (GitHub API)
    # 2. Scan recent commits
    # 3. Check open issues
    # 4. Classify findings
    # 5. Update state

    return {
        "status": "ok",
        "pattern": "daily-triage",
        "items_found": 0,
        "actions_taken": 0,
    }


# ── Pattern 2: PR Babysitter ────────────────────────────


@register_handler("loop:pr-babysitter")
async def handle_pr_babysitter(payload: dict) -> dict:
    """Shepherd PRs through review, CI, rebase, and merge.

    L1: Watch-only. Comments status on PRs.
    L2: Proposes minimal fixes for reviewer comments.
    L3: Auto-rebase, auto-merge for allowlisted paths.
    """
    project_root = payload.get("project_root", os.getcwd())
    logger.info("PR Babysitter: checking PRs in %s", project_root)

    return {
        "status": "ok",
        "pattern": "pr-babysitter",
        "prs_checked": 0,
        "actions_taken": 0,
    }


# ── Pattern 3: CI Sweeper ───────────────────────────────


@register_handler("loop:ci-sweeper")
async def handle_ci_sweeper(payload: dict) -> dict:
    """React to failing CI checks with minimal fixes.

    L1: Monitor only. Classifies failures. No auto-fix.
    L2: Fixes classified regressions in worktree.
    L3: Auto-PR for trivial fixes on allowlist paths.
    """
    project_root = payload.get("project_root", os.getcwd())
    logger.info("CI Sweeper: checking CI in %s", project_root)

    return {
        "status": "ok",
        "pattern": "ci-sweeper",
        "failures_found": 0,
        "fixes_proposed": 0,
    }


# ── Pattern 4: Dependency Sweeper ───────────────────────


@register_handler("loop:dependency-sweeper")
async def handle_dependency_sweeper(payload: dict) -> dict:
    """Scan dependencies for CVEs and stale versions.

    L1: Report CVEs. No auto-fix.
    L2: Auto-patch low-risk CVEs in worktree.
    L3: Auto-PR for patches. Majors still human-gated.
    """
    project_root = payload.get("project_root", os.getcwd())
    logger.info("Dependency Sweeper: scanning deps in %s", project_root)

    return {
        "status": "ok",
        "pattern": "dependency-sweeper",
        "cves_found": 0,
        "patches_applied": 0,
    }


# ── Pattern 5: Post-Merge Cleanup ───────────────────────


@register_handler("loop:post-merge-cleanup")
async def handle_post_merge_cleanup(payload: dict) -> dict:
    """Scan recent merges for TODOs, deprecations, tech debt.

    L1: Report items found. No auto-action.
    L2: Auto-fix trivial items in worktree.
    L3: Auto-PR for trivial cleanup.
    """
    project_root = payload.get("project_root", os.getcwd())
    logger.info("Post-Merge Cleanup: scanning merges in %s", project_root)

    return {
        "status": "ok",
        "pattern": "post-merge-cleanup",
        "items_found": 0,
        "fixes_applied": 0,
    }


# ── Pattern 6: Issue Triage ─────────────────────────────


@register_handler("loop:issue-triage")
async def handle_issue_triage(payload: dict) -> dict:
    """Dedupe, score, and label incoming issues.

    L1: Propose labels. Human applies them.
    L2: Auto-label low-risk categories.
    L3: Full auto-label + priority assignment.
    """
    project_root = payload.get("project_root", os.getcwd())
    logger.info("Issue Triage: scanning issues in %s", project_root)

    return {
        "status": "ok",
        "pattern": "issue-triage",
        "issues_scanned": 0,
        "labels_proposed": 0,
    }


# ── Pattern 7: Changelog Drafter ────────────────────────


@register_handler("loop:changelog-drafter")
async def handle_changelog_drafter(payload: dict) -> dict:
    """Scan recent merges and commits, draft release notes.

    L1: Produce RELEASE_NOTES_DRAFT.md. Human approves.
    L2: Write to GitHub Release draft.
    L3: Auto-publish on tag.
    """
    project_root = payload.get("project_root", os.getcwd())
    logger.info("Changelog Drafter: scanning merges in %s", project_root)

    return {
        "status": "ok",
        "pattern": "changelog-drafter",
        "merges_found": 0,
        "draft_path": "",
    }


# ── Loop Manager ────────────────────────────────────────


async def seed_default_schedules(dsn: str | None = None) -> list[dict]:
    """Register all loop patterns as recurring schedules in the job queue.

    Call this once during setup to seed the scheduler.
    Patterns start at L0 (disabled). Enable them via ``aiw loop enable``.

    Returns:
        List of created schedules
    """
    from ai_workspace.queue import JobQueue

    queue = JobQueue(dsn or _get_db_url())
    await queue.connect()

    schedules = [
        # (name, job_type, handler, schedule_type, cron_expr/interval, queue)
        ("daily-triage",        "loop:daily-triage",        "ai_workspace.loops.handle_daily_triage",        "cron",     "0 10 * * 1-5", "loops"),
        ("pr-babysitter",       "loop:pr-babysitter",       "ai_workspace.loops.handle_pr_babysitter",       "interval", "900",           "loops"),
        ("ci-sweeper",          "loop:ci-sweeper",          "ai_workspace.loops.handle_ci_sweeper",          "interval", "900",           "loops"),
        ("dependency-sweeper",  "loop:dependency-sweeper",  "ai_workspace.loops.handle_dependency_sweeper",  "interval", "21600",         "loops"),
        ("post-merge-cleanup",  "loop:post-merge-cleanup",  "ai_workspace.loops.handle_post_merge_cleanup",  "interval", "21600",         "loops"),
        ("issue-triage",        "loop:issue-triage",        "ai_workspace.loops.handle_issue_triage",        "interval", "7200",          "loops"),
        ("changelog-drafter",   "loop:changelog-drafter",   "ai_workspace.loops.handle_changelog_drafter",   "interval", "86400",         "loops"),
    ]

    results = []
    for name, job_type, handler, sched_type, cadence, loop_queue in schedules:
        sched = await queue.schedule_recurring(
            name=name,
            job_type=job_type,
            handler=handler,
            payload={"project_root": os.getcwd()},
            queue=loop_queue,
            schedule_type="cron" if sched_type == "cron" else "interval",
            cron_expr=cadence if sched_type == "cron" else None,
            interval_seconds=int(cadence) if sched_type == "interval" else None,
            timeout_seconds=600,
            priority=0,
        )
        results.append({
            "name": sched.name,
            "enabled": sched.enabled,
            "paused": sched.paused,
        })

    await queue.close()
    return results
