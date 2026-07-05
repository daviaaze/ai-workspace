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

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Grid, Horizontal, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Button, Label, Static

# ═══════════════════════════════════════════════════════════
# Filter Bar — status/surface/model filter tabs
# ═══════════════════════════════════════════════════════════


class FilterTab(Button):
    """A single tab in the filter bar."""

    DEFAULT_CSS = """
    FilterTab {
        min-width: 10;
        height: 1;
        margin: 0 0 0 0;
        padding: 0 2;
        border: none;
        background: transparent;
        color: $text;
        text-style: dim;
    }
    FilterTab.-active {
        background: $primary 25%;
        color: $text;
        text-style: bold;
        border-bottom: solid $primary;
    }
    FilterTab:hover {
        background: $primary 15%;
    }
    """

    def __init__(self, label: str, filter_value: str, **kwargs) -> None:
        super().__init__(label, **kwargs)
        self.filter_value = filter_value
        self.classes = ""

    def on_click(self) -> None:
        self.emit_filter()

    def emit_filter(self) -> None:
        from textual.message import Message

        class FilterChanged(Message):
            def __init__(self, filter_type: str, value: str) -> None:
                self.filter_type = filter_type
                self.value = value
                super().__init__()

        self.post_message(self.FilterChanged(self.id or "", self.filter_value))


class FilterBar(Static):
    """Horizontal filter bar with grouped tabs.

    Shows filter groups as labelled tab rows:

        Status: [All] [Running] [Blocked] [Done]
        Sort: [Name] [Status] [Progress]

    Clicking a tab activates it and deactivates its group siblings.
    """

    DEFAULT_CSS = """
    FilterBar {
        height: auto;
        width: 1fr;
        background: $surface;
        border: solid $primary 20%;
        padding: 1;
        margin: 0 0 1 0;
    }
    FilterBar .filter-group {
        height: auto;
    }
    FilterBar .filter-label {
        text-style: bold;
        padding: 0 1 0 0;
    }
    """

    def compose(self) -> ComposeResult:
        # Status filter
        with Horizontal(classes="filter-group"):
            yield Label("Status:", classes="filter-label")
            for label, val in [("All", "all"), ("Running", "running"),
                               ("Blocked", "blocked"), ("Done", "done")]:
                tab = FilterTab(label, val, id=f"status-{val}")
                tab.classes = "-active" if val == "all" else ""
                yield tab

        yield Label("")

        # Surface filter
        with Horizontal(classes="filter-group"):
            yield Label("Surface:", classes="filter-label")
            for label, val in [("All", "all"), ("Chat", "chat"),
                               ("Research", "research"), ("Code", "code")]:
                tab = FilterTab(label, val, id=f"surface-{val}")
                tab.classes = "-active" if val == "all" else ""
                yield tab

        yield Label("")

        # Sort
        with Horizontal(classes="filter-group"):
            yield Label("Sort:", classes="filter-label")
            for label, val in [("Name", "name"), ("Status", "status"),
                               ("Progress", "progress"), ("Recent", "recent")]:
                tab = FilterTab(label, val, id=f"sort-{val}")
                tab.classes = "-active" if val == "recent" else ""
                yield tab

    @property
    def active_filters(self) -> dict[str, str]:
        """Get currently active filters as ``{group: value}``."""
        filters: dict[str, str] = {}
        for tab in self.query(FilterTab):
            if "-active" in (tab.classes or ""):
                group = tab.id.split("-")[0] if tab.id else ""
                filters[group] = tab.filter_value
        return filters


# ═══════════════════════════════════════════════════════════
# Expandable Card — lazy-loaded previews
# ═══════════════════════════════════════════════════════════


