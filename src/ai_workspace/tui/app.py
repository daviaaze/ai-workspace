"""
AI Workstation TUI — polished agent interface, pi-inspired.

Layout (top→bottom):
  Header  — shortcuts: /help · /research · /tasks · /model · F2 F3
  Conversation — structured messages: user, agent, tool-call blocks, errors
  Input   — task entry with slash-command autocomplete
  Footer  — context-rich: session, tokens, cost, model (pi-style)

Overlays: F1 Help · F2 Research · F3 Tasks · F5 Refresh
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
from textual.containers import Vertical
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

# ── Color constants (Rich markup) ──────────────────────────────────

P = "#5B8DEE"  # primary
D = "#7C8DB5"  # dim
T = "#A0A5B8"  # text
F = "#6E7082"  # faint
S = "#5FA874"  # success
W = "#D4A853"  # warning
E = "#E0556A"  # error


# ── Custom widgets ─────────────────────────────────────────────────


class HeaderBar(Static):
    """Top bar: workspace path + discoverable shortcuts."""

    path: reactive[str] = reactive("")

    def on_mount(self) -> None:
        self.path = self._short_path()

    def _short_path(self) -> str:
        h = str(Path.home())
        cwd = str(Path.cwd())
        if cwd.startswith(h):
            cwd = "~" + cwd[len(h):]
        if len(cwd) > 30:
            cwd = "…" + cwd[-29:]
        return cwd

    def render(self) -> str:
        return (
            f" [bold {P}]aiw[/]  [{T}]{self.path}[/]   "
            f"[{F}]/help[/] [{D}]·[/] [{F}]/research[/] [{D}]·[/] "
            f"[{F}]/tasks[/] [{D}]·[/] [{F}]/model[/] [{D}]·[/] "
            f"[{F}]/cost[/] [{D}]·[/] [{F}]/quit[/]   "
            f"[{D}]F2[/] [{F}]Research[/] [{D}]F3[/] [{F}]Tasks[/]"
        )


class AgentBar(Static):
    """Running agents. Collapses when idle. layout=True for height changes."""

    agents: reactive[list[dict]] = reactive([], layout=True)

    def render(self) -> str:
        active = [a for a in self.agents if a.get("status") == "running"]
        if not active:
            return ""
        lines = []
        for a in active:
            name = a.get("name", "?")
            task = (a.get("task", "") or "")[:70]
            elapsed = int(time.time() - a.get("started", time.time()))
            m, s = divmod(elapsed, 60)
            timer = f"{m}:{s:02d}" if elapsed > 0 else ""
            lines.append(
                f" [{W}]●[/] [{T}]{name}[/] [{D}]{timer}[/] [{F}]{task}[/]"
            )
        return "\n".join(lines)

    def upsert(self, name: str, **kw) -> None:
        cur = [dict(a) for a in self.agents]
        for a in cur:
            if a.get("name") == name:
                a.update(kw)
                self.agents = cur
                return
        entry = {"name": name, "status": "running", "task": "", "started": time.time()}
        entry.update(kw)
        self.agents = cur + [entry]

    def remove(self, name: str) -> None:
        self.agents = [a for a in self.agents if a.get("name") != name]


class StatusBar(Static):
    """Pi-style footer: session, tokens, cost, model. Updates every 10s."""

    tokens_in: reactive[int] = reactive(0)
    tokens_out: reactive[int] = reactive(0)
    cost: reactive[str] = reactive("--")
    model: reactive[str] = reactive("qwen3:14b")
    session: reactive[str] = reactive("")

    def render(self) -> str:
        h = str(Path.home())
        cwd = str(Path.cwd()).replace(h, "~")[:25]
        parts = [f"[{D}]{cwd}[/]"]
        if self.session:
            parts.append(f"[{D}]{self.session[:12]}[/]")
        if self.tokens_in or self.tokens_out:
            parts.append(f"[{D}]↑{self.tokens_in//1000}K ↓{self.tokens_out//1000}K[/]")
        if self.cost and self.cost != "--":
            parts.append(f"[{D}]{self.cost}[/]")
        parts.append(f"[{D}]{self.model}[/]")
        parts.append(f"[{D}]F1 help[/]")
        return " · ".join(parts)

    def update_session(self, sid: str) -> None:
        self.session = sid[:12] if sid else ""

    def update_tokens(self, inp: int, out: int) -> None:
        self.tokens_in = inp
        self.tokens_out = out

    def update_cost(self, c: str) -> None:
        self.cost = c


# ── Message formatting helpers ─────────────────────────────────────


def _user_msg(text: str) -> str:
    return f"\n[{P}]▸[/] [{T}]{text}[/]"


def _agent_msg(name: str, text: str) -> str:
    return f"\n[{P}]{name}[/] [{T}]{text}[/]"


def _tool_block(name: str, step: int, tool: str, args: str) -> str:
    return (
        f"\n[{P}]{name}[/] [{D}]· step {step}[/]\n"
        f"[{F}]┌─ {tool}[/]\n"
        f"[{F}]│ {args[:90]}[/]\n"
        f"[{F}]└─ ...[/]"
    )


def _tool_result(text: str) -> str:
    lines = text.strip().split("\n")[:6]
    result = "\n".join(f"[{F}]│ {line[:90]}[/]" for line in lines)
    return f"[{D}]┌─ result[/]\n{result}\n[{D}]└─[/]"


def _error_msg(text: str) -> str:
    return f"[{E}]✗ {text}[/]"


def _done_msg(name: str, steps: int, tokens: int) -> str:
    return f"[{S}]✓[/] [{D}]{name}[/] [{F}]done · {steps} steps · {tokens//1000}K tokens[/]"


def _system_msg(text: str) -> str:
    return f"[{D}]{text}[/]"


# ── Overlays ───────────────────────────────────────────────────────


class HelpScreen(ModalScreen[None]):
    CSS = """
    HelpScreen { align: center middle; background: $background 85%; }
    #help-box { width: 54; height: auto; max-height: 90%; background: $surface;
                border: solid $primary 40%; padding: 1 2; }
    """
    BINDINGS = [Binding("escape", "dismiss", "Close"), Binding("q", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        cmds = [
            ("/research <query>", "Deep research"),
            ("/tasks", "Browse tasks (F3)"),
            ("/model <name>", "Switch model"),
            ("/cost", "Cost summary"),
            ("/clear", "Clear conversation"),
            ("/help", "This help"),
            ("/quit", "Exit"),
        ]
        with Static(id="help-box"):
            yield Label(
                f"\n[bold {P}]AI Workstation[/]\n\n"
                + "\n".join(f"  [bold {P}]{c:<26}[/] [{T}]{d}[/]" for c, d in cmds)
                + f"\n\n[bold {P}]Keys[/]\n"
                f"  [bold]Enter[/]  [{T}]Send[/]   [bold]Tab[/] [{T}]Complete[/]\n"
                f"  [bold]F1[/]     [{T}]Help[/]   [bold]F2[/] [{T}]Research[/]\n"
                f"  [bold]F3[/]     [{T}]Tasks[/]  [bold]F5[/] [{T}]Refresh[/]\n"
                f"  [bold]Ctrl+C[/] [{T}]Quit[/]\n\n"
            )
    def action_dismiss(self) -> None: self.dismiss()


class _DataScreen(ModalScreen[None]):
    """Base for data overlays (research, tasks)."""
    BINDINGS = [Binding("escape", "dismiss", "Close"), Binding("q", "dismiss", "Close")]
    def action_dismiss(self) -> None: self.dismiss()


class ResearchScreen(_DataScreen):
    CSS = """
    ResearchScreen { align: center middle; background: $background 90%; }
    #box { width: 90%; height: 85%; background: $surface; border: solid $primary 40%; padding: 1 2; }
    """
    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Static(f"[bold {P}]📜 Research History[/]", id="title")
            yield Static("Loading...", id="content")
    def on_mount(self) -> None:
        try:
            from ai_workspace.knowledge import KnowledgeStore
            s = KnowledgeStore(); s.initialize()
            rows = s.get_research_history(limit=50); s.close()
            if not rows:
                self.query_one("#content", Static).update(f"[{D}]No research yet.[/]")
                return
            lines = []
            for r in rows:
                c = r.get("confidence", 0) or 0
                color = S if c > 0.7 else W if c > 0.4 else E
                q = (r.get("query") or "?")[:100]
                summary = (r.get("summary") or "")[:150]
                lines.append(f"[{color}]{c:.0%}[/] [{T}]{q}[/]")
                if summary:
                    lines.append(f"   [{D}]{summary}[/]")
            self.query_one("#content", Static).update("\n".join(lines))
        except Exception as e:
            self.query_one("#content", Static).update(f"[{E}]Error: {e}[/]")


class TasksScreen(_DataScreen):
    CSS = """
    TasksScreen { align: center middle; background: $background 90%; }
    #box { width: 90%; height: 85%; background: $surface; border: solid $primary 40%; padding: 1 2; }
    """
    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Static(f"[bold {P}]📋 Tasks[/]", id="title")
            yield Static("Loading...", id="content")
    def on_mount(self) -> None:
        try:
            from ai_workspace.knowledge import KnowledgeStore
            s = KnowledgeStore(); s.initialize()
            tasks = s.get_tasks(limit=50); s.close()
            if not tasks:
                self.query_one("#content", Static).update(f"[{D}]No tasks.[/]")
                return
            lines = []
            for t in tasks:
                st = t.get("status", "?")
                icon = (f"[{S}]✓[/]" if st in ("done","completed") else
                        f"[{W}]●[/]" if st == "in_progress" else
                        f"[{E}]✗[/]" if st == "failed" else f"[{D}]○[/]")
                title = (t.get("title") or "?")[:90]
                sched = t.get("schedule", "")
                sch = f" [{D}]{sched}[/]" if sched else ""
                lines.append(f" {icon} [{T}]{title}[/]{sch}")
            self.query_one("#content", Static).update("\n".join(lines))
        except Exception as e:
            self.query_one("#content", Static).update(f"[{E}]Error: {e}[/]")


# ── Main screen ────────────────────────────────────────────────────


class MainScreen(Screen[None]):
    AUTO_FOCUS = "#task-input"

    BINDINGS = [
        Binding("f1", "help", "Help"),
        Binding("f2", "research", "Research"),
        Binding("f3", "tasks", "Tasks"),
        Binding("f5", "refresh", "Refresh"),
        Binding("tab", "complete", "", show=False),
        Binding("escape", "dismiss", "", show=False),
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
        self.set_interval(15, self._tick_status)

    def _welcome(self) -> None:
        log = self.query_one("#conversation", RichLog)
        log.write(f"[bold {P}]AI Workstation[/]")
        log.write(f"[{D}]Type a task to spawn an agent. /help for commands.[/]")
        try:
            from ai_workspace.knowledge import KnowledgeStore
            s = KnowledgeStore(); s.initialize(); c = s.conn.cursor()
            c.execute("SELECT COUNT(*) FROM research_entries"); rt = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM tasks WHERE status='pending'"); tp = c.fetchone()[0]
            c.close(); s.close()
            log.write(f"[{D}]{rt} research entries · {tp} pending tasks[/]")
        except Exception:
            pass
        log.write("")

    def _tick_status(self) -> None:
        try:
            from ai_workspace.knowledge import KnowledgeStore
            s = KnowledgeStore(); s.initialize(); c = s.conn.cursor()
            c.execute("SELECT COUNT(*) FROM tasks WHERE status='pending'"); tp = c.fetchone()[0]
            c.close(); s.close()
            # Update just tasks count for now
        except Exception:
            pass

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

    def action_dismiss(self) -> None:
        p = self.query_one("#cmd-palette", CommandPalette)
        if p.display:
            p.hide()
            return
        app = self.app
        if app and len(app.screen_stack) > 1:
            app.pop_screen()

    # ── Actions ────────────────────────────────────────────────

    def action_help(self) -> None:      self.app.push_screen(HelpScreen())
    def action_research(self) -> None:  self.app.push_screen(ResearchScreen())
    def action_tasks(self) -> None:     self.app.push_screen(TasksScreen())

    def action_refresh(self) -> None:
        self._tick_status()
        self.emit(f"[{D}]— Refreshed —[/]")

    def emit(self, text: str) -> None:
        """Write a line to the conversation log."""
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

        if cmd == "/help":
            self.push_screen(HelpScreen())
        elif cmd == "/quit":
            self.exit()
        elif cmd == "/clear":
            self.m.query_one("#conversation", RichLog).clear()
            self.m.emit(_system_msg("Cleared"))
        elif cmd == "/model":
            if args:
                self._default_model = args
            self.m.query_one("#status-bar", StatusBar).model = self._default_model
            self.m.emit(_system_msg(f"Model: {self._default_model}"))
        elif cmd == "/research":
            if args:
                self.m.emit(_system_msg(f"Researching: {args}"))
                await self._run_research(args)
            else:
                self.push_screen(ResearchScreen())
        elif cmd == "/tasks":
            self.push_screen(TasksScreen())
        elif cmd == "/cost":
            await self._show_cost()
        else:
            self.m.emit(f"[{W}]Unknown: {cmd} · try /help[/]")

    # ── Agent spawn + live stream ─────────────────────────────

    async def _spawn_agent(self, text: str) -> None:
        self._agent_count += 1
        name = f"agent-{self._agent_count}"
        self.m.emit(_user_msg(text))

        bar = self.m.query_one("#agent-bar", AgentBar)
        bar.upsert(name, status="running", task=text)

        try:
            from ai_workspace.tui.worker import AgentConfig, AgentWorker
            from ai_workspace.core.sessions import SessionStore

            store = SessionStore(); store.initialize()
            session = store.create_session(cwd=str(Path.cwd()), model=self._default_model, label=text[:40])
            store.add_message(session_id=session.id, role="user", content=text)
            store.close()

            self.m.query_one("#status-bar", StatusBar).update_session(session.id)

            worker = AgentWorker(AgentConfig(
                lane_id=name, agent_type="general", model=self._default_model,
                session_id=session.id, cwd=str(Path.cwd()),
            ))

            step_count = 0
            token_count = 0

            async def run():
                nonlocal step_count, token_count
                t = asyncio.create_task(worker.run_agent(text))
                while not t.done() or not worker.queue.empty():
                    try:
                        line = await asyncio.wait_for(worker.queue.get(), timeout=0.1)
                        stripped = line.strip()
                        if stripped.startswith("Step"):
                            step_count += 1
                            self.m.emit(f"\n[{D}]── Step {step_count} ──[/]")
                        elif stripped.startswith("Thought:") or stripped.startswith("🤔"):
                            self.m.emit(f"[{D}]{stripped}[/]")
                        elif stripped.startswith("Action:") or stripped.startswith("🔧"):
                            self.m.emit(f"[{W}]{stripped}[/]")
                        elif stripped.startswith("Observation:") or stripped.startswith("👁"):
                            self.m.emit(f"[{F}]{stripped[:300]}[/]")
                        else:
                            self.m.emit(f"[{D}]{stripped}[/]")
                        token_count += len(stripped.split())
                    except asyncio.TimeoutError:
                        continue
                await t
                ok = worker.status.name == "COMPLETED"
                bar.upsert(name, status="done" if ok else "error")
                if ok:
                    self.m.emit(_done_msg(name, step_count, token_count))
                else:
                    self.m.emit(_error_msg(str(worker._error or "Unknown error")))
                self.set_timer(5.0, lambda: bar.remove(name))

                # Update footer tokens
                sb = self.m.query_one("#status-bar", StatusBar)
                sb.update_tokens(token_count * 2, token_count * 3)

            asyncio.create_task(run())

        except Exception as e:
            logger.exception("spawn")
            bar.upsert(name, status="error")
            self.m.emit(_error_msg(str(e)))

    # ── Research / Cost ───────────────────────────────────────

    async def _run_research(self, query: str) -> None:
        try:
            from ai_workspace.search import DeepSearchEngine
            loop = asyncio.get_event_loop()
            def do():
                import asyncio as aio
                return aio.run(DeepSearchEngine(max_depth=2).research(query))
            r = await loop.run_in_executor(None, do)
            self.m.emit(
                f"\n[{S}]Research complete[/] [{D}]· "
                f"{len(r.sub_questions)} sub-questions · {r.confidence:.0%} confidence[/]"
            )
            if r.answer:
                self.m.emit(f"[{T}]{r.answer[:500]}[/]")
        except Exception as e:
            self.m.emit(_error_msg(str(e)))

    async def _show_cost(self) -> None:
        try:
            from ai_workspace.core.cost import CostService
            c = CostService(); c.initialize()
            b = c.budget.budget_summary()
            self.m.emit(
                f"\n[{S}]Cost[/] [{D}]· today: ${b['today_spent']:.4f} / "
                f"${b['today_budget']:.2f} ({b['today_pct']}%)[/]"
            )
            self.m.query_one("#status-bar", StatusBar).update_cost(
                f"${b['today_spent']:.4f}"
            )
        except Exception as e:
            self.m.emit(_error_msg(str(e)))


# ── Entry ──────────────────────────────────────────────────────────


def run_tui():
    AIWorkspaceApp().run()
