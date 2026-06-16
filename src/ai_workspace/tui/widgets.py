"""
Custom Textual widgets for the AI Workspace agent operations center.

Widgets:
- StatusBar: top bar showing workspace, model, task counts, agent statuses, time
- TaskPanel: left panel with task tree, progress bars, status indicators
- AgentLane: single agent's live output stream with thinking overlay
- PermissionModal: overlay for approve/deny decisions
- CommandPalette: vim-style command input (":" prefix)
- NodePanel: shows mesh nodes and their capabilities (collapsible)
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import ClassVar

from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table as RichTable
from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import (
    Button,
    Input,
    Label,
    ListItem,
    ListView,
    ProgressBar,
    Static,
)


# ═══════════════════════════════════════════════════════════════
# Status Bar (top)
# ═══════════════════════════════════════════════════════════════

class StatusBar(Static):
    """Top bar showing workspace, model, task counts, agent statuses, clock,
    and cache/cost metrics."""

    workspace: reactive[str] = reactive("none")
    model: reactive[str] = reactive("—")
    tasks_active: reactive[int] = reactive(0)
    tasks_total: reactive[int] = reactive(0)
    agents_online: reactive[int] = reactive(0)
    agents_total: reactive[int] = reactive(0)
    pending_permissions: reactive[int] = reactive(0)
    mesh_nodes: reactive[int] = reactive(1)
    # Cache/cost metrics
    cache_entries: reactive[int] = reactive(0)
    cache_hits: reactive[int] = reactive(0)
    tokens_saved: reactive[int] = reactive(0)
    today_cost: reactive[float] = reactive(0.0)
    month_cost: reactive[float] = reactive(0.0)
    # Source stats
    source_domains: reactive[int] = reactive(0)

    def render(self) -> Text:
        agent_icon = "⚡" if self.agents_online == self.agents_total and self.agents_total > 0 else (
            "🟡" if self.agents_online > 0 else "○"
        )
        perm_indicator = f" {self.pending_permissions}🔒" if self.pending_permissions > 0 else ""
        node_indicator = f" mesh:{self.mesh_nodes}" if self.mesh_nodes > 1 else ""
        now = datetime.now().strftime("%H:%M")
        
        # Cache info line
        cache_info = ""
        if self.cache_entries > 0:
            hit_rate = (self.cache_hits / max(self.cache_hits + self.cache_entries, 1)) * 100
            cache_info = (
                f"💾 {self.cache_entries}e "
                f"{self.tokens_saved:,}t saved "
            )
        cost_info = f"${self.today_cost:.3f} today" if self.today_cost > 0 else "$0 today"
        source_info = f" 🛡️ {self.source_domains}d" if self.source_domains > 0 else ""

        return Text.from_markup(
            f"[bold]aiw[/]  "
            f"ws:[cyan]{self.workspace}[/]  "
            f"[dim]{self.model}[/]  "
            f"tasks:{self.tasks_active}/{self.tasks_total}  "
            f"agents:{self.agents_online}{agent_icon}{perm_indicator}"
            f"{node_indicator}  "
            f"{cache_info}"
            f"[dim]{cost_info}[/]"
            f"{source_info}  "
            f"[dim]{now}[/]",
        )


# ═══════════════════════════════════════════════════════════════
# Task Panel (left sidebar)
# ═══════════════════════════════════════════════════════════════

class TaskItem(ListItem):
    """A single task in the task panel."""

    def __init__(
        self,
        task_id: str,
        title: str,
        status: str = "notstarted",
        agent: str = "",
        progress: float = 0.0,
        assignee: str = "agent",
    ) -> None:
        super().__init__()
        self.task_id = task_id
        self.task_title = title
        self.task_status = status
        self.task_agent = agent
        self.task_progress = progress
        self.task_assignee = assignee

    def render(self) -> Text:
        icons = {
            "ongoing": "●",
            "notstarted": "○",
            "completed": "✅",
            "blocked": "🛑",
            "rejected": "✗",
            "cron": "🕐",
        }
        colors = {
            "ongoing": "green",
            "notstarted": "dim white",
            "completed": "green",
            "blocked": "red",
            "rejected": "red",
            "cron": "cyan",
        }
        icon = icons.get(self.task_status, "?")
        color = colors.get(self.task_status, "white")

        # Progress bar (5 chars)
        if self.task_progress > 0:
            filled = int(self.task_progress / 20)
            bar = "█" * filled + "░" * (5 - filled)
        else:
            bar = "═" * 5 if self.task_status == "notstarted" else " " * 5

        # Build text without markup to avoid Rich parsing agent names as style tags
        text = Text()
        text.append(f"{icon} ", style=color)
        text.append(f"{self.task_title[:30]}", style="bold")
        if self.task_agent:
            text.append(f" [{self.task_agent}]")
        text.append("  ")
        text.append(bar, style=color)
        if self.task_progress > 0:
            text.append(f" {self.task_progress:.0f}%")
        return text


class TaskPanel(Static):
    """Left panel showing task tree with status indicators."""

    filter: reactive[str] = reactive("all")

    class TaskSelected(Message):
        """Posted when a task is selected."""

        def __init__(self, task_id: str) -> None:
            super().__init__()
            self.task_id = task_id

    class NewTask(Message):
        """Posted when user wants to create a new task."""

    def compose(self) -> ComposeResult:
        with Vertical(id="task-panel-inner"):
            yield Label("Tasks", id="task-panel-title")
            with Horizontal(id="task-filters"):
                for f_id, f_label in [
                    ("all", "All"),
                    ("ongoing", "Ongoing"),
                    ("notstarted", "Not Started"),
                    ("blocked", "Blocked"),
                    ("completed", "Done"),
                ]:
                    yield Button(f_label, id=f"filter-{f_id}", variant="default")
            yield ListView(id="task-list")

    def update_tasks(self, tasks: list[dict]) -> None:
        """Replace all tasks in the list."""
        try:
            list_view = self.query_one("#task-list", ListView)
        except NoMatches:
            return
        list_view.clear()
        for t in tasks:
            list_view.append(TaskItem(
                task_id=t.get("id", ""),
                title=t.get("title", "?"),
                status=t.get("status", "notstarted"),
                agent=t.get("agent", ""),
                progress=t.get("progress", 0.0),
                assignee=t.get("assignee", "agent"),
            ))

    @on(ListView.Selected, "#task-list")
    def on_task_selected(self, event: ListView.Selected) -> None:
        if event.item and hasattr(event.item, "task_id"):
            self.post_message(self.TaskSelected(event.item.task_id))


# ═══════════════════════════════════════════════════════════════
# Agent Lane (one per agent, main content area)
# ═══════════════════════════════════════════════════════════════

class AgentLane(Static):
    """A single agent's live output stream with thinking overlay."""

    agent_name: reactive[str] = reactive("agent")
    agent_model: reactive[str] = reactive("—")
    agent_node: reactive[str] = reactive("")
    current_task: reactive[str] = reactive("")
    task_status: reactive[str] = reactive("notstarted")
    task_progress: reactive[float] = reactive(0.0)
    show_thinking: reactive[bool] = reactive(False)
    is_paused: reactive[bool] = reactive(False)
    is_offline: reactive[bool] = reactive(False)
    has_permission_pending: reactive[bool] = reactive(False)

    MAX_LINES = 500

    def __init__(
        self,
        agent_name: str = "agent",
        agent_model: str = "—",
        agent_node: str = "",
        current_task: str = "",
        task_status: str = "notstarted",
        task_progress: float = 0.0,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.agent_name = agent_name
        self.agent_model = agent_model
        self.agent_node = agent_node
        self.current_task = current_task
        self.task_status = task_status
        self.task_progress = task_progress
        self._output_lines: list[str] = []
        self._thinking_lines: list[str] = []

    def compose(self) -> ComposeResult:
        with Vertical(id=f"lane-{self.agent_name}"):
            # Header
            yield Label(self._render_header(), id="lane-header")
            # Output area
            yield VerticalScroll(Label("", id="lane-output"), id="lane-output-container")
            # Thinking area (collapsible)
            yield VerticalScroll(
                Label("", id="lane-thinking"),
                id="lane-thinking-container",
                classes="hidden",
            )

    def _render_header(self) -> str:
        node_label = f" @ {self.agent_node}" if self.agent_node else ""
        status_icons = {
            "ongoing": "●",
            "notstarted": "○",
            "completed": "✅",
            "blocked": "🛑",
            "rejected": "✗",
        }
        icon = status_icons.get(self.task_status, "●")

        if self.is_offline:
            color = "dim"
        elif self.has_permission_pending:
            color = "bold orange1"
        elif self.task_status == "ongoing":
            color = "bold green"
        elif self.task_status == "completed":
            color = "green"
        elif self.task_status == "blocked":
            color = "bold yellow"
        else:
            color = "dim"

        return (
            f"[{color}]{self.agent_name}[/] "
            f"[dim]({self.agent_model}){node_label}[/]  "
            f"{icon} {self.current_task[:40]}"
            + (f"  [{color}]{self.task_progress:.0f}%[/]" if self.task_progress > 0 else "")
            + (" [bold orange1]🔒[/]" if self.has_permission_pending else "")
            + (" [dim]⏸[/]" if self.is_paused else "")
        )

    def append_output(self, text: str) -> None:
        """Append a line to the agent's output stream."""
        self._output_lines.append(text)
        if len(self._output_lines) > self.MAX_LINES:
            self._output_lines = self._output_lines[-self.MAX_LINES:]
        self._refresh_output()

    def append_thinking(self, text: str) -> None:
        """Append a line to the agent's thinking stream."""
        self._thinking_lines.append(text)
        if len(self._thinking_lines) > self.MAX_LINES:
            self._thinking_lines = self._thinking_lines[-self.MAX_LINES:]
        if self.show_thinking:
            self._refresh_thinking()

    def _refresh_output(self) -> None:
        try:
            label = self.query_one("#lane-output", Label)
            label.update("\n".join(self._output_lines[-50:]))
        except NoMatches:
            pass

    def _refresh_thinking(self) -> None:
        try:
            label = self.query_one("#lane-thinking", Label)
            label.update("\n".join(
                f"[dim italic]{line}[/]" for line in self._thinking_lines[-30:]
            ))
        except NoMatches:
            pass

    def watch_show_thinking(self, show: bool) -> None:
        """Toggle thinking visibility."""
        try:
            container = self.query_one("#lane-thinking-container", VerticalScroll)
            container.set_class(not show, "hidden")
            if show:
                self._refresh_thinking()
        except NoMatches:
            pass

    def watch_is_offline(self) -> None:
        self._update_header()

    def watch_has_permission_pending(self) -> None:
        self._update_header()

    def watch_task_status(self) -> None:
        self._update_header()

    def watch_task_progress(self) -> None:
        self._update_header()

    def _update_header(self) -> None:
        try:
            header = self.query_one("#lane-header", Label)
            header.update(self._render_header())
        except NoMatches:
            pass


# ═══════════════════════════════════════════════════════════════
# Permission Modal
# ═══════════════════════════════════════════════════════════════

class PermissionModal(Static):
    """Modal overlay for permission requests."""

    DEFAULT_CSS = """
    PermissionModal {
        display: none;
        layer: overlay;
        background: $surface;
        border: thick $warning;
        padding: 1 2;
        width: 60;
        height: auto;
        dock: top;
        offset-x: 20;
        offset-y: 3;
    }
    PermissionModal.visible {
        display: block;
    }
    """

    class Verdict(Message):
        """Posted when human makes a decision."""

        def __init__(self, request_id: str, behavior: str) -> None:
            super().__init__()
            self.request_id = request_id
            self.behavior = behavior  # "allow", "allow_always", "deny"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._request_id: str = ""
        self._agent_name: str = ""
        self._tool_name: str = ""
        self._description: str = ""
        self._input_preview: str = ""

    def show_request(
        self,
        request_id: str,
        agent_name: str,
        task_title: str,
        tool_name: str,
        description: str = "",
        input_preview: str = "",
    ) -> None:
        """Display a permission request."""
        self._request_id = request_id
        self._agent_name = agent_name
        self._tool_name = tool_name
        self._description = description
        self._input_preview = input_preview
        self.set_class(True, "visible")
        self.refresh()

    def hide(self) -> None:
        self.set_class(False, "visible")

    def render(self) -> Panel:
        if not self._request_id:
            return Panel("", title="Permission")
        body = (
            f"[bold]Agent:[/] {self._agent_name}\n"
            f"[bold]Tool:[/]  {self._tool_name}\n"
        )
        if self._description:
            body += f'[italic]"{self._description}"[/]\n'
        if self._input_preview:
            body += f"\n[dim]{self._input_preview[:200]}[/]\n"
        body += (
            "\n"
            "[bold][a][/] Allow Once    "
            "[bold][A][/] Always Allow    "
            "[bold][d][/] Deny    "
            "[bold][Esc][/] Dismiss"
        )
        return Panel(body, title="🔒 Permission Required", border_style="orange1")

    def key_a(self) -> None:
        if self._request_id:
            self.post_message(self.Verdict(self._request_id, "allow"))
            self.hide()

    def key_shift_a(self) -> None:  # Textual uses uppercase for shift
        if self._request_id:
            self.post_message(self.Verdict(self._request_id, "allow_always"))
            self.hide()

    def key_d(self) -> None:
        if self._request_id:
            self.post_message(self.Verdict(self._request_id, "deny"))
            self.hide()

    def key_escape(self) -> None:
        self.hide()


# ═══════════════════════════════════════════════════════════════
# Command Palette
# ═══════════════════════════════════════════════════════════════

class CommandPalette(Static):
    """Vim-style command input (":" prefix)."""

    DEFAULT_CSS = """
    CommandPalette {
        display: none;
        layer: overlay;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
        width: 60;
        height: auto;
        dock: bottom;
        offset-x: 10;
    }
    CommandPalette.visible {
        display: block;
    }
    """

    class Command(Message):
        """Posted when a command is entered."""

        def __init__(self, command: str) -> None:
            super().__init__()
            self.command = command

    def compose(self) -> ComposeResult:
        yield Input(placeholder=":spawn coding --task \"Fix auth bug\"", id="cmd-input")

    def show(self) -> None:
        self.set_class(True, "visible")
        try:
            self.query_one("#cmd-input", Input).focus()
        except NoMatches:
            pass

    def hide(self) -> None:
        self.set_class(False, "visible")

    @on(Input.Submitted, "#cmd-input")
    def on_command_submitted(self, event: Input.Submitted) -> None:
        if event.value.strip():
            self.post_message(self.Command(event.value.strip()))
        self.hide()
        try:
            self.query_one("#cmd-input", Input).value = ""
        except NoMatches:
            pass


# ═══════════════════════════════════════════════════════════════
# Node Panel (mesh nodes, collapsible)
# ═══════════════════════════════════════════════════════════════

class NodePanel(Static):
    """Shows mesh nodes and their status."""

    nodes: reactive[list[dict]] = reactive([])

    def render(self) -> Panel:
        if not self.nodes:
            return Panel("[dim]No mesh nodes[/]", title="Nodes")

        lines = []
        for n in self.nodes:
            status_dot = "[green]●[/]" if n.get("status") == "online" else "[red]○[/]"
            agents = n.get("agent_count", 0)
            cpu = n.get("cpu_pct", 0)
            gpu = " GPU:✓" if n.get("gpu_available") else ""
            lines.append(
                f"{status_dot} [bold]{n.get('hostname', '?')}[/] "
                f"({n.get('id', '?')[:10]})  "
                f"CPU:{cpu}%{gpu}  agents:{agents}"
            )
        return Panel("\n".join(lines), title="Nodes")


# ═══════════════════════════════════════════════════════════════
# Toast / Notification widget
# ═══════════════════════════════════════════════════════════════

class Toast(Static):
    """Floating notification that auto-dismisses."""

    DEFAULT_CSS = """
    Toast {
        display: none;
        layer: overlay;
        background: $surface;
        border: solid $success;
        padding: 1 2;
        width: auto;
        max-width: 50;
        height: auto;
        dock: top;
        offset-x: 2;
        offset-y: 6;
    }
    Toast.visible {
        display: block;
    }
    Toast.-warning {
        border: solid $warning;
    }
    Toast.-error {
        border: solid $error;
    }
    """

    def show(self, message: str, severity: str = "info", duration: float = 4.0) -> None:
        self.update(message)
        self.set_class(True, "visible")
        if severity == "warning":
            self.add_class("-warning")
        elif severity == "error":
            self.add_class("-error")
        self.set_timer(duration, self._dismiss)

    def _dismiss(self) -> None:
        self.set_class(False, "visible")
        self.remove_class("-warning")
        self.remove_class("-error")
