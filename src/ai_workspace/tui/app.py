"""
AI Workstation TUI — clean agent interface inspired by pi.

Layout (top to bottom):
  1. Header — workspace path
  2. Agent bar — collapsible, shows only when agents are running
  3. Conversation — scrollable messages + agent steps (the main area)
  4. Input — type tasks or /commands with autocomplete
  5. Footer — context-rich: research, tasks, confidence, model

Overlays (F1-F4): Help, Research, Tasks, Telemetry
"""

from __future__ import annotations

import asyncio
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

from ai_workspace.tui.command_palette import CommandPalette

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

# ── Rich-compatible color constants ─────────────────────────────────

C = {
    "primary": "#5B8DEE",
    "dim": "#7C8DB5",
    "text": "#A0A5B8",
    "faint": "#6E7082",
    "success": "#5FA874",
    "warning": "#D4A853",
    "error": "#E0556A",
}


def _b(text: str, color: str = C["primary"]) -> str:
    return f"[bold {color}]{text}[/]"


def _d(text: str) -> str:
    return f"[{C['dim']}]{text}[/]"


def _t(text: str) -> str:
    return f"[{C['text']}]{text}[/]"


# ── Data fetchers ──────────────────────────────────────────────────


def _fetch_telemetry() -> dict:
    try:
        from ai_workspace.knowledge import KnowledgeStore
        s = KnowledgeStore(); s.initialize(); c = s.conn.cursor()
        c.execute("SELECT COUNT(*) FROM research_entries"); rt = c.fetchone()[0]
        c.execute("SELECT ROUND(AVG(confidence)::numeric,2) FROM research_entries WHERE confidence>0")
        ac = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(*) FROM tasks WHERE status='pending'"); tp = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM agent_memory"); am = c.fetchone()[0]
        c.close(); s.close()
        return {"rt": rt, "ac": ac, "tp": tp, "am": am}
    except Exception:
        return {}


# ── Agent status bar ───────────────────────────────────────────────


class AgentBar(Static):
    """Collapsible bar showing running agents. Hidden when empty."""

    agents: reactive[list[dict]] = reactive([])
    count: reactive[int] = reactive(0)

    def render(self) -> str:
        if not self.agents:
            return ""
        active = [a for a in self.agents if a.get("status") == "running"]
        if not active:
            return ""
        lines = []
        for a in active:
            name = a.get("name", "?")
            task = (a.get("task", "") or "")[:60]
            lines.append(
                f" {_b('●', C['warning'])} {_b(name, C['text'])} "
                f" {_d(task)}"
            )
        return "\n".join(lines)

    def upsert(self, name: str, **kw) -> None:
        cur = list(self.agents)
        for a in cur:
            if a.get("name") == name:
                a.update(kw)
                self.agents = cur
                self.count = len([a for a in cur if a.get("status") == "running"])
                return
        entry = {"name": name, "status": "running", "task": ""}
        entry.update(kw)
        self.agents = cur + [entry]
        self.count = len([a for a in self.agents if a.get("status") == "running"])

    def remove(self, name: str) -> None:
        self.agents = [a for a in self.agents if a.get("name") != name]
        self.count = len([a for a in self.agents if a.get("status") == "running"])


# ── Overlay screens ────────────────────────────────────────────────


