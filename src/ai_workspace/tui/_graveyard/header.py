"""
Header Bar — single-line status bar for the AI Workspace TUI v3.

Simplified from the v2 dual-row header+tabs to a single line:
  aiw  ~/Projects/ai-workspace  git:main ↑2 ~3  model  $0.002  14:32

Design principle (from lazygit): "One screen, one purpose."
The header shows only essential info — everything else is an overlay.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from rich.text import Text
from textual.reactive import reactive
from textual.widgets import Static


class HeaderBar(Static):
    """Single-line header with workspace, git, model, cost, time."""

    DEFAULT_CSS = """
    HeaderBar {
        dock: top;
        height: 1;
        padding: 0 2;
        background: $surface;
        border-bottom: solid $primary;
    }
    """

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

    def render(self) -> Text:
        parts: list[str] = ["[bold]aiw[/]"]

        # Workspace path
        cwd_short = self.cwd
        home = str(Path.home())
        if cwd_short.startswith(home):
            cwd_short = "~" + cwd_short[len(home):]
        if len(cwd_short) > 30:
            cwd_short = "…" + cwd_short[-29:]
        parts.append(f"[cyan]{cwd_short}[/]")

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

        # Model
        if self.model and self.model != "—":
            parts.append(f"[dim]{self.model}[/]")

        # Agents
        if self.agents_total > 0:
            icon = "" if self.agents_online == self.agents_total else (
                "" if self.agents_online > 0 else ""
            )
            parts.append(f"{self.agents_online}{icon}")

        # Tasks
        if self.tasks_total > 0:
            parts.append(f"tasks:{self.tasks_active}/{self.tasks_total}")

        # Permissions pending
        if self.pending_permissions > 0:
            parts.append(f"[bold orange1]{self.pending_permissions}[/]")

        # Cost
        if self.today_cost > 0:
            parts.append(f"[yellow]${self.today_cost:.3f}[/]")
        else:
            parts.append("[dim]$0[/]")

        # Cache
        if self.tokens_saved > 0:
            parts.append(f"[dim]{self.tokens_saved:,}t[/]")

        # Time
        now = datetime.now().strftime("%H:%M")
        parts.append(f"[dim]{now}[/]")

        return Text.from_markup("  ".join(parts))


    def watch_cwd(self) -> None:
        self.refresh()

    def watch_git_branch(self) -> None:
        self.refresh()

    def watch_git_ahead(self) -> None:
        self.refresh()

    def watch_git_behind(self) -> None:
        self.refresh()

    def watch_git_modified(self) -> None:
        self.refresh()

    def watch_git_staged(self) -> None:
        self.refresh()

    def watch_model(self) -> None:
        self.refresh()

    def watch_agents_online(self) -> None:
        self.refresh()

    def watch_agents_total(self) -> None:
        self.refresh()

    def watch_tasks_active(self) -> None:
        self.refresh()

    def watch_tasks_total(self) -> None:
        self.refresh()

    def watch_pending_permissions(self) -> None:
        self.refresh()

    def watch_today_cost(self) -> None:
        self.refresh()

    def watch_tokens_saved(self) -> None:
        self.refresh()
