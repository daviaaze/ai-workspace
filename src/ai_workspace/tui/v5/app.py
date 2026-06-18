"""
TUI v5 — Router-based terminal interface for AI Workspace.

Single main screen (chat-first) with overlays for secondary views.
Integrates with the AgentLoop for real-time streaming of agent steps.

Layout:
  Header (workspace, model, cost, tokens)
  AgentMonitor (collapsible, visible when agents are active)
  Conversation (infinite scroll of messages + agent steps)
  InputBar + HelpBar (slash commands, context-aware shortcuts)

Overlays (ModalScreen):
  Chat (F2), Files (Ctrl+O), Git (Ctrl+G), Search (/search),
  Help (F1), Dashboard (F3)

Refs: SPEC_TUI_V5.md
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.theme import Theme
from textual.widgets import Footer, Input, Label, Static

from ai_workspace.agents.loop import (
    LoopParams,
    LoopPattern,
    LoopEvent,
    TerminalReason,
    LoopState,
    suggest_pattern,
    agent_loop,
)
from ai_workspace.tui.v5.agent_monitor import AgentMonitor
from ai_workspace.tui.v5.conversation import Conversation, ConversationEntry
from ai_workspace.tui.v5.input_bar import InputBar, SLASH_COMMANDS

logger = logging.getLogger("aiw.tui.v5")


# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------

THEME = Theme(
    name="workstation",
    primary="#5B8DEE",
    secondary="#7C8DB5",
    accent="#5B8DEE",
    warning="#D4A853",
    error="#E0556A",
    success="#5FA874",
    background="#0F1117",
    surface="#161822",
    panel="#1D1F2B",
    dark=True,
    variables={
        "block-cursor-foreground": "#0F1117",
        "block-cursor-background": "#5B8DEE",
        "input-cursor-background": "#5B8DEE",
        "input-cursor-foreground": "#0F1117",
        "input-selection-background": "#5B8DEE 30%",
        "footer-key-foreground": "#5B8DEE",
        "footer-description-foreground": "#7C8DB5",
        "footer-background": "#161822",
    },
)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------


class Header(Static):
    """Top bar: workspace, model, agent count, cost, tokens, clock."""

    cwd: reactive[str] = reactive("~")
    model: reactive[str] = reactive("qwen3:14b")
    agents_online: reactive[int] = reactive(0)
    agents_total: reactive[int] = reactive(0)
    cost_today: reactive[str] = reactive("$0.00")
    tokens: reactive[str] = reactive("0t")
    clock: reactive[str] = reactive("")

    def render(self) -> str:
        # Shorten path
        home = str(Path.home())
        p = self.cwd
        if p.startswith(home):
            p = "~" + p[len(home):]
        if len(p) > 32:
            p = "..." + p[-29:]

        parts = [f"[bold $primary]aiw[/]  [$text 70%]{p}[/]"]

        parts.append(f"[$text 60%]{self.model}[/]")

        if self.agents_total:
            parts.append(
                f"[$success]{self.agents_online}[/]/"
                f"[$text 40%]{self.agents_total}[/] agents"
            )

        if self.cost_today and self.cost_today != "$0.00":
            parts.append(f"[$text 50%]{self.cost_today}[/]")

        if self.tokens and self.tokens != "0t":
            parts.append(f"[$text 50%]{self.tokens}[/]")

        if self.clock:
            parts.append(f"[$text 40%]{self.clock}[/]")

        return "  ".join(parts)


# ---------------------------------------------------------------------------
# Help overlay
# ---------------------------------------------------------------------------


class HelpScreen(ModalScreen[None]):
    """Keyboard and command reference."""

    CSS = """
    HelpScreen {
        align: center middle;
        background: $background 85%;
    }
    #help-box {
        width: 56;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: solid $primary 40%;
        padding: 1 2;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with Static(id="help-box"):
            yield Label(
                "\n"
                "[bold $primary]AI Workspace[/] — Commands\n"
                "\n"
                + "\n".join(
                    f"  [bold $text 80%]{cmd:<36}[/] [$text 60%]{desc}[/]"
                    for cmd, desc in SLASH_COMMANDS.items()
                )
                + "\n\n"
                "  [bold $primary]Shortcuts[/]\n"
                "  [bold]F1[/] [$text 60%]Help[/]              "
                "[bold]F2[/] [$text 60%]Chat[/]\n"
                "  [bold]F3[/] [$text 60%]Dashboard[/]        "
                "[bold]Ctrl+O[/] [$text 60%]Files[/]\n"
                "  [bold]Ctrl+G[/] [$text 60%]Git[/]           "
                "[bold]Ctrl+S[/] [$text 60%]Spawn[/]\n"
                "  [bold]Space[/] [$text 60%]Pause[/]          "
                "[bold]Ctrl+K[/] [$text 60%]Kill[/]\n"
                "  [bold]Ctrl+C[/] [$text 60%]Quit[/]\n"
                "\n",
            )

    def action_dismiss(self) -> None:
        self.dismiss()