class HelpScreen(ModalScreen[None]):
    CSS = """
    HelpScreen { align: center middle; background: $background 85%; }
    #help-box { width: 56; height: auto; max-height: 90%; background: $surface; border: solid $primary 40%; padding: 1 2; }
    """
    BINDINGS = [Binding("escape", "dismiss", "Close"), Binding("q", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        cmds = "\n".join(
            f"  [bold {C['primary']}]{c:<28}[/] [{C['text']}]{d}[/]"
            for c, d in [
                ("/research <query>", "Run deep research"),
                ("/tasks", "Browse tasks (F3)"),
                ("/model <name>", "Switch model"),
                ("/cost", "Show cost summary"),
                ("/clear", "Clear conversation"),
                ("/help", "This reference"),
                ("/quit", "Exit"),
            ]
        )
        with Static(id="help-box"):
            yield Label(
                f"\n[bold {C['primary']}]AI Workstation[/]\n\n"
                + cmds
                + f"\n\n[bold {C['primary']}]Keys[/]\n"
                f"  [bold]Enter[/]      [{C['text']}]Send[/]\n"
                f"  [bold]Tab[/]        [{C['text']}]Complete command[/]\n"
                f"  [bold]F1[/]         [{C['text']}]Help[/]\n"
                f"  [bold]F2[/]         [{C['text']}]Research[/]\n"
                f"  [bold]F3[/]         [{C['text']}]Tasks[/]\n"
                f"  [bold]F5[/]         [{C['text']}]Refresh[/]\n"
                f"  [bold]Ctrl+C[/]     [{C['text']}]Quit[/]\n\n"
            )

    def action_dismiss(self) -> None:
        self.dismiss()


class ResearchScreen(ModalScreen[None]):
    """Overlay: browse recent research with confidence scores."""

    CSS = """
    ResearchScreen { align: center middle; background: $background 90%; }
    #research-box { width: 90%; height: 85%; background: $surface; border: solid $primary 40%; padding: 1 2; }
    """
    BINDINGS = [Binding("escape", "dismiss", "Close"), Binding("q", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        with Vertical(id="research-box"):
            yield Static(_b("📜 Research History", C["primary"]), id="rs-title")
            yield Static("Loading...", id="rs-content")

    def on_mount(self) -> None:
        try:
            from ai_workspace.knowledge import KnowledgeStore
            s = KnowledgeStore(); s.initialize()
            rows = s.get_research_history(limit=50)
            s.close()
            if not rows:
                self.query_one("#rs-content", Static).update(_d("No research yet."))
                return
            lines = []
            for r in rows:
                conf = r.get("confidence", 0) or 0
                color = C["success"] if conf > 0.7 else C["warning"] if conf > 0.4 else C["error"]
                q = (r.get("query") or "?")[:80]
                summary = (r.get("summary") or "")[:120]
                lines.append(f"[{color}]{conf:.0%}[/] {_t(q)}")
                if summary:
                    lines.append(f"   {_d(summary)}")
            self.query_one("#rs-content", Static).update("\n".join(lines))
        except Exception as e:
            self.query_one("#rs-content", Static).update(f"[{C['error']}]Error: {e}[/]")

    def action_dismiss(self) -> None:
        self.dismiss()


class TasksScreen(ModalScreen[None]):
    """Overlay: browse tasks with status and schedule."""

    CSS = """
    TasksScreen { align: center middle; background: $background 90%; }
    #tasks-box { width: 90%; height: 85%; background: $surface; border: solid $primary 40%; padding: 1 2; }
    """
    BINDINGS = [Binding("escape", "dismiss", "Close"), Binding("q", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        with Vertical(id="tasks-box"):
            yield Static(_b("📋 Tasks", C["primary"]), id="ts-title")
            yield Static("Loading...", id="ts-content")

    def on_mount(self) -> None:
        try:
            from ai_workspace.knowledge import KnowledgeStore
            s = KnowledgeStore(); s.initialize()
            tasks = s.get_tasks(limit=50)
            s.close()
            if not tasks:
                self.query_one("#ts-content", Static).update(_d("No tasks."))
                return
            lines = []
            for t in tasks:
                st = t.get("status", "?")
                if st in ("done", "completed"):
                    icon = f"[{C['success']}]✓[/]"
                elif st == "in_progress":
                    icon = f"[{C['warning']}]●[/]"
                elif st == "failed":
                    icon = f"[{C['error']}]✗[/]"
                else:
                    icon = f"[{C['dim']}]○[/]"
                title = (t.get("title") or "?")[:70]
                sched = t.get("schedule", "")
                sch = f" {_d(sched)}" if sched else ""
                lines.append(f" {icon} {_t(title)}{sch}")
            self.query_one("#ts-content", Static).update("\n".join(lines))
        except Exception as e:
            self.query_one("#ts-content", Static).update(f"[{C['error']}]Error: {e}[/]")

    def action_dismiss(self) -> None:
        self.dismiss()


class TelemetryScreen(ModalScreen[None]):
    """Overlay: full telemetry snapshot."""

    CSS = """
    TelemetryScreen { align: center middle; background: $background 90%; }
    #telemetry-box { width: 70%; height: auto; background: $surface; border: solid $primary 40%; padding: 1 2; }
    """
    BINDINGS = [Binding("escape", "dismiss", "Close"), Binding("q", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        with Static(id="telemetry-box"):
            yield Static("Loading...", id="tm-content")

    def on_mount(self) -> None:
        try:
            from ai_workspace.knowledge import KnowledgeStore
            s = KnowledgeStore(); s.initialize(); c = s.conn.cursor()
            c.execute("SELECT COUNT(*) FROM research_entries WHERE created_at > NOW() - INTERVAL '24 hours'")
            r24 = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM research_entries"); rt = c.fetchone()[0]
            c.execute("SELECT ROUND(AVG(confidence)::numeric,2) FROM research_entries WHERE confidence>0")
            ac = c.fetchone()[0] or 0
            c.execute("SELECT COUNT(*) FROM tasks"); tt = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM tasks WHERE status='pending'"); tp = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM tasks WHERE status IN ('done','completed')"); td = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM agent_memory"); am = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM knowledge_entries"); ke = c.fetchone()[0]
            c.close(); s.close()
            self.query_one("#tm-content", Static).update(
                f"\n[bold {C['primary']}]Telemetry[/]\n\n"
                f"  {_b('📊 Research')}    {r24} last 24h / {rt} total\n"
                f"  {_b('🎯 Confidence')}  {float(ac):.0%} avg\n"
                f"  {_b('📋 Tasks')}       {tp} pending / {td} done / {tt} total\n"
                f"  {_b('🧠 Memories')}    {am} facts\n"
                f"  {_b('📚 Knowledge')}   {ke} entries\n\n"
            )
        except Exception as e:
            self.query_one("#tm-content", Static).update(f"[{C['error']}]Error: {e}[/]")

    def action_dismiss(self) -> None:
        self.dismiss()


# ── Main screen ────────────────────────────────────────────────────


class MainScreen(Screen[None]):
    AUTO_FOCUS = "#task-input"

    BINDINGS = [
        Binding("f1", "help", "Help"),
        Binding("f2", "research", "Research"),
        Binding("f3", "tasks", "Tasks"),
        Binding("f5", "refresh", "Refresh"),
        Binding("tab", "complete", "", show=False),
        Binding("escape", "dismiss_or_pop", "", show=False),
        Binding("ctrl+c", "quit", "Quit", priority=True),
    ]

    def compose(self) -> ComposeResult:
        # Header
        yield Static(id="header")
        # Agent bar (collapses when empty)
        yield AgentBar(id="agent-bar")
        # Main conversation area
        yield RichLog(id="conversation", highlight=True, markup=True, wrap=True, max_lines=5000)
        # Command palette (appears above input when typing /)
        yield CommandPalette(id="cmd-palette")
        # Input area
        yield Input(
            placeholder="Type a task or /command...  (F1 help  F2 research  F3 tasks)",
            id="task-input",
        )
        # Footer-like status bar (pi-style: context-rich)
        yield Static(id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        self._load_header()
        self._load_status()
        self._write_welcome()
        self.set_interval(30, self._load_status)

    def _load_header(self) -> None:
        h = str(Path.home())
        cwd = str(Path.cwd())
        if cwd.startswith(h):
            cwd = "~" + cwd[len(h):]
        if len(cwd) > 50:
            cwd = "…" + cwd[-49:]
        self.query_one("#header", Static).update(
            f" {_b('aiw')}  {_t(cwd)}"
        )

    def _load_status(self) -> None:
        """Update the pi-style status bar."""
        t = _fetch_telemetry()
        rt = t.get("rt", "?")
        tp = t.get("tp", 0)
        ac = float(t.get("ac", 0))
        self.query_one("#status-bar", Static).update(
            f" {_d(f'research:{rt}')}  "
            f"{_d(f'tasks:{tp}')}  "
            f"{_d(f'conf:{ac:.0%}')}  "
            f"{_d('qwen3:14b')}  "
            f"{_d('/help')}"
        )

    def _write_welcome(self) -> None:
        log = self.query_one("#conversation", RichLog)
        t = _fetch_telemetry()
        rt = t.get("rt", 0)
        tp = t.get("tp", 0)
        log.write(_b("AI Workstation", C["primary"]))
        log.write(f"  {_d(f'{rt} research, {tp} tasks pending')}")
        log.write("")
        log.write(_d("Type a task to spawn an agent. /help for commands."))
        log.write(_d("F2 Research  F3 Tasks  F5 Refresh  Ctrl+C Quit"))
        log.write("")

    # ── Conversation helpers ────────────────────────────────────

    def say(self, text: str) -> None:
        self.query_one("#conversation", RichLog).write(text)

    # ── Slash command palette ────────────────────────────────────

    @on(Input.Changed, "#task-input")
    def _on_input_changed(self, event: Input.Changed) -> None:
        self.query_one("#cmd-palette", CommandPalette).filter(event.value)

    def action_complete(self) -> None:
        """Tab: complete selected command."""
        p = self.query_one("#cmd-palette", CommandPalette)
        cmd = p.selected_command
        if cmd:
            inp = self.query_one("#task-input", Input)
            inp.value = cmd
            inp.cursor_position = len(cmd)
            p.hide()

    def action_dismiss_or_pop(self) -> None:
        """Escape: dismiss palette or pop overlay."""
        p = self.query_one("#cmd-palette", CommandPalette)
        if p.display:
            p.hide()
            return
        app = self.app
        if app and len(app.screen_stack) > 1:
            app.pop_screen()

    # ── Overlay actions ──────────────────────────────────────────

    def action_help(self) -> None:
        self.app.push_screen(HelpScreen())

    def action_research(self) -> None:
        self.app.push_screen(ResearchScreen())

    def action_tasks(self) -> None:
        self.app.push_screen(TasksScreen())

    def action_refresh(self) -> None:
        self._load_status()
        self.say(_d("— Refreshed —"))


# ── App ─────────────────────────────────────────────────────────────


class AIWorkspaceApp(App[None]):
    TITLE = "AI Workstation"

    CSS = """
    * { scrollbar-size-vertical: 1; scrollbar-color: $primary 10%; scrollbar-background: $background; }
    Screen { background: $background; }

    #header {
        dock: top; height: 1; padding: 0 2;
        background: $surface; border-bottom: solid $primary 25%;
    }
    #agent-bar {
        dock: top; height: auto; padding: 0 2;
        background: $panel; border-bottom: solid $warning 15%;
    }
    #conversation {
        height: 1fr;
        background: $background;
        padding: 0 2;
    }
    #cmd-palette {
        dock: bottom;
    }
    #task-input {
        dock: bottom; height: 3; margin: 0 2 1 2;
        background: $surface;
        color: $text;
        border: solid $primary 20%;
        padding: 0 1;
    }
    #task-input:focus { border: solid $primary 50%; }
    #status-bar {
        dock: bottom; height: 1; padding: 0 2;
        background: $surface;
        border-top: solid $primary 15%;
        color: $text 60%;
    }
    Footer { dock: bottom; background: $surface; }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._default_model = "qwen3:14b"
        self._agent_count = 0

    def on_mount(self) -> None:
        self.register_theme(THEME)
        self.theme = "workstation"
        self.push_screen(MainScreen())

    @property
    def m(self) -> MainScreen:
        for s in self.screen_stack:
            if isinstance(s, MainScreen):
                return s
        raise RuntimeError("MainScreen not found")

    # ── Input ─────────────────────────────────────────────────────

    @on(Input.Submitted, "#task-input")
    async def on_input(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        event.input.value = ""

        if text.startswith("/"):
            await self._handle_slash(text)
        else:
            await self._spawn_agent(text)

    async def _handle_slash(self, text: str) -> None:
        cmd, _, args = text.partition(" ")

        if cmd == "/help":
            self.push_screen(HelpScreen())
        elif cmd == "/quit":
            self.exit()
        elif cmd == "/clear":
            self.m.query_one("#conversation", RichLog).clear()
            self.m.say(_d("Cleared"))
        elif cmd == "/model":
            if args:
                self._default_model = args
                self.m.say(f"{_d('Model:')} {args}")
            else:
                self.m.say(f"{_d('Model:')} {self._default_model}")
        elif cmd == "/research":
            if args:
                self.m.say(f"\n{_b('Researching:', C['primary'])} {args}")
                await self._run_research(args)
            else:
                self.push_screen(ResearchScreen())
        elif cmd == "/tasks":
            self.push_screen(TasksScreen())
        elif cmd == "/cost":
            await self._show_cost()
        else:
            self.m.say(f"[{C['warning']}]Unknown: {cmd}  (try /help)[/]")

    # ── Agent spawning ────────────────────────────────────────────

    async def _spawn_agent(self, text: str) -> None:
        self._agent_count += 1
        name = f"agent-{self._agent_count}"
        self.m.say(f"\n{_b('▸', C['primary'])} {_t(text)}")

        bar = self.m.query_one("#agent-bar", AgentBar)
        bar.upsert(name, status="running", task=text)

        try:
            from ai_workspace.tui.worker import AgentConfig, AgentWorker
            from ai_workspace.core.sessions import SessionStore

            store = SessionStore(); store.initialize()
            session = store.create_session(cwd=str(Path.cwd()), model=self._default_model, label=text[:40])
            store.add_message(session_id=session.id, role="user", content=text)
            store.close()

            config = AgentConfig(
                lane_id=name, agent_type="general", model=self._default_model,
                session_id=session.id, cwd=str(Path.cwd()),
            )
            worker = AgentWorker(config)

            async def run_and_stream():
                task = asyncio.create_task(worker.run_agent(text))
                while not task.done() or not worker.queue.empty():
                    try:
                        line = await asyncio.wait_for(worker.queue.get(), timeout=0.1)
                        self.m.say(_d(line))
                    except asyncio.TimeoutError:
                        continue
                await task
                if worker.status.name == "COMPLETED":
                    bar.upsert(name, status="done")
                    self.m.say(f"\n{_b('✓', C['success'])} {_d('Done')}")
                elif worker.status.name == "ERROR":
                    bar.upsert(name, status="error")
                    self.m.say(f"\n[{C['error']}]Error: {worker._error}[/]")
                self.set_timer(5.0, lambda: bar.remove(name))

            asyncio.create_task(run_and_stream())

        except ImportError as e:
            bar.upsert(name, status="error")
            self.m.say(f"[{C['error']}]Agent unavailable: {e}[/]")
        except Exception as e:
            logger.exception("Agent error")
            bar.upsert(name, status="error")
            self.m.say(f"[{C['error']}]Error: {e}[/]")

    # ── Research ──────────────────────────────────────────────────

    async def _run_research(self, query: str) -> None:
        try:
            from ai_workspace.search import DeepSearchEngine
            loop = asyncio.get_event_loop()

            def do():
                import asyncio as aio
                engine = DeepSearchEngine(max_depth=2)
                return aio.run(engine.research(query))

            result = await loop.run_in_executor(None, do)
            self.m.say(
                f"[{C['success']}]Done: {len(result.sub_questions)} sub-questions, "
                f"confidence {result.confidence:.0%}[/]"
            )
            if result.answer:
                self.m.say(_t(result.answer[:500]))
        except ImportError as e:
            self.m.say(f"[{C['error']}]Research unavailable: {e}[/]")
        except Exception as e:
            self.m.say(f"[{C['error']}]Error: {e}[/]")

    # ── Cost ──────────────────────────────────────────────────────

    async def _show_cost(self) -> None:
        try:
            from ai_workspace.core.cost import CostService
            cost = CostService(); cost.initialize()
            budget = cost.budget.budget_summary()
            self.m.say(
                f"[{C['text']}]Today: ${budget['today_spent']:.4f} / "
                f"${budget['today_budget']:.2f} ({budget['today_pct']}%)[/]"
            )
        except Exception as e:
            self.m.say(f"[{C['error']}]Cost unavailable: {e}[/]")


# ── Entry point ────────────────────────────────────────────────────


def run_tui():
    app = AIWorkspaceApp()
    app.run()


if __name__ == "__main__":
    run_tui()
