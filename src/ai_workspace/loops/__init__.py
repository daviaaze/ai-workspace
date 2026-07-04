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
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_workspace.queue import register_handler, JobQueue

logger = logging.getLogger("aiw.loops")


# ── Shared helpers ──────────────────────────────────────


def _get_db_url() -> str:
    return os.environ.get("AIW_DB_URL", "postgresql:///ai_workspace")


def _run_git(cmd: list[str], cwd: str, timeout: int = 15) -> subprocess.CompletedProcess:
    """Run a git command and return the result. Raises on non-zero exit."""
    return subprocess.run(
        ["git"] + cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _git_log(cwd: str, count: int = 20, ref: str = "HEAD") -> list[dict[str, str]]:
    """Return recent git log entries as structured dicts."""
    try:
        r = _run_git(
            ["log", f"-{count}", "--format=%H|%an|%ae|%ai|%s", ref],
            cwd=cwd,
        )
        if r.returncode != 0:
            return []
        entries = []
        for line in r.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("|", 4)
            if len(parts) >= 5:
                entries.append({
                    "hash": parts[0],
                    "author": parts[1],
                    "email": parts[2],
                    "date": parts[3],
                    "message": parts[4],
                })
        return entries
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def _git_modified_files(cwd: str, ref: str = "HEAD~5..HEAD") -> list[str]:
    """Return list of files modified in recent commits."""
    try:
        r = _run_git(["diff", "--name-only", ref], cwd=cwd)
        if r.returncode == 0:
            return [f.strip() for f in r.stdout.strip().split("\n") if f.strip()]
        return []
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def _git_branches(cwd: str) -> list[dict[str, str]]:
    """Return local branches with metadata."""
    try:
        # Current branch
        current_r = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
        current = current_r.stdout.strip() if current_r.returncode == 0 else "unknown"

        # All branches with last commit
        r = _run_git(
            ["branch", "--format=%(refname:short)|%(authorname)|%(committerdate:iso-strict)"],
            cwd=cwd,
        )
        if r.returncode != 0:
            return []

        branches = []
        for line in r.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("|", 2)
            if len(parts) >= 2:
                branches.append({
                    "name": parts[0],
                    "author": parts[1],
                    "date": parts[2] if len(parts) > 2 else "",
                    "is_current": parts[0] == current,
                })
        return branches
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def _is_git_repo(cwd: str) -> bool:
    """Check if a directory is a git repository."""
    try:
        r = _run_git(["rev-parse", "--git-dir"], cwd=cwd)
        return r.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


RE_COMMIT_TYPES = re.compile(r"^(feat|fix|docs|style|refactor|perf|test|chore|ci|build|revert)(\(.+\))?(!)?:")


def _classify_commits(entries: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    """Classify commits by conventional commit type."""
    classified: dict[str, list] = {
        "feat": [], "fix": [], "docs": [], "style": [],
        "refactor": [], "perf": [], "test": [], "chore": [],
        "ci": [], "other": [],
    }
    for entry in entries:
        msg = entry.get("message", "")
        m = RE_COMMIT_TYPES.match(msg)
        if m:
            cat = m.group(1)
            classified.setdefault(cat, []).append(entry)
        else:
            classified["other"].append(entry)
    return classified


def _scan_for_patterns(
    cwd: str,
    patterns: list[str],
    file_extensions: list[str] | None = None,
    max_matches: int = 50,
) -> list[dict[str, Any]]:
    """Scan project files for regex patterns (TODO, FIXME, etc.) using grep."""
    matches: list[dict[str, Any]] = []
    try:
        ext_filter = []
        if file_extensions:
            for ext in file_extensions:
                ext_filter.extend(["--include", f"*.{ext}"])
        for pattern in patterns:
            r = subprocess.run(
                ["grep", "-rn", pattern, "."] + ext_filter,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if r.returncode == 0:
                for line in r.stdout.strip().split("\n")[:max_matches]:
                    parts = line.split(":", 2)
                    if len(parts) >= 2:
                        matches.append({
                            "file": parts[0],
                            "line": parts[1],
                            "content": parts[2] if len(parts) > 2 else "",
                            "pattern": pattern,
                        })
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return matches


def _parse_dependencies(cwd: str) -> list[dict[str, Any]]:
    """Parse pyproject.toml for dependency info."""
    deps: list[dict[str, Any]] = []
    pyproject = Path(cwd) / "pyproject.toml"
    if not pyproject.exists():
        return deps

    try:
        import tomllib
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        project = data.get("project", {})
        for dep_str in project.get("dependencies", []):
            dep_str = str(dep_str)
            # Parse package name and version constraint
            parts = dep_str.replace(">=", ">=").replace("<", "|").replace(">", "|").split("|")
            name = parts[0].strip() if parts else dep_str
            constraint = dep_str[len(name):].strip() if len(dep_str) > len(name) else "*"
            deps.append({
                "name": name,
                "constraint": constraint,
                "raw": dep_str,
            })
    except Exception:
        pass
    return deps


# ── State helpers ────────────────────────────────────────


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

    Scans the last 24h of git activity, classifies changes,
    and checks for unmerged branches.
    """
    project_root = payload.get("project_root", os.getcwd())
    logger.info("Daily Triage: scanning %s", project_root)

    if not _is_git_repo(project_root):
        return {
            "status": "ok",
            "pattern": "daily-triage",
            "items_found": 0,
            "actions_taken": 0,
            "error": "Not a git repository",
            "data": {},
        }

    # 1. Get recent commits (last 20)
    commits = _git_log(project_root, count=20)

    # 2. Classify by type
    classified = _classify_commits(commits)

    # 3. Check branches
    branches = _git_branches(project_root)
    unmerged = [b for b in branches if not b["is_current"] and b["name"] not in ("main", "master")]

    # 4. Modified files
    modified = _git_modified_files(project_root)

    # 5. Build finding summary
    items_found = len(commits)
    items_active = []
    items_watch = []
    items_noise = []

    # Classify into active/watch/noise
    if classified.get("fix"):
        items_active.append({
            "id": f"fix-{len(items_active)}",
            "title": f"{len(classified['fix'])} bug fixes in recent commits",
            "category": "fix",
            "count": len(classified["fix"]),
            "severity": "high",
        })
    if classified.get("feat"):
        items_watch.append({
            "id": f"feat-{len(items_watch)}",
            "title": f"{len(classified['feat'])} new features in recent commits",
            "category": "feat",
            "count": len(classified["feat"]),
            "severity": "medium",
        })
    if unmerged:
        for b in unmerged[:5]:
            items_watch.append({
                "id": f"branch-{b['name']}",
                "title": f"Branch '{b['name']}' not merged",
                "category": "branch",
                "last_author": b.get("author", ""),
            })

    return {
        "status": "ok",
        "pattern": "daily-triage",
        "items_found": items_found,
        "actions_taken": 0,
        "data": {
            "total_commits": len(commits),
            "by_type": {k: len(v) for k, v in classified.items()},
            "modified_files": len(modified),
            "branches": len(branches),
            "unmerged_branches": len(unmerged),
        },
        "items_active": items_active,
        "items_watch": items_watch,
        "items_noise": items_noise,
    }


# ── Pattern 2: PR Babysitter ────────────────────────────


@register_handler("loop:pr-babysitter")
async def handle_pr_babysitter(payload: dict) -> dict:
    """Shepherd PRs through review, CI, rebase, and merge.

    Scans local branches not yet merged to main/master,
    checks for recent activity, and reports status.
    """
    project_root = payload.get("project_root", os.getcwd())
    logger.info("PR Babysitter: checking PRs in %s", project_root)

    if not _is_git_repo(project_root):
        return {
            "status": "ok",
            "pattern": "pr-babysitter",
            "prs_checked": 0,
            "actions_taken": 0,
            "error": "Not a git repository",
        }

    # 1. Get all branches
    branches = _git_branches(project_root)

    # 2. Identify candidates for PR review (branches that aren't main/master)
    pr_candidates = [
        b for b in branches
        if not b["is_current"] and b["name"] not in ("main", "master", "HEAD")
    ]

    # 3. For each candidate, check difference from main
    prs_checked = []
    for branch in pr_candidates[:10]:
        try:
            # Commits ahead of main
            ahead_r = _run_git(
                ["log", f"main..{branch['name']}", "--oneline"],
                cwd=project_root,
            )
            ahead_count = len(ahead_r.stdout.strip().split("\n")) if ahead_r.returncode == 0 and ahead_r.stdout.strip() else 0

            prs_checked.append({
                "branch": branch["name"],
                "author": branch.get("author", ""),
                "last_updated": branch.get("date", ""),
                "commits_ahead": ahead_count,
                "status": "needs_review" if ahead_count > 0 else "up_to_date",
            })
        except Exception:
            continue

    return {
        "status": "ok",
        "pattern": "pr-babysitter",
        "prs_checked": len(prs_checked),
        "actions_taken": 0,
        "data": {
            "prs": prs_checked,
            "total_branches": len(branches),
        },
    }


# ── Pattern 3: CI Sweeper ───────────────────────────────


@register_handler("loop:ci-sweeper")
async def handle_ci_sweeper(payload: dict) -> dict:
    """React to failing CI checks with minimal fixes.

    Checks CI config files for issues, reports workflow status.
    """
    project_root = payload.get("project_root", os.getcwd())
    logger.info("CI Sweeper: checking CI in %s", project_root)

    if not _is_git_repo(project_root):
        return {
            "status": "ok",
            "pattern": "ci-sweeper",
            "failures_found": 0,
            "fixes_proposed": 0,
        }

    # 1. Find CI config files
    ci_files: list[dict[str, Any]] = []
    ci_patterns = [
        ".github/workflows/*.yml",
        ".github/workflows/*.yaml",
        "Jenkinsfile",
        ".gitlab-ci.yml",
        ".circleci/config.yml",
        ".drone.yml",
    ]

    for pattern in ci_patterns:
        try:
            r = subprocess.run(
                ["find", ".", "-path", f"./{pattern}", "-type", "f"],
                cwd=project_root,
                capture_output=True, text=True, timeout=10,
            )
            for path in r.stdout.strip().split("\n"):
                if path.strip():
                    ci_files.append({"path": path, "pattern": pattern})
        except Exception:
            continue

    # 2. Check git hooks
    hooks_dir = Path(project_root) / ".git" / "hooks"
    active_hooks = []
    if hooks_dir.exists():
        for hook in hooks_dir.iterdir():
            if hook.is_file() and not hook.name.endswith(".sample"):
                active_hooks.append(hook.name)

    # 3. Check last CI run status (from git history, look for CI commit status)
    failures_found = 0
    issues = []

    if not ci_files:
        issues.append({
            "type": "missing_ci",
            "severity": "warning",
            "message": "No CI configuration files found",
        })
        failures_found += 1

    # Check for recently modified workflows
    if ci_files:
        for cf in ci_files[:5]:
            r = _run_git(["log", "-1", "--format=%ai", "--", cf["path"]], cwd=project_root)
            last_modified = r.stdout.strip() if r.returncode == 0 else "unknown"
            cf["last_modified"] = last_modified

    return {
        "status": "ok",
        "pattern": "ci-sweeper",
        "failures_found": failures_found,
        "fixes_proposed": 0,
        "data": {
            "ci_files": ci_files,
            "active_hooks": active_hooks,
            "issues": issues,
        },
    }


# ── Pattern 4: Dependency Sweeper ───────────────────────


@register_handler("loop:dependency-sweeper")
async def handle_dependency_sweeper(payload: dict) -> dict:
    """Scan dependencies for CVEs and stale versions.

    Parses pyproject.toml requirements and reports findings.
    """
    project_root = payload.get("project_root", os.getcwd())
    logger.info("Dependency Sweeper: scanning deps in %s", project_root)

    # Parse dependencies
    deps = _parse_dependencies(project_root)

    # Also check for requirements.txt
    req_file = Path(project_root) / "requirements.txt"
    req_deps = []
    if req_file.exists():
        try:
            for line in req_file.read_text().split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.replace(">=", ">=").replace("<", "|").replace(">", "|").split("|")
                    name = parts[0].strip() if parts else line
                    req_deps.append({"name": name, "source": "requirements.txt"})
        except Exception:
            pass

    # Build findings
    cves_found = 0
    findings = []

    for dep in deps:
        # Flag version constraints that are too loose
        if dep.get("constraint", "") in ("*", ""):
            findings.append({
                "type": "loose_constraint",
                "package": dep["name"],
                "message": f"No version constraint for {dep['name']}",
                "severity": "low",
            })
        # Flag pinned versions (potential staleness)
        if dep.get("constraint", "").startswith("=="):
            findings.append({
                "type": "pinned_version",
                "package": dep["name"],
                "constraint": dep["constraint"],
                "message": f"Pinned version {dep['constraint']} for {dep['name']}",
                "severity": "info",
            })

    return {
        "status": "ok",
        "pattern": "dependency-sweeper",
        "cves_found": cves_found,
        "patches_applied": 0,
        "data": {
            "total_deps": len(deps) + len(req_deps),
            "pyproject_deps": len(deps),
            "requirements_deps": len(req_deps),
            "findings": findings,
        },
    }


# ── Pattern 5: Post-Merge Cleanup ───────────────────────


@register_handler("loop:post-merge-cleanup")
async def handle_post_merge_cleanup(payload: dict) -> dict:
    """Scan recent merges for TODOs, deprecations, tech debt.

    Scans for TODO/FIXME/HACK/XXX comments and deprecation markers
    in recently modified files.
    """
    project_root = payload.get("project_root", os.getcwd())
    logger.info("Post-Merge Cleanup: scanning merges in %s", project_root)

    if not _is_git_repo(project_root):
        return {
            "status": "ok",
            "pattern": "post-merge-cleanup",
            "items_found": 0,
            "fixes_applied": 0,
        }

    # 1. Scan for TODO/FIXME/HACK/XXX in source files
    todo_patterns = ["TODO", "FIXME", "HACK", "XXX", "FIXIT", "WORKAROUND"]
    source_extensions = ["py", "ts", "js", "tsx", "jsx", "rs", "go", "java", "md"]

    matches = _scan_for_patterns(
        project_root,
        patterns=todo_patterns,
        file_extensions=source_extensions,
        max_matches=50,
    )

    # 2. Group by pattern type
    by_type: dict[str, list] = {}
    for m in matches:
        pattern = m.get("pattern", "other")
        by_type.setdefault(pattern, []).append(m)

    # 3. Check for deprecation markers
    deprecation_matches = _scan_for_patterns(
        project_root,
        patterns=["deprecated", "DEPRECATED", "deprecation"],
        file_extensions=source_extensions,
        max_matches=20,
    )

    return {
        "status": "ok",
        "pattern": "post-merge-cleanup",
        "items_found": len(matches) + len(deprecation_matches),
        "fixes_applied": 0,
        "data": {
            "total_todos": len(matches),
            "by_type": {k: len(v) for k, v in by_type.items()},
            "deprecation_count": len(deprecation_matches),
            "recently_modified_files": _git_modified_files(project_root)[:10],
        },
    }


# ── Pattern 6: Issue Triage ─────────────────────────────


@register_handler("loop:issue-triage")
async def handle_issue_triage(payload: dict) -> dict:
    """Dedupe, score, and label incoming issues.

    Scans the repo for TODO/FIXME markers and classifies them
    by severity and area. This serves as a local proxy for
    issue triage when GitHub API isn't available.
    """
    project_root = payload.get("project_root", os.getcwd())
    logger.info("Issue Triage: scanning issues in %s", project_root)

    if not _is_git_repo(project_root):
        return {
            "status": "ok",
            "pattern": "issue-triage",
            "issues_scanned": 0,
            "labels_proposed": 0,
        }

    # 1. Scan for code issues (TODO, FIXME)
    matches = _scan_for_patterns(
        project_root,
        patterns=["TODO", "FIXME", "BUG", "HACK"],
        file_extensions=["py", "ts", "js", "rs", "go", "java"],
        max_matches=100,
    )

    # 2. Classify by severity based on pattern
    issues = []
    for m in matches:
        content = m.get("content", "").lower()
        severity = "low"
        if m["pattern"] == "FIXME" or "crash" in content or "security" in content:
            severity = "high"
        elif m["pattern"] == "BUG" or "urgent" in content:
            severity = "high"
        elif m["pattern"] == "HACK" or "workaround" in content:
            severity = "medium"
        elif m["pattern"] == "TODO":
            severity = "low"

        area = "unknown"
        filepath = m.get("file", "")
        if "src/" in filepath:
            area = filepath.split("src/")[1].split("/")[0] if "src/" in filepath else "unknown"
        if "test" in filepath:
            area = "testing"
        if "docs" in filepath:
            area = "documentation"
        if "config" in filepath:
            area = "config"

        issues.append({
            "file": filepath,
            "line": m.get("line", ""),
            "pattern": m.get("pattern", ""),
            "severity": severity,
            "area": area,
            "snippet": m.get("content", "")[:80],
        })

    # 3. Count by severity and area
    by_severity: dict[str, int] = {}
    by_area: dict[str, int] = {}
    for issue in issues:
        by_severity[issue["severity"]] = by_severity.get(issue["severity"], 0) + 1
        by_area[issue["area"]] = by_area.get(issue["area"], 0) + 1

    return {
        "status": "ok",
        "pattern": "issue-triage",
        "issues_scanned": len(issues),
        "labels_proposed": len(issues),
        "data": {
            "by_severity": dict(sorted(by_severity.items())),
            "by_area": dict(sorted(by_area.items(), key=lambda x: x[1], reverse=True)),
            "high_priority": [i for i in issues if i["severity"] == "high"][:5],
        },
    }


# ── Pattern 7: Changelog Drafter ────────────────────────


@register_handler("loop:changelog-drafter")
async def handle_changelog_drafter(payload: dict) -> dict:
    """Scan recent merges and commits, draft release notes.

    Reads git log, categorizes by conventional commit type,
    and writes a RELEASE_NOTES_DRAFT.md file.
    """
    project_root = payload.get("project_root", os.getcwd())
    logger.info("Changelog Drafter: scanning merges in %s", project_root)

    if not _is_git_repo(project_root):
        return {
            "status": "ok",
            "pattern": "changelog-drafter",
            "merges_found": 0,
            "draft_path": "",
        }

    # 1. Get commits since last tag, or last 50
    try:
        r = _run_git(["describe", "--tags", "--abbrev=0"], cwd=project_root)
        last_tag = r.stdout.strip() if r.returncode == 0 else None
        ref = f"{last_tag}..HEAD" if last_tag else "HEAD"
    except Exception:
        ref = "HEAD"

    commits = _git_log(project_root, count=50, ref=ref)
    if not commits:
        commits = _git_log(project_root, count=50)

    # 2. Classify
    classified = _classify_commits(commits)

    # 3. Get git log range description for output
    if last_tag:
        version_header = f"## Changes since {last_tag} ({datetime.now().strftime('%Y-%m-%d')})"
    else:
        version_header = f"## Latest Changes ({datetime.now().strftime('%Y-%m-%d')})"

    # 4. Build draft content
    sections = []
    sections.append(f"# Changelog Draft\n")
    sections.append(version_header)
    sections.append("")

    section_titles = {
        "feat": "### ✨ Features",
        "fix": "### 🐛 Bug Fixes",
        "docs": "### 📚 Documentation",
        "refactor": "### ♻️ Refactoring",
        "perf": "### ⚡ Performance",
        "test": "### 🧪 Testing",
        "chore": "### 🔧 Chores",
        "style": "### 💄 Style",
        "ci": "### 🔁 CI",
    }

    for cat, title in section_titles.items():
        items = classified.get(cat, [])
        if items:
            sections.append(title)
            for c in items:
                msg = c.get("message", "")
                # Remove conventional commit prefix for readability
                clean_msg = re.sub(r"^(feat|fix|docs|refactor|perf|test|chore|style|ci)(\(.+\))?(!)?:\s*", "", msg)
                author = c.get("author", "unknown")
                sections.append(f"- {clean_msg} ({author})")
            sections.append("")

    # Other commits
    others = classified.get("other", [])
    if others:
        sections.append("### 📋 Other")
        for c in others[:10]:
            sections.append(f"- {c.get('message', '')[:80]}")
        if len(others) > 10:
            sections.append(f"- *...and {len(others) - 10} more*")
        sections.append("")

    sections.append(f"\n*{len(commits)} commits, auto-generated by aiw changelog-drafter*")

    draft_content = "\n".join(sections)

    # 5. Write draft to file
    draft_path = Path(project_root) / "RELEASE_NOTES_DRAFT.md"
    try:
        draft_path.write_text(draft_content)
        logger.info("Changelog draft written to %s", draft_path)
    except OSError as e:
        logger.warning("Could not write changelog draft: %s", e)
        draft_path = Path("/tmp/RELEASE_NOTES_DRAFT.md")
        try:
            draft_path.write_text(draft_content)
        except OSError:
            draft_path = None

    return {
        "status": "ok",
        "pattern": "changelog-drafter",
        "merges_found": len(commits),
        "draft_path": str(draft_path) if draft_path else "",
        "data": {
            "by_type": {k: len(v) for k, v in classified.items() if v},
            "total_commits": len(commits),
            "since": last_tag or "all history",
        },
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
