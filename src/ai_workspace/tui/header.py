"""
Header Bar — unified top bar with tab navigation and status info.

Replaces the old single-line StatusBar with a cleaner two-row header:
- Row 1: Logo | Workspace | Git | Model | Cost | Time
- Row 2: Tab navigation (Dashboard / Agents / Tasks / Chat / Search / Metrics)

Collapses to a single row on narrow terminals (< 100 cols).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Static, Tab, Tabs


class HeaderBar(Vertical):
    """Unified header with status info and tab navigation."""

    DEFAULT_CSS = """
    HeaderBar {
        height: auto;
        background: $surface;
        border-bottom: solid $primary-background;
    }

    #header-top {
        height: 1;
        padding: 0 2;
        background: $surface;
    }

    #header-logo {
        width: auto;
        text-style: bold;
        color: $primary;
    }

    #header-workspace {
        width: 1fr;
        padding: 0 2;
    }

    #header-meta {
        width: auto;
        text-align: right;
    }

    #header-tabs {
        height: auto;
        background: $surface;
        border-top: solid $primary-background 20%;
    }

    #header-tabs Tabs {
        height: auto;
        background: $surface;
    }

    /* All tabs */
    #header-tabs Tab {
        padding: 0 2;
        color: $text 40%;
    }

    #header-tabs Tab:hover {
        color: $text;
    }

    /* Active tab: override Textual defaults */
    #header-tabs Tab.-active {
        background: $accent 35%;
        color: $text !important;
        text-style: bold;
    }

    /* Suppress the default green Underline beneath active tab */
    #header-tabs Tabs > Underline > .--highlight {
        color: $accent;
    }
    """

    # Status reactives
    workspace: reactive[str] = reactive("personal")
    cwd: reactive[str] = reactive("~")
    git_branch: reactive[str] = reactive("")
    git_ahead: reactive[int] = reactive(0)
    git_behind: reactive[int] = reactive(0)
    git_modified: reactive[int] = reactive(0)
    git_staged: reactive[int] = reactive(0)
    model: reactive[str] = reactive("—")
    tasks_active: reactive[int] = reactive(0)
    tasks_total: reactive[int] = reactive(0)
    agents_online: reactive[int] = reactive(0)
    agents_total: reactive[int] = reactive(0)
    pending_permissions: reactive[int] = reactive(0)
    tokens_saved: reactive[int] = reactive(0)
    today_cost: reactive[float] = reactive(0.0)
    cache_entries: reactive[int] = reactive(0)

    # Tab labels
    TAB_LABELS = [
        ("dashboard", "🏠 Dashboard"),
        ("agents", "🤖 Agents"),
        ("tasks", "📋 Tasks"),
        ("git", " Git"),
        ("chat", "💬 Chat"),
        ("search", "🔍 Search"),
        ("metrics", "📊 Metrics"),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._tab_ids = [t[0] for t in self.TAB_LABELS]

    def compose(self) -> ComposeResult:
        with Horizontal(id="header-top"):
            yield Static("[bold]aiw[/]", id="header-logo")
            yield Static(self._render_workspace(), id="header-workspace")
            yield Static(self._render_meta(), id="header-meta")
        with Horizontal(id="header-tabs"):
            yield Tabs(
                Tab("🏠 Dashboard", id="dashboard"),
                Tab("🤖 Agents", id="agents"),
                Tab("📋 Tasks", id="tasks"),
                Tab(" Git", id="git"),
                Tab("💬 Chat", id="chat"),
                Tab("🔍 Search", id="search"),
                Tab("📊 Metrics", id="metrics"),
                id="main-tabs",
            )

    def _render_workspace(self) -> Text:
        """Render workspace path and git info."""
        cwd_short = self.cwd
        home = str(Path.home())
        if cwd_short.startswith(home):
            cwd_short = "~" + cwd_short[len(home):]
        if len(cwd_short) > 35:
            cwd_short = "…" + cwd_short[-34:]

        parts = [f"[cyan]{cwd_short}[/]"]

        # Git info
        if self.git_branch:
            git_parts = [f"[dim] {self.git_branch}[/]"]
            if self.git_ahead > 0:
                git_parts.append(f"[green]↑{self.git_ahead}[/]")
            if self.git_behind > 0:
                git_parts.append(f"[red]↓{self.git_behind}[/]")
            if self.git_modified > 0:
                git_parts.append(f"[yellow]~{self.git_modified}[/]")
            if self.git_staged > 0:
                git_parts.append(f"[green]+{self.git_staged}[/]")
            parts.append(" ".join(git_parts))

        return Text.from_markup("  ".join(parts))

    def _render_meta(self) -> Text:
        """Render model, cost, and time."""
        parts = []

        # Model
        if self.model and self.model != "—":
            parts.append(f"[dim]{self.model}[/]")

        # Agents
        if self.agents_total > 0:
            agent_icon = "⚡" if self.agents_online == self.agents_total else (
                "🟡" if self.agents_online > 0 else "○"
            )
            parts.append(f"agents:{self.agents_online}{agent_icon}")

        # Tasks
        if self.tasks_total > 0:
            parts.append(f"tasks:{self.tasks_active}/{self.tasks_total}")

        # Permissions
        if self.pending_permissions > 0:
            parts.append(f"[bold orange1]🔒 {self.pending_permissions}[/]")

        # Cost
        if self.today_cost > 0:
            parts.append(f"[yellow]${self.today_cost:.3f}[/]")
        else:
            parts.append("[dim]$0[/]")

        # Cache
        if self.tokens_saved > 0:
            parts.append(f"[dim]💾 {self.tokens_saved:,}t[/]")

        # Time
        now = datetime.now().strftime("%H:%M")
        parts.append(f"[dim]{now}[/]")

        return Text.from_markup("  ".join(parts))

    def watch_workspace(self) -> None:
        self._refresh_workspace()

    def watch_cwd(self) -> None:
        self._refresh_workspace()

    def watch_git_branch(self) -> None:
        self._refresh_workspace()

    def watch_git_ahead(self) -> None:
        self._refresh_workspace()

    def watch_git_behind(self) -> None:
        self._refresh_workspace()

    def watch_git_modified(self) -> None:
        self._refresh_workspace()

    def watch_git_staged(self) -> None:
        self._refresh_workspace()

    def watch_model(self) -> None:
        self._refresh_meta()

    def watch_agents_online(self) -> None:
        self._refresh_meta()

    def watch_agents_total(self) -> None:
        self._refresh_meta()

    def watch_tasks_active(self) -> None:
        self._refresh_meta()

    def watch_tasks_total(self) -> None:
        self._refresh_meta()

    def watch_pending_permissions(self) -> None:
        self._refresh_meta()

    def watch_today_cost(self) -> None:
        self._refresh_meta()

    def watch_tokens_saved(self) -> None:
        self._refresh_meta()

    def _refresh_workspace(self) -> None:
        try:
            self.query_one("#header-workspace", Static).update(self._render_workspace())
        except Exception:
            pass

    def _refresh_meta(self) -> None:
        try:
            self.query_one("#header-meta", Static).update(self._render_meta())
        except Exception:
            pass

    def set_active_tab(self, tab_id: str) -> None:
        """Programmatically switch tabs."""
        try:
            tabs = self.query_one("#main-tabs", Tabs)
            idx = self._tab_ids.index(tab_id)
            tabs.active = tab_id
        except (ValueError, Exception):
            pass

    def get_tab_id(self, tab_index: int) -> str:
        """Get tab ID by index."""
        return self._tab_ids[tab_index] if 0 <= tab_index < len(self._tab_ids) else "dashboard"
