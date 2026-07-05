"""
Data loader — connects the TUI to the real knowledge store.

Falls back to data from memory/ markdown files and git status
if the database is unavailable.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def _count_markdown_sections(memory_type: str) -> int:
    """Count sections in a memory markdown file."""
    workspace = Path(os.environ.get("AIW_WORKSPACE", Path.home() / "Projects" / "pessoal" / "ai-workspace"))
    filepath = workspace / "memory" / f"{memory_type}.md"
    if filepath.exists():
        content = filepath.read_text()
        # Count sections separated by '---' that contain a '## ' heading
        return len([s for s in content.split("\n---") if "## " in s])
    return 0


def _load_tasks_from_memory() -> list[dict[str, Any]]:
    """Try to load task-like entries from memory files."""
    workspace = Path(os.environ.get("AIW_WORKSPACE", Path.home() / "Projects" / "pessoal" / "ai-workspace"))
    filepath = workspace / "memory" / "learning-log.md"
    tasks: list[dict[str, Any]] = []

    if filepath.exists():
        content = filepath.read_text()
        # Parse recent learning entries as tasks
        entries = content.split("\n## ")
        for i, entry in enumerate(entries[1:6], 1):  # Last 5 entries
            title = entry.split("\n")[0].strip()[:60]
            tasks.append({
                "id": f"mem-{i}",
                "title": title or f"Learning entry {i}",
                "status": "completed" if "fix" in entry.lower() or "resolved" in entry.lower() else "ongoing",
                "agent": "sys",
                "progress": 100 if "fix" in entry.lower() else 50,
                "assignee": "agent",
                "priority": 3,
            })

    # Also check git status for active work
    try:
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True, text=True, cwd=str(workspace), timeout=3
        )
        if result.returncode == 0 and result.stdout.strip():
            files = [f for f in result.stdout.strip().split("\n") if f]
            tasks.append({
                "id": "git-changes",
                "title": f"Uncommitted changes ({len(files)} files)",
                "status": "ongoing",
                "agent": "coding",
                "progress": 50,
                "assignee": "agent",
                "priority": 5,
            })
    except Exception:
        pass

    return tasks if tasks else [
        {"id": "demo-1", "title": "Start the TUI and spawn an agent", "status": "notstarted", "agent": "general", "progress": 0, "assignee": "agent"},
        {"id": "demo-2", "title": "Run aiw search for research", "status": "notstarted", "agent": "research", "progress": 0, "assignee": "agent"},
    ]


def load_tasks(limit: int = 50) -> list[dict[str, Any]]:
    """Load tasks from the knowledge store, with markdown fallback."""
    try:
        from ai_workspace.knowledge import KnowledgeStore
        store = KnowledgeStore()
        store.initialize()
        tasks = store.get_tasks(limit=limit)
        store.close()

        result = []
        for t in tasks:
            result.append({
                "id": str(t.get("id", "")),
                "title": t.get("title", "?")[:60],
                "status": t.get("status", "notstarted"),
                "agent": t.get("agent", ""),
                "progress": float(t.get("progress", 0)),
                "assignee": t.get("assignee", "agent"),
                "priority": t.get("priority", 0),
            })

        if result:
            return result
    except Exception:
        pass

    # Fallback: load from memory/ markdown files
    return _load_tasks_from_memory()


def load_metrics() -> dict[str, Any]:
    """Load metrics from the knowledge store and cache, with fallback."""
    try:
        from ai_workspace.core.cost import CostService
        from ai_workspace.knowledge import KnowledgeStore

        store = KnowledgeStore()
        store.initialize()
        c = store.conn.cursor()

        c.execute("SELECT COUNT(*) FROM tasks")
        total = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM tasks WHERE status IN ('ongoing', 'in_progress')")
        active = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM agent_memory")
        memories = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM knowledge_entries")
        kb_entries = c.fetchone()[0]

        c.close()
        store.close()

        # Cache & cost stats
        cost = CostService()
        cache_stats = cost.cache.stats()
        today_cost = cost.budget.today_spent()
        month_cost = cost.budget.month_spent()

        # Source reputation stats
        try:
            from ai_workspace.core.sources import SourceReputationService
            src = SourceReputationService()
            src.initialize()
            src_stats = src.stats()
        except Exception:
            src_stats = {"total_domains": 0, "cred1_coverage": 0, "avg_score": 0.5}

        return {
            "tasks_active": active,
            "tasks_total": total,
            "memories": memories,
            "kb_entries": kb_entries,
            "db_connected": True,
            "cache_entries": cache_stats["total_entries"],
            "cache_hits": cache_stats["total_hits"],
            "tokens_saved": cache_stats["tokens_saved"],
            "cost_saved": cache_stats["cost_saved"],
            "today_cost": today_cost,
            "month_cost": month_cost,
            "source_domains": src_stats["total_domains"],
            "source_cred1": src_stats["cred1_coverage"],
            "source_avg_score": src_stats["avg_score"],
        }
    except Exception:
        pass

    # Fallback: count from memory/ markdown files
    memories_count = sum(_count_markdown_sections(t) for t in ('conventions', 'project-patterns', 'learning-log'))

    # Try to get cache stats from local files
    cache_entries = 0
    try:
        workspace = Path(os.environ.get("AIW_WORKSPACE", Path.home() / "Projects" / "pessoal" / "ai-workspace"))
        research_dir = workspace / "data" / "research"
        if research_dir.exists():
            cache_entries = len(list(research_dir.glob("*.json")))
    except Exception:
        pass

    tasks = _load_tasks_from_memory()

    return {
        "tasks_active": len([t for t in tasks if t.get("status") == "ongoing"]),
        "tasks_total": len(tasks),
        "memories": memories_count,
        "kb_entries": cache_entries,
        "db_connected": False,
        "cache_entries": cache_entries,
        "cache_hits": 0,
        "tokens_saved": 0,
        "cost_saved": 0.0,
        "today_cost": 0.0,
        "month_cost": 0.0,
        "source_domains": 0,
        "source_cred1": 0,
        "source_avg_score": 0.5,
    }


def load_agent_status() -> list[dict[str, Any]]:
    """Load agent connection status.

    Returns real agent status when workers are active. Empty list when idle.
    The TUI updates this via update_agents() when agents are spawned.
    """
    return []
