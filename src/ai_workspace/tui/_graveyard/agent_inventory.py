"""
Agent Inventory Panel — game-style agent cards with MCP/skill loadout.

Shows agents as character-like cards with:
  - Status indicator (health-bar style)
  - Task and progress
  - Skill slots (coding, research, search)
  - MCP equipment (filesystem, git, db, web)
  - Quick actions (spawn, kill, focus)

Design (inspired by RPG character screens):
[  Agents ]
                                                                
   coding-1   
    ONLINE   Fix auth middleware                          
    80%  0:03:12                                   
                                                             
   Skills:  [web] [code] [search]                            
   MCPs:    [ fs] [ git] [ db]                          
                                                             
   [ Chat] [ Pause] [ Kill] [ Detail]                
    
                                                                
   research-1   
    IDLE   MCP tools comparison                           
    0%                                             
   Skills:  [web] [search]                                   
   MCPs:    [ fs]                                          
   [ Resume] [ Kill]                                      
    
                                                                
  [ Spawn New Agent]                                         

"""

from __future__ import annotations

from typing import Any

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Label, Static


class AgentCard(Static):
    """A single agent displayed as a character-style card."""

    DEFAULT_CSS = """
    AgentCard {
        height: auto;
        border: solid $primary 20%;
        background: $surface;
        padding: 1;
        margin: 0 0 1 0;
    }

    AgentCard:hover {
        border: solid $primary;
    }

    AgentCard.-focused {
        border: solid $accent;
        background: $boost;
    }

    AgentCard .card-header {
        height: 1;
        padding: 0 1;
    }

    AgentCard .card-status {
        height: 1;
        padding: 0 1;
    }

    AgentCard .card-progress {
        height: auto;
        padding: 0 1;
    }

    AgentCard .card-loadout {
        height: auto;
        padding: 0 1;
    }

    AgentCard .card-actions {
        height: auto;
        padding: 1 1 0 1;
    }

    AgentCard .card-actions Button {
        margin: 0 1 0 0;
        min-width: 8;
    }

    AgentCard .card-empty {
        padding: 1 2;
        text-style: dim;
        text-align: center;
    }

    AgentCard .skill-badge {
        padding: 0 1;
        border: solid $success 40%;
        text-style: bold;
    }

    AgentCard .skill-badge:hover {
        border: solid $success;
    }

    AgentCard .mcp-badge {
        padding: 0 1;
        border: solid $primary 40%;
    }

    AgentCard .mcp-badge:hover {
        border: solid $primary;
    }
    """

    class ChatRequested(Message):
        def __init__(self, agent_name: str) -> None:
            super().__init__()
            self.agent_name = agent_name

    class PauseRequested(Message):
        def __init__(self, agent_name: str) -> None:
            super().__init__()
            self.agent_name = agent_name

    class KillRequested(Message):
        def __init__(self, agent_name: str) -> None:
            super().__init__()
            self.agent_name = agent_name

    class DetailRequested(Message):
        def __init__(self, agent_name: str) -> None:
            super().__init__()
            self.agent_name = agent_name

    class FocusRequested(Message):
        def __init__(self, agent_name: str) -> None:
            super().__init__()
            self.agent_name = agent_name

    agent_name: reactive[str] = reactive("")
    agent_model: reactive[str] = reactive("")
    task: reactive[str] = reactive("")
    status: reactive[str] = reactive("notstarted")
    progress: reactive[float] = reactive(0.0)
    runtime: reactive[str] = reactive("")
    skills: reactive[list[str]] = reactive(["code", "search"])
    mcps: reactive[list[str]] = reactive(["filesys", "git"])
    is_focused: reactive[bool] = reactive(False)
    is_paused: reactive[bool] = reactive(False)

    def __init__(
        self,
        agent_name: str = "",
        model: str = "",
        task: str = "",
        status: str = "notstarted",
        progress: float = 0.0,
        runtime: str = "",
        skills: list[str] | None = None,
        mcps: list[str] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.agent_name = agent_name
        self.agent_model = model
        self.task = task
        self.status = status
        self.progress = progress
        self.runtime = runtime
        self.skills = skills or ["code", "search"]
        self.mcps = mcps or ["filesys", "git"]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self._render_header(), classes="card-header")
            yield Label(self._render_status(), classes="card-status")
            yield Label(self._render_progress(), classes="card-progress")

            with Horizontal(classes="card-loadout"):
                skill_text = " ".join(
                    f"[bold green]{s}[/]" for s in self.skills
                )
                yield Label(f"Skills: {skill_text}")
            with Horizontal(classes="card-loadout"):
                mcp_text = " ".join(
                    f"[cyan]{m}[/]" for m in self.mcps
                )
                yield Label(f"MCPs: {mcp_text}")

            with Horizontal(classes="card-actions"):
                yield Button(" Chat", id=f"card-chat-{self.agent_name}", variant="primary")
                yield Button(" Pause" if not self.is_paused else " Resume",
                           id=f"card-pause-{self.agent_name}", variant="default")
                yield Button(" Kill", id=f"card-kill-{self.agent_name}", variant="error")
                yield Button(" Detail", id=f"card-detail-{self.agent_name}", variant="default")

    def _render_header(self) -> str:
        model_str = f" · {self.agent_model}" if self.agent_model else ""
        return f"[bold]{self.agent_name}[/][dim]{model_str}[/]"

    def _render_status(self) -> str:
        status_map = {
            "ongoing": ("", "ONLINE", "green"),
            "notstarted": ("", "OFFLINE", "dim"),
            "completed": ("", "DONE", "green"),
            "blocked": ("", "PAUSED", "yellow"),
            "rejected": ("", "KILLED", "red"),
        }
        dot, label, color = status_map.get(self.status, ("", self.status.upper(), "white"))
        task_str = self.task[:35] if self.task else "—"
        return f"[{color}]{dot} {label}[/]  {task_str}"

    def _render_progress(self) -> str:
        if self.progress > 0:
            width = 10
            filled = int((self.progress / 100) * width)
            bar = "" * filled + "" * (width - filled)
            color = "green" if self.progress < 70 else ("yellow" if self.progress < 90 else "red")
            pct = f"[{color}]{bar}[/] {self.progress:.0f}%"
        else:
            pct = "" * 10 + " 0%"

        runtime_str = f"  {self.runtime}" if self.runtime else ""
        return f"{pct}{runtime_str}"

    def watch_is_focused(self, value: bool) -> None:
        if value:
            self.add_class("-focused")
        else:
            self.remove_class("-focused")

    def on_click(self) -> None:
        self.post_message(self.FocusRequested(self.agent_name))

    # Button presses bubble up to App for handling
    # (IDs are dynamic: card-chat-{name}, card-pause-{name}, etc.)


