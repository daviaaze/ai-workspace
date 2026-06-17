"""
Dashboard View — overview home screen for the AI Workspace TUI.

Shows at-a-glance summary of all system state:
- Agent status cards (compact summary of all agents)
- Task summary (recent + active tasks)
- Activity feed (last N system events)
- Quick stats (cost, tokens, cache)
- Quick actions (spawn, search, new task)

Layout adapts: 2-column grid on large, single column on small.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from rich.panel import Panel
from rich.table import Table as RichTable
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Button, Label, Static


class GitSummaryCard(Static):
    """Card showing git status summary."""

    DEFAULT_CSS = """
    GitSummaryCard {
        height: auto;
        border: solid $primary-background;
        background: $surface;
        padding: 1;
    }
    GitSummaryCard .card-title {
        text-style: bold;
        padding: 0 1 1 1;
        border-bottom: solid $primary-background;
    }
    """

    branch: reactive[str] = reactive("")
    ahead: reactive[int] = reactive(0)
    behind: reactive[int] = reactive(0)
    modified: reactive[int] = reactive(0)
    staged: reactive[int] = reactive(0)
    untracked: reactive[int] = reactive(0)
    commit_hash: reactive[str] = reactive("")
    is_git_repo: reactive[bool] = reactive(False)

    def render(self) -> Text:
        lines = ["[bold] Git[/]"]
        lines.append("")

        if not self.is_git_repo:
            lines.append("[dim]Not a git repository.[/]")
            return Text.from_markup("\n".join(lines))

        # Branch and sync status
        sync_parts = [f"[bold cyan]{self.branch}[/]"]
        if self.ahead > 0:
            sync_parts.append(f"[green]↑{self.ahead}[/]")
        if self.behind > 0:
            sync_parts.append(f"[red]↓{self.behind}[/]")
        lines.append("  " + " ".join(sync_parts))

        if self.commit_hash:
            lines.append(f"  [dim] {self.commit_hash[:7]}[/]")

        lines.append("")

        # Changes
        changes = []
        if self.modified > 0:
            changes.append(f"[yellow]{self.modified} modified[/]")
        if self.staged > 0:
            changes.append(f"[green]{self.staged} staged[/]")
        if self.untracked > 0:
            changes.append(f"[dim]{self.untracked} untracked[/]")

        if changes:
            lines.append("  " + "  ".join(changes))
        else:
            lines.append("  [dim]Working tree clean[/]")

        return Text.from_markup("\n".join(lines))


class QuickStat(Static):
    """A single stat display: label + value + optional delta."""

    DEFAULT_CSS = """
    QuickStat {
        height: auto;
        padding: 1 2;
        text-align: center;
    }
    QuickStat .stat-value {
        text-style: bold;
        text-align: center;
    }
    QuickStat .stat-label {
        text-style: dim;
        text-align: center;
    }
    """

    label: reactive[str] = reactive("")
    value: reactive[str] = reactive("")
    color: reactive[str] = reactive("white")

    def render(self) -> Text:
        return Text.from_markup(
            f"[{self.color}]{self.value}[/]\n[dim]{self.label}[/]"
        )


class AgentSummaryCard(Static):
    """Card showing summary of all agents."""

    DEFAULT_CSS = """
    AgentSummaryCard {
        height: auto;
        border: solid $primary-background;
        background: $surface;
        padding: 1;
    }
    AgentSummaryCard .card-title {
        text-style: bold;
        padding: 0 1 1 1;
        border-bottom: solid $primary-background;
    }
    AgentSummaryCard .agent-row {
        height: 1;
        padding: 0 1;
    }
    AgentSummaryCard .agent-row:hover {
        background: $primary-background 20%;
    }
    AgentSummaryCard .empty-state {
        padding: 2;
        text-style: dim;
        text-align: center;
    }
    """

    agents: reactive[list[dict[str, Any]]] = reactive([])

    def render(self) -> Text:
        lines = ["[bold]🤖 Agents[/]"]
        lines.append("")

        if not self.agents:
            lines.append("[dim]No agents running.[/]")
            lines.append("[dim]Press [bold]Ctrl+S[/] to spawn one.[/]")
            return Text.from_markup("\n".join(lines))

        # Table header
        lines.append(
            f"{'Name':<20} {'Status':<10} {'Task':<30} {'Progress':<8}"
        )
        lines.append("─" * 70)

        for a in self.agents:
            name = a.get("name", "?")[:18]
            status = a.get("task_status", "notstarted")
            task = a.get("current_task", "—")[:28]
            progress = a.get("task_progress", 0)

            status_icons = {
                "ongoing": "[green]●[/]",
                "notstarted": "[dim]○[/]",
                "completed": "[green]✅[/]",
                "blocked": "[yellow]🛑[/]",
                "rejected": "[red]✗[/]",
            }
            icon = status_icons.get(status, "●")

            progress_str = ""
            if progress > 0:
                filled = int(progress / 10)
                bar = "█" * filled + "░" * (10 - filled)
                progress_str = f"[{bar}] {progress:.0f}%"

            lines.append(
                f"{name:<20} {icon} {status:<8} {task:<30} {progress_str}"
            )

        return Text.from_markup("\n".join(lines))


class TaskSummaryCard(Static):
    """Card showing recent and active tasks."""

    DEFAULT_CSS = """
    TaskSummaryCard {
        height: auto;
        border: solid $primary-background;
        background: $surface;
        padding: 1;
    }
    TaskSummaryCard .card-title {
        text-style: bold;
        padding: 0 1 1 1;
        border-bottom: solid $primary-background;
    }
    """

    tasks: reactive[list[dict[str, Any]]] = reactive([])
    max_display: int = 8

    def render(self) -> Text:
        lines = ["[bold]📋 Tasks[/]"]
        lines.append("")

        if not self.tasks:
            lines.append("[dim]No tasks yet.[/]")
            lines.append("[dim]Press [bold]Ctrl+N[/] to create one.[/]")
            return Text.from_markup("\n".join(lines))

        # Show active first, then recent
        active = [t for t in self.tasks if t.get("status") in ("ongoing", "blocked")]
        other = [t for t in self.tasks if t.get("status") not in ("ongoing", "blocked")]
        display = (active + other)[: self.max_display]

        for t in display:
            status = t.get("status", "notstarted")
            title = t.get("title", "?")[:35]
            agent = t.get("agent", "")
            progress = t.get("progress", 0)

            icons = {
                "ongoing": "[green]●[/]",
                "notstarted": "[dim]○[/]",
                "completed": "[green]✅[/]",
                "blocked": "[yellow]🛑[/]",
                "rejected": "[red]✗[/]",
                "cron": "[cyan]🕐[/]",
            }
            icon = icons.get(status, "?")

            agent_str = f" [dim]({agent})[/]" if agent else ""
            progress_str = f" [dim]{progress:.0f}%[/]" if progress > 0 else ""

            lines.append(f"  {icon} {title}{agent_str}{progress_str}")

        remaining = len(self.tasks) - len(display)
        if remaining > 0:
            lines.append(f"[dim]  … and {remaining} more[/]")

        return Text.from_markup("\n".join(lines))


class ActivityFeed(Static):
    """Card showing recent system activity / event log."""

    DEFAULT_CSS = """
    ActivityFeed {
        height: auto;
        border: solid $primary-background;
        background: $surface;
        padding: 1;
    }
    ActivityFeed .card-title {
        text-style: bold;
        padding: 0 1 1 1;
        border-bottom: solid $primary-background;
    }
    ActivityFeed .activity-row {
        height: 1;
        padding: 0 1;
    }
    """

    events: reactive[list[dict[str, Any]]] = reactive([])
    max_events: int = 10

    def render(self) -> Text:
        lines = ["[bold]📡 Activity[/]"]
        lines.append("")

        if not self.events:
            lines.append("[dim]No recent activity.[/]")
            return Text.from_markup("\n".join(lines))

        for e in self.events[-self.max_events :]:
            ts = e.get("timestamp", "")
            if isinstance(ts, datetime):
                ts = ts.strftime("%H:%M:%S")
            else:
                ts = str(ts)[:8]

            severity = e.get("severity", "info")
            icons = {
                "info": "[dim]›[/]",
                "warning": "[yellow]⚠[/]",
                "error": "[red]✗[/]",
                "success": "[green]✓[/]",
            }
            icon = icons.get(severity, "›")

            msg = e.get("message", "")[:55]
            lines.append(f"  {icon} [dim]{ts}[/]  {msg}")

        return Text.from_markup("\n".join(lines))

    def log(self, message: str, severity: str = "info") -> None:
        """Add a new event to the feed."""
        self.events.append({
            "timestamp": datetime.now(),
            "message": message,
            "severity": severity,
        })
        # Trim old events
        if len(self.events) > 100:
            self.events = self.events[-100:]
        self.refresh()


class QuickStatsCard(Static):
    """Card showing key metrics in a row."""

    DEFAULT_CSS = """
    QuickStatsCard {
        height: auto;
        border: solid $primary-background;
        background: $surface;
        padding: 1;
    }
    QuickStatsCard .card-title {
        text-style: bold;
        padding: 0 1 1 1;
        border-bottom: solid $primary-background;
    }
    """

    today_cost: reactive[float] = reactive(0.0)
    month_cost: reactive[float] = reactive(0.0)
    tokens_saved: reactive[int] = reactive(0)
    cache_hits: reactive[int] = reactive(0)
    cache_entries: reactive[int] = reactive(0)
    agents_online: reactive[int] = reactive(0)
    tasks_active: reactive[int] = reactive(0)

    def render(self) -> Text:
        lines = ["[bold]📊 Quick Stats[/]"]
        lines.append("")

        stats = []

        if self.agents_online > 0:
            stats.append(f"[bold cyan]{self.agents_online}[/] agents running")
        if self.tasks_active > 0:
            stats.append(f"[bold cyan]{self.tasks_active}[/] active tasks")

        stats.append(f"Today: [bold yellow]${self.today_cost:.4f}[/]")
        if self.month_cost > 0:
            stats.append(f"Month: [dim]${self.month_cost:.4f}[/]")
        if self.tokens_saved > 0:
            stats.append(f"Saved: [green]{self.tokens_saved:,}[/] tokens")
        if self.cache_hits > 0:
            stats.append(f"Cache: [green]{self.cache_hits}[/] hits")
        if self.cache_entries > 0:
            stats.append(f"Cache: [dim]{self.cache_entries}[/] entries")

        if not stats:
            lines.append("[dim]No metrics yet. Start an agent to see stats.[/]")
        else:
            # Render in 2-column layout
            for i in range(0, len(stats), 2):
                left = stats[i]
                right = stats[i + 1] if i + 1 < len(stats) else ""
                lines.append(f"  {left:<30} {right}")

        return Text.from_markup("\n".join(lines))


class QuickActions(Static):
    """Card with quick action buttons."""

    DEFAULT_CSS = """
    QuickActions {
        height: auto;
        border: solid $primary-background;
        background: $surface;
        padding: 1;
    }
    QuickActions .card-title {
        text-style: bold;
        padding: 0 1 1 1;
        border-bottom: solid $primary-background;
    }
    QuickActions Button {
        margin: 0 1 0 0;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("[bold]⚡ Quick Actions[/]")
        yield Label("")
        with Horizontal():
            yield Button("🚀 Spawn Agent", id="qa-spawn", variant="primary")
            yield Button("📝 New Task", id="qa-task", variant="default")
            yield Button("🔍 Search", id="qa-search", variant="default")
            yield Button("📁 Workspace", id="qa-workspace", variant="default")


class DashboardView(VerticalScroll):
    """Main dashboard view — the home screen of the TUI."""

    DEFAULT_CSS = """
    DashboardView {
        height: 1fr;
        padding: 1;
    }

    DashboardView #dashboard-grid {
        grid-size: 2;
        grid-columns: 1fr 1fr;
        grid-rows: auto;
        height: auto;
        padding: 0;
    }

    DashboardView #dashboard-grid > * {
        margin: 0 1 1 0;
    }

    DashboardView #dashboard-grid > *:last-child {
        column-span: 2;
    }

    /* Single column on narrow terminals */
    @media (max-width: 100) {
        DashboardView #dashboard-grid {
            grid-size: 1;
        }
        DashboardView #dashboard-grid > *:last-child {
            column-span: 1;
        }
    }
    """

    agents: reactive[list[dict[str, Any]]] = reactive([])
    tasks: reactive[list[dict[str, Any]]] = reactive([])

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._activity_feed: ActivityFeed | None = None

    def compose(self) -> ComposeResult:
        with Grid(id="dashboard-grid"):
            yield AgentSummaryCard(id="dash-agents")
            yield TaskSummaryCard(id="dash-tasks")
            yield QuickStatsCard(id="dash-stats")
            yield GitSummaryCard(id="dash-git")
            yield ActivityFeed(id="dash-activity")
            yield QuickActions(id="dash-actions")

    def on_mount(self) -> None:
        self._activity_feed = self.query_one("#dash-activity", ActivityFeed)

    def update_agents(self, agents: list[dict[str, Any]]) -> None:
        self.agents = agents
        try:
            self.query_one("#dash-agents", AgentSummaryCard).agents = agents
        except Exception:
            pass

    def update_tasks(self, tasks: list[dict[str, Any]]) -> None:
        self.tasks = tasks
        try:
            self.query_one("#dash-tasks", TaskSummaryCard).tasks = tasks
        except Exception:
            pass

    def update_stats(
        self,
        today_cost: float = 0.0,
        month_cost: float = 0.0,
        tokens_saved: int = 0,
        cache_hits: int = 0,
        cache_entries: int = 0,
        agents_online: int = 0,
        tasks_active: int = 0,
    ) -> None:
        try:
            card = self.query_one("#dash-stats", QuickStatsCard)
            card.today_cost = today_cost
            card.month_cost = month_cost
            card.tokens_saved = tokens_saved
            card.cache_hits = cache_hits
            card.cache_entries = cache_entries
            card.agents_online = agents_online
            card.tasks_active = tasks_active
        except Exception:
            pass

    def update_git(
        self,
        branch: str = "",
        ahead: int = 0,
        behind: int = 0,
        modified: int = 0,
        staged: int = 0,
        untracked: int = 0,
        commit_hash: str = "",
        is_git_repo: bool = False,
    ) -> None:
        """Update git summary card."""
        try:
            card = self.query_one("#dash-git", GitSummaryCard)
            card.branch = branch
            card.ahead = ahead
            card.behind = behind
            card.modified = modified
            card.staged = staged
            card.untracked = untracked
            card.commit_hash = commit_hash
            card.is_git_repo = is_git_repo
        except Exception:
            pass

    def log_activity(self, message: str, severity: str = "info") -> None:
        """Log an activity event."""
        try:
            feed = self.query_one("#dash-activity", ActivityFeed)
            feed.log(message, severity)
        except Exception:
            pass
