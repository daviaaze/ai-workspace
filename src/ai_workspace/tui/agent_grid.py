"""
Agent Grid View — redesigned agent management view.

Replaces the old horizontal AgentLane layout with:
- Agent list (DataTable) for overview
- Selected agent detail panel with live output
- Better scalability for many agents
- Sortable/filterable list

Layout:
┌─ Agents ──────────────────────────────────────────────────────────────┐
│ [Spawn] [Kill] [Pause] [Chat]  Filter: [________]  Status: [all ▼]   │
├─────────────────────────────┬─────────────────────────────────────────┤
│ Name     Status  Task      P│  coding-agent  qwen3:14b  ● ongoing    │
│ coding   ● 80%   Fix auth… │  ─────────────────────────────────────  │
│ research ● 40%   Research… │  > Live output...                       │
│                            │  > More output...                       │
│                            │                                         │
│                            │  ── thinking ──                         │
│                            │  > reasoning trace...                   │
├─────────────────────────────┴─────────────────────────────────────────┤
│ [^S] spawn  [Space] pause  [^X] kill  [^Enter] chat  [^D] detail     │
└───────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import asyncio
from typing import Any

from rich.text import Text
from textual import on, work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import (
    Button,
    DataTable,
    Input,
    Label,
    Select,
    Static,
)

from ai_workspace.tui.widgets import AgentLane


class AgentList(DataTable):
    """Sortable list of all agents."""

    DEFAULT_CSS = """
    AgentList {
        width: 40;
        height: 1fr;
        border: solid $primary-background;
        background: $panel;
    }
    AgentList:focus {
        border: solid $accent;
    }
    AgentList .datatable--header {
        background: $boost;
        text-style: bold;
    }
    AgentList .datatable--cursor {
        background: $accent 30%;
    }
    """

    class Selected(Message):
        """Posted when an agent row is selected."""

        def __init__(self, agent_name: str) -> None:
            super().__init__()
            self.agent_name = agent_name

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._agents: list[dict[str, Any]] = []
        self._agent_rows: dict[str, int] = {}  # name -> row key
        self.add_columns("Agent", "Status", "Progress", "Task")
        self.cursor_type = "row"
        self.zebra_stripes = True

    def update_agents(self, agents: list[dict[str, Any]]) -> None:
        """Refresh the agent list."""
        self._agents = agents
        self.clear()
        self._agent_rows = {}

        for a in agents:
            name = a.get("name", "?")
            status = a.get("task_status", "notstarted")
            progress = a.get("task_progress", 0)
            task = a.get("current_task", "—")[:25]

            status_icons = {
                "ongoing": "[green]●[/]",
                "notstarted": "[dim]○[/]",
                "completed": "[green]✅[/]",
                "blocked": "[yellow]🛑[/]",
                "rejected": "[red]✗[/]",
            }
            icon = status_icons.get(status, "●")

            progress_str = f"{progress:.0f}%" if progress > 0 else "—"

            row_key = self.add_row(
                name,
                f"{icon} {status}",
                progress_str,
                task,
            )
            self._agent_rows[name] = row_key

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Find agent name from row key and post message."""
        for name, key in self._agent_rows.items():
            if key == event.row_key:
                self.post_message(self.Selected(name))
                return


class AgentDetail(VerticalScroll):
    """Right panel showing selected agent's live output."""

    DEFAULT_CSS = """
    AgentDetail {
        width: 1fr;
        height: 1fr;
        border: solid $primary-background;
        background: $panel;
        padding: 0 1;
    }
    AgentDetail:focus {
        border: solid $accent;
    }
    AgentDetail #detail-empty {
        padding: 4;
        text-style: dim;
        text-align: center;
    }
    """

    agent_name: reactive[str] = reactive("")
    agent_data: reactive[dict[str, Any]] = reactive({})

    def compose(self) -> ComposeResult:
        yield Label(
            "[dim]Select an agent to view details.[/]\n"
            "[dim]Use [bold]↑↓[/] to navigate the agent list.[/]",
            id="detail-empty",
        )

    def show_agent(self, agent: dict[str, Any]) -> None:
        """Display an agent's details."""
        self.agent_data = agent
        self.agent_name = agent.get("name", "")

        # Remove empty state
        try:
            self.query_one("#detail-empty", Label).remove()
        except NoMatches:
            pass

        # TODO: Mount an AgentLane or custom output widget here
        # For now, render as text
        self._render_agent()

    def _render_agent(self) -> None:
        if not self.agent_data:
            return

        a = self.agent_data
        name = a.get("name", "?")
        model = a.get("model", "—")
        status = a.get("task_status", "notstarted")
        task = a.get("current_task", "—")
        progress = a.get("task_progress", 0)
        node = a.get("node", "")

        status_icons = {
            "ongoing": "[green]●[/]",
            "notstarted": "[dim]○[/]",
            "completed": "[green]✅[/]",
            "blocked": "[yellow]🛑[/]",
            "rejected": "[red]✗[/]",
        }
        icon = status_icons.get(status, "●")

        progress_bar = ""
        if progress > 0:
            filled = int(progress / 5)
            bar = "█" * filled + "░" * (20 - filled)
            progress_bar = f"[{bar}] {progress:.0f}%\n"

        node_str = f" @ {node}" if node else ""

        content = (
            f"[bold]{name}[/] [dim]({model}){node_str}[/]\n"
            f"{icon} {status}  {task}\n"
            f"{progress_bar}\n"
            f"[dim]Live output will appear here...[/]"
        )

        self.update(Text.from_markup(content))

    def clear(self) -> None:
        """Clear detail view."""
        self.agent_data = {}
        self.agent_name = ""
        self.update(Text.from_markup(
            "[dim]Select an agent to view details.[/]\n"
            "[dim]Use [bold]↑↓[/] to navigate the agent list.[/]"
        ))


