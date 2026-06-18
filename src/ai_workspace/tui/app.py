"""
AI Workstation — terminal dashboard for the AI Workspace.

Single-screen chat-first TUI with overlays.

Type a task → Enter → agent spawns and begins.
Slash commands: /help, /model, /research, /tasks, /quit
Shortcuts: F1 help, Ctrl+O files, Ctrl+C quit
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.theme import Theme
from textual.widgets import Footer, Input, Label, RichLog, Static

logger = logging.getLogger("aiw.tui")

# ── Theme ──────────────────────────────────────────────────────────

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

SLASH_COMMANDS = {
    "/help": "Show this reference",
    "/model <name>": "Switch default model",
    "/research <query>": "Run deep research",
    "/tasks": "List pending tasks",
    "/clear": "Clear conversation",
    "/cost": "Show cost summary",
    "/sessions": "List recent sessions",
    "/export": "Export session to JSONL",
    "/spawn <type> <task>": "Spawn typed agent",
    "/quit": "Exit",
}

# ── Help Screen ────────────────────────────────────────────────────


class HelpScreen(ModalScreen[None]):
    """Keyboard and slash-command reference."""

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
            cmd_text = "\n".join(
                f"  [bold $text 80%]{cmd:<28}[/] [$text 60%]{desc}[/]"
                for cmd, desc in SLASH_COMMANDS.items()
            )
            yield Label(
                "\n"
                "[bold $primary]AI Workstation[/] — Commands\n\n"
                + cmd_text
                + "\n\n"
                "  [bold $primary]Shortcuts[/]\n"
                "  [bold]Enter[/]    [$text 60%]Send input[/]\n"
                "  [bold]F1[/]       [$text 60%]This help[/]\n"
                "  [bold]Ctrl+C[/]   [$text 60%]Quit[/]\n"
                "\n",
            )

    def action_dismiss(self) -> None:
        self.dismiss()


# ── Main Screen ────────────────────────────────────────────────────


class MainScreen(Screen[None]):
    """Primary screen: header, conversation log, input bar, footer."""

    AUTO_FOCUS = "#task-input"

    BINDINGS = [
        Binding("f1", "help", "Help"),
        Binding("ctrl+c", "quit", "Quit", priority=True),
    ]

    def compose(self) -> ComposeResult:
        yield Static(id="top-bar")
        with VerticalScroll(id="conversation"):
            yield RichLog(id="log", highlight=True, markup=True, wrap=True, max_lines=5000)
        with Vertical(id="input-area"):
            yield Input(
                placeholder="Type a task or /command...",
                id="task-input",
            )
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one("#log", RichLog)
        log.write("[bold #5B8DEE]AI Workstation[/]\n")
        log.write(f"[#7C8DB5]{Path.cwd()}[/]\n\n")
        log.write("[#A0A5B8]Type a task and press [bold]Enter[/] — agent spawns and begins.[/]\n")
        log.write("[#A0A5B8]/help for commands    F1 for reference[/]\n")

    def action_help(self) -> None:
        self.app.push_screen(HelpScreen())

    def write_line(self, text: str) -> None:
        self.query_one("#log", RichLog).write(text)

    @property
    def input_value(self) -> str:
        return self.query_one("#task-input", Input).value

    def clear_input(self) -> None:
        inp = self.query_one("#task-input", Input)
        inp.value = ""
        inp.focus()


# ── App ─────────────────────────────────────────────────────────────


class AIWorkspaceApp(App[None]):
    TITLE = "AI Workstation"
    SUB_TITLE = ""

    CSS = """
    * { scrollbar-size-vertical: 1; }
    Screen { background: $background; }
    #top-bar {
        dock: top;
        height: 1;
        padding: 0 2;
        background: $surface;
        border-bottom: solid $primary 25%;
        color: $primary;
    }
    #conversation {
        height: 1fr;
        padding: 1 2;
        background: $background;
    }
    #conversation RichLog {
        height: 1fr;
        background: $background;
    }
    #input-area {
        dock: bottom;
        height: auto;
        padding: 1 2;
        background: $surface;
        border-top: solid $primary 25%;
    }
    #task-input {
        width: 1fr;
        background: $background;
        border: solid $primary 20%;
        padding: 1;
    }
    #task-input:focus {
        border: solid $primary 50%;
    }
    Footer {
        dock: bottom;
        background: $surface;
        border-top: solid $primary 25%;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.cwd = str(Path.cwd())
        self._default_model = "qwen3:14b"
        self._main: MainScreen | None = None

    def on_mount(self) -> None:
        self.register_theme(THEME)
        self.theme = "workstation"
        self._main = MainScreen()
        self.push_screen(self._main)
        self._load_header()

    @property
    def m(self) -> MainScreen:
        assert self._main is not None
        return self._main

    def _load_header(self) -> None:
        h = str(Path.home())
        cwd = self.cwd
        if cwd.startswith(h):
            cwd = "~" + cwd[len(h):]
        try:
            self.m.query_one("#top-bar", Static).update(
                f"[bold $primary]aiw[/]  [$text 70%]{cwd}[/]  [$text 60%]{self._default_model}[/]  [$text 40%]{datetime.now().strftime('%H:%M')}[/]"
            )
        except Exception:
            pass

    # ── Input handling ──────────────────────────────────────────

    @on(Input.Submitted, "#task-input")
    async def on_input(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        event.input.value = ""

        self.m.write_line(f"\n[bold #5B8DEE]You:[/] {text}")

        if text.startswith("/"):
            await self._handle_slash(text)
        else:
            await self._handle_task(text)

    async def _handle_slash(self, text: str) -> None:
        cmd, _, args = text.partition(" ")

        if cmd == "/help":
            self.push_screen(HelpScreen())

        elif cmd == "/quit":
            self.exit()

        elif cmd == "/clear":
            self.m.query_one("#log", RichLog).clear()
            self.m.write_line("[#7C8DB5]Cleared.[/]")

        elif cmd == "/model":
            if args:
                self._default_model = args
                self.m.write_line(f"[#7C8DB5]Default model: {args}[/]")
            else:
                self.m.write_line(f"[#7C8DB5]Default model: {self._default_model}[/]")

        elif cmd == "/research":
            if args:
                self.m.write_line(f"[#7C8DB5]Researching: {args}...[/]")
                await self._run_research(args)
            else:
                self.m.write_line("[#D4A853]Usage: /research <query>[/]")

        elif cmd == "/tasks":
            await self._show_tasks()

        elif cmd == "/cost":
            await self._show_cost()

        elif cmd == "/sessions":
            await self._show_sessions()

        elif cmd == "/export":
            self.m.write_line("[#7C8DB5]Export: not yet implemented[/]")

        elif cmd == "/spawn":
            parts = args.split(" ", 1)
            atype = parts[0] if parts else "general"
            task = parts[1] if len(parts) > 1 else ""
            if task:
                await self._handle_task(f"[{atype}] {task}")
            else:
                self.m.write_line("[#D4A853]Usage: /spawn <type> <task>[/]")

        else:
            self.m.write_line(f"[#D4A853]Unknown: {cmd}  (try /help)[/]")

    async def _handle_task(self, text: str) -> None:
        """Handle a free-text task — spawn an agent."""
        self.m.write_line(f"[#7C8DB5]Spawning agent for: {text[:60]}...[/]")
        try:
            from ai_workspace.tui.worker import AgentConfig, AgentWorker

            from ai_workspace.core.sessions import SessionStore

            store = SessionStore()
            store.initialize()
            session = store.create_session(
                cwd=self.cwd,
                model=self._default_model,
                label=text[:40],
            )
            store.add_message(session_id=session.id, role="user", content=text)
            store.close()

            config = AgentConfig(
                lane_id="agent-1",
                agent_type="general",
                model=self._default_model,
                session_id=session.id,
                cwd=self.cwd,
            )
            worker = AgentWorker(config)
            # Run in thread via asyncio
            import asyncio

            loop = asyncio.get_event_loop()

            def run_agent():
                asyncio.run(worker.run_agent(text))

            await loop.run_in_executor(None, run_agent)
            self.m.write_line("[#7C8DB5]Agent completed.[/]")

        except ImportError as e:
            self.m.write_line(f"[#E0556A]Agent system unavailable: {e}[/]")
        except Exception as e:
            self.m.write_line(f"[#E0556A]Agent error: {e}[/]")

    async def _run_research(self, query: str) -> None:
        """Run deep research and show results."""
        try:
            from ai_workspace.search import DeepSearchEngine

            engine = DeepSearchEngine(max_depth=2)

            import asyncio

            loop = asyncio.get_event_loop()

            def do_research():
                result = asyncio.run(engine.research(query))
                return result

            result = await loop.run_in_executor(None, do_research)
            self.m.write_line(
                f"[#5FA874]Research complete: {len(result.sub_questions)} sub-questions, "
                f"confidence {result.confidence:.0%}[/]"
            )
            if result.answer:
                self.m.write_line(f"[#A0A5B8]{result.answer[:500]}[/]")
        except ImportError as e:
            self.m.write_line(f"[#E0556A]Research system unavailable: {e}[/]")
        except Exception as e:
            self.m.write_line(f"[#E0556A]Research error: {e}[/]")

    async def _show_tasks(self) -> None:
        """Show pending tasks."""
        try:
            from ai_workspace.knowledge import KnowledgeStore

            store = KnowledgeStore()
            store.initialize()
            tasks = store.get_tasks(status="pending", limit=10)
            store.close()

            if not tasks:
                self.m.write_line("[#7C8DB5]No pending tasks.[/]")
                return

            self.m.write_line("[bold #5B8DEE]Pending Tasks:[/]")
            for t in tasks:
                prio = "🔴" if t.get("priority", 0) > 7 else "🟡" if t.get("priority", 0) > 3 else "🟢"
                self.m.write_line(
                    f"  {prio} [#A0A5B8]{t.get('title', '?')[:60]}[/]"
                )
        except Exception as e:
            self.m.write_line(f"[#E0556A]Cannot fetch tasks: {e}[/]")

    async def _show_cost(self) -> None:
        """Show cost summary."""
        try:
            from ai_workspace.core.cost import CostService

            cost = CostService()
            cost.initialize()
            cache = cost.cache.stats()
            budget = cost.budget.budget_summary()
            self.m.write_line(
                f"[#A0A5B8]Today: ${budget['today_spent']:.4f} / ${budget['today_budget']:.2f}"
                f" ({budget['today_pct']}%)[/]\n"
                f"[#A0A5B8]Cache: {cache['total_entries']} entries, "
                f"{cache['total_hits']} hits, {cache['tokens_saved']:,} tokens saved[/]"
            )
        except Exception as e:
            self.m.write_line(f"[#E0556A]Cost info unavailable: {e}[/]")

    async def _show_sessions(self) -> None:
        """Show recent sessions."""
        try:
            from ai_workspace.core.sessions import SessionStore

            store = SessionStore()
            store.initialize()
            sessions = store.list_sessions(limit=10)
            store.close()

            if not sessions:
                self.m.write_line("[#7C8DB5]No sessions found.[/]")
                return

            self.m.write_line("[bold #5B8DEE]Recent Sessions:[/]")
            for s in sessions:
                label = s.get("label") or s.get("id", "?")[:12]
                cwd = s.get("cwd", "?")[:30]
                self.m.write_line(f"  [#A0A5B8]{label}[/]  [#7C8DB5]{cwd}[/]")
        except Exception as e:
            self.m.write_line(f"[#E0556A]Sessions unavailable: {e}[/]")

    # ── Actions ──────────────────────────────────────────────────

    def action_quit(self) -> None:
        self.exit()


# ── Entry point ────────────────────────────────────────────────────


def run_tui():
    app = AIWorkspaceApp()
    app.run()


if __name__ == "__main__":
    run_tui()
