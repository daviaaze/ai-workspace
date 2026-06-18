"""
AI Workstation v3 — terminal agent dashboard with multi-agent swarm.

Type a task and press Enter — agent spawns and starts coding.
Ctrl+J spawn · F2 chat · Space pause · Ctrl+K kill · / for commands.
"""

from __future__ import annotations

import asyncio
import logging
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

from ai_workspace.tui.worker import AgentConfig, AgentWorker
from ai_workspace.tui.widgets import AgentLane, PermissionModal, Toast

logger = logging.getLogger("aiw.tui")

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
    "/help": "Show command reference",
    "/model <name>": "Switch model (e.g. /model qwen3:14b)",
    "/clear": "Clear agent output",
    "/retry": "Retry last task",
    "/export": "Export session to JSONL",
    "/sessions": "List recent sessions",
    "/spawn <type> <task>": "Spawn typed agent (coding, research, general)",
    "/cost": "Show budget and cache stats",
    "/git": "Show git status",
    "/quit": "Exit",
}


class Header(Static):
    """Top bar: workspace path, git info, agent count."""

    cwd: reactive[str] = reactive("~")
    git_branch: reactive[str] = reactive("")
    git_ahead: reactive[int] = reactive(0)
    git_behind: reactive[int] = reactive(0)
    git_modified: reactive[int] = reactive(0)
    agents_online: reactive[int] = reactive(0)
    agents_total: reactive[int] = reactive(0)

    def render(self) -> str:
        home = str(Path.home())
        p = self.cwd
        if p.startswith(home):
            p = "~" + p[len(home):]
        if len(p) > 36:
            p = "\u2026" + p[-35:]

        parts = [f"[bold $primary]aiw[/]  [$text 70%]{p}[/]"]

        if self.git_branch:
            g = "[$text 50%]git:[/] [$text 60%]" + self.git_branch + "[/]"
            indicators = []
            if self.git_ahead:
                indicators.append(f"[$success]+{self.git_ahead}[/]")
            if self.git_behind:
                indicators.append(f"[$error]-{self.git_behind}[/]")
            if self.git_modified:
                indicators.append(f"[$warning]~{self.git_modified}[/]")
            if indicators:
                g += " " + " ".join(indicators)
            parts.append(g)

        if self.agents_total:
            parts.append(
                f"[$success]{self.agents_online}[/]/"
                f"[$text 40%]{self.agents_total}[/] "
                f"[$text 50%]agents[/]"
            )

        return "  ".join(parts)


class Body(VerticalScroll):
    """Container for agent output lanes."""


