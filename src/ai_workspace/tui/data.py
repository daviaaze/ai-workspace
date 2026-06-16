"""
Data loader — connects the TUI to the real knowledge store.

Falls back to demo data if the database is unavailable.
"""

from __future__ import annotations

from typing import Any


def load_tasks(limit: int = 50) -> list[dict[str, Any]]:
    """Load tasks from the knowledge store, with demo fallback."""
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
    
    # Demo fallback
    return [
        {"id": "demo-1", "title": "Fix auth middleware bug", "status": "ongoing", "agent": "coding", "progress": 80, "assignee": "agent"},
        {"id": "demo-2", "title": "Add integration tests for TUI", "status": "notstarted", "agent": "coding", "progress": 0, "assignee": "agent"},
        {"id": "demo-3", "title": "Research MCP tool marketplace", "status": "ongoing", "agent": "research", "progress": 40, "assignee": "agent"},
        {"id": "demo-4", "title": "Set up CI/CD pipeline", "status": "completed", "agent": "devops", "progress": 100, "assignee": "agent"},
        {"id": "demo-5", "title": "Daily knowledge sync", "status": "cron", "agent": "sys", "progress": 0, "assignee": "agent"},
    ]


def load_metrics() -> dict[str, Any]:
    """Load metrics from the knowledge store and cache, with demo fallback."""
    try:
        from ai_workspace.knowledge import KnowledgeStore
        from ai_workspace.core.cost import CostService
        
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
        today_cost = cost.logger.today_cost()
        month_cost = cost.logger.month_cost()
        
        # Source reputation stats
        try:
            from ai_workspace.core.sources import SourceReputationService
            src = SourceReputationService()
            src_stats = src.stats()
        except Exception:
            src_stats = {"total_domains": 0, "cred1_coverage": 0, "avg_score": 0.5}
        
        return {
            "tasks_active": active,
            "tasks_total": total,
            "memories": memories,
            "kb_entries": kb_entries,
            "db_connected": True,
            # Cache stats
            "cache_entries": cache_stats["total_entries"],
            "cache_hits": cache_stats["total_hits"],
            "tokens_saved": cache_stats["tokens_saved"],
            "cost_saved": cache_stats["cost_saved"],
            "today_cost": today_cost,
            "month_cost": month_cost,
            # Source stats
            "source_domains": src_stats["total_domains"],
            "source_cred1": src_stats["cred1_coverage"],
            "source_avg_score": src_stats["avg_score"],
        }
    except Exception:
        return {
            "tasks_active": 3,
            "tasks_total": 5,
            "memories": 0,
            "kb_entries": 0,
            "db_connected": False,
            "cache_entries": 0,
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
    """Load agent connection status, with demo fallback."""
    # In the future, this will query the MCP server manager for active sessions
    # For now, return demo data
    return [
        {"name": "coding", "model": "claude-3.7", "node": "local", "online": True,
         "current_task": "Fix auth middleware bug", "task_status": "ongoing", "task_progress": 80},
        {"name": "research", "model": "gemini-2.5", "node": "local", "online": True,
         "current_task": "Research MCP tools", "task_status": "ongoing", "task_progress": 40},
    ]