class ExpandableCard(Static):
    """A card with lazy-loaded preview content.

    Shows a compact summary line by default. Clicking toggles
    expansion to reveal full details. Follows Career-Ops'
    "don't load until selected" pattern.

    Subclass and override ``_render_preview()`` and ``_render_detail()``.
    """

    expanded: reactive[bool] = reactive(False)

    DEFAULT_CSS = """
    ExpandableCard {
        height: auto;
        border: solid $primary 20%;
        background: $panel;
        padding: 1;
    }
    ExpandableCard:hover {
        border: solid $primary 50%;
    }
    ExpandableCard .expand-toggle {
        text-style: bold;
    }
    """

    def __init__(self, item_id: str, **kwargs):
        super().__init__(**kwargs)
        self._item_id = item_id
        self._detail_loaded = False

    def on_click(self) -> None:
        self.expanded = not self.expanded
        if self.expanded and not self._detail_loaded:
            self._detail_loaded = True
            self.load_detail()
        self.refresh()

    def load_detail(self) -> None:
        """Override to load detail data when first expanded.

        Called once when the card is first clicked open.
        """

    def render(self) -> Text:
        if self.expanded:
            return self._render_detail()
        return self._render_preview()

    def _render_preview(self) -> Text:
        """Compact summary line (always visible)."""
        return Text(f"[dim]▶[/] {self._item_id}")

    def _render_detail(self) -> Text:
        """Full detail content (visible when expanded)."""
        return Text(f"[dim]▼[/] {self._item_id} (no detail loaded)")


# ═══════════════════════════════════════════════════════════
# Inline Clickable Status
# ═══════════════════════════════════════════════════════════

STATUS_CYCLE = [
    "notstarted",
    "ongoing",
    "blocked",
    "completed",
    "rejected",
]

STATUS_ICONS = {
    "ongoing": "[green][/]",
    "notstarted": "[dim][/]",
    "completed": "[green]✓[/]",
    "blocked": "[yellow]![/]",
    "rejected": "[red]✗[/]",
}

STATUS_COLORS = {
    "ongoing": "green",
    "notstarted": "dim",
    "completed": "green",
    "blocked": "yellow",
    "rejected": "red",
}


def cycle_status(current: str) -> str:
    """Cycle to the next status."""
    try:
        idx = STATUS_CYCLE.index(current)
        return STATUS_CYCLE[(idx + 1) % len(STATUS_CYCLE)]
    except ValueError:
        return "notstarted"


class GitSummaryCard(Static):
    """Card showing git status summary."""

    DEFAULT_CSS = """
    GitSummaryCard {
        height: auto;
        border: solid $primary 20%;
        background: $panel;
        padding: 1;
    }
    GitSummaryCard .card-title {
        text-style: bold;
        padding: 0 1 1 1;
        border-bottom: solid $primary 20%;
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
    """Card showing summary of all agents.

    Supports filter-by-status, sort modes, and inline status
    changes by clicking on the status label (Career-Ops inspired).
    """

    DEFAULT_CSS = """
    AgentSummaryCard {
        height: auto;
        border: solid $primary 20%;
        background: $panel;
        padding: 1;
    }
    AgentSummaryCard .card-title {
        text-style: bold;
        padding: 0 1 1 1;
        border-bottom: solid $primary 20%;
    }
    AgentSummaryCard .agent-row {
        height: 1;
        padding: 0 1;
    }
    AgentSummaryCard .agent-row:hover {
        background: $primary 20%;
    }
    AgentSummaryCard .empty-state {
        padding: 2;
        text-style: dim;
        text-align: center;
    }
    """

    agents: reactive[list[dict[str, Any]]] = reactive([])
    filter_status: reactive[str] = reactive("all")
    filter_surface: reactive[str] = reactive("all")
    sort_mode: reactive[str] = reactive("recent")

    def render(self) -> Text:
        lines = ["[bold] Agents[/]"]
        lines.append("")

        # Apply filters
        filtered = self.agents
        if self.filter_status != "all":
            filtered = [
                a for a in filtered
                if a.get("task_status", "notstarted") == self.filter_status
            ]
        if self.filter_surface != "all":
            filtered = [
                a for a in filtered
                if a.get("surface", "").lower() == self.filter_surface
            ]

        # Apply sort
        filtered = self._sorted(filtered)

        if not filtered:
            if self.agents:
                lines.append("[dim]No agents match current filters.[/]")
            else:
                lines.append("[dim]No agents running.[/]")
                lines.append("[dim]Press [bold]Ctrl+S[/] to spawn one.[/]")
            return Text.from_markup("\n".join(lines))

        # Sort mode indicator
        sort_hint = {
            "name": "(by name)",
            "status": "(by status)",
            "progress": "(by progress)",
            "recent": "(most recent)",
        }.get(self.sort_mode, "")
        lines.append(f"[dim]{sort_hint}[/]")

        # Table header
        lines.append(
            f"{'Name':<20} {'Status':<12} {'Task':<30} {'Progress':<8}"
        )
        lines.append("" * 72)

        for a in filtered:
            name = a.get("name", "?")[:18]
            status = a.get("task_status", "notstarted")
            task = a.get("current_task", "—")[:28]
            progress = a.get("task_progress", 0)

            icon = STATUS_ICONS.get(status, "")
            color = STATUS_COLORS.get(status, "white")

            progress_str = ""
            if progress > 0:
                filled = int(progress / 10)
                bar = "" * filled + "" * (10 - filled)
                progress_str = f"[{bar}] {progress:.0f}%"

            # Render status as clickable inline
            status_label = f"[{color}]{icon} {status:<8}[/]"

            lines.append(
                f"{name:<20} {status_label} {task:<30} {progress_str}"
            )

        return Text.from_markup("\n".join(lines))

    def _sorted(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Sort agents by the current sort mode."""
        key_map = {
            "name": lambda a: a.get("name", ""),
            "status": lambda a: STATUS_CYCLE.index(
                a.get("task_status", "notstarted")
            ),
            "progress": lambda a: -a.get("task_progress", 0),
            "recent": lambda a: -a.get("updated_at", 0),
        }
        key_fn = key_map.get(self.sort_mode)
        if key_fn:
            return sorted(items, key=key_fn)
        return items

    def on_click(self) -> None:
        """Inline status cycle: clicking cycles status of first agent.

        In a full implementation, each agent row would have its own
        clickable status widget. For now, clicking cycles the first.
        """
        if not self.agents:
            return
        first = self.agents[0]
        current = first.get("task_status", "notstarted")
        first["task_status"] = cycle_status(current)
        self.refresh()


