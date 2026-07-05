"""
Agent Monitor — collapsible bar showing active agent progress.

Visible only when there are running agents. Shows compact cards
with: agent name, type, current task, step count, and progress.

Refs: SPEC_TUI_V5.md
"""

from __future__ import annotations

from typing import ClassVar

from textual.containers import Horizontal, Vertical
from textual.reactive import reactive


class AgentCard(Horizontal):
    """A single agent card in the monitor bar.

    Shows: [icon] agent-name status "task description" step N/M progress%
    """

    agent_name: reactive[str] = reactive("")
    agent_type: reactive[str] = reactive("general")
    status: reactive[str] = reactive("idle")  # idle, running, paused, done, error
    current_task: reactive[str] = reactive("")
    current_step: reactive[int] = reactive(0)
    total_steps: reactive[int | None] = reactive(None)
    progress_pct: reactive[int] = reactive(0)

    TYPE_MARKERS: ClassVar[dict[str, str]] = {
        "coding": "C",
        "research": "R",
        "general": "G",
    }

    STATUS_MARKERS: ClassVar[dict[str, str]] = {
        "idle": "[$text 50%]idle[/]",
        "running": "[$primary]running[/]",
        "paused": "[$warning]paused[/]",
        "done": "[$success]done[/]",
        "error": "[$error]error[/]",
    }

    def render(self) -> str:
        marker = self.TYPE_MARKERS.get(self.agent_type, "?")
        status_str = self.STATUS_MARKERS.get(self.status, self.status)

        # Progress
        if self.total_steps:
            progress = f" step {self.current_step}/{self.total_steps}"
        elif self.progress_pct > 0:
            progress = f" {self.progress_pct}%"
        else:
            progress = ""

        # Task text (truncated)
        task = self.current_task[:40] if self.current_task else ""

        return (
            f" [$text 60%]{marker}[/] "
            f"[bold $text 80%]{self.agent_name}[/] "
            f"{status_str} "
            f"[$text 70%]{task}[/]{progress}"
        )


class AgentMonitor(Vertical):
    """Collapsible bar that shows all active agent cards.

    Hidden (height 0) when no agents are running. Automatically
    shrinks when all agents complete.
    """

    DEFAULT_CSS = """
    AgentMonitor {
        height: auto;
        padding: 0 1;
        background: $surface;
        border-bottom: solid $primary 20%;
    }
    """

    agents: reactive[list[dict]] = reactive([])
    """List of agent state dicts. Each has: name, type, status, task, step, total_steps, pct."""

    def watch_agents(self, agents: list[dict]) -> None:
        """Rebuild cards when agent list changes."""
        # Guard: remove_children needs a running Textual app
        try:
            self.remove_children()
        except Exception:
            pass  # No app context (e.g., during testing)

        if not agents:
            try:
                self.styles.height = "0"
            except Exception:
                pass
            return

        try:
            self.styles.height = "auto"
        except Exception:
            pass

        for ag in agents:
            try:
                self.mount(AgentCard(
                    agent_name=ag.get("name", "agent"),
                    agent_type=ag.get("type", "general"),
                    status=ag.get("status", "idle"),
                    current_task=ag.get("task", ""),
                    current_step=ag.get("step", 0),
                    total_steps=ag.get("total_steps"),
                    progress_pct=ag.get("pct", 0),
                ))
            except Exception:
                pass  # No app context

    def upsert_agent(self, name: str, **kwargs: object) -> None:
        """Add or update an agent card."""
        # Find existing or create new entry
        found = False
        updated = []
        for ag in self.agents:
            if ag.get("name") == name:
                ag.update(kwargs)
                found = True
            updated.append(ag)

        if not found:
            entry = {"name": name, "type": "general", "status": "idle", "task": "", "step": 0, "pct": 0}
            entry.update(kwargs)
            updated.append(entry)

        self.agents = updated

    def remove_agent(self, name: str) -> None:
        """Remove an agent card from the monitor."""
        self.agents = [ag for ag in self.agents if ag.get("name") != name]