class HelpScreen(ModalScreen[None]):
    """Keyboard / command reference."""

    CSS = """
    HelpScreen {
        align: center middle;
        background: $background 85%;
    }
    #help-box {
        width: 52;
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
                "[bold $primary]AI Workstation[/] — Commands\n"
                "\n"
                + "\n".join(
                    f"  [bold $text 80%]{cmd:<32}[/] [$text 60%]{desc}[/]"
                    for cmd, desc in SLASH_COMMANDS.items()
                )
                + "\n\n"
                "  [bold $primary]Shortcuts[/]\n"
                "  [bold]Ctrl+J[/] [$text 60%]Spawn agent[/]     "
                "[bold]F2[/] [$text 60%]Chat with agent[/]\n"
                "  [bold]Space[/] [$text 60%]Pause / Resume[/]   "
                "[bold]Ctrl+K[/] [$text 60%]Kill agent[/]\n"
                "  [bold]Ctrl+P[/] [$text 60%]Find (fuzzy)[/]    "
                "[bold]Ctrl+O[/] [$text 60%]Switch workspace[/]\n"
                "  [bold]F1[/] [$text 60%]This help[/]           "
                "[bold]Ctrl+C[/] [$text 60%]Quit[/]\n"
                "\n",
            )

    def action_dismiss(self) -> None:
        self.dismiss()


class SessionPicker(ModalScreen[str | None]):
    """Resume a previous session."""

    CSS = """
    SessionPicker {
        align: center middle;
        background: $background 85%;
    }
    #session-box {
        width: 60;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: solid $primary 40%;
        padding: 1 2;
    }
    """

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    def __init__(self, sessions: list[dict]) -> None:
        super().__init__()
        self.sessions = sessions

    def compose(self) -> ComposeResult:
        with Static(id="session-box"):
            yield Label("[bold $primary]Recent Sessions[/]\n")
            if not self.sessions:
                yield Label("  [$text 60%]No sessions. Type a task to begin.[/]")
                return
            for i, s in enumerate(self.sessions[:9]):
                label = s.get("label") or (s.get("id", "")[:12])
                cwd = s.get("cwd", ".")[:30]
                updated = (s.get("updated_at") or "")[:16]
                yield Label(
                    f"  [bold $primary]{i + 1}.[/] {label}\n"
                    f"    [$text 50%]{cwd}  {updated}[/]"
                )

    def action_dismiss(self) -> None:
        self.dismiss(None)

    def key_1(self) -> None: self._pick(0)
    def key_2(self) -> None: self._pick(1)
    def key_3(self) -> None: self._pick(2)
    def key_4(self) -> None: self._pick(3)
    def key_5(self) -> None: self._pick(4)
    def key_6(self) -> None: self._pick(5)
    def key_7(self) -> None: self._pick(6)
    def key_8(self) -> None: self._pick(7)
    def key_9(self) -> None: self._pick(8)

    def _pick(self, idx: int) -> None:
        if idx < len(self.sessions):
            self.dismiss(self.sessions[idx].get("id"))


class MainScreen(Screen[None]):
    AUTO_FOCUS = None

    BINDINGS = [
        Binding("ctrl+j", "spawn", "Spawn"),
        Binding("f2", "chat", "Chat"),
        Binding("space", "pause", "Pause"),
        Binding("ctrl+k", "kill", "Kill"),
        Binding("ctrl+p", "find", "Find"),
        Binding("ctrl+o", "workspace", "Wksp"),
        Binding("escape", "dismiss", "Dismiss", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Header(id="header")
        with Body(id="body"):
            yield Label("", id="body-empty")
        yield Footer()
        yield PermissionModal(id="permission-modal")
        yield Toast(id="toast")

    def show_empty(self) -> None:
        h = str(Path.home())
        cwd = self.app.cwd if hasattr(self.app, "cwd") else str(Path.cwd())
        if cwd.startswith(h):
            cwd = "~" + cwd[len(h):]
        if len(cwd) > 42:
            cwd = "\u2026" + cwd[-41:]

        self.query_one("#body-empty", Label).update(
            "\n\n"
            "     [bold $primary]AI Workstation[/]\n"
            "\n"
            f"     [$text 50%]{cwd}[/]\n"
            "\n"
            "     [$text 60%]Type a task and press [bold]Enter[/] — agent spawns and begins.[/]\n"
            "     [$text 60%]/help [dim]for commands[/]    /sessions [dim]to resume[/]    F1 [dim]for reference[/][/]\n"
        )

    def hide_empty(self) -> None:
        self.query_one("#body-empty", Label).update("")

    def action_spawn(self) -> None:
        self.app.action_spawn()

    def action_chat(self) -> None:
        self.app.action_chat()

    def action_pause(self) -> None:
        self.app.action_pause()

    def action_kill(self) -> None:
        self.app.action_kill()

    def action_find(self) -> None:
        self.app.action_find()

    def action_workspace(self) -> None:
        self.app.action_workspace()

    def action_dismiss(self) -> None:
        self.app.action_dismiss()


class AIWorkspaceApp(App[None], inherit_bindings=False):
    TITLE = "AI Workstation"
    SUB_TITLE = ""
    AUTO_FOCUS = None

    CSS = """
    * { scrollbar-size-vertical: 1; scrollbar-color: $primary 10%; scrollbar-color-hover: $primary 60%; scrollbar-background: $background; }
    Screen { background: $background; }
    Header { dock: top; height: 1; padding: 0 2; background: $surface; border-bottom: solid $primary 25%; }
    Body { height: 1fr; padding: 1; background: $background; }
    Body > AgentLane { height: auto; margin: 0 0 1 0; border: solid $primary 15%; background: $surface; padding: 1 2; }
    Body > AgentLane:focus-within { border: solid $primary 40%; }
    #body-empty { padding: 4 6; text-align: center; }
    Footer { dock: bottom; background: $surface; border-top: solid $primary 25%; }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("f1", "help", "Help"),
        Binding("ctrl+p", "command_palette", "Commands"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.cwd = str(Path.cwd())
        self._main: MainScreen | None = None
        self._agents: dict[str, AgentLane] = {}
        self._agent_workers: dict[str, AgentWorker] = {}
        self._default_model = "qwen3:14b"

    def on_mount(self) -> None:
        self.register_theme(THEME)
        self.theme = "workstation"
        self._main = MainScreen()
        self.push_screen(self._main)
        self._load_git()
        self.set_timer(0.3, lambda: self._show_empty_safe())
        self.set_interval(60, self._tick_clock)
        self.set_interval(0.5, self._poll_permissions)

    @property
    def m(self) -> MainScreen:
        assert self._main is not None
        return self._main

    def _show_empty_safe(self) -> None:
        if self._main:
            self._main.show_empty()

    def _poll_permissions(self) -> None:
        try:
            modal = self.m.query_one("#permission-modal", PermissionModal)
        except Exception:
            return
        if modal._pending_request is not None:
            return
        for name, worker in list(self._agent_workers.items()):
            perm = worker.pending_permission
            if perm is not None:
                modal.show_request(
                    request_id=perm.request_id,
                    agent_name=perm.agent_name,
                    task_title=perm.description[:60],
                    tool_name=perm.tool_name,
                    description=perm.description,
                    input_preview=perm.preview[:500],
                )
                modal._pending_request = perm
                modal.set_class(True, "visible")
                modal.refresh()
                self._show_toast(
                    f"Permission required: {perm.agent_name} wants to {perm.tool_name}",
                    "warning",
                )
                return

    def _tick_clock(self) -> None:
        try:
            self.m.query_one("#header", Header).refresh()
        except Exception:
            pass  # header may unmount during agent destruction

    def _load_git(self) -> None:
        try:
            import subprocess

            r = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                cwd=self.cwd,
                timeout=2,
            )
            if r.returncode == 0:
                self.m.query_one("#header", Header).git_branch = r.stdout.strip()

            r = subprocess.run(
                ["git", "status", "--branch", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=self.cwd,
                timeout=2,
            )
            if r.returncode == 0:
                h = self.m.query_one("#header", Header)
                for line in r.stdout.split("\n"):
                    if line.startswith("## ") and " [" in line:
                        ab = line.split(" [", 1)[1].rstrip("]")
                        for part in ab.split(","):
                            part = part.strip()
                            if "ahead " in part:
                                try:
                                    h.git_ahead = int(part.split("ahead ")[1])
                                except (ValueError, IndexError):
                                    logger.debug("git ahead parse: %s", part)
                    elif len(line) >= 2 and line[1] not in (" ", "?"):
                        h.git_modified += 1
        except Exception:
            logger.debug("git info unavailable in %s", self.cwd)

    def spawn_agent(
        self, task: str, agent_type: str = "general", model: str | None = None
    ) -> AgentLane:
        self.m.hide_empty()
        lane = AgentLane(
            agent_name=f"agent-{len(self._agents) + 1}",
            agent_model=model or self._default_model,
            current_task=task[:60],
            task_status="notstarted",
        )
        self._agents[lane.agent_name] = lane
        self.m.query_one("#body", Body).mount(lane)
        self.m.query_one("#header", Header).agents_total = len(self._agents)
        self.m.query_one("#header", Header).agents_online = len(self._agents)
        return lane

    def remove_agent(self, name: str) -> None:
        lane = self._agents.pop(name, None)
        if lane:
            try:
                lane.remove()
            except Exception:
                logger.debug("remove_agent: lane already removed")
        self._agent_workers.pop(name, None)
        try:
            h = self.m.query_one("#header", Header)
            h.agents_online = len(self._agents)
            h.agents_total = len(self._agents)
        except Exception:
            logger.debug("remove_agent: header query failed during teardown")
        if not self._agents and self._main:
            self._main.show_empty()

    def _get_focused(self) -> tuple:
        for name, lane in self._agents.items():
            if lane.has_focus:
                return name, lane, self._agent_workers.get(name)
        if self._agents:
            name = next(iter(self._agents))
            return name, self._agents[name], self._agent_workers.get(name)
        return None, None, None

    @on(Input.Submitted)
    async def on_input(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        event.input.value = ""

        if text.startswith("/"):
            await self._handle_slash(text)
            return

        if text.startswith(":cd "):
            p = Path(text[4:].strip()).expanduser().resolve()
            if p.is_dir():
                self.cwd = str(p)
                self.m.query_one("#header", Header).cwd = str(p)
                self._show_toast(f"Workspace: {self.cwd[:50]}", "info")
            else:
                self._show_toast(f"Not found: {text[4:]}", "error")
            return

        await self._spawn_from_input(text)

    async def _spawn_from_input(
        self, text: str, agent_type: str = "general", model: str | None = None
    ) -> None:
        lane = self.spawn_agent(text, agent_type=agent_type, model=model)
        lane.append_output(f"> [bold]You:[/] {text}")
        try:
            from ai_workspace.core.sessions import SessionStore

            store = SessionStore()
            store.initialize()
            s = store.create_session(
                cwd=self.cwd,
                model=model or self._default_model,
                label=text[:40],
            )
            store.add_message(session_id=s.id, role="user", content=text)
            store.close()

            config = AgentConfig(
                lane_id=lane.agent_name,
                agent_type=agent_type,
                model=model or self._default_model,
                session_id=s.id,
                cwd=self.cwd,
            )
            worker = AgentWorker(config)
            self._agent_workers[lane.agent_name] = worker
            lane.attach_worker(worker)
            asyncio.create_task(worker.start_loop(text))
            self._show_toast(f"{lane.agent_name} spawned ({agent_type})", "info")
        except Exception as e:
            logger.exception("Failed to spawn agent")
            lane.append_output(f"[$error]Failed to start agent: {e}[/]")
            self._show_toast(f"Agent spawn failed: {e}", "error")

    async def _handle_slash(self, text: str) -> None:
        cmd, _, args = text.partition(" ")

        if cmd == "/help":
            self.push_screen(HelpScreen())
        elif cmd == "/quit":
            self.exit()
        elif cmd == "/clear":
            _, lane, _ = self._get_focused()
            if lane:
                lane._output_lines.clear()
                lane._refresh_output()
                self._show_toast("Output cleared", "info")
            else:
                self._show_toast("No agent to clear", "warning")
        elif cmd == "/retry":
            _, lane, worker = self._get_focused()
            if worker and worker.config.current_task:
                await self._spawn_from_input(worker.config.current_task)
                self._show_toast("Retrying last task", "info")
            else:
                self._show_toast("Nothing to retry", "warning")
        elif cmd == "/export":
            _, __, worker = self._get_focused()
            if worker and worker.config.session_id:
                try:
                    from ai_workspace.core.sessions import SessionStore

                    store = SessionStore()
                    store.initialize()
                    path = store.export_jsonl(worker.config.session_id)
                    store.close()
                    self._show_toast(f"Exported: {path}", "info")
                except Exception as e:
                    self._show_toast(f"Export failed: {e}", "error")
            else:
                self._show_toast("No session to export", "warning")
        elif cmd == "/sessions":
            await self._show_sessions()
        elif cmd == "/model":
            if args:
                self._default_model = args
                self._show_toast(f"Default model: {args}", "info")
            else:
                self._show_toast(f"Default model: {self._default_model}", "info")
        elif cmd == "/spawn":
            parts = args.split(" ", 1)
            atype = parts[0] if parts else "general"
            task = parts[1] if len(parts) > 1 else ""
            if task:
                await self._spawn_from_input(task, agent_type=atype)
            else:
                self._show_toast("Usage: /spawn <type> <task>", "warning")
        elif cmd == "/cost":
            await self._show_cost()
        elif cmd == "/git":
            self._load_git()
            h = self.m.query_one("#header", Header)
            self._show_toast(
                f"git:{h.git_branch} +{h.git_ahead} -{h.git_behind} ~{h.git_modified}",
                "info",
            )
        else:
            self._show_toast(f"Unknown: {cmd}  (try /help)", "warning")

    async def _show_sessions(self) -> None:
        try:
            from ai_workspace.core.sessions import SessionStore

            store = SessionStore()
            store.initialize()
            sessions = store.list_sessions(limit=10)
            store.close()
            self.push_screen(SessionPicker(sessions))
        except Exception as e:
            self._show_toast(f"Cannot list sessions: {e}", "error")

    async def _show_cost(self) -> None:
        try:
            from ai_workspace.core.cost import CostService

            cost = CostService()
            cost.initialize()
            cache = cost.cache.stats()
            budget = cost.budget.budget_summary()
            msg = (
                f"Today: ${budget['today_spent']:.4f} / ${budget['today_budget']:.2f}"
                f" ({budget['today_pct']}%)"
                f"  Cache: {cache['total_entries']} entries, "
                f"{cache['total_hits']} hits, {cache['tokens_saved']:,} tokens saved"
            )
            self._show_toast(msg, "info")
        except Exception as e:
            self._show_toast(f"Cost info unavailable: {e}", "error")

    @on(PermissionModal.Verdict)
    def on_verdict(self, event: PermissionModal.Verdict) -> None:
        pass

    def action_spawn(self) -> None:
        try:
            self.m.query_one(Footer).query_one(Input).focus()
        except Exception:
            logger.debug("Cannot focus input")

    def action_chat(self) -> None:
        name, lane, worker = self._get_focused()
        if worker:
            from ai_workspace.tui.chat import push_chat_screen

            push_chat_screen(
                self,
                agent_name=name or "agent",
                model=worker.config.model,
                session_id=worker.config.session_id,
                cwd=worker.config.cwd or self.cwd,
                agent_type=worker.config.agent_type,
                worker=worker,
                context_manager=getattr(worker.config, "context_manager", None),
            )
        else:
            self._show_toast("No agent — spawn one first (Ctrl+J)", "warning")

    def action_pause(self) -> None:
        name, lane, worker = self._get_focused()
        if worker and worker.status.name == "RUNNING":
            worker.pause()
            lane.is_paused = True
            self._show_toast(f"{name} paused", "warning")
        elif worker and worker.status.name == "PAUSED":
            worker.resume()
            lane.is_paused = False
            self._show_toast(f"{name} resumed", "info")
        else:
            self._show_toast("No running agent to pause", "warning")

    def action_kill(self) -> None:
        name, lane, worker = self._get_focused()
        if not worker:
            self._show_toast("No agent to kill", "warning")
            return
        if lane and getattr(lane, "_kill_pending", False):
            lane._kill_pending = False
            worker.kill()
            lane.detach_worker()
            lane.task_status = "rejected"
            self._show_toast(f"{name} killed", "error")
            self.set_timer(5.0, lambda n=name: self.remove_agent(n))
        elif lane:
            lane._kill_pending = True
            self._show_toast(
                f"Press Ctrl+K again to kill {name}", "warning"
            )
            self.set_timer(
                3.0,
                lambda l=lane: setattr(l, "_kill_pending", False) if l else None,
            )

    def action_detail(self) -> None:
        name, lane, worker = self._get_focused()
        if lane:
            from ai_workspace.tui.detail import DetailScreen

            sid = worker.config.session_id if worker else ""
            self.push_screen(
                DetailScreen(
                    lane=lane,
                    session_id=sid,
                    context_manager=(
                        getattr(worker.config, "context_manager", None)
                        if worker
                        else None
                    ),
                )
            )
        else:
            self._show_toast("No agent to view", "warning")

    def action_find(self) -> None:
        try:
            from ai_workspace.tui.fuzzy import FuzzyFinder

            self.push_screen(FuzzyFinder())
        except Exception as e:
            logger.warning("FuzzyFinder unavailable: %s", e)
            self._show_toast(f"Find unavailable: {e}", "error")

    def action_workspace(self) -> None:
        try:
            from ai_workspace.tui.workspace import WorkspaceSwitcher

            self.push_screen(WorkspaceSwitcher())
        except Exception as e:
            logger.warning("WorkspaceSwitcher unavailable: %s", e)
            self._show_toast(f"Workspace unavailable: {e}", "error")

    def action_dismiss(self) -> None:
        if len(self.screen_stack) > 1:
            self.pop_screen()

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_command_palette(self) -> None:
        self.action_find()

    def _show_toast(
        self, message: str, severity: str = "info", duration: float = 4.0
    ) -> None:
        try:
            toast = self.m.query_one("#toast", Toast)
            toast.show(message, severity, duration)
        except Exception:
            pass  # toast may not be mounted; non-critical


def run_tui():
    app = AIWorkspaceApp()
    app.run()


if __name__ == "__main__":
    run_tui()