class AgentsView(Vertical):
    """Full agent management view with list + detail."""

    DEFAULT_CSS = """
    AgentsView {
        height: 1fr;
        padding: 1;
        background: $background;
    }

    AgentsView #agents-toolbar {
        height: auto;
        padding: 0 0 1 0;
    }

    AgentsView #agents-toolbar Button {
        margin: 0 1 0 0;
    }

    AgentsView #agents-toolbar Input {
        width: 25;
        margin: 0 1 0 0;
    }

    AgentsView #agents-toolbar Select {
        width: 15;
        margin: 0;
    }

    AgentsView #agents-body {
        height: 1fr;
    }
    """

    agents: reactive[list[dict[str, Any]]] = reactive([])
    selected_agent: reactive[str] = reactive("")

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._filtered_agents: list[dict[str, Any]] = []
        self._status_filter: str = "all"

    def compose(self) -> ComposeResult:
        with Horizontal(id="agents-toolbar"):
            yield Button("🚀 Spawn", id="av-spawn", variant="primary")
            yield Button("⏸ Pause", id="av-pause", variant="default")
            yield Button("🔴 Kill", id="av-kill", variant="error")
            yield Button("💬 Chat", id="av-chat", variant="default")
            yield Input(placeholder="Filter agents...", id="av-filter")
            yield Select(
                [("All", "all"), ("Running", "ongoing"), ("Done", "completed"),
                 ("Blocked", "blocked"), ("Idle", "notstarted")],
                value="all",
                id="av-status-filter",
            )

        with Horizontal(id="agents-body"):
            yield AgentList(id="agent-list")
            yield AgentDetail(id="agent-detail")

    def update_agents(self, agents: list[dict[str, Any]]) -> None:
        self.agents = agents
        self._apply_filter()

    def _apply_filter(self) -> None:
        """Apply text and status filters."""
        try:
            filter_input = self.query_one("#av-filter", Input)
            text_filter = filter_input.value.lower()
        except NoMatches:
            text_filter = ""

        filtered = self.agents

        # Status filter
        if self._status_filter != "all":
            filtered = [a for a in filtered if a.get("task_status") == self._status_filter]

        # Text filter
        if text_filter:
            filtered = [
                a for a in filtered
                if text_filter in a.get("name", "").lower()
                or text_filter in a.get("current_task", "").lower()
            ]

        self._filtered_agents = filtered

        try:
            agent_list = self.query_one("#agent-list", AgentList)
            agent_list.update_agents(filtered)
        except NoMatches:
            pass

    @on(AgentList.Selected)
    def on_agent_selected(self, event: AgentList.Selected) -> None:
        self.selected_agent = event.agent_name
        agent = next(
            (a for a in self.agents if a.get("name") == event.agent_name),
            {},
        )
        try:
            detail = self.query_one("#agent-detail", AgentDetail)
            detail.show_agent(agent)
        except NoMatches:
            pass

    @on(Input.Changed, "#av-filter")
    def on_filter_changed(self, event: Input.Changed) -> None:
        self._apply_filter()

    @on(Select.Changed, "#av-status-filter")
    def on_status_filter_changed(self, event: Select.Changed) -> None:
        self._status_filter = str(event.value) if event.value else "all"
        self._apply_filter()

    def get_selected_agent(self) -> dict[str, Any] | None:
        """Get the currently selected agent data."""
        if not self.selected_agent:
            return None
        return next(
            (a for a in self.agents if a.get("name") == self.selected_agent),
            None,
        )
