"""
Dashboard overlay (F3) — stats, activity, cost snapshot.
All colors use theme variables ($primary, $text, etc.).
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Static


class StatCard(Static):
    """Single metric card: label + value."""

    label: reactive[str] = reactive("")
    value: reactive[str] = reactive("—")

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("", classes="stat-label")
            yield Static("", classes="stat-value")

    def watch_label(self, value: str) -> None:
        self.query_one(".stat-label", Static).update(value)

    def watch_value(self, value: str) -> None:
        self.query_one(".stat-value", Static).update(value)


class DashboardScreen(ModalScreen[None]):
    """Full dashboard: stats and activity."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
        Binding("f3", "dismiss", "Close"),
        Binding("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="dashboard-box"):
            yield Static("Dashboard", id="dashboard-title")
            with Grid(id="stats-row"):
                yield StatCard(id="stat-agents")
                yield StatCard(id="stat-tasks")
                yield StatCard(id="stat-cost")
                yield StatCard(id="stat-cache")
            with Vertical(id="activity-section"):
                yield Static("Recent Activity")
                yield Static("Loading...", id="activity-log")

    def on_mount(self) -> None:
        self._load()

    def action_refresh(self) -> None:
        self._load()

    def action_dismiss(self) -> None:
        self.dismiss()

    def _load(self) -> None:
        """Load stats and activity from services."""
        # Stats
        try:
            from ai_workspace.agents.context_manager import ContextManager
            cm = ContextManager()
            stats = cm.stats() if hasattr(cm, "stats") else {"total_blocks": 0}
            self._set_stat("stat-agents", "Agents", str(stats.get("total_blocks", 0)))
        except Exception:
            self._set_stat("stat-agents", "Agents", "—")

        try:
            from ai_workspace.knowledge import KnowledgeStore
            ks = KnowledgeStore()
            ks.initialize()
            tasks = ks.get_tasks(limit=0) or []
            self._set_stat("stat-tasks", "Tasks", str(len(tasks)))
            ks.close()
        except Exception:
            self._set_stat("stat-tasks", "Tasks", "—")

        try:
            from ai_workspace.core.cost import CostService
            cs = CostService()
            cs.initialize()
            budget = cs.budget.budget_summary()
            today = budget.get("today_spent", 0)
            self._set_stat("stat-cost", "Today", f"${today:.4f}")
        except Exception:
            self._set_stat("stat-cost", "Today", "—")

        try:
            from ai_workspace.core.db import get_db
            db = get_db()
            c = db.cursor()
            c.execute("SELECT COUNT(*) FROM cache_entries")
            count = c.fetchone()[0]
            c.close()
            self._set_stat("stat-cache", "Cache", str(count))
        except Exception:
            self._set_stat("stat-cache", "Cache", "—")

        # Activity log
        try:
            from ai_workspace.knowledge import KnowledgeStore
            ks = KnowledgeStore()
            ks.initialize()
            research = ks.get_research_history(limit=10) or []
            tasks = ks.get_tasks(limit=10) or []
            ks.close()

            lines = []
            for r in research:
                lines.append(f"  [$text 60%]research:[/] [$text 80%]{(r.get('query') or '?')[:80]}[/]")
            for t in tasks:
                lines.append(f"  [$text 60%]task:[/] [$text 80%]{(t.get('title') or '?')[:80]}[/]")
            if not lines:
                lines.append(f"  [$text 40%]No recent activity[/]")

            self.query_one("#activity-log", Static).update("\n".join(lines))
        except Exception as e:
            self.query_one("#activity-log", Static).update(f"  [$error]Error: {e}[/]")

    def _set_stat(self, widget_id: str, label: str, value: str) -> None:
        try:
            card = self.query_one(f"#{widget_id}", StatCard)
            card.label = label
            card.value = value
        except Exception:
            pass