class TaskSummaryCard(Static):
    """Card showing recent and active tasks.

    Supports filter-by-status and grouped view (active vs done).
    """

    DEFAULT_CSS = """
    TaskSummaryCard {
        height: auto;
        border: solid $primary 20%;
        background: $panel;
        padding: 1;
    }
    TaskSummaryCard .card-title {
        text-style: bold;
        padding: 0 1 1 1;
        border-bottom: solid $primary 20%;
    }
    """

    tasks: reactive[list[dict[str, Any]]] = reactive([])
    filter_status: reactive[str] = reactive("all")
    max_display: int = 8

    def render(self) -> Text:
        lines = ["[bold] Tasks[/]"]
        lines.append("")

        if not self.tasks:
            lines.append("[dim]No tasks yet.[/]")
            lines.append("[dim]Press [bold]Ctrl+N[/] to create one.[/]")
            return Text.from_markup("\n".join(lines))

        # Apply status filter
        if self.filter_status != "all":
            filtered = [
                t for t in self.tasks
                if t.get("status", "notstarted") == self.filter_status
            ]
        else:
            filtered = self.tasks

        # Grouped view: active first, then done
        active = [t for t in filtered if t.get("status") in ("ongoing", "blocked")]
        done = [t for t in filtered if t.get("status") in ("completed", "rejected")]
        other = [t for t in filtered if t not in active and t not in done]
        display = (active + done + other)[: self.max_display]

        # Render grouped sections
        sections: list[tuple[str, list[dict[str, Any]]]] = []
        if active:
            sections.append(("Active", active[:4]))
        if done:
            sections.append(("Done", done[:3]))
        if not sections:
            sections.append(("Tasks", display))

        for section_label, items in sections:
            lines.append(f"[dim]{section_label}[/]")
            for t in items:
                status = t.get("status", "notstarted")
                title = t.get("title", "?")[:35]
                agent = t.get("agent", "")
                progress = t.get("progress", 0)

                icon = STATUS_ICONS.get(status, "?")
                color = STATUS_COLORS.get(status, "white")

                agent_str = f" [dim]({agent})[/]" if agent else ""
                progress_str = f" [{color}]{progress:.0f}%[/]" if progress > 0 else ""

                lines.append(f"  {icon} [{color}]{title}[/]{agent_str}{progress_str}")
            lines.append("")

        remaining = len(filtered) - len(display)
        if remaining > 0:
            lines.append(f"[dim]… and {remaining} more[/]")

        return Text.from_markup("\n".join(lines))


