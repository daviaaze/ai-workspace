"""
AI Workstation TUI — agent dashboard with live telemetry and streaming.

Layout:
  Top bar     — workspace path, model, clock
  Metrics     — research/tasks/memories/confidence at a glance
  Agent status— shows running agents with live progress (wired to AgentWorker)
  Body        — scrollable sections: Research, Tasks
  Input bar   — slash commands + free-text agent spawning
  Footer      — key bindings

Overlays: Help (F1)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.theme import Theme
from textual.widgets import Footer, Input, Label, Static

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

# ── Color constants (for render() strings — Rich markup, not Textual CSS) ──

CLR = {
    "primary": "#5B8DEE",
    "secondary": "#7C8DB5",
    "success": "#5FA874",
    "warning": "#D4A853",
    "error": "#E0556A",
    "dim": "#7C8DB5",
    "text": "#A0A5B8",
    "bright": "#E0E2EA",
    "faint": "#6E7082",
}


def _b(text: str, color: str = CLR["primary"]) -> str:
    return f"[bold {color}]{text}[/]"


def _d(text: str) -> str:
    return f"[{CLR['dim']}]{text}[/]"


def _t(text: str) -> str:
    return f"[{CLR['text']}]{text}[/]"


# ── Data fetchers ──────────────────────────────────────────────────


def _fetch_telemetry() -> dict:
    try:
        from ai_workspace.knowledge import KnowledgeStore
        s = KnowledgeStore(); s.initialize(); c = s.conn.cursor()
        c.execute("SELECT COUNT(*) FROM research_entries WHERE created_at > NOW() - INTERVAL '24 hours'")
        r24 = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM research_entries"); rt = c.fetchone()[0]
        c.execute("SELECT ROUND(AVG(confidence)::numeric,2) FROM research_entries WHERE confidence > 0")
        ac = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(*) FROM tasks WHERE status='pending'"); tp = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM tasks"); tt = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM tasks WHERE status IN ('done','completed')"); td = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM agent_memory"); am = c.fetchone()[0]
        c.close(); s.close()
        return {"r24": r24, "rt": rt, "ac": ac, "tp": tp, "tt": tt, "td": td, "am": am}
    except Exception:
        return {}


def _fetch_research(limit: int = 10) -> list[dict]:
    try:
        from ai_workspace.knowledge import KnowledgeStore
        s = KnowledgeStore(); s.initialize()
        results = s.get_research_history(limit=limit)
        s.close(); return results
    except Exception:
        return []


def _fetch_tasks(limit: int = 20) -> list[dict]:
    try:
        from ai_workspace.knowledge import KnowledgeStore
        s = KnowledgeStore(); s.initialize()
        tasks = s.get_tasks(limit=limit)
        s.close(); return tasks
    except Exception:
        return []


# ── Agent status widget ────────────────────────────────────────────


class AgentStatusBar(Static):
    """Shows currently running agents with live status. Collapses when empty."""

    agents: reactive[list[dict]] = reactive([])

    def render(self) -> str:
        if not self.agents:
            return ""
        lines = [f"\n{_b('🤖 AGENTS', CLR['primary'])}"]
        for ag in self.agents:
            name = ag.get("name", "?")
            status = ag.get("status", "idle")
            task = (ag.get("task", "") or "")[:60]
            task_str = f" {_t(task)}" if task else ""

            if status == "running":
                icon = f"[{CLR['warning']}]●[/]"
                stat = f"[{CLR['warning']}]running[/]"
            elif status == "done":
                icon = f"[{CLR['success']}]✓[/]"
                stat = f"[{CLR['success']}]done[/]"
            elif status == "error":
                icon = f"[{CLR['error']}]✗[/]"
                stat = f"[{CLR['error']}]error[/]"
            else:
                icon = f"[{CLR['dim']}]○[/]"
                stat = _d(status)

            lines.append(f"  {icon} {_b(name, CLR['bright'])} {stat}{task_str}")
        return "\n".join(lines)

    def upsert(self, name: str, **kwargs) -> None:
        current = list(self.agents)
        for ag in current:
            if ag.get("name") == name:
                ag.update(kwargs)
                self.agents = current
                return
        entry = {"name": name, "status": "idle", "task": ""}
        entry.update(kwargs)
        self.agents = current + [entry]

    def remove(self, name: str) -> None:
        self.agents = [ag for ag in self.agents if ag.get("name") != name]


# ── Help screen ────────────────────────────────────────────────────


class HelpScreen(ModalScreen[None]):
    CSS = """
    HelpScreen { align: center middle; background: $background 85%; }
    #help-box {
        width: 58; height: auto; max-height: 90%;
        background: $surface; border: solid $primary 40%; padding: 1 2;
    }
    """
    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
    ]

    def compose(self) -> ComposeResult:
        cmds = "\n".join(
            f"  [bold {CLR['primary']}]{cmd:<32}[/] [{CLR['text']}]{desc}[/]"
            for cmd, desc in [
                ("/research <query>", "Run deep research"),
                ("/tasks", "List all tasks"),
                ("/model <name>", "Switch LLM model"),
                ("/cost", "Show cost summary"),
                ("/clear", "Clear agent output"),
                ("/help", "This reference"),
                ("/quit", "Exit"),
            ]
        )
        with Static(id="help-box"):
            yield Label(
                f"\n[bold {CLR['primary']}]AI Workstation[/] — Commands\n\n"
                + cmds
                + f"\n\n  [bold {CLR['primary']}]Keys[/]\n"
                f"  [bold]Enter[/]     [{CLR['text']}]Send input[/]\n"
                f"  [bold]F1[/]        [{CLR['text']}]This help[/]\n"
                f"  [bold]F5[/]        [{CLR['text']}]Refresh data[/]\n"
                f"  [bold]Ctrl+C[/]    [{CLR['text']}]Quit[/]\n\n"
            )

    def action_dismiss(self) -> None:
        self.dismiss()


# ── Main screen ────────────────────────────────────────────────────


class MainScreen(Screen[None]):
    AUTO_FOCUS = "#task-input"

    BINDINGS = [
        Binding("f1", "help", "Help"),
        Binding("f5", "refresh", "Refresh"),
        Binding("tab", "complete", "Complete", show=False),
        Binding("up", "palette_up", "", show=False),
        Binding("down", "palette_down", "", show=False),
        Binding("escape", "dismiss_palette", "", show=False),
        Binding("ctrl+c", "quit", "Quit", priority=True),
    ]

    def compose(self) -> ComposeResult:
        yield Static(id="top-bar")
        # Metrics
        yield Static(id="metrics-line1")
        yield Static(id="metrics-line2")
        # Agent status bar
        yield AgentStatusBar(id="agents")
        # Scrollable body
        with VerticalScroll(id="body"):
            yield Static(id="research-header")
            yield Static(id="research-section")
            yield Static(id="tasks-header")
            yield Static(id="tasks-section")
            yield Static(id="output")
        # Command palette (appears above input when typing /)
        yield CommandPalette(id="cmd-palette")
        # Input
        with Vertical(id="input-area"):
            yield Input(
                placeholder="Type a task or /command...  (F1 help  F5 refresh  Ctrl+C quit)",
                id="task-input",
            )
        # Info bar
        yield Static(id="info-bar")
        yield Footer()

    def on_mount(self) -> None:
        self._load_bars()
        self._refresh_all()
        # Pre-load command palette registry so first / is instant
        self.query_one("#cmd-palette", CommandPalette)

    @on(Input.Changed, "#task-input")
    def _on_input_changed(self, event: Input.Changed) -> None:
        """Filter command palette as user types."""
        palette = self.query_one("#cmd-palette", CommandPalette)
        palette.filter(event.value)

    def _complete_command(self) -> None:
        """Complete the current command from palette into the input."""
        palette = self.query_one("#cmd-palette", CommandPalette)
        cmd = palette.selected_command
        if cmd:
            inp = self.query_one("#task-input", Input)
            inp.value = cmd
            inp.cursor_position = len(cmd)
            palette.hide()

    def _dismiss_palette(self) -> None:
        """Hide the command palette."""
        self.query_one("#cmd-palette", CommandPalette).hide()

    def _load_bars(self) -> None:
        h = str(Path.home())
        cwd = str(Path.cwd())
        if cwd.startswith(h):
            cwd = "~" + cwd[len(h):]
        if len(cwd) > 40:
            cwd = "…" + cwd[-39:]
        now = datetime.now().strftime("%H:%M")
        self.query_one("#top-bar", Static).update(
            f" {_b('aiw')}  [{CLR['text']}]{cwd}[/]  [{CLR['dim']}]qwen3:14b[/]  [{CLR['faint']}]{now}[/]"
        )
        # Info bar below input
        self.query_one("#info-bar", Static).update(
            f" [{CLR['dim']}]model:[/] qwen3:14b  "
            f"[{CLR['dim']}]cost:[/] --  "
            f"[{CLR['dim']}]agents:[/] 0  "
            f"[{CLR['dim']}]type /help for commands[/]"
        )

    def _refresh_all(self) -> None:
        # ── Metrics (split over 2 lines to avoid clipping) ──
        t = _fetch_telemetry()
        if t:
            r24, rt = t.get('r24', 0), t.get('rt', 0)
            tp, td = t.get('tp', 0), t.get('td', 0)
            am = t.get('am', 0)
            ac = float(t.get('ac', 0))
            self.query_one("#metrics-line1", Static).update(
                f" {_b('📊', CLR['primary'])} {_t(f'{r24}/{rt} research')}  "
                f"{_b('📋', CLR['warning'])} {_t(f'{tp} pending / {td} done')}"
            )
            self.query_one("#metrics-line2", Static).update(
                f" {_b('🧠', CLR['success'])} {_t(f'{am} memories')}  "
                f"{_b('🎯', CLR['secondary'])} {_t(f'{ac:.0%} conf')}"
            )
        else:
            self.query_one("#metrics-line1", Static).update(_d("Telemetry unavailable"))
            self.query_one("#metrics-line2", Static).update("")

        # ── Research ──
        research = _fetch_research(10)
        self.query_one("#research-header", Static).update(
            f"\n{_b('📜 RECENT RESEARCH', CLR['primary'])}"
        )
        if research:
            lines = []
            for r in research:
                conf = r.get("confidence", 0) or 0
                if conf > 0.7:
                    color = CLR["success"]
                elif conf > 0.4:
                    color = CLR["warning"]
                else:
                    color = CLR["error"]
                query = (r.get("query") or "?")[:80]
                summary = (r.get("summary") or "")[:120]
                lines.append(f"  [{color}]{conf:.0%}[/] [{CLR['text']}]{query}[/]")
                if summary:
                    lines.append(f"     [{CLR['faint']}]{summary}[/]")
            self.query_one("#research-section", Static).update("\n".join(lines))
        else:
            self.query_one("#research-section", Static).update(
                f"  {_d('No research yet. Try /research <query>')}"
            )

        # ── Tasks ──
        tasks = _fetch_tasks(20)
        self.query_one("#tasks-header", Static).update(
            f"\n{_b('📋 TASKS', CLR['primary'])}"
        )
        if tasks:
            lines = []
            for t in tasks:
                status = t.get("status", "?")
                title = (t.get("title") or "?")[:70]
                schedule = t.get("schedule") or ""
                sched = f" [{CLR['faint']}]{schedule}[/]" if schedule else ""

                if status in ("done", "completed"):
                    icon = f"[{CLR['success']}]✓[/] {_d('done')}"
                elif status == "in_progress":
                    icon = f"[{CLR['warning']}]●[/] {_d('running')}"
                elif status == "failed":
                    icon = f"[{CLR['error']}]✗[/] {_d('failed')}"
                else:
                    icon = f"[{CLR['dim']}]○[/] {_d(status)}"

                lines.append(f"  {icon}  [{CLR['text']}]{title}[/]{sched}")
            self.query_one("#tasks-section", Static).update("\n".join(lines))
        else:
            self.query_one("#tasks-section", Static).update(
                f"  {_d('No tasks.')}"
            )

    def action_help(self) -> None:
        self.app.push_screen(HelpScreen())

    def action_refresh(self) -> None:
        self._refresh_all()
        self._log(f"{_d('Refreshed')}")

    def action_complete(self) -> None:
        """Tab: complete the selected command."""
        self._complete_command()

    def action_palette_up(self) -> None:
        """↑: move selection up."""
        self.query_one("#cmd-palette", CommandPalette).move_up()

    def action_palette_down(self) -> None:
        """↓: move selection down."""
        self.query_one("#cmd-palette", CommandPalette).move_down()

    def action_dismiss_palette(self) -> None:
        """Escape: dismiss palette if visible, else pop screen."""
        palette = self.query_one("#cmd-palette", CommandPalette)
        if palette.has_class("visible"):
            palette.hide()
        else:
            # Only pop if there's an overlay
            app = self.app
            if app and len(app.screen_stack) > 1:
                app.pop_screen()

    def _log(self, text: str) -> None:
        """Append a line to the agent output area."""
        output = self.query_one("#output", Static)
        current = output.render()
        if isinstance(current, str):
            new = (current + "\n" + text).strip()
        else:
            new = text
        output.update(new)


# ── App ─────────────────────────────────────────────────────────────


class AIWorkspaceApp(App[None]):
    TITLE = "AI Workstation"
    SUB_TITLE = ""

    CSS = """
    * { scrollbar-size-vertical: 1; scrollbar-color: $primary 10%; scrollbar-background: $background; }
    Screen { background: $background; }
    #top-bar {
        dock: top; height: 1; padding: 0 2;
        background: $surface; border-bottom: solid $primary 25%;
    }
    #metrics-line1 { dock: top; height: 1; padding: 0 2; background: $panel; }
    #metrics-line2 { dock: top; height: 1; padding: 0 2; background: $panel; border-bottom: solid $primary 15%; }
    #agents { dock: top; height: auto; padding: 0 2; background: $surface; border-bottom: solid $success 15%; }
    #body {
        height: 1fr;
        padding: 0 2;
        background: $background;
    }
    #input-area {
        dock: bottom; height: auto; padding: 1 2 0 2;
        background: $surface; border-top: solid $primary 25%;
    }
    #task-input {
        width: 1fr;
        background: $background;
        color: $text;
        border: solid $primary 20%;
        padding: 0 1;
        height: 3;
    }
    #task-input:focus {
        border: solid $primary 50%;
    }
    #info-bar {
        dock: bottom; height: 1; padding: 0 2;
        background: $surface;
        color: $text 50%;
    }
    Footer { dock: bottom; background: $surface; border-top: solid $primary 20%; }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._default_model = "qwen3:14b"
        self._agent_workers: dict[str, asyncio.Task] = {}
        self._agent_count = 0

    def on_mount(self) -> None:
        self.register_theme(THEME)
        self.theme = "workstation"
        self._main = MainScreen()
        self.push_screen(self._main)

    @property
    def m(self) -> MainScreen:
        """Return MainScreen, even if an overlay is active."""
        # Walk screen stack bottom-up to find MainScreen
        for screen in self.screen_stack:
            if isinstance(screen, MainScreen):
                return screen
        raise RuntimeError("MainScreen not found in screen stack")

    # ── Input handling ──────────────────────────────────────────

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
            self.m.query_one("#output", Static).update("")
            self.m._log(_d("Cleared"))

        elif cmd == "/model":
            if args:
                self._default_model = args
                self.m._log(f"{_d('Model:')} {args}")
            else:
                self.m._log(f"{_d('Model:')} {self._default_model}")

        elif cmd == "/research":
            if args:
                self.m._log(f"\n{_b('Researching:', CLR['primary'])} {args}")
                await self._run_research(args)
                self.m.action_refresh()
            else:
                self.m._log(f"[{CLR['warning']}]Usage: /research <query>[/]")

        elif cmd == "/tasks":
            self.m.action_refresh()

        elif cmd == "/cost":
            await self._show_cost()

        else:
            self.m._log(f"[{CLR['warning']}]Unknown: {cmd}  (try /help)[/]")

    # ── Agent spawning with live streaming ───────────────────────

    async def _spawn_agent(self, text: str) -> None:
        self._agent_count += 1
        name = f"agent-{self._agent_count}"

        self.m._log(f"\n{_b('▸', CLR['primary'])} {_t(text)}")

        # Show agent status as running
        agents_bar = self.m.query_one("#agents", AgentStatusBar)
        agents_bar.upsert(name, status="running", task=text)

        try:
            from ai_workspace.tui.worker import AgentConfig, AgentWorker
            from ai_workspace.core.sessions import SessionStore

            store = SessionStore(); store.initialize()
            session = store.create_session(
                cwd=str(Path.cwd()),
                model=self._default_model,
                label=text[:40],
            )
            store.add_message(session_id=session.id, role="user", content=text)
            store.close()

            config = AgentConfig(
                lane_id=name,
                agent_type="general",
                model=self._default_model,
                session_id=session.id,
                cwd=str(Path.cwd()),
            )
            worker = AgentWorker(config)

            # Start the agent in background and drain the queue live
            async def _run_and_stream() -> None:
                # Start agent
                agent_task = asyncio.create_task(worker.run_agent(text))

                # Drain output queue until agent completes
                while not agent_task.done() or not worker.queue.empty():
                    try:
                        line = await asyncio.wait_for(worker.queue.get(), timeout=0.1)
                        self.m._log(_d(line))
                    except asyncio.TimeoutError:
                        continue

                await agent_task  # Let any exception propagate

                if worker.status.name == "COMPLETED":
                    agents_bar.upsert(name, status="done", task=text)
                    self.m._log(f"\n{_b('✓', CLR['success'])} {_d('Agent completed')}")
                elif worker.status.name == "ERROR":
                    agents_bar.upsert(name, status="error", task=text)
                    self.m._log(f"\n[{CLR['error']}]Agent error: {worker._error}[/]")
                else:
                    agents_bar.upsert(name, status="done", task=text)

                # Remove after a delay
                self.set_timer(5.0, lambda: agents_bar.remove(name))

            self._agent_workers[name] = asyncio.create_task(_run_and_stream())

        except ImportError as e:
            agents_bar.upsert(name, status="error", task=f"Import error: {e}")
            self.m._log(f"[{CLR['error']}]Agent system unavailable: {e}[/]")
        except Exception as e:
            logger.exception("Agent error")
            agents_bar.upsert(name, status="error", task=str(e)[:60])
            self.m._log(f"[{CLR['error']}]Agent error: {e}[/]")

    # ── Research ─────────────────────────────────────────────────

    async def _run_research(self, query: str) -> None:
        try:
            from ai_workspace.search import DeepSearchEngine

            @work(thread=True)
            def do_research() -> str | None:
                import asyncio as aio
                engine = DeepSearchEngine(max_depth=2)
                result = aio.run(engine.research(query))
                return (
                    f"[{CLR['success']}]Done: {len(result.sub_questions)} sub-questions, "
                    f"confidence {result.confidence:.0%}[/]\n"
                    f"[{CLR['text']}]{result.answer[:300]}[/]"
                    if result.answer else ""
                )

            worker = do_research()
            # We need to await this — use a polling approach
            while not worker.is_finished:
                await asyncio.sleep(0.1)
            if worker.result:
                self.m._log(worker.result)
        except ImportError as e:
            self.m._log(f"[{CLR['error']}]Research unavailable: {e}[/]")
        except Exception as e:
            self.m._log(f"[{CLR['error']}]Research error: {e}[/]")

    # ── Cost ─────────────────────────────────────────────────────

    async def _show_cost(self) -> None:
        try:
            from ai_workspace.core.cost import CostService
            cost = CostService(); cost.initialize()
            cache = cost.cache.stats()
            budget = cost.budget.budget_summary()
            self.m._log(
                f"[{CLR['text']}]Today: ${budget['today_spent']:.4f} / ${budget['today_budget']:.2f}"
                f" ({budget['today_pct']}%) | "
                f"Cache: {cache['total_entries']} entries, {cache['total_hits']} hits, "
                f"{cache['tokens_saved']:,} tokens saved[/]"
            )
        except Exception as e:
            self.m._log(f"[{CLR['error']}]Cost unavailable: {e}[/]")


# ── Entry point ────────────────────────────────────────────────────


def run_tui():
    app = AIWorkspaceApp()
    app.run()


if __name__ == "__main__":
    run_tui()