class AgentInventoryPanel(VerticalScroll):
    """Full agent inventory with card list and spawn button.

    This is the content widget mounted inside a SidePanel on the left stack.
    """

    DEFAULT_CSS = """
    AgentInventoryPanel {
        height: 1fr;
        padding: 1;
    }

    AgentInventoryPanel #inv-header {
        dock: top;
        height: 1;
        padding: 0 1 1 1;
        text-style: bold;
        border-bottom: solid $primary 20%;
        background: $boost;
    }

    AgentInventoryPanel #inv-cards {
        height: 1fr;
        padding: 1 0 0 0;
    }

    AgentInventoryPanel #inv-footer {
        dock: bottom;
        height: auto;
        padding: 1 0 0 0;
    }

    AgentInventoryPanel #inv-empty {
        padding: 2 2;
        text-style: dim;
        text-align: center;
    }
    """

    class SpawnRequested(Message):
        """Posted when user wants to spawn a new agent."""
        pass

    agents: reactive[list[dict[str, Any]]] = reactive([])

    def compose(self) -> ComposeResult:
        yield Label(" Agents", id="inv-header")
        yield VerticalScroll(id="inv-cards")
        with Horizontal(id="inv-footer"):
            yield Button(" Spawn Agent", id="inv-spawn", variant="primary")

    def update_agents(self, agents: list[dict[str, Any]]) -> None:
        """Refresh the agent card list."""
        self.agents = agents
        try:
            container = self.query_one("#inv-cards", VerticalScroll)
        except NoMatches:
            return

        # Remove old cards
        for child in list(container.children):
            if isinstance(child, AgentCard):
                child.remove()

        try:
            container.query_one("#inv-empty").remove()
        except NoMatches:
            pass

        if not agents:
            container.mount(Label(
                "No agents equipped.\n\n"
                "[dim]Type a task to auto-spawn,[/]\n"
                "[dim]or press [bold] Spawn[/] below.[/]",
                id="inv-empty",
            ))
            return

        for a in agents:
            card = AgentCard(
                agent_name=a.get("name", "?"),
                model=a.get("model", ""),
                task=a.get("current_task", ""),
                status=a.get("task_status", "notstarted"),
                progress=a.get("task_progress", 0.0),
                runtime=a.get("runtime", ""),
                skills=a.get("skills", ["code", "search"]),
                mcps=a.get("mcps", ["filesys", "git"]),
                id=f"card-{a.get('name', '?')}",
            )
            container.mount(card)

    def focus_agent(self, agent_name: str) -> None:
        """Highlight a specific agent card."""
        try:
            container = self.query_one("#inv-cards", VerticalScroll)
            for child in container.children:
                if isinstance(child, AgentCard):
                    child.is_focused = (child.agent_name == agent_name)
        except NoMatches:
            pass

    @on(Button.Pressed, "#inv-spawn")
    def on_spawn(self, event: Button.Pressed) -> None:
        event.stop()
        self.post_message(self.SpawnRequested())
