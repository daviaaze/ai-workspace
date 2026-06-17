"""
AI Workspace TUI v2 — Tabbed Dashboard Redesign.

New architecture:
┌─ HeaderBar (tabs + status) ────────────────────────────────────────────┐
├─ ContentSwitcher (Dashboard | Agents | Tasks) ─────────────────────────┤
├─ BottomBar (agent status + context hints) ─────────────────────────────┤
└─ Overlays: PermissionModal, CommandPalette, FuzzyFinder, Toast, etc.   │

Tabs:
  🏠 Dashboard — Overview cards (agents, tasks, activity, stats)
  🤖 Agents   — Agent grid with list + detail
  📋 Tasks    — Full DataTable with filters
  💬 Chat     — Pushes ChatScreen (existing)
  🔍 Search   — Opens FuzzyFinder overlay
  📊 Metrics  — Opens AgentMetrics overlay

Keybindings preserved from v1:
  Tab         — cycle focus
  Ctrl+S      — spawn agent
  Ctrl+N      — new task
  Ctrl+D      — detail view
  Ctrl+W      — workspace switcher
  Ctrl+P      — permissions
  Ctrl+F      — fuzzy find
  Ctrl+G      — knowledge graph
  Ctrl+E      — context workbench
  Ctrl+M      — metrics
  Ctrl+L      — cycle layout (agents view)
  Space       — pause/resume
  Ctrl+X      — kill agent
  Ctrl+Enter  — chat
  :           — command palette
  q           — quit (when not in input)
  F1 / ?      — help
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from textual import on, work
from textual.app import App, ComposeResult, Screen
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.content import Content
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import (
    Button,
    ContentSwitcher,
    Header,
    Input,
    Label,
    ListView,
    Static,
    Tabs,
)

from ai_workspace.tui.header import HeaderBar
from ai_workspace.tui.dashboard import DashboardView
from ai_workspace.tui.agent_grid import AgentsView
from ai_workspace.tui.task_table import TasksView
from ai_workspace.tui.git_panel import GitPanel
from ai_workspace.tui.bottom_bar import BottomBar

from ai_workspace.tui.worker import AgentConfig, AgentWorker
from ai_workspace.agents.message_queue import MessagePriority
from ai_workspace.agents.context_manager import ContextManager
from ai_workspace.tui.widgets import (
    AgentLane,
    CommandPalette,
    NodePanel,
    PermissionModal,
    StatusBar,
    TaskItem,
    TaskPanel,
    Toast,
)
from ai_workspace.tui.data import load_tasks, load_metrics, load_agent_status
from ai_workspace.tui.context_workbench import ContextWorkbench
from ai_workspace.tui.chat import push_chat_screen
from ai_workspace.tui.detail import DetailScreen
from ai_workspace.tui.fuzzy import FuzzyFinder, FuzzyResult, ResultKind
from ai_workspace.tui.metrics import AgentMetrics
from ai_workspace.tui.workspace import WorkspaceSwitcher, WorkspaceEntry
from ai_workspace.tui.graph import KnowledgeGraph
from ai_workspace.tui.help import HelpScreen


class SpawnDialog(Screen):
    """Modal screen for spawning a new agent."""

    CSS = """
    SpawnDialog {
        align: center middle;
        background: $background 60%;
    }
    #spawn-container {
        width: 50;
        height: auto;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }
    #spawn-title {
        text-style: bold;
        color: $accent;
        padding: 0 0 1 0;
    }
    #spawn-container Input {
        margin: 0 0 1 0;
        background: $panel;
    }
    #spawn-container Button {
        margin: 1 1 0 0;
    }
    """

    class Spawn(Message):
        def __init__(self, agent_type: str, model: str, project: str, task: str, session_id: str, cwd: str) -> None:
            super().__init__()
            self.agent_type = agent_type
            self.model = model
            self.project = project
            self.task = task
            self.session_id = session_id
            self.cwd = cwd

    def compose(self) -> ComposeResult:
        with Container(id="spawn-container"):
            yield Label("[bold]Spawn Agent[/]", id="spawn-title")
            yield Input(placeholder="agent type: coding, research, general...", id="spawn-type")
            yield Input(placeholder="model (default: qwen3:14b)", id="spawn-model")
            yield Input(placeholder="directory (default: current)", id="spawn-dir")
            yield Input(placeholder="project (optional)", id="spawn-project")
            yield Input(placeholder="session ID (optional)", id="spawn-session")
            yield Input(placeholder="task description...", id="spawn-task")
            with Horizontal():
                yield Button("Spawn", id="btn-spawn-confirm", variant="primary")
                yield Button("Cancel", id="btn-spawn-cancel")

    def on_mount(self) -> None:
        try:
            self.query_one("#spawn-type", Input).focus()
        except Exception:
            pass

    @on(Button.Pressed, "#btn-spawn-confirm")
    def on_spawn(self) -> None:
        try:
            agent_type = self.query_one("#spawn-type", Input).value or "general"
            model = self.query_one("#spawn-model", Input).value or "qwen3:14b"
            cwd = self.query_one("#spawn-dir", Input).value or str(Path.cwd())
            project = self.query_one("#spawn-project", Input).value or ""
            session_id = self.query_one("#spawn-session", Input).value or ""
            task = self.query_one("#spawn-task", Input).value or "New task"
        except Exception:
            agent_type, model, cwd, project, session_id, task = "general", "qwen3:14b", str(Path.cwd()), "", "", "New task"
        self.dismiss(self.Spawn(agent_type, model, project, task, session_id, cwd))

    @on(Button.Pressed, "#btn-spawn-cancel")
    def on_cancel(self) -> None:
        self.dismiss(None)


class AIWorkspaceApp(App):
    """AI Workspace TUI v2 — Tabbed Dashboard."""

    TITLE = "AI Workspace"
    SUB_TITLE = "Agent Operations Center"

    CSS = """
    /* ── Global ── */
    Screen {
        layers: base overlay;
        overflow: hidden hidden;
    }

    #app-container {
        height: 1fr;
    }

    #main-content {
        height: 1fr;
        background: $background;
        overflow: hidden hidden;
    }

    #main-content > * {
        height: 1fr;
    }

    /* ── Overlay widgets ── */
    #permission-modal {
        display: none;
        layer: overlay;
        background: $surface;
        border: thick $warning;
        padding: 1 2;
        width: 60;
        height: auto;
        dock: top;
        offset-x: 20;
        offset-y: 3;
    }
    #permission-modal.visible {
        display: block;
    }

    #command-palette {
        display: none;
        layer: overlay;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
        width: 60;
        height: auto;
        dock: bottom;
        offset-x: 10;
    }
    #command-palette.visible {
        display: block;
    }

    #toast {
        display: none;
        layer: overlay;
        background: $surface;
        border: solid $success;
        padding: 1 2;
        width: auto;
        max-width: 50;
        height: auto;
        dock: top;
        offset-x: 2;
        offset-y: 6;
    }
    #toast.visible {
        display: block;
    }
    #toast.-warning {
        border: solid $warning;
    }
    #toast.-error {
        border: solid $error;
    }
    """

    BINDINGS = [
        ("tab", "cycle_focus", "Cycle Focus"),
        ("ctrl+k", "toggle_tasks", "Tasks"),
        ("ctrl+t", "toggle_thinking", "Thinking"),
        ("ctrl+shift+t", "toggle_thinking_all", "Think All"),
        ("ctrl+s", "show_spawn", "Spawn Agent"),
        ("ctrl+n", "new_task", "New Task"),
        ("ctrl+d", "detail_view", "Detail"),
        ("ctrl+w", "switch_workspace", "Workspace"),
        ("ctrl+p", "view_permissions", "Permissions"),
        ("ctrl+f", "fuzzy_find", "Find"),
        ("ctrl+g", "knowledge_graph", "Graph"),
        ("ctrl+e", "context_workbench", "Context"),
        ("ctrl+l", "cycle_layout", "Layout"),
        ("ctrl+m", "toggle_metrics", "Metrics"),
        ("ctrl+r", "refresh_git", "Git Refresh"),
        ("space", "toggle_pause", "Pause/Resume"),
        ("ctrl+x", "kill_agent", "Kill"),
        ("ctrl+shift+n", "toggle_nodes", "Nodes"),
        ("ctrl+c", "quit", "Quit"),
        ("q", "quit", "Quit"),
        (":", "command_palette", "Command"),
        ("escape", "dismiss_modal", "Dismiss"),
        ("ctrl+enter", "open_chat", "Chat"),
        ("f1", "show_help", "Help"),
        ("question_mark", "show_help", "Help"),
    ]

    show_thinking_all: reactive[bool] = reactive(False)
    current_layout: reactive[str] = reactive("auto")
    layout_mode: reactive[int] = reactive(0)

    def __init__(self) -> None:
        super().__init__()
        self.cwd = str(Path.cwd())
        self._agents: dict[str, AgentLane] = {}
        self._agent_workers: dict[str, AgentWorker] = {}
        self._tasks: list[dict] = []
        self._focus_order = ["dashboard", "agents", "tasks", "bottom-input"]
        self._focus_index = 0
        self.context_manager = ContextManager(
            context_window_tokens=128_000,
            session_id=None,
        )

    def compose(self) -> ComposeResult:
        """Build the tabbed dashboard layout."""
        # Header with tabs
        yield HeaderBar(id="header-bar")

        # Main content area
        with ContentSwitcher(id="main-content", initial="dashboard"):
            yield DashboardView(id="dashboard")
            yield AgentsView(id="agents")
            yield TasksView(id="tasks")
            yield GitPanel(id="git", cwd=self.cwd)

        # Bottom bar
        yield BottomBar(id="bottom-bar")

        # Overlays — NOT in main layout flow
        yield PermissionModal(id="permission-modal")
        yield CommandPalette(id="command-palette")
        yield Toast(id="toast")
        yield FuzzyFinder(id="fuzzy-finder")
        yield AgentMetrics(id="agent-metrics")
        yield WorkspaceSwitcher(id="workspace-switcher")
        yield KnowledgeGraph(id="knowledge-graph")
        yield ContextWorkbench(id="context-workbench")

        # DO NOT add Footer() — duplicates BottomBar keybindings and steals vertical space

    # ─── Lifecycle ──────────────────────────────────────────────

    def on_mount(self) -> None:
        """Initialize from DB or start empty."""
        try:
            self._load_data()
        except Exception:
            pass
        self.set_interval(60, self._tick_clock)
        self.set_interval(0.5, self._poll_permissions)

    def _tick_clock(self) -> None:
        """Refresh the header clock."""
        try:
            self.query_one("#header-bar", HeaderBar).refresh()
        except Exception:
            pass

    def _poll_permissions(self) -> None:
        """Check all workers for pending permission requests."""
        try:
            modal = self.query_one(PermissionModal)
        except Exception:
            return

        if modal._pending_request is not None:
            return

        for name, worker in list(self._agent_workers.items()):
            perm = worker.pending_permission
            if perm is not None:
                modal._pending_request = perm
                modal._request_id = perm.request_id
                modal._agent_name = perm.agent_name
                modal._tool_name = perm.tool_name
                modal._description = perm.description
                modal._input_preview = perm.preview[:500]
                modal.set_class(True, "visible")
                modal.refresh()
                self.notify(
                    f"🔒 {perm.agent_name} wants to: {perm.tool_name}",
                    severity="warning",
                )
                return

    def _load_data(self) -> None:
        """Load real data from knowledge store."""
        metrics = load_metrics()
        tasks = load_tasks()
        status = load_agent_status()

        # Load git status
        git_branch = ""
        git_ahead = 0
        git_behind = 0
        git_modified = 0
        git_staged = 0
        git_untracked = 0
        git_hash = ""
        is_git_repo = False
        try:
            import subprocess
            # Branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, cwd=self.cwd, timeout=2
            )
            if result.returncode == 0 and result.stdout.strip():
                git_branch = result.stdout.strip()
                is_git_repo = True

            # Ahead/behind and status counts
            result = subprocess.run(
                ["git", "status", "--branch", "--porcelain"],
                capture_output=True, text=True, cwd=self.cwd, timeout=2
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if line.startswith("## "):
                        branch_line = line[3:]
                        if " [" in branch_line:
                            ahead_behind = branch_line.split(" [", 1)[1].rstrip("]")
                            if "ahead " in ahead_behind:
                                try:
                                    git_ahead = int(ahead_behind.split("ahead ")[1].split(",")[0].split("]")[0])
                                except (ValueError, IndexError):
                                    pass
                            if "behind " in ahead_behind:
                                try:
                                    git_behind = int(ahead_behind.split("behind ")[1].split(",")[0].split("]")[0])
                                except (ValueError, IndexError):
                                    pass
                    elif line.startswith("?? "):
                        git_untracked += 1
                    elif len(line) >= 2:
                        if line[0] not in (" ", "?"):
                            git_staged += 1
                        if line[1] not in (" ", "?"):
                            git_modified += 1

            # Commit hash
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, cwd=self.cwd, timeout=2
            )
            if result.returncode == 0:
                git_hash = result.stdout.strip()
        except Exception:
            pass

        # Update header
        try:
            header = self.query_one("#header-bar", HeaderBar)
            header.cwd = self.cwd
            header.model = "qwen3:14b"
            header.tasks_active = metrics.get("tasks_active", 0)
            header.tasks_total = metrics.get("tasks_total", 0)
            header.agents_online = len([a for a in status if a.get("online")])
            header.agents_total = len(status)
            header.tokens_saved = metrics.get("tokens_saved", 0)
            header.today_cost = metrics.get("today_cost", 0.0)
            header.cache_entries = metrics.get("cache_entries", 0)
            header.git_branch = git_branch
            header.git_ahead = git_ahead
            header.git_behind = git_behind
            header.git_modified = git_modified
            header.git_staged = git_staged
        except Exception:
            pass

        # Update dashboard
        try:
            dashboard = self.query_one("#dashboard", DashboardView)
            dashboard.update_agents(status)
            dashboard.update_tasks(tasks)
            dashboard.update_stats(
                today_cost=metrics.get("today_cost", 0.0),
                month_cost=metrics.get("month_cost", 0.0),
                tokens_saved=metrics.get("tokens_saved", 0),
                cache_hits=metrics.get("cache_hits", 0),
                cache_entries=metrics.get("cache_entries", 0),
                agents_online=len([a for a in status if a.get("online")]),
                tasks_active=metrics.get("tasks_active", 0),
            )
            dashboard.update_git(
                branch=git_branch,
                ahead=git_ahead,
                behind=git_behind,
                modified=git_modified,
                staged=git_staged,
                untracked=git_untracked,
                commit_hash=git_hash,
                is_git_repo=is_git_repo,
            )
        except Exception:
            pass

        # Update agents view
        try:
            agents_view = self.query_one("#agents", AgentsView)
            agents_view.update_agents(status)
        except Exception:
            pass

        # Update tasks view
        try:
            tasks_view = self.query_one("#tasks", TasksView)
            tasks_view.update_tasks(tasks)
        except Exception:
            pass

        # Update bottom bar
        try:
            bottom = self.query_one("#bottom-bar", BottomBar)
            bottom.agents_online = len([a for a in status if a.get("online")])
            bottom.agents_total = len(status)
        except Exception:
            pass

        self._tasks = tasks

    # ─── Tab Navigation ─────────────────────────────────────────

    @on(Tabs.TabActivated, "#main-tabs")
    def on_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Switch main content based on tab selection."""
        tab_id = event.tab.id
        if not tab_id:
            return

        # Update bottom bar hints
        try:
            bottom = self.query_one("#bottom-bar", BottomBar)
            bottom.set_tab(tab_id)
        except Exception:
            pass

        # Route to appropriate view or overlay
        if tab_id in ("dashboard", "agents", "tasks", "git"):
            try:
                switcher = self.query_one("#main-content", ContentSwitcher)
                switcher.current = tab_id
            except Exception:
                pass
            
            # Refresh views when tab becomes visible
            if tab_id == "tasks":
                try:
                    tasks_view = self.query_one("#tasks", TasksView)
                    tasks_view.update_tasks(self._tasks)
                except Exception:
                    pass
            elif tab_id == "agents":
                try:
                    agents_view = self.query_one("#agents", AgentsView)
                    agents_view.update_agents([
                        {"name": name, **cfg} 
                        for name, cfg in self._agent_workers.items()
                    ] if hasattr(self, '_agent_workers') else [])
                except Exception:
                    pass
        elif tab_id == "chat":
            self.action_open_chat()
            # Reset tab to previous after opening chat overlay
            try:
                tabs = self.query_one("#main-tabs", Tabs)
                switcher = self.query_one("#main-content", ContentSwitcher)
                # Find tab matching current content
                current = switcher.current
                if current:
                    tabs.active = current
            except Exception:
                pass
        elif tab_id == "search":
            self.action_fuzzy_find()
            # Reset tab
            try:
                tabs = self.query_one("#main-tabs", Tabs)
                switcher = self.query_one("#main-content", ContentSwitcher)
                current = switcher.current
                if current:
                    tabs.active = current
            except Exception:
                pass
        elif tab_id == "metrics":
            self.action_toggle_metrics()
            # Reset tab
            try:
                tabs = self.query_one("#main-tabs", Tabs)
                switcher = self.query_one("#main-content", ContentSwitcher)
                current = switcher.current
                if current:
                    tabs.active = current
            except Exception:
                pass

    # ─── Agent Lane Management ─────────────────────────────────

    def _spawn_agent_lane(
        self,
        agent_name: str,
        model: str = "claude-3.7",
        node: str = "",
        task: str = "",
        status: str = "notstarted",
        progress: float = 0.0,
    ) -> AgentLane:
        """Create a new agent lane in the UI."""
        lane = AgentLane(
            agent_name=agent_name,
            agent_model=model,
            agent_node=node,
            current_task=task,
            task_status=status,
            task_progress=progress,
        )
        self._agents[agent_name] = lane
        return lane

    # ─── Keybinding Actions ────────────────────────────────────

    def action_cycle_focus(self) -> None:
        """Cycle focus between main views and bottom input."""
        try:
            switcher = self.query_one("#main-content", ContentSwitcher)
            bottom_input = self.query_one("#bb-input", Input)

            current = switcher.current
            if current == "dashboard":
                switcher.current = "agents"
                try:
                    self.query_one("#agent-list", AgentLane).focus()
                except Exception:
                    pass
            elif current == "agents":
                switcher.current = "tasks"
                try:
                    self.query_one("#task-table", AgentLane).focus()
                except Exception:
                    pass
            else:
                switcher.current = "dashboard"
                bottom_input.focus()
        except Exception:
            pass

    def action_toggle_tasks(self) -> None:
        """Switch to Tasks tab."""
        try:
            tabs = self.query_one("#main-tabs", Tabs)
            tabs.active = "tasks"
        except Exception:
            pass

    def action_toggle_thinking(self) -> None:
        """Toggle thinking for the focused agent."""
        if self.show_thinking_all:
            for lane in self._agents.values():
                lane.show_thinking = False
            self.show_thinking_all = False
            self.notify("Thinking: hidden", severity="information")
            return

        focused = None
        for name, lane in self._agents.items():
            if lane.has_focus:
                focused = lane
                break
        if not focused and self._agents:
            focused = list(self._agents.values())[0]

        if focused:
            if not focused.show_thinking:
                focused.show_thinking = True
                self.notify(f"Thinking: {focused.agent_name}", severity="information")
            else:
                for lane in self._agents.values():
                    lane.show_thinking = True
                self.show_thinking_all = True
                self.notify("Thinking: all agents", severity="information")
        else:
            self.notify("No agents connected", severity="warning")

    def action_toggle_thinking_all(self) -> None:
        """Toggle thinking for all agents."""
        self.show_thinking_all = not self.show_thinking_all
        for lane in self._agents.values():
            lane.show_thinking = self.show_thinking_all
        state = "visible" if self.show_thinking_all else "hidden"
        self.notify(f"Thinking: {state} for all agents", severity="information")

    def action_show_spawn(self) -> None:
        """Open the spawn agent dialog."""
        self.push_screen(SpawnDialog(), callback=self._on_spawn_result)

    def _on_spawn_result(self, result: SpawnDialog.Spawn | None) -> None:
        if result is None:
            return
        self.post_message(result)

    def action_new_task(self) -> None:
        """Create a new task."""
        try:
            bottom_input = self.query_one("#bb-input", Input)
            bottom_input.focus()
            bottom_input.value = "/task "
        except Exception:
            pass

    def action_detail_view(self) -> None:
        """Expand focused agent to full-screen detail view."""
        focused_name = None
        focused_lane = None
        for name, lane in self._agents.items():
            if lane.has_focus:
                focused_name = name
                focused_lane = lane
                break

        if not focused_lane:
            self.notify("Focus an agent first", severity="warning")
            return

        worker = self._agent_workers.get(focused_name) if focused_name else None
        session_id = worker.config.session_id if worker else ""

        detail = DetailScreen(
            lane=focused_lane,
            session_id=session_id,
            context_manager=self.context_manager,
        )
        self.push_screen(detail)

    def action_switch_workspace(self) -> None:
        """Open workspace switcher."""
        try:
            switcher = self.query_one(WorkspaceSwitcher)
            switcher.show(cwd=self.cwd)
        except Exception as e:
            self.notify(f"Workspace switcher error: {e}", severity="error")

    def action_view_permissions(self) -> None:
        """Show pending permissions."""
        try:
            modal = self.query_one(PermissionModal)
            for name, worker in self._agent_workers.items():
                perm = worker.pending_permission
                if perm is not None:
                    modal._pending_request = perm
                    modal._request_id = perm.request_id
                    modal._agent_name = perm.agent_name
                    modal._tool_name = perm.tool_name
                    modal._description = perm.description
                    modal._input_preview = perm.preview[:500]
                    modal.set_class(True, "visible")
                    modal.refresh()
                    return
            self.notify("No pending permissions", severity="information")
        except Exception:
            self.notify("No pending permissions", severity="information")

    def action_fuzzy_find(self) -> None:
        """Open fuzzy finder."""
        try:
            finder = self.query_one(FuzzyFinder)
            finder.show(cwd=self.cwd, tasks=self._tasks)
        except Exception as e:
            self.notify(f"Fuzzy finder error: {e}", severity="error")

    def action_knowledge_graph(self) -> None:
        """Open knowledge graph."""
        try:
            graph = self.query_one(KnowledgeGraph)
            graph.show()
        except Exception as e:
            self.notify(f"Knowledge graph error: {e}", severity="error")

    def action_context_workbench(self) -> None:
        """Open context workbench."""
        try:
            wb = self.query_one("#context-workbench", ContextWorkbench)
            wb.context_manager = self.context_manager
            wb.show()
        except Exception as e:
            self.notify(f"Context workbench error: {e}", severity="error")

    def action_toggle_metrics(self) -> None:
        """Toggle agent metrics panel."""
        try:
            metrics = self.query_one(AgentMetrics)
            if metrics.has_class("visible"):
                metrics.hide()
                return

            focused_name = None
            focused_lane = None
            for name, lane in self._agents.items():
                if lane.has_focus:
                    focused_name = name
                    focused_lane = lane
                    break

            worker = self._agent_workers.get(focused_name) if focused_name else None

            metrics.show(
                worker=worker,
                agent_name=focused_lane.agent_name if focused_lane else "—",
                agent_model=focused_lane.agent_model if focused_lane else "—",
                session_id=worker.config.session_id if worker else "",
                cwd=worker.config.cwd if worker else self.cwd,
                agent_type=worker.config.agent_type if worker else "general",
                context_manager=self.context_manager,
            )
        except Exception as e:
            self.notify(f"Metrics error: {e}", severity="error")

    def action_cycle_layout(self) -> None:
        """Cycle through layout modes."""
        self.layout_mode = (self.layout_mode + 1) % 4
        modes = {0: "auto", 1: "1-col", 2: "2-col", 3: "grid"}
        mode = modes[self.layout_mode]
        self.notify(f"Layout: {mode}", severity="information")

    def action_toggle_pause(self) -> None:
        """Pause or resume the focused agent."""
        for name, lane in self._agents.items():
            if lane.has_focus and name in self._agent_workers:
                worker = self._agent_workers[name]
                if worker.status.name == "RUNNING":
                    worker.pause()
                    lane.is_paused = True
                    self.notify(f"⏸ {name} paused", severity="warning")
                elif worker.status.name == "PAUSED":
                    worker.resume()
                    lane.is_paused = False
                    self.notify(f"▶ {name} resumed")
                return
        self.notify("Focus an active agent to pause", severity="warning")

    def action_kill_agent(self) -> None:
        """Kill the focused agent."""
        for name, lane in self._agents.items():
            if lane.has_focus and name in self._agent_workers:
                if getattr(lane, '_kill_pending', False):
                    lane._kill_pending = False
                    worker = self._agent_workers[name]
                    worker.kill()
                    lane.detach_worker()
                    self.notify(f"🔴 {name} killed", severity="error")
                else:
                    lane._kill_pending = True
                    self.notify(
                        f"⚠ Press Ctrl+X again to confirm kill [bold]{name}[/]",
                        severity="warning",
                    )
                    self.set_timer(3.0, lambda: setattr(lane, '_kill_pending', False))
                return
        self.notify("Focus an active agent to kill", severity="warning")

    def action_toggle_nodes(self) -> None:
        """Toggle node panel."""
        self.notify("Node panel not implemented in v2 yet", severity="information")

    def action_refresh_git(self) -> None:
        """Refresh git status."""
        try:
            git_panel = self.query_one("#git", GitPanel)
            git_panel.cwd = self.cwd
            git_panel.refresh_git()
            self.notify("Git status refreshed", severity="information")
        except Exception:
            pass

    def action_command_palette(self) -> None:
        """Open the command palette."""
        try:
            palette = self.query_one(CommandPalette)
            palette.show()
        except Exception:
            pass

    def action_open_chat(self) -> None:
        """Open chat screen for the selected agent."""
        focused_name = None
        focused_lane = None
        for name, lane in self._agents.items():
            if lane.has_focus:
                focused_name = name
                focused_lane = lane
                break

        if focused_name and focused_name in self._agent_workers:
            worker = self._agent_workers[focused_name]
            push_chat_screen(
                self,
                agent_name=focused_name,
                model=worker.config.model,
                session_id=worker.config.session_id,
                cwd=worker.config.cwd or self.cwd,
                agent_type=worker.config.agent_type,
                worker=worker,
                context_manager=self.context_manager,
            )
        elif focused_lane:
            push_chat_screen(
                self,
                agent_name=focused_lane.agent_name,
                model=focused_lane.agent_model,
                cwd=self.cwd,
                agent_type="general",
                context_manager=self.context_manager,
            )
        else:
            push_chat_screen(
                self,
                agent_name="general",
                model="qwen3:14b",
                cwd=self.cwd,
                agent_type="general",
                context_manager=self.context_manager,
            )

    def action_dismiss_modal(self) -> None:
        """Dismiss any open modal."""
        try:
            self.query_one(PermissionModal).hide()
        except Exception:
            pass
        try:
            self.query_one(CommandPalette).hide()
        except Exception:
            pass

    def action_show_help(self) -> None:
        """Show keyboard shortcut reference."""
        self.push_screen(HelpScreen())

    # ─── Message Handlers ──────────────────────────────────────

    @on(SpawnDialog.Spawn)
    def on_spawn(self, event: SpawnDialog.Spawn) -> None:
        """Handle agent spawn from dialog."""
        agent_cwd = event.cwd or self.cwd
        session_id = event.session_id.strip() if event.session_id else ""
        if not session_id:
            from ai_workspace.core.sessions import SessionStore
            store = SessionStore()
            store.initialize()
            s = store.create_session(
                cwd=agent_cwd,
                model=event.model,
                label=f"{event.agent_type}: {event.task[:40]}",
            )
            store.close()
            session_id = s.id

        lane = self._spawn_agent_lane(
            agent_name=f"{event.agent_type}-{session_id[:6]}",
            model=event.model,
            node=agent_cwd[:30],
            task=event.task,
        )

        config = AgentConfig(
            lane_id=event.agent_type,
            agent_type=event.agent_type,
            project=event.project or None,
            model=event.model,
            session_id=session_id,
            cwd=agent_cwd,
            context_manager=self.context_manager,
        )
        worker = AgentWorker(config)
        worker_key = f"{event.agent_type}-{session_id[:8]}"
        self._agent_workers[worker_key] = worker
        lane.attach_worker(worker)

        asyncio.create_task(worker.start_loop(event.task))
        self.notify(
            f"Spawned: {event.agent_type} ({event.model}) @ {agent_cwd[:30]}",
            severity="information",
        )

        # Log to dashboard
        try:
            dashboard = self.query_one("#dashboard", DashboardView)
            dashboard.log_activity(
                f"Spawned {event.agent_type} agent: {event.task[:40]}",
                "success",
            )
        except Exception:
            pass

    @on(CommandPalette.Command)
    def on_command(self, event: CommandPalette.Command) -> None:
        """Handle command palette input."""
        cmd = event.command.strip()
        self.notify(f"Command: {cmd}", severity="information")

        if cmd.startswith("spawn"):
            parts = cmd.split()
            agent_type = "coding"
            task = "New task"
            model = "claude-3.7"
            for i, p in enumerate(parts[1:], 1):
                if p == "--task" and i + 1 < len(parts):
                    task = " ".join(parts[i + 1:]).lstrip('"').rstrip('"')
                    break
                elif p == "--model" and i + 1 < len(parts):
                    model = parts[i + 1]
                elif not p.startswith("--") and i == 1:
                    agent_type = p
            self._spawn_agent_lane(agent_type, model=model, node="local", task=task)
        elif cmd.startswith("task"):
            task_title = cmd[5:].strip().lstrip('"').rstrip('"')
            self._tasks.append({
                "id": f"t{len(self._tasks)+1}",
                "title": task_title,
                "status": "notstarted",
                "agent": "",
                "progress": 0,
            })
            self._refresh_tasks()
        elif cmd in ("quit", "q"):
            self.exit()
        elif cmd.startswith("cd "):
            new_dir = cmd[3:].strip()
            from pathlib import Path as P
            p = P(new_dir).expanduser().resolve()
            if p.is_dir():
                self.cwd = str(p)
                try:
                    header = self.query_one("#header-bar", HeaderBar)
                    header.cwd = str(p)
                except Exception:
                    pass
                self.notify(f"📁 {self.cwd[:50]}", severity="information")
            else:
                self.notify(f"Not found: {new_dir}", severity="error")
        elif cmd.startswith("model "):
            new_model = cmd[6:].strip()
            self.notify(f"Model: {new_model} (applied to next spawn)", severity="information")

    @on(Input.Submitted, "#bb-input")
    def on_quick_input(self, event: Input.Submitted) -> None:
        """Handle input from the bottom bar."""
        text = event.value.strip()
        if not text:
            return
        event.input.value = ""

        if text.startswith("/task"):
            task_title = text[6:].strip().lstrip('"').rstrip('"')
            self._tasks.append({
                "id": f"t{len(self._tasks)+1}",
                "title": task_title or "New task",
                "status": "notstarted",
                "agent": "",
                "progress": 0,
            })
            self._refresh_tasks()
            self.notify(f"Task created: {task_title or 'New task'}")
        elif text.startswith(":"):
            try:
                palette = self.query_one(CommandPalette)
                palette.show()
                inp = palette.query_one("#cmd-input", Input)
                inp.value = text[1:]
            except Exception:
                pass
        else:
            # Auto-spawn general agent with the message
            lane = self._spawn_agent_lane(
                agent_name=f"quick-{text[:15].replace(' ', '-')}",
                model="qwen3:14b",
                node=self.cwd[:30],
                task=text[:60],
            )
            from ai_workspace.core.sessions import SessionStore
            store = SessionStore()
            store.initialize()
            s = store.create_session(cwd=self.cwd, model="qwen3:14b", label=text[:40])
            store.add_message(session_id=s.id, role="user", content=text)
            store.close()

            config = AgentConfig(
                lane_id=f"quick-{s.id[:6]}",
                agent_type="general",
                model="qwen3:14b",
                session_id=s.id,
                cwd=self.cwd,
                context_manager=self.context_manager,
            )
            worker = AgentWorker(config)
            worker_key = f"quick-{s.id[:8]}"
            self._agent_workers[worker_key] = worker
            lane.attach_worker(worker)
            asyncio.create_task(worker.start_loop(text))
            self.notify(f"Auto-spawned agent @ {self.cwd[:30]}")

    def _refresh_tasks(self) -> None:
        """Refresh task displays across views."""
        try:
            dashboard = self.query_one("#dashboard", DashboardView)
            dashboard.update_tasks(self._tasks)
        except Exception:
            pass
        try:
            tasks_view = self.query_one("#tasks", TasksView)
            tasks_view.update_tasks(self._tasks)
        except Exception:
            pass
        try:
            header = self.query_one("#header-bar", HeaderBar)
            header.tasks_total = len(self._tasks)
            header.tasks_active = len([t for t in self._tasks if t.get("status") == "ongoing"])
        except Exception:
            pass

    @on(WorkspaceSwitcher.Selected)
    def on_workspace_selected(self, event: WorkspaceSwitcher.Selected) -> None:
        """Handle workspace selection."""
        entry = event.entry
        path = entry.path

        if not path or not Path(path).is_dir():
            self.notify(f"Directory not found: {path}", severity="error")
            return

        self.cwd = str(Path(path).resolve())

        try:
            header = self.query_one("#header-bar", HeaderBar)
            header.cwd = self.cwd
            import subprocess as sp
            result = sp.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, cwd=self.cwd, timeout=2,
            )
            if result.returncode == 0 and result.stdout.strip():
                header.git_branch = result.stdout.strip()
            else:
                header.git_branch = ""
        except Exception:
            pass

        try:
            self._load_data()
        except Exception:
            pass

        # Update git panel cwd
        try:
            git_panel = self.query_one("#git", GitPanel)
            git_panel.cwd = self.cwd
            git_panel.refresh_git()
        except Exception:
            pass

        self.notify(f"📁 Switched to {self.cwd[:50]}", severity="information")

    @on(FuzzyFinder.Selected)
    def on_fuzzy_selected(self, event: FuzzyFinder.Selected) -> None:
        """Handle fuzzy finder selection."""
        r = event.result
        if r.kind == ResultKind.FILE:
            path = r.data.get("path", "")
            self.notify(f"📄 {path}", severity="information")
        elif r.kind == ResultKind.TASK:
            task_id = r.data.get("task_id", "")
            self.notify(f"Task: {task_id}", severity="information")
        elif r.kind == ResultKind.SESSION:
            session_id = r.data.get("session_id", "")
            self.notify(f"Session: {session_id[:12]}…", severity="information")
        elif r.kind == ResultKind.COMMAND:
            command = r.data.get("command", r.label)
            self.post_message(CommandPalette.Command(command))

    @on(PermissionModal.Verdict)
    def on_permission_verdict(self, event: PermissionModal.Verdict) -> None:
        """Handle permission verdict."""
        self.notify(
            f"Permission: {event.behavior} for {event.request_id[:12]}...",
            severity="information",
        )

    # ─── Dashboard Quick Actions ───────────────────────────────

    @on(Button.Pressed, "#qa-spawn")
    def on_qa_spawn(self, event: Button.Pressed) -> None:
        self.action_show_spawn()

    @on(Button.Pressed, "#qa-task")
    def on_qa_task(self, event: Button.Pressed) -> None:
        self.action_new_task()

    @on(Button.Pressed, "#qa-search")
    def on_qa_search(self, event: Button.Pressed) -> None:
        self.action_fuzzy_find()

    @on(Button.Pressed, "#qa-workspace")
    def on_qa_workspace(self, event: Button.Pressed) -> None:
        self.action_switch_workspace()

    # ─── Agents View Actions ───────────────────────────────────

    @on(Button.Pressed, "#av-spawn")
    def on_av_spawn(self, event: Button.Pressed) -> None:
        self.action_show_spawn()

    @on(Button.Pressed, "#av-pause")
    def on_av_pause(self, event: Button.Pressed) -> None:
        self.action_toggle_pause()

    @on(Button.Pressed, "#av-kill")
    def on_av_kill(self, event: Button.Pressed) -> None:
        self.action_kill_agent()

    @on(Button.Pressed, "#av-chat")
    def on_av_chat(self, event: Button.Pressed) -> None:
        self.action_open_chat()

    # ─── Tasks View Actions ────────────────────────────────────

    @on(Button.Pressed, "#tv-new")
    def on_tv_new(self, event: Button.Pressed) -> None:
        self.action_new_task()

    @on(Button.Pressed, "#tv-toggle")
    def on_tv_toggle(self, event: Button.Pressed) -> None:
        try:
            tasks_view = self.query_one("#tasks", TasksView)
            task = tasks_view.get_selected_task()
            if task:
                task_id = task.get("id")
                current_status = task.get("status", "notstarted")
                new_status = "completed" if current_status != "completed" else "notstarted"
                # Update task
                for t in self._tasks:
                    if t.get("id") == task_id:
                        t["status"] = new_status
                        t["progress"] = 100 if new_status == "completed" else 0
                        break
                self._refresh_tasks()
                self.notify(f"Task {task_id}: {new_status}")
        except Exception:
            pass

    @on(Button.Pressed, "#tv-delete")
    def on_tv_delete(self, event: Button.Pressed) -> None:
        try:
            tasks_view = self.query_one("#tasks", TasksView)
            task = tasks_view.get_selected_task()
            if task:
                task_id = task.get("id")
                self._tasks = [t for t in self._tasks if t.get("id") != task_id]
                self._refresh_tasks()
                self.notify(f"Deleted task {task_id}")
        except Exception:
            pass

    # ─── Demo: Simulate agent activity ─────────────────────────

    def key_f5(self) -> None:
        """F5: Simulate agent activity for demo."""
        import random
        coding = self._agents.get("coding")
        if coding:
            actions = [
                "> Running: go build ./...",
                "  ✅ Build successful",
                "> Running: go vet ./...",
                "  No issues found",
            ]
            coding.append_output(random.choice(actions))
            coding.task_progress = min(100, coding.task_progress + random.randint(2, 8))
            if coding.task_progress >= 100:
                coding.task_status = "completed"
                coding.append_output("✅ Task completed successfully.")
                self.notify("coding: task completed!", severity="information")


def run_tui():
    """Entry point for `aiw tui` command."""
    app = AIWorkspaceApp()
    app.run()


if __name__ == "__main__":
    run_tui()