# ---------------------------------------------------------------------------
# Main screen
# ---------------------------------------------------------------------------


class MainScreen(Screen[None]):
    """Primary screen: header, monitor, conversation, input."""

    AUTO_FOCUS = None

    BINDINGS = [
        Binding("ctrl+s", "spawn", "Spawn"),
        Binding("f1", "help", "Help"),
        Binding("f2", "chat", "Chat"),
        Binding("f3", "dashboard", "Dashboard"),
        Binding("space", "pause", "Pause"),
        Binding("ctrl+k", "kill", "Kill"),
        Binding("ctrl+o", "files", "Files"),
        Binding("ctrl+g", "git", "Git"),
        Binding("escape", "dismiss_overlay", "", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Header(id="header")
        yield AgentMonitor(id="monitor")
        yield Conversation(id="conversation")
        yield InputBar(id="input")

    def on_mount(self) -> None:
        self.query_one("#input", InputBar).focus_input()
        self._update_clock()
        self.set_interval(60, self._update_clock)

    def _update_clock(self) -> None:
        try:
            now = datetime.now().strftime("%H:%M")
            self.query_one("#header", Header).clock = now
        except Exception:
            pass

    # -- Action handlers (delegated to app) --

    def action_spawn(self) -> None:
        self.app.action_spawn()

    def action_help(self) -> None:
        self.app.push_screen(HelpScreen())

    def action_chat(self) -> None:
        self.app.action_chat()

    def action_dashboard(self) -> None:
        self.app.action_dashboard()

    def action_pause(self) -> None:
        self.app.action_pause()

    def action_kill(self) -> None:
        self.app.action_kill()

    def action_files(self) -> None:
        self.app.action_files()

    def action_git(self) -> None:
        self.app.action_git()

    def action_dismiss_overlay(self) -> None:
        if len(self.app.screen_stack) > 1:
            self.app.pop_screen()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------


class AIWorkspaceApp(App[None], inherit_bindings=False):
    """TUI v5 application — router-based, chat-first, AgentLoop-powered."""

    TITLE = "AI Workspace"
    SUB_TITLE = ""
    AUTO_FOCUS = None

    CSS = """
    * { scrollbar-size-vertical: 1; scrollbar-color: $primary 10%; scrollbar-color-hover: $primary 60%; scrollbar-background: $background; }
    Screen { background: $background; }
    Header { dock: top; height: 1; padding: 0 2; background: $surface; border-bottom: solid $primary 25%; }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.cwd = str(Path.cwd())
        self._main: MainScreen | None = None
        self._default_model = "qwen3:14b"
        self._agent_task: asyncio.Task | None = None
        self._agent_running = False
        self._agent_name = "agent-1"
        self._current_step = 0

    # -- Lifecycle --

    def on_mount(self) -> None:
        self.register_theme(THEME)
        self.theme = "workstation"
        self._main = MainScreen()
        self.push_screen(self._main)
        self._load_git_info()

    @property
    def m(self) -> MainScreen:
        assert self._main is not None
        return self._main

    # -- Agent loop integration --

    async def _step_callback(self, event: LoopEvent) -> None:
        """Called by AgentLoop for each event. Updates the TUI."""
        try:
            conv = self.m.query_one("#conversation", Conversation)
            monitor = self.m.query_one("#monitor", AgentMonitor)
        except Exception:
            return

        etype = event.type
        data = event.data

        if etype == "token":
            # Append text to last agent entry
            conv.add_agent_result(data.get("text", ""))

        elif etype == "thinking":
            self._current_step += 1
            conv.add_agent_thought(
                data.get("thought", ""),
                agent_name=self._agent_name,
                step=self._current_step,
            )
            monitor.upsert_agent(
                self._agent_name,
                status="running",
                step=self._current_step,
            )

        elif etype == "tool_call":
            conv.add_agent_action(
                data.get("tool", "?"),
                str(data.get("args", "")),
                agent_name=self._agent_name,
                step=self._current_step,
            )

        elif etype == "tool_result":
            conv.add_agent_observation(
                data.get("result", ""),
                agent_name=self._agent_name,
                step=self._current_step,
            )

        elif etype == "error":
            conv.add_error(f"{data.get('message', 'Unknown error')}")

        elif etype == "phase":
            pass  # Internal phase indicator, no display needed

        elif etype == "done":
            reason = data.get("reason", "completed")
            turns = data.get("turns", 0)
            tokens = data.get("tokens", 0)

            if reason == "completed":
                conv.add_system(f"Done in {turns} turns, {tokens} tokens")
                monitor.upsert_agent(self._agent_name, status="done")
            else:
                conv.add_error(f"Stopped: {reason}")
                monitor.upsert_agent(self._agent_name, status="error")

            self._agent_running = False
            self._current_step = 0
            self._refresh_input_bar()

    async def _run_agent(self, task: str) -> None:
        """Execute the agent loop for a given task."""
        tools: list[dict] = []
        # Auto-detect pattern
        pattern = suggest_pattern(task, tools)

        # Build params
        params = LoopParams(
            task=task,
            pattern=pattern,
            model=self._default_model,
            tools=tools,
            tool_handlers={},
            max_turns=20,
            stream=True,
            on_step=None,  # We handle events via the async generator
        )

        # Update header
        try:
            header = self.m.query_one("#header", Header)
            header.model = self._default_model
        except Exception:
            pass

        # Add user message to conversation
        conv = self.m.query_one("#conversation", Conversation)
        conv.add_user_message(task)

        # Spawn agent in monitor
        monitor = self.m.query_one("#monitor", AgentMonitor)
        monitor.upsert_agent(
            self._agent_name,
            type="general",
            status="running",
            task=task[:60],
            step=0,
            pct=0,
        )

        self._agent_running = True
        self._refresh_input_bar()
        self._current_step = 0

        try:
            async for event in agent_loop(params):
                await self._step_callback(event)
        except Exception as exc:
            logger.exception("Agent loop failed")
            conv.add_error(f"Agent error: {exc}")
            monitor.upsert_agent(self._agent_name, status="error")
            self._agent_running = False
            self._refresh_input_bar()

    # -- Slash command handling --

    async def _handle_slash(self, text: str) -> None:
        cmd, _, args = text.partition(" ")

        if cmd == "/help":
            self.push_screen(HelpScreen())

        elif cmd == "/quit":
            self.exit()

        elif cmd == "/clear":
            try:
                self.m.query_one("#conversation", Conversation).clear()
            except Exception:
                pass

        elif cmd == "/model":
            if args:
                self._default_model = args
                self._show_toast(f"Model: {args}", "info")
            else:
                self._show_toast(f"Model: {self._default_model}", "info")

        elif cmd == "/git":
            self._load_git_info()
            try:
                h = self.m.query_one("#header", Header)
                self._show_toast(f"git status loaded", "info")
            except Exception:
                pass

        else:
            self._show_toast(f"Unknown: {cmd} (try /help)", "warning")

    # -- Input handling --

    @on(Input.Submitted)
    async def on_input(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        event.input.value = ""

        if text.startswith("/"):
            await self._handle_slash(text)
            return

        # Start agent loop for this task
        self._agent_task = asyncio.create_task(self._run_agent(text))

    # -- Actions (keybindings) --

    def action_spawn(self) -> None:
        try:
            self.m.query_one("#input", InputBar).focus_input()
        except Exception:
            pass

    def action_chat(self) -> None:
        self._show_toast("Chat overlay: not yet implemented", "info")

    def action_dashboard(self) -> None:
        self._show_toast("Dashboard: not yet implemented", "info")

    def action_pause(self) -> None:
        if self._agent_running and self._agent_task:
            self._agent_task.cancel()
            self._agent_running = False
            self._show_toast("Agent cancelled", "warning")
            self._refresh_input_bar()
        else:
            self._show_toast("No agent running", "warning")

    def action_kill(self) -> None:
        if self._agent_task and not self._agent_task.done():
            self._agent_task.cancel()
            self._agent_running = False
            try:
                self.m.query_one("#monitor", AgentMonitor).upsert_agent(
                    self._agent_name,
                    status="error",
                )
            except Exception:
                pass
            self._show_toast("Agent killed", "error")
            self._refresh_input_bar()

    def action_files(self) -> None:
        self._show_toast("File browser: not yet implemented", "info")

    def action_git(self) -> None:
        self._show_toast("Git panel: not yet implemented", "info")

    # -- Helpers --

    def _refresh_input_bar(self) -> None:
        try:
            self.m.query_one("#input", InputBar).agent_running = self._agent_running
        except Exception:
            pass

    def _show_toast(self, message: str, severity: str = "info") -> None:
        """Show a toast notification in the conversation."""
        try:
            conv = self.m.query_one("#conversation", Conversation)
            prefix = {
                "info": "[$text 50%]",
                "warning": "[$warning]",
                "error": "[$error]",
            }.get(severity, "[$text 50%]")
            conv.add_system(f"{prefix}-- {message} --[/]")
        except Exception:
            pass

    def _load_git_info(self) -> None:
        """Load git branch into header."""
        try:
            import subprocess
            r = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, cwd=self.cwd, timeout=2,
            )
            if r.returncode == 0:
                branch = r.stdout.strip()
                if branch:
                    try:
                        self.m.query_one("#header", Header).cwd = f"{self.cwd} ({branch})"
                    except Exception:
                        pass
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run_tui():
    app = AIWorkspaceApp()
    app.run()


if __name__ == "__main__":
    run_tui()
