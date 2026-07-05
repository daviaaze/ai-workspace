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
    """Full dashboard: stats, health, and activity."""

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
                yield StatCard(id="stat-health")
            with Grid(id="health-row"):
                yield Static("DB: —", id="health-db")
                yield Static("Ollama: —", id="health-ollama")
                yield Static("MCP: —", id="health-mcp")
                yield Static("Circuit: —", id="health-circuit")
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

        # ── Health Check ──
        # Summary card
        health_ok = 0
        health_total = 4

        # DB health
        try:
            from ai_workspace.core.db import get_db
            db = get_db()
            db.execute("SELECT 1")
            db.close()
            self.query_one("#health-db", Static).update("[green]DB: ✓[/]")
            health_ok += 1
        except Exception:
            self.query_one("#health-db", Static).update("[red]DB: ✗[/]")

        # Ollama health
        try:
            import json
            import urllib.request
            req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
            resp = urllib.request.urlopen(req, timeout=3)
            data = json.loads(resp.read().decode())
            models = data.get("models", [])
            self.query_one("#health-ollama", Static).update(
                f"[green]Ollama: {len(models)} models[/]"
            )
            health_ok += 1
        except Exception:
            self.query_one("#health-ollama", Static).update("[red]Ollama: ✗[/]")

        # MCP health
        try:
            from ai_workspace.mcp_client import get_cached_mcp_bundle
            bundle = get_cached_mcp_bundle()
            if bundle and bundle.tool_definitions:
                n = len(bundle.tool_definitions)
                self.query_one("#health-mcp", Static).update(f"[green]MCP: {n} tools[/]")
                health_ok += 1
            else:
                self.query_one("#health-mcp", Static).update("[yellow]MCP: no tools[/]")
        except Exception:
            self.query_one("#health-mcp", Static).update("[yellow]MCP: not started[/]")
        # Not counting MCP as critical for health_ok

        # Circuit breakers health
        try:
            from ai_workspace.core.cost import CostService
            cs = CostService()
            cs.initialize()
            summary = cs.budget.budget_summary()
            circuits = summary.get("circuits", {})
            open_circuits = [p for p, s in circuits.items() if s == "open"]
            if open_circuits:
                self.query_one("#health-circuit", Static).update(
                    f"[red]Circuit: {', '.join(open_circuits)} OPEN[/]"
                )
            else:
                self.query_one("#health-circuit", Static).update("[green]Circuit: all closed[/]")
                health_ok += 1
        except Exception:
            self.query_one("#health-circuit", Static).update("[yellow]Circuit: —[/]")

        # Overall health badge
        health_pct = round(health_ok / health_total * 100) if health_total else 0
        if health_pct >= 75:
            badge = f"[green]✓ {health_ok}/{health_total}[/]"
        elif health_pct >= 50:
            badge = f"[yellow]~ {health_ok}/{health_total}[/]"
        else:
            badge = f"[red]✗ {health_ok}/{health_total}[/]"
        self._set_stat("stat-health", "Health", badge)

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
                lines.append("  [$text 40%]No recent activity[/]")

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