class ActivityFeed(Static):
    """Card showing recent system activity / event log."""

    DEFAULT_CSS = """
    ActivityFeed {
        height: auto;
        border: solid $primary 20%;
        background: $panel;
        padding: 1;
    }
    ActivityFeed .card-title {
        text-style: bold;
        padding: 0 1 1 1;
        border-bottom: solid $primary 20%;
    }
    ActivityFeed .activity-row {
        height: 1;
        padding: 0 1;
    }
    """

    events: reactive[list[dict[str, Any]]] = reactive([])
    max_events: int = 10

    def render(self) -> Text:
        lines = ["[bold] Activity[/]"]
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
                "warning": "[yellow][/]",
                "error": "[red][/]",
                "success": "[green][/]",
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
        border: solid $primary 20%;
        background: $panel;
        padding: 1;
    }
    QuickStatsCard .card-title {
        text-style: bold;
        padding: 0 1 1 1;
        border-bottom: solid $primary 20%;
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
        lines = ["[bold] Quick Stats[/]"]
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
        border: solid $primary 20%;
        background: $panel;
        padding: 1;
    }
    QuickActions .card-title {
        text-style: bold;
        padding: 0 1 1 1;
        border-bottom: solid $primary 20%;
    }
    QuickActions Button {
        margin: 0 1 0 0;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("[bold] Quick Actions[/]")
        yield Label("")
        with Horizontal():
            yield Button(" Spawn Agent", id="qa-spawn", variant="primary")
            yield Button(" New Task", id="qa-task", variant="default")
            yield Button(" Search", id="qa-search", variant="default")
            yield Button(" Workspace", id="qa-workspace", variant="default")


class DashboardView(VerticalScroll, can_focus=False):
    """Main dashboard view — the home screen of the TUI.

    Career-Ops inspired enhancements:
    - Filter tabs (by status, surface)
    - Sort modes (name, status, progress, recent)
    - Grouped task view (active vs done)
    - Inline status changes (click to cycle)
    """

    DEFAULT_CSS = """
    DashboardView {
        height: 1fr;
        padding: 1;
        overflow: hidden hidden;
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

    """

    agents: reactive[list[dict[str, Any]]] = reactive([])
    tasks: reactive[list[dict[str, Any]]] = reactive([])

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._activity_feed: ActivityFeed | None = None
        self._filter_bar: FilterBar | None = None

    def compose(self) -> ComposeResult:
        yield FilterBar(id="dash-filters")
        with Grid(id="dashboard-grid"):
            yield AgentSummaryCard(id="dash-agents")
            yield TaskSummaryCard(id="dash-tasks")
            yield QuickStatsCard(id="dash-stats")
            yield GitSummaryCard(id="dash-git")
            yield ActivityFeed(id="dash-activity")
            yield QuickActions(id="dash-actions")

    def on_mount(self) -> None:
        self._activity_feed = self.query_one("#dash-activity", ActivityFeed)
        self._filter_bar = self.query_one("#dash-filters", FilterBar)

    def _on_filter_tab_filter_changed(
        self, event: FilterTab.FilterChanged,
    ) -> None:
        """Handle filter tab changes from the FilterBar."""
        filter_type = event.filter_type
        value = event.value

        try:
            agents_card = self.query_one("#dash-agents", AgentSummaryCard)
            tasks_card = self.query_one("#dash-tasks", TaskSummaryCard)

            if filter_type.startswith("status"):
                agents_card.filter_status = value
                tasks_card.filter_status = value
            elif filter_type.startswith("surface"):
                agents_card.filter_surface = value
            elif filter_type.startswith("sort"):
                agents_card.sort_mode = value

            agents_card.refresh()
            tasks_card.refresh()
        except Exception:
            pass

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
