"""
AI Workstation TUI — clean agent interface.

Layout:
  Header  — workspace path
  AgentBar— collapsible, shows running agents  
  Body    — RichLog conversation (scrollable, markup-aware)
  Input   — task / slash command entry with autocomplete
  StatusBar— context: research, tasks, confidence, model
  
Overlays: F1 Help  F2 Research  F3 Tasks  F5 Refresh
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
)

# ── Color helpers for Rich markup in render() ──────────────────────

C = {
    "primary": "#5B8DEE",
    "dim": "#7C8DB5",
    "text": "#A0A5B8",
    "faint": "#6E7082",
    "success": "#5FA874",
    "warning": "#D4A853",
    "error": "#E0556A",
    "bright": "#E0E2EA",
}


# ── Custom widgets (reactive-driven, render() only, no update()) ───


class HeaderBar(Static):
    """Top bar: branding + workspace path. Uses render(), not update()."""

    path: reactive[str] = reactive("")

    def on_mount(self) -> None:
        self.path = self._short_path()

    def _short_path(self) -> str:
        h = str(Path.home())
        cwd = str(Path.cwd())
        if cwd.startswith(h):
            cwd = "~" + cwd[len(h):]
        if len(cwd) > 55:
            cwd = "…" + cwd[-54:]
        return cwd

    def render(self) -> str:
        return f" [bold {C['primary']}]aiw[/]  [{C['text']}]{self.path}[/]"


class AgentBar(Static):
    """Shows running agents. Collapses to empty string when idle."""

    agents: reactive[list[dict]] = reactive([], layout=True)

    def render(self) -> str:
        active = [a for a in self.agents if a.get("status") == "running"]
        if not active:
            return ""
        lines = []
        for a in active:
            name = a.get("name", "?")
            task = (a.get("task", "") or "")[:70]
            lines.append(
                f" [{C['warning']}]●[/] [{C['bright']}]{name}[/] [{C['text']}]{task}[/]"
            )
        return "\n".join(lines)

    def upsert(self, name: str, **kw) -> None:
        cur = [dict(a) for a in self.agents]
        for a in cur:
            if a.get("name") == name:
                a.update(kw)
                self.agents = cur
                return
        entry = {"name": name, "status": "running", "task": ""}
        entry.update(kw)
        self.agents = cur + [entry]

    def remove(self, name: str) -> None:
        self.agents = [a for a in self.agents if a.get("name") != name]


class StatusBar(Static):
    """Bottom bar: telemetry context + model. Updates every 30s."""

    research: reactive[int] = reactive(0)
    tasks: reactive[int] = reactive(0)
    confidence: reactive[str] = reactive("—")
    model: reactive[str] = reactive("qwen3:14b")

    def render(self) -> str:
        return (
            f" [{C['dim']}]research:{self.research}[/]  "
            f"[{C['dim']}]tasks:{self.tasks}[/]  "
            f"[{C['dim']}]conf:{self.confidence}[/]  "
            f"[{C['dim']}]{self.model}[/]  "
            f"[{C['dim']}]/help[/]"
        )

    def refresh_data(self) -> None:
        try:
            from ai_workspace.knowledge import KnowledgeStore
            s = KnowledgeStore(); s.initialize(); c = s.conn.cursor()
            c.execute("SELECT COUNT(*) FROM research_entries"); self.research = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM tasks WHERE status='pending'"); self.tasks = c.fetchone()[0]
            c.execute("SELECT ROUND(AVG(confidence)::numeric,2) FROM research_entries WHERE confidence>0")
            ac = c.fetchone()[0]
            self.confidence = f"{float(ac or 0):.0%}"
            c.close(); s.close()
        except Exception:
            pass


# ── Overlay screens ────────────────────────────────────────────────


class HelpScreen(ModalScreen[None]):
    CSS = """
    HelpScreen { align: center middle; background: $background 85%; }
    #help-box { width: 54; height: auto; max-height: 90%; background: $surface; border: solid $primary 40%; padding: 1 2; }
    """
    BINDINGS = [Binding("escape", "dismiss", "Close"), Binding("q", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        lines = [
            ("/research <query>", "Run deep research"),
            ("/tasks", "Browse tasks (F3)"),
            ("/model <name>", "Switch LLM model"),
            ("/cost", "Show cost summary"),
            ("/clear", "Clear conversation"),
            ("/help", "This reference"),
            ("/quit", "Exit"),
        ]
        cmd_text = "\n".join(
            f"  [bold {C['primary']}]{c:<26}[/] [{C['text']}]{d}[/]"
            for c, d in lines
        )
        with Static(id="help-box"):
            yield Label(
                f"\n[bold {C['primary']}]AI Workstation[/]\n\n"
                + cmd_text
                + f"\n\n[bold {C['primary']}]Keys[/]\n"
                f"  [bold]Enter[/]  [{C['text']}]Send[/]\n"
                f"  [bold]Tab[/]    [{C['text']}]Complete command[/]\n"
                f"  [bold]F1[/]     [{C['text']}]Help[/]\n"
                f"  [bold]F2[/]     [{C['text']}]Research overlay[/]\n"
                f"  [bold]F3[/]     [{C['text']}]Tasks overlay[/]\n"
                f"  [bold]F5[/]     [{C['text']}]Refresh[/]\n"
                f"  [bold]Ctrl+C[/] [{C['text']}]Quit[/]\n\n"
            )
    def action_dismiss(self) -> None: self.dismiss()


class ResearchScreen(ModalScreen[None]):
    CSS = """
    ResearchScreen { align: center middle; background: $background 90%; }
    #research-box { width: 90%; height: 85%; background: $surface; border: solid $primary 40%; padding: 1 2; }
    """
    BINDINGS = [Binding("escape", "dismiss", "Close"), Binding("q", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        with Vertical(id="research-box"):
            yield Static(f"[bold {C['primary']}]📜 Research History[/]", id="rs-title")
            yield Static("Loading...", id="rs-content")

    def on_mount(self) -> None:
        try:
            from ai_workspace.knowledge import KnowledgeStore
            s = KnowledgeStore(); s.initialize()
            rows = s.get_research_history(limit=50); s.close()
            if not rows:
                self.query_one("#rs-content", Static).update(f"[{C['dim']}]No research yet.[/]")
                return
            lines = []
            for r in rows:
                conf = r.get("confidence", 0) or 0
                color = C["success"] if conf > 0.7 else C["warning"] if conf > 0.4 else C["error"]
                q = (r.get("query") or "?")[:100]
                summary = (r.get("summary") or "")[:140]
                lines.append(f"[{color}]{conf:.0%}[/] [{C['text']}]{q}[/]")
                if summary:
                    lines.append(f"   [{C['dim']}]{summary}[/]")
            self.query_one("#rs-content", Static).update("\n".join(lines))
        except Exception as e:
            self.query_one("#rs-content", Static).update(f"[{C['error']}]Error: {e}[/]")
    def action_dismiss(self) -> None: self.dismiss()


class TasksScreen(ModalScreen[None]):
    CSS = """
    TasksScreen { align: center middle; background: $background 90%; }
    #tasks-box { width: 90%; height: 85%; background: $surface; border: solid $primary 40%; padding: 1 2; }
    """
    BINDINGS = [Binding("escape", "dismiss", "Close"), Binding("q", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        with Vertical(id="tasks-box"):
            yield Static(f"[bold {C['primary']}]📋 Tasks[/]", id="ts-title")
            yield Static("Loading...", id="ts-content")

    def on_mount(self) -> None:
        try:
            from ai_workspace.knowledge import KnowledgeStore
            s = KnowledgeStore(); s.initialize()
            tasks = s.get_tasks(limit=50); s.close()
            if not tasks:
                self.query_one("#ts-content", Static).update(f"[{C['dim']}]No tasks.[/]")
                return
            lines = []
            for t in tasks:
                st = t.get("status", "?")
                icon = (
                    f"[{C['success']}]✓[/]" if st in ("done", "completed") else
                    f"[{C['warning']}]●[/]" if st == "in_progress" else
                    f"[{C['error']}]✗[/]" if st == "failed" else
                    f"[{C['dim']}]○[/]"
                )
                title = (t.get("title") or "?")[:80]
                sched = t.get("schedule", "")
                sch = f" [{C['dim']}]{sched}[/]" if sched else ""
                lines.append(f" {icon} [{C['text']}]{title}[/]{sch}")
            self.query_one("#ts-content", Static).update("\n".join(lines))
        except Exception as e:
            self.query_one("#ts-content", Static).update(f"[{C['error']}]Error: {e}[/]")
    def action_dismiss(self) -> None: self.dismiss()


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
        yield HeaderBar(id="header")
        yield AgentBar(id="agent-bar")
        yield RichLog(id="conversation", highlight=True, markup=True, wrap=True, max_lines=5000)
        yield CommandPalette(id="cmd-palette")
        yield Input(placeholder="Type a task or /command...", id="task-input")
        yield StatusBar(id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        self._welcome()
        self.query_one("#status-bar", StatusBar).refresh_data()
        self.set_interval(30, lambda: self.query_one("#status-bar", StatusBar).refresh_data())

    def _welcome(self) -> None:
        log = self.query_one("#conversation", RichLog)
        log.write(f"[bold {C['primary']}]AI Workstation[/]")
        log.write(f"[{C['dim']}]Type a task to spawn an agent. /help for commands.[/]")
        log.write(f"[{C['dim']}]F1 Help  F2 Research  F3 Tasks  F5 Refresh[/]")
        log.write("")

    # ── Slash palette ──────────────────────────────────────────

    @on(Input.Changed, "#task-input")
    def _on_input_changed(self, event: Input.Changed) -> None:
        self.query_one("#cmd-palette", CommandPalette).filter(event.value)

    def action_complete(self) -> None:
        p = self.query_one("#cmd-palette", CommandPalette)
        cmd = p.selected_command
        if cmd:
            inp = self.query_one("#task-input", Input)
            inp.value = cmd
            inp.cursor_position = len(cmd)
            p.hide()

    def action_dismiss_or_pop(self) -> None:
        p = self.query_one("#cmd-palette", CommandPalette)
        if p.display:
            p.hide()
            return
        app = self.app
        if app and len(app.screen_stack) > 1:
            app.pop_screen()

    # ── Actions ────────────────────────────────────────────────

    def action_help(self) -> None: self.app.push_screen(HelpScreen())
    def action_research(self) -> None: self.app.push_screen(ResearchScreen())
    def action_tasks(self) -> None: self.app.push_screen(TasksScreen())

    def action_refresh(self) -> None:
        self.query_one("#status-bar", StatusBar).refresh_data()
        self.query_one("#conversation", RichLog).write(f"[{C['dim']}]— Refreshed —[/]")

    def say(self, text: str) -> None:
        self.query_one("#conversation", RichLog).write(text)


# ── App ─────────────────────────────────────────────────────────────


class AIWorkspaceApp(App[None]):
    TITLE = "AI Workstation"

    CSS = """
    * { scrollbar-size-vertical: 1; }
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
    #cmd-palette { dock: bottom; }
    #task-input {
        dock: bottom; height: 3; margin: 0 2 1 2;
        background: $surface; color: $text;
        border: solid $primary 20%; padding: 0 1;
    }
    #task-input:focus { border: solid $primary 50%; }
    #status-bar {
        dock: bottom; height: 1; padding: 0 2;
        background: $surface; border-top: solid $primary 15%;
    }
    Footer { dock: bottom; background: $surface; }
    """

    BINDINGS = [Binding("ctrl+c", "quit", "Quit", priority=True)]

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

    # ── Input ─────────────────────────────────────────────────

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

        if cmd == "/help":       self.push_screen(HelpScreen())
        elif cmd == "/quit":     self.exit()
        elif cmd == "/clear":    self.m.query_one("#conversation", RichLog).clear(); self.m.say(f"[{C['dim']}]Cleared[/]")
        elif cmd == "/model":    self.m.say(f"[{C['dim']}]Model:[/] {args or self._default_model}")
        elif cmd == "/research": self.push_screen(ResearchScreen()) if not args else await self._run_research(args)
        elif cmd == "/tasks":    self.push_screen(TasksScreen())
        elif cmd == "/cost":     await self._show_cost()
        else:                   self.m.say(f"[{C['warning']}]Unknown: {cmd}[/]")

    # ── Agent spawn + live stream ─────────────────────────────

    async def _spawn_agent(self, text: str) -> None:
        self._agent_count += 1
        name = f"agent-{self._agent_count}"
        self.m.say(f"\n[{C['primary']}]▸[/] [{C['text']}]{text}[/]")

        bar = self.m.query_one("#agent-bar", AgentBar)
        bar.upsert(name, status="running", task=text)

        try:
            from ai_workspace.tui.worker import AgentConfig, AgentWorker
            from ai_workspace.core.sessions import SessionStore

            store = SessionStore(); store.initialize()
            session = store.create_session(cwd=str(Path.cwd()), model=self._default_model, label=text[:40])
            store.add_message(session_id=session.id, role="user", content=text)
            store.close()

            worker = AgentWorker(AgentConfig(
                lane_id=name, agent_type="general", model=self._default_model,
                session_id=session.id, cwd=str(Path.cwd()),
            ))

            async def run():
                t = asyncio.create_task(worker.run_agent(text))
                while not t.done() or not worker.queue.empty():
                    try:
                        line = await asyncio.wait_for(worker.queue.get(), timeout=0.1)
                        self.m.say(f"[{C['dim']}]{line}[/]")
                    except asyncio.TimeoutError:
                        continue
                await t
                ok = worker.status.name == "COMPLETED"
                bar.upsert(name, status="done" if ok else "error")
                self.m.say(f"\n[{C['success']}]✓[/] [{C['dim']}]Done[/]" if ok else f"\n[{C['error']}]Error: {worker._error}[/]")
                self.set_timer(5.0, lambda: bar.remove(name))

            asyncio.create_task(run())

        except Exception as e:
            logger.exception("spawn")
            bar.upsert(name, status="error")
            self.m.say(f"[{C['error']}]{e}[/]")

    # ── Research / Cost ───────────────────────────────────────

    async def _run_research(self, query: str) -> None:
        self.m.say(f"\n[{C['primary']}]Researching:[/] {query}")
        try:
            from ai_workspace.search import DeepSearchEngine
            loop = asyncio.get_event_loop()
            def do():
                import asyncio as aio
                return aio.run(DeepSearchEngine(max_depth=2).research(query))
            r = await loop.run_in_executor(None, do)
            self.m.say(f"[{C['success']}]Done: {len(r.sub_questions)} sub-questions, {r.confidence:.0%}[/]")
            if r.answer:
                self.m.say(f"[{C['text']}]{r.answer[:500]}[/]")
        except Exception as e:
            self.m.say(f"[{C['error']}]{e}[/]")

    async def _show_cost(self) -> None:
        try:
            from ai_workspace.core.cost import CostService
            c = CostService(); c.initialize()
            b = c.budget.budget_summary()
            self.m.say(f"[{C['text']}]${b['today_spent']:.4f} / ${b['today_budget']:.2f} ({b['today_pct']}%)[/]")
        except Exception as e:
            self.m.say(f"[{C['error']}]{e}[/]")


# ── Entry ──────────────────────────────────────────────────────────


def run_tui():
    AIWorkspaceApp().run()
