"""
Detail View — full-screen expand of a focused agent lane.

Opened with Ctrl+D. Shows the agent's output, thinking, and status
at full width/height with more visible output lines and live metrics.

Layout:
 Detail: coding-agent
 Model: qwen3:14b  Status:  ongoing  45%  Session: abc123def  0:03:12


  > Live output stream...
  > Full agent output with all lines visible...
  > ...

   thinking
  > Agent reasoning trace...



 [^D/^L/Esc back]  [^T thinking]  [Space pause]  [^X kill]  [^Enter chat]

"""

from __future__ import annotations

from textual.app import ComposeResult, Screen
from textual.containers import Container, VerticalScroll
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widgets import Footer, Label, Static

from ai_workspace.tui.widgets import AgentLane


class DetailHeader(Static):
    """Header bar showing agent metadata in detail view."""

    agent_name: reactive[str] = reactive("")
    agent_model: reactive[str] = reactive("")
    status: reactive[str] = reactive("")
    progress: reactive[float] = reactive(0.0)
    session_id: reactive[str] = reactive("")
    runtime: reactive[str] = reactive("")
    tokens_used: reactive[int] = reactive(0)
    cost: reactive[float] = reactive(0.0)

    def render(self) -> str:
        status_icons = {
            "ongoing": "[green][/]",
            "notstarted": "[dim][/]",
            "completed": "[green][/]",
            "blocked": "[yellow][/]",
            "rejected": "[red][/]",
        }
        icon = status_icons.get(self.status, "")

        parts = [
            f"[bold]{self.agent_name}[/]",
            f"[dim]{self.agent_model}[/]",
            f"{icon} {self.status}",
        ]
        if self.progress > 0:
            parts.append(f"{self.progress:.0f}%")
        if self.session_id:
            parts.append(f"[dim]session:{self.session_id[:10]}[/]")
        if self.runtime:
            parts.append(f"[dim]{self.runtime}[/]")
        if self.tokens_used > 0:
            parts.append(f"{self.tokens_used:,} tok")
        if self.cost > 0:
            parts.append(f"${self.cost:.4f}")

        return "  ".join(parts)


class DetailScreen(Screen[None]):
    """Full-screen detail view for a single agent lane.

    Takes the existing AgentLane widget and shows it maximized with
    extra metadata (model, session, runtime, tokens, cost).
    """

    CSS = """
    DetailScreen {
        layers: base;
    }

    #detail-header {
        height: 1;
        padding: 0 2;
        background: $boost;
        border-bottom: solid $primary 20%;
    }

    #detail-body {
        height: 1fr;
    }

    #detail-body > AgentLane {
        height: 1fr;
        border: none;
    }

    #detail-body > AgentLane > #lane-output-container {
        height: 1fr;
    }

    #detail-body > AgentLane > #lane-thinking-container {
        max-height: 50%;
    }

    #detail-help {
        dock: bottom;
        height: 1;
        padding: 0 2;
        background: $boost;
        border-top: solid $primary 20%;
        text-style: dim;
    }
    """

    BINDINGS = [
        ("ctrl+d", "back", "Back"),
        ("ctrl+l", "back", "Back"),
        ("escape", "back", "Back"),
        ("q", "back", "Back"),
        ("ctrl+t", "toggle_thinking", "Thinking"),
        ("space", "toggle_pause", "Pause"),
        ("ctrl+x", "kill", "Kill"),
        ("ctrl+enter", "open_chat", "Chat"),
    ]

    def __init__(
        self,
        lane: AgentLane,
        session_id: str = "",
        context_manager=None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._lane = lane
        self._session_id = session_id
        self._context_manager = context_manager
        self._start_time = None
        self._runtime_timer = None
        self._original_parent = lane.parent  # Save for restore on dismiss

    def compose(self) -> ComposeResult:
        yield DetailHeader(id="detail-header")
        with Container(id="detail-body"):
            # The lane is mounted via mount() after compose
            yield VerticalScroll(id="detail-body-placeholder")
        yield Label(
            "[dim][^D/Esc] back  [^T] thinking  [Space] pause  "
            "[^X] kill  [^Enter] chat[/]",
            id="detail-help",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Mount the actual lane widget and start runtime tracking."""
        import time

        # Replace placeholder with actual lane
        try:
            placeholder = self.query_one("#detail-body-placeholder", VerticalScroll)
            placeholder.remove()
        except NoMatches:
            pass

        # Clone lane state into detail view
        # We mount the lane into our body — it keeps its worker/drain_timer
        try:
            body = self.query_one("#detail-body", Container)
            body.mount(self._lane)
        except NoMatches:
            pass

        # Update header
        self._start_time = time.time()
        self._update_header()

        # Start periodic header refresh (runtime counter)
        self._runtime_timer = self.set_interval(1.0, self._update_header)

    def _update_header(self) -> None:
        """Refresh the detail header with current metrics."""
        import time

        try:
            header = self.query_one(DetailHeader)
        except NoMatches:
            return

        header.agent_name = self._lane.agent_name
        header.agent_model = self._lane.agent_model
        header.status = self._lane.task_status
        header.progress = self._lane.task_progress
        header.session_id = self._session_id

        # Runtime
        if self._start_time:
            elapsed = int(time.time() - self._start_time)
            h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
            if h > 0:
                header.runtime = f"{h}:{m:02d}:{s:02d}"
            else:
                header.runtime = f"{m}:{s:02d}"

        # Token/cost from context manager
        if self._context_manager:
            header.tokens_used = self._context_manager.total_tokens

        # Cost from CostService
        try:
            from ai_workspace.core.cost import CostService
            cost = CostService()
            header.cost = cost.logger.today_cost()
        except Exception:
            header.cost = 0.0

        header.refresh()


    def action_back(self) -> None:
        """Return to agent lanes — restore lane to original parent before dismiss."""
        # Stop runtime timer
        if self._runtime_timer:
            self._runtime_timer.stop()
            self._runtime_timer = None
        # Return lane widget to its original parent in the main app
        if self._lane and self._original_parent:
            try:
                self._lane.remove()  # Remove from our screen
                self._original_parent.mount(self._lane)
            except Exception:
                pass
        self.dismiss(None)

    def action_toggle_thinking(self) -> None:
        """Toggle thinking visibility for this lane."""
        if self._lane:
            self._lane.show_thinking = not self._lane.show_thinking

    def action_toggle_pause(self) -> None:
        """Pause/resume via lane's worker."""
        # The lane handles this — we just toggle the reactive
        if self._lane:
            self._lane.is_paused = not self._lane.is_paused

    def action_kill(self) -> None:
        """Kill the agent."""
        if self._lane and self._lane._worker:
            self._lane._worker.kill()
            self._lane.detach_worker()
            self._lane.task_status = "rejected"

    def action_open_chat(self) -> None:
        """Open chat screen for this agent."""
        from ai_workspace.tui.chat import push_chat_screen

        # Try to get the app (parent)
        app = self.app
        if not app:
            return

        worker = self._lane._worker if self._lane else None
        push_chat_screen(
            app,
            agent_name=self._lane.agent_name if self._lane else "agent",
            model=self._lane.agent_model if self._lane else "qwen3:14b",
            session_id=self._session_id,
            cwd=getattr(app, 'cwd', '.'),
            worker=worker,
            context_manager=self._context_manager,
        )
