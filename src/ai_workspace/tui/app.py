"""
AI Workspace TUI — Agent Operations Center.

Layout:
┌─ StatusBar ───────────────────────────────────────────────────────────────────┐
│ aiw  ws:personal  claude-3.7  tasks:3/12  agents:2⚡  14:32                    │
├──────────┬───────────────────────┬────────────────────────────────────────────┤
│ TASKS    │  AGENT LANE 1         │  AGENT LANE 2                               │
│          │                       │                                             │
│ ● task1  │  > Live output...     │  > Live output...                           │
│ ○ task2  │                       │                                             │
│ ✅ task3 │  ── thinking ──       │  ── thinking ──                             │
│          │  (dimmed, togglable)  │  (dimmed, togglable)                        │
│ [New +]  │                       │                                             │
├──────────┴───────────────────────┴────────────────────────────────────────────┤
│ :spawn coding --task "Fix bug"                          [^T] think [^S] spawn  │
└────────────────────────────────────────────────────────────────────────────────┘

Keybindings:
  Tab         — cycle focus (tasks → lanes → command)
  Ctrl+K      — toggle task panel
  Ctrl+T      — toggle thinking (once=focused, twice=all, again=hide)
  Ctrl+S      — spawn agent dialog
  Ctrl+N      — new task
  Ctrl+D      — detail view (expand focused lane)
  Ctrl+W      — switch workspace
  Ctrl+P      — view pending permissions
  Ctrl+F      — fuzzy find
  Ctrl+G      — knowledge graph
  Ctrl+E      — context workbench
  Ctrl+L      — cycle layout (1-col, 2-col, grid)
  :           — command palette
  a/A/d/Esc   — permission modal (when visible)
  !prefix     — interrupt agent (clear context, fresh start)
  q           — quit
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListView,
    Static,
)

from ai_workspace.tui.worker import AgentConfig, AgentWorker
from ai_workspace.agents.message_queue import MessagePriority
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


class SpawnDialog(Static):
    """Dialog for spawning a new agent."""

    DEFAULT_CSS = """
    SpawnDialog {
        display: none;
        layer: overlay;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
        width: 50;
        height: auto;
        dock: top;
        offset-x: 15;
        offset-y: 5;
    }
    SpawnDialog.visible {
        display: block;
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
        yield Label("[bold]Spawn Agent[/]", id="spawn-title")
        yield Input(placeholder="agent type: coding, research, general...", id="spawn-type")
        yield Input(placeholder="model (default: qwen3:14b)", id="spawn-model")
        yield Input(placeholder="directory (default: current)", id="spawn-dir")
        yield Input(placeholder="project (optional)", id="spawn-project")
        yield Input(placeholder="session ID (optional, for persistent history)", id="spawn-session")
        yield Input(placeholder="task description...", id="spawn-task")
        with Horizontal():
            yield Button("Spawn", id="btn-spawn-confirm", variant="primary")
            yield Button("Cancel", id="btn-spawn-cancel")

    def show(self) -> None:
        self.set_class(True, "visible")
        try:
            self.query_one("#spawn-type", Input).focus()
        except Exception:
            pass

    def hide(self) -> None:
        self.set_class(False, "visible")

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
        self.post_message(self.Spawn(agent_type, model, project, task, session_id, cwd))
        self.hide()

    @on(Button.Pressed, "#btn-spawn-cancel")
    def on_cancel(self) -> None:
        self.hide()


class AIWorkspaceApp(App):
    """Agent Operations Center — primary human interface for aiw."""

    TITLE = "AI Workspace"
    SUB_TITLE = "Agent Operations Center"

    CSS = """
    /* ── Global Layout ── */
    #main-container {
        height: 1fr;
    }
    
    #center-area {
        height: 1fr;
    }
    
    /* ── Task Panel ── */
    #task-panel {
        width: 28;
        height: 1fr;
        border: solid $primary-background;
        background: $surface;
        display: block;
    }
    #task-panel.hidden {
        display: none;
    }
    #task-panel-inner {
        height: 1fr;
    }
    #task-panel-title {
        padding: 1 2;
        text-style: bold;
        background: $boost;
    }
    #task-filters {
        padding: 0 1;
    }
    #task-filters Button {
        min-width: 0;
        padding: 0 1;
    }
    #task-list {
        height: 1fr;
    }
    
    /* ── Agent Lanes ── */
    .lane-container {
        height: 1fr;
        border: solid $primary-background;
        margin: 0 1;
    }
    .lane-container:focus-within {
        border: solid $accent;
    }
    
    AgentLane {
        height: 1fr;
        padding: 0 1;
    }
    
    #lane-header {
        padding: 1 0;
        text-style: bold;
        background: $boost;
    }
    
    #lane-output-container {
        height: 1fr;
        overflow-y: auto;
    }
    
    #lane-thinking-container {
        height: auto;
        max-height: 40%;
        border-top: dashed $warning;
        margin-top: 1;
    }
    #lane-thinking-container.hidden {
        display: none;
    }
    
    /* ── Command Bar ── */
    #command-bar {
        dock: bottom;
        height: 2;
        padding: 0 2;
        background: $boost;
        border-top: solid $primary-background;
    }
    #keybinding-hints {
        width: 1fr;
        text-style: dim;
    }
    #quick-input {
        width: 30;
    }
    
    /* ── Node Panel ── */
    #node-panel {
        height: auto;
        max-height: 10;
        border: solid $primary-background;
        margin: 1;
        display: block;
    }
    #node-panel.hidden {
        display: none;
    }
    
    /* ── Utility ── */
    .hidden {
        display: none;
    }
    
    Screen {
        layers: base overlay;
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
        ("space", "toggle_pause", "Pause/Resume"),
        ("ctrl+x", "kill_agent", "Kill"),
        ("ctrl+shift+n", "toggle_nodes", "Nodes"),
        ("ctrl+c", "quit", "Quit"),
        ("q", "quit", "Quit"),
        (":", "command_palette", "Command"),
        ("escape", "dismiss_modal", "Dismiss"),
    ]

    show_thinking_all: reactive[bool] = reactive(False)
    current_layout: reactive[str] = reactive("auto")  # auto, 1col, 2col, grid
    layout_mode: reactive[int] = reactive(0)  # 0=auto, 1=1col, 2=2col, 3=grid

    def __init__(self) -> None:
        super().__init__()
        self.cwd = str(Path.cwd())
        self._agents: dict[str, AgentLane] = {}
        self._agent_workers: dict[str, AgentWorker] = {}
        self._tasks: list[dict] = []
        self._focus_order = ["task-panel", "lanes", "command"]
        self._focus_index = 0

    def compose(self) -> ComposeResult:
        """Build the agent operations center layout."""
        # Status bar (top)
        yield StatusBar(id="status-bar")

        # Main content
        with Horizontal(id="main-container"):
            # Task panel (left)
            yield TaskPanel(id="task-panel")

            # Center: agent lanes (dynamically populated)
            with Horizontal(id="center-area"):
                with VerticalScroll(id="lanes-container", classes="lane-container"):
                    yield Label("[dim]No agents connected. Use Ctrl+S or :spawn to start.[/]", id="empty-lanes")

        # Node panel (collapsible, below lanes)
        yield NodePanel(id="node-panel", classes="hidden")

        # Command bar (bottom)
        with Horizontal(id="command-bar"):
            yield Static(
                "[dim][Tab] focus  [^S] spawn  [Space] pause  [^X] kill"
                "  :cmd  :cd ~/dir  :sessions  [^Q] quit[/]",
                id="keybinding-hints",
            )
            yield Input(placeholder="Type message or command...", id="quick-input")

        # Overlays (layer=overlay)
        yield PermissionModal(id="permission-modal")
        yield CommandPalette(id="command-palette")
        yield SpawnDialog(id="spawn-dialog")
        yield Toast(id="toast")

    # ─── Lifecycle ──────────────────────────────────────────────

    def on_mount(self) -> None:
        """Initialize from DB or start empty."""
        try:
            self._load_data()
        except Exception:
            pass
        self.set_interval(60, self._tick_clock)

    def _tick_clock(self) -> None:
        """Refresh the status bar clock."""
        try:
            self.query_one(StatusBar).refresh()
        except Exception:
            pass

    def _load_data(self) -> None:
        """Load real data from knowledge store."""
        metrics = load_metrics()
        tasks = load_tasks()
        status = self.query_one(StatusBar)
        status.cwd = self.cwd
        status.model = "qwen3:14b"
        status.tasks_active = metrics.get("tasks_active", 0)
        status.tasks_total = metrics.get("tasks_total", 0)
        status.agents_online = 0
        status.agents_total = 0
        status.cache_entries = metrics.get("cache_entries", 0)
        status.cache_hits = metrics.get("cache_hits", 0)
        status.tokens_saved = metrics.get("tokens_saved", 0)
        status.today_cost = metrics.get("today_cost", 0.0)
        status.month_cost = metrics.get("month_cost", 0.0)
        status.source_domains = metrics.get("source_domains", 0)
        
        # Detect git branch
        try:
            import subprocess
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, cwd=self.cwd, timeout=2
            )
            if result.returncode == 0 and result.stdout.strip():
                status.git_branch = result.stdout.strip()
        except Exception:
            pass
        
        task_panel = self.query_one(TaskPanel)
        task_panel.update_tasks(tasks)
        self._tasks = tasks

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

        # Remove empty state if present
        try:
            empty = self.query_one("#empty-lanes", Label)
            empty.remove()
        except Exception:
            pass

        # Mount the lane
        try:
            container = self.query_one("#lanes-container", VerticalScroll)
            container.mount(lane)
        except Exception:
            pass

        self._agents[agent_name] = lane
        self._update_layout()
        return lane

    def _update_layout(self) -> None:
        """Adjust lane widths based on agent count."""
        count = len(self._agents)
        lanes = list(self._agents.values())
        for i, lane in enumerate(lanes):
            lane.styles.width = f"{100 // max(count, 1)}%"

        # Update status bar
        try:
            status = self.query_one(StatusBar)
            status.agents_online = count
            status.agents_total = count
            status.refresh()
        except Exception:
            pass

    # ─── Keybinding Actions ────────────────────────────────────

    def action_cycle_focus(self) -> None:
        """Cycle focus between task panel, lanes, and command bar."""
        try:
            task_panel = self.query_one(TaskPanel)
            lanes_container = self.query_one("#lanes-container", VerticalScroll)
            quick_input = self.query_one("#quick-input", Input)

            if task_panel.has_focus:
                if self._agents:
                    first_lane = list(self._agents.values())[0]
                    first_lane.focus()
                else:
                    quick_input.focus()
            elif any(l.has_focus for l in self._agents.values()):
                quick_input.focus()
            else:
                task_panel.focus()
        except Exception:
            pass

    def action_toggle_tasks(self) -> None:
        """Toggle task panel visibility."""
        try:
            panel = self.query_one(TaskPanel)
            panel.set_class(not panel.has_class("hidden"), "hidden")
        except Exception:
            pass

    def action_toggle_thinking(self) -> None:
        """Toggle thinking for the focused agent, first agent if none focused, or all if toggled twice."""
        if self.show_thinking_all:
            for lane in self._agents.values():
                lane.show_thinking = False
            self.show_thinking_all = False
            self.notify("Thinking: hidden", severity="information")
            return

        # Find focused agent, or fall back to first agent
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
        try:
            dialog = self.query_one(SpawnDialog)
            dialog.show()
        except Exception:
            self.notify("Spawn dialog not available", severity="warning")

    def action_new_task(self) -> None:
        """Create a new task."""
        try:
            quick_input = self.query_one("#quick-input", Input)
            quick_input.focus()
            quick_input.value = "/task "
        except Exception:
            pass

    def action_detail_view(self) -> None:
        """Expand focused agent to detail view."""
        self.notify("Detail view — not yet implemented", severity="information")

    def action_switch_workspace(self) -> None:
        """Switch workspace."""
        self.notify("Workspace switcher — not yet implemented", severity="information")

    def action_view_permissions(self) -> None:
        """View pending permissions."""
        self.notify("No pending permissions", severity="information")

    def action_fuzzy_find(self) -> None:
        """Open fuzzy find."""
        self.notify("Fuzzy find — not yet implemented", severity="information")

    def action_knowledge_graph(self) -> None:
        """Open knowledge graph."""
        self.notify("Knowledge graph — not yet implemented", severity="information")

    def action_context_workbench(self) -> None:
        """Open context workbench."""
        self.notify("Context workbench — not yet implemented", severity="information")

    def action_cycle_layout(self) -> None:
        """Cycle through layout modes."""
        self.notify("Layout cycling — not yet implemented", severity="information")

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
        self.notify("Focus an active agent lane to pause", severity="warning")

    def action_kill_agent(self) -> None:
        """Kill the focused agent."""
        for name, lane in self._agents.items():
            if lane.has_focus and name in self._agent_workers:
                worker = self._agent_workers[name]
                worker.kill()
                lane.detach_worker()
                self.notify(f"🔴 {name} killed", severity="error")
                return
        self.notify("Focus an active agent lane to kill", severity="warning")

    def action_toggle_nodes(self) -> None:
        """Toggle node panel visibility."""
        try:
            panel = self.query_one(NodePanel)
            panel.set_class(not panel.has_class("hidden"), "hidden")
        except Exception:
            pass

    def action_command_palette(self) -> None:
        """Open the command palette."""
        try:
            palette = self.query_one(CommandPalette)
            palette.show()
        except Exception:
            pass

    def action_dismiss_modal(self) -> None:
        """Dismiss any open modal."""
        try:
            self.query_one(PermissionModal).hide()
        except Exception:
            pass
        try:
            self.query_one(SpawnDialog).hide()
        except Exception:
            pass
        try:
            self.query_one(CommandPalette).hide()
        except Exception:
            pass

    # ─── Message Handlers ──────────────────────────────────────

    @on(TaskPanel.TaskSelected)
    def on_task_selected(self, event: TaskPanel.TaskSelected) -> None:
        """When a task is selected, highlight its agent lane."""
        task = next((t for t in self._tasks if t.get("id") == event.task_id), None)
        if task and task.get("agent") in self._agents:
            lane = self._agents[task["agent"]]
            lane.focus()
            self.notify(f"Focused: {task['agent']} — {task['title'][:40]}")

    @on(PermissionModal.Verdict)
    def on_permission_verdict(self, event: PermissionModal.Verdict) -> None:
        """Handle permission verdict."""
        self.notify(
            f"Permission: {event.behavior} for {event.request_id[:12]}...",
            severity="information",
        )

    @on(CommandPalette.Command)
    def on_command(self, event: CommandPalette.Command) -> None:
        """Handle command palette input."""
        cmd = event.command.strip()
        self.notify(f"Command: {cmd}", severity="information")

        # Basic command parsing
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
            task_panel = self.query_one(TaskPanel)
            self._tasks.append({
                "id": f"t{len(self._tasks)+1}",
                "title": task_title,
                "status": "notstarted",
                "agent": "",
                "progress": 0,
            })
            task_panel.update_tasks(self._tasks)
        elif cmd == "thinking on":
            self.action_toggle_thinking_all()
            if not self.show_thinking_all:
                self.action_toggle_thinking_all()
        elif cmd == "thinking off":
            if self.show_thinking_all:
                self.action_toggle_thinking_all()
        elif cmd in ("quit", "q"):
            self.exit()
        elif cmd.startswith("sessions"):
            # List recent sessions
            from ai_workspace.core.sessions import SessionStore
            store = SessionStore()
            store.initialize()
            sessions = store.list_sessions(limit=5)
            store.close()
            if sessions:
                for s in sessions:
                    self.notify(
                        f"{s['id'][:8]}… {s.get('label','')[:20]} "
                        f"{s.get('entry_count',0)}e",
                        severity="information",
                    )
            else:
                self.notify("No sessions yet", severity="warning")
        elif cmd.startswith("model "):
            new_model = cmd[6:].strip()
            self.notify(f"Model: {new_model} (applied to next spawn)", severity="information")
        elif cmd.startswith("cd "):
            new_dir = cmd[3:].strip()
            from pathlib import Path as P
            p = P(new_dir).expanduser().resolve()
            if p.is_dir():
                self.cwd = str(p)
                try:
                    self.query_one(StatusBar).cwd = str(p)
                except Exception:
                    pass
                self.notify(f"📁 {self.cwd[:50]}", severity="information")
            else:
                self.notify(f"Not found: {new_dir}", severity="error")

    @on(SpawnDialog.Spawn)
    def on_spawn(self, event: SpawnDialog.Spawn) -> None:
        """Handle agent spawn from dialog — create real AgentWorker with session."""
        # Use provided dir or TUI's default
        agent_cwd = event.cwd or self.cwd
        
        # Auto-create session if none provided
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
        )
        worker = AgentWorker(config)
        worker_key = f"{event.agent_type}-{session_id[:8]}"
        self._agent_workers[worker_key] = worker
        lane.attach_worker(worker)
        
        asyncio.create_task(worker.start_loop(event.task))
        self.notify(
            f"Spawned: {event.agent_type} ({event.model}) @ {agent_cwd[:30]}"
            + (f" — session {session_id[:8]}" if session_id else "")
            + " | Loop mode — agent stays alive for follow-ups",
            severity="information",
        )

    @on(Input.Submitted, "#quick-input")
    def on_quick_input(self, event: Input.Submitted) -> None:
        """Handle input from the command bar."""
        text = event.value.strip()
        if not text:
            return
        event.input.value = ""

        if text.startswith("/task"):
            task_title = text[6:].strip().lstrip('"').rstrip('"')
            task_panel = self.query_one(TaskPanel)
            self._tasks.append({
                "id": f"t{len(self._tasks)+1}",
                "title": task_title or "New task",
                "status": "notstarted",
                "agent": "",
                "progress": 0,
            })
            task_panel.update_tasks(self._tasks)
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
            # Check if any agent lane is focused and has an active worker
            focused = None
            focused_name = None
            for name, lane in self._agents.items():
                if lane.has_focus:
                    focused = lane
                    focused_name = name
                    break
            
            if focused and focused_name and focused_name in self._agent_workers:
                # Reply to focused agent (loop mode or one-shot)
                worker = self._agent_workers[focused_name]
                
                # Check for interrupt prefix (!)
                if text.startswith("!"):
                    priority = MessagePriority.INTERRUPT
                    clean_text = text[1:].strip()
                    if not clean_text:
                        self.notify("Interrupt requires a message after '!'", severity="warning")
                        return
                    text = clean_text
                else:
                    priority = MessagePriority.NORMAL
                
                if worker.config.session_id:
                    try:
                        from ai_workspace.core.sessions import SessionStore
                        store = SessionStore()
                        store.initialize()
                        store.add_message(session_id=worker.config.session_id, role="user", content=text)
                        store.close()
                    except Exception:
                        pass
                
                asyncio.create_task(worker.send_message(text, priority=priority))
                
                if priority >= MessagePriority.INTERRUPT:
                    self.notify(f"⚡ Interrupt sent to {focused_name}", severity="warning")
                else:
                    pending = worker.pending_message_count
                    queue_info = f" [{pending} pending]" if pending > 0 else ""
                    self.notify(f"📨 Sent to {focused_name}{queue_info}")
            elif focused:
                # Focused lane but no active worker (completed/dead)
                focused.append_output(f"> [bold]You:[/] {text}")
                self.notify(f"Note: agent not running, message logged")
            else:
                # No agent focused → auto-spawn a general agent
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
                )
                worker = AgentWorker(config)
                worker_key = f"quick-{s.id[:8]}"
                self._agent_workers[worker_key] = worker
                lane.attach_worker(worker)
                asyncio.create_task(worker.start_loop(text))
                self.notify(f"Auto-spawned agent @ {self.cwd[:30]} | Loop mode")

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
                "> Committing changes...",
                "  git commit -m 'fix: validate JWT expiry in auth middleware'",
                "> Pushing to remote...",
                "  git push origin fix/auth-middleware-expiry",
            ]
            coding.append_output(random.choice(actions))
            coding.task_progress = min(100, coding.task_progress + random.randint(2, 8))
            if coding.task_progress >= 100:
                coding.task_status = "completed"
                coding.append_output("✅ Task completed successfully.")
                self.notify("coding: task completed!", severity="information")

        research = self._agents.get("research")
        if research:
            actions = [
                "> Filtering results by Playwright support...",
                "> Checking GitHub stars and recent activity...",
                "> Comparing API documentation quality...",
                "> Generating comparison table...",
            ]
            research.append_output(random.choice(actions))
            research.task_progress = min(100, research.task_progress + random.randint(3, 10))
            if research.task_progress >= 100:
                research.task_status = "completed"
                research.append_output("✅ Research complete. Report generated.")
                self.notify("research: task completed!", severity="information")


def run_tui():
    """Entry point for `aiw tui` command."""
    app = AIWorkspaceApp()
    app.run()


if __name__ == "__main__":
    run_tui()
