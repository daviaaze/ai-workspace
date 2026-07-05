"""Custom Textual widgets — agent output lane, permission modal, toast, command palette."""

from __future__ import annotations

import asyncio
import logging
import time

from rich.panel import Panel
from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import (
    Input,
    Label,
    Static,
)

log = logging.getLogger("aiw.tui.widgets")


class AgentLane(Static):
    """Live output stream for a single agent. Shows task, status, runtime, and output."""

    can_focus = True

    agent_name: reactive[str] = reactive("agent")
    agent_model: reactive[str] = reactive("")
    agent_node: reactive[str] = reactive("")
    current_task: reactive[str] = reactive("")
    task_status: reactive[str] = reactive("notstarted")
    task_progress: reactive[float] = reactive(0.0)
    show_thinking: reactive[bool] = reactive(False)
    is_paused: reactive[bool] = reactive(False)
    is_offline: reactive[bool] = reactive(False)
    has_permission_pending: reactive[bool] = reactive(False)
    pending_messages: reactive[int] = reactive(0)

    MAX_LINES = 500

    def __init__(
        self,
        agent_name: str = "agent",
        agent_model: str = "",
        agent_node: str = "",
        current_task: str = "",
        task_status: str = "notstarted",
        task_progress: float = 0.0,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.agent_name = agent_name
        self.agent_model = agent_model
        self.agent_node = agent_node
        self.current_task = current_task
        self.task_status = task_status
        self.task_progress = task_progress
        self._output_lines: list[str] = []
        self._thinking_lines: list[str] = []
        self._worker = None
        self._drain_timer = None
        self._start_time: float | None = None
        self._runtime_timer = None
        self._kill_pending = False

    def attach_worker(self, worker) -> None:
        self._worker = worker
        self.task_status = "ongoing"
        self._start_time = time.time()
        self._drain_timer = self.set_interval(0.05, self._drain_queue)
        if self._runtime_timer is None:
            self._runtime_timer = self.set_interval(30, self._update_header)

    def detach_worker(self) -> None:
        if self._drain_timer:
            self._drain_timer.stop()
            self._drain_timer = None
        if self._runtime_timer:
            self._runtime_timer.stop()
            self._runtime_timer = None
        self._worker = None

    async def _drain_queue(self) -> None:
        if not self._worker:
            return
        for _ in range(20):
            try:
                line = self._worker.queue.get_nowait()
                self.append_output(line)
            except asyncio.QueueEmpty:
                break

        if hasattr(self._worker, "pending_message_count"):
            count = self._worker.pending_message_count
            if count != self.pending_messages:
                self.pending_messages = count

        if self._worker.pending_permission:
            self._show_permission(self._worker.pending_permission)

        status_map = {
            "RUNNING": "ongoing",
            "PAUSED": "blocked",
            "COMPLETED": "completed",
            "ERROR": "rejected",
            "KILLED": "rejected",
            "IDLE": "ongoing",
        }
        new_status = status_map.get(self._worker.status.name, self.task_status)
        if new_status != self.task_status:
            self.task_status = new_status

    def _show_permission(self, request) -> None:
        try:
            app = self.app
            if app is None:
                request.resolve(None)
                return
            from ai_workspace.tui.widgets import PermissionModal

            modal = app.query_one(PermissionModal)
            modal.show_request(
                request_id=request.request_id,
                agent_name=request.agent_name,
                task_title=request.description[:60],
                tool_name=request.tool_name,
                description=request.description,
                input_preview=request.preview[:500],
            )
            modal._pending_request = request
        except Exception as e:
            log.warning("Permission modal unavailable: %s", e)
            try:
                request.resolve(None)
            except Exception:
                pass

    def compose(self) -> ComposeResult:
        with Vertical(id=f"lane-{self.agent_name}"):
            yield Label(self._render_header(), id="lane-header")
            yield VerticalScroll(Label("", id="lane-output"), id="lane-output-container")
            yield VerticalScroll(
                Label("", id="lane-thinking"),
                id="lane-thinking-container",
                classes="hidden",
            )

    def _render_header(self) -> str:
        node_info = f" [{self.agent_node}]" if self.agent_node else ""

        status_label = {
            "ongoing": "[$success]running[/]",
            "notstarted": "[$text 40%]pending[/]",
            "completed": "[$success]done[/]",
            "blocked": "[$warning]paused[/]",
            "rejected": "[$error]stopped[/]",
        }.get(self.task_status, "[$text 40%]pending[/]")

        name = f"[bold]{self.agent_name}[/]"
        model = f" [$text 50%]{self.agent_model}[/]" if self.agent_model else ""
        task = f" [$text 70%]{self.current_task[:50]}[/]" if self.current_task else ""

        indicators = []
        if self.is_paused:
            indicators.append("[$warning]PAUSED[/]")
        if self.has_permission_pending:
            indicators.append("[$warning]AWAITING APPROVAL[/]")
        if self.pending_messages > 0:
            indicators.append(f"[$text 50%]{self.pending_messages} queued[/]")
        if self._start_time and self.task_status in ("ongoing", "notstarted"):
            elapsed = int(time.time() - self._start_time)
            if elapsed >= 0:
                m, s = divmod(elapsed, 60)
                if m >= 60:
                    h, m = divmod(m, 60)
                    indicators.append(f"[$text 50%]{h}:{m:02d}:{s:02d}[/]")
                else:
                    indicators.append(f"[$text 50%]{m}:{s:02d}[/]")

        indicator_str = "  ".join(indicators) if indicators else ""
        if indicator_str:
            indicator_str = "  " + indicator_str

        return f"{name}{model}{node_info}  {status_label}{task}{indicator_str}"

    def on_mount(self) -> None:
        self._refresh_output()
        self._refresh_thinking()

    def append_output(self, text: str) -> None:
        self._output_lines.append(text)
        if len(self._output_lines) > self.MAX_LINES:
            self._output_lines = self._output_lines[-self.MAX_LINES:]
        self._refresh_output()

    def append_thinking(self, text: str) -> None:
        self._thinking_lines.append(text)
        if len(self._thinking_lines) > self.MAX_LINES:
            self._thinking_lines = self._thinking_lines[-self.MAX_LINES:]
        if self.show_thinking:
            self._refresh_thinking()

    def _refresh_output(self) -> None:
        try:
            label = self.query_one("#lane-output", Label)
            label.update("\n".join(self._output_lines[-50:]))
        except NoMatches:
            pass

    def _refresh_thinking(self) -> None:
        try:
            label = self.query_one("#lane-thinking", Label)
            label.update("\n".join(
                f"[$text 60% italic]{line}[/]" for line in self._thinking_lines[-30:]
            ))
        except NoMatches:
            pass

    def watch_show_thinking(self, show: bool) -> None:
        try:
            container = self.query_one("#lane-thinking-container", VerticalScroll)
            container.set_class(not show, "hidden")
            if show:
                self._refresh_thinking()
        except NoMatches:
            pass

    def watch_is_offline(self) -> None:
        self._update_header()

    def watch_has_permission_pending(self) -> None:
        self._update_header()

    def watch_pending_messages(self) -> None:
        self._update_header()

    def watch_task_status(self) -> None:
        self._update_header()

    def watch_task_progress(self) -> None:
        self._update_header()

    def _update_header(self) -> None:
        try:
            header = self.query_one("#lane-header", Label)
            header.update(self._render_header())
        except NoMatches:
            pass


class PermissionModal(Static):
    """Modal for human approval of dangerous tool calls."""

    DEFAULT_CSS = """
    PermissionModal {
        display: none;
        layer: overlay;
        background: $surface;
        border: solid $warning 60%;
        padding: 1 2;
        width: 60;
        height: auto;
        dock: top;
        offset-x: 20;
        offset-y: 3;
    }
    PermissionModal.visible {
        display: block;
    }
    """

    class Verdict(Message):
        def __init__(self, request_id: str, behavior: str) -> None:
            super().__init__()
            self.request_id = request_id
            self.behavior = behavior

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._request_id: str = ""
        self._agent_name: str = ""
        self._tool_name: str = ""
        self._description: str = ""
        self._input_preview: str = ""
        self._pending_request = None

    def show_request(
        self,
        request_id: str,
        agent_name: str,
        task_title: str,
        tool_name: str,
        description: str = "",
        input_preview: str = "",
    ) -> None:
        self._request_id = request_id
        self._agent_name = agent_name
        self._tool_name = tool_name
        self._description = description
        self._input_preview = input_preview
        self.set_class(True, "visible")
        self.refresh()

    def hide(self) -> None:
        self.set_class(False, "visible")

    def render(self) -> Panel:
        if not self._request_id:
            return Panel("", title="Permission")
        body = (
            f"[bold]Agent:[/] {self._agent_name}\n"
            f"[bold]Action:[/] {self._tool_name}\n"
        )
        if self._description:
            body += f'  "{self._description}"\n'
        if self._input_preview:
            body += f"\n[$text 60%]{self._input_preview[:300]}[/]\n"
        body += (
            "\n"
            "[bold $primary][a][/] Allow once    "
            "[bold $success][A][/] Always allow    "
            "[bold $error][d][/] Deny    "
            "[$text 50%]Esc to dismiss[/]"
        )
        return Panel(body, title="Permission Required", border_style="orange1")

    def key_a(self) -> None:
        self._resolve("allow")

    def key_A(self) -> None:
        self._resolve("allow_always")

    def key_d(self) -> None:
        self._resolve("deny")

    def key_escape(self) -> None:
        self._resolve("deny")

    def _resolve(self, behavior: str) -> None:
        if self._pending_request:
            from ai_workspace.tui.permissions import PermissionVerdict
            verdict_map = {
                "allow": PermissionVerdict.ALLOW,
                "allow_always": PermissionVerdict.ALLOW_ALWAYS,
                "deny": PermissionVerdict.DENY,
            }
            self._pending_request.resolve(verdict_map.get(behavior, PermissionVerdict.DENY))
            self._pending_request = None
        elif self._request_id:
            self.post_message(self.Verdict(self._request_id, behavior))
        self.hide()


class Toast(Static):
    """Floating notification that auto-dismisses."""

    DEFAULT_CSS = """
    Toast {
        display: none;
        layer: overlay;
        background: $surface;
        border: solid $success 50%;
        padding: 1 2;
        width: auto;
        max-width: 54;
        height: auto;
        dock: top;
        offset-x: 2;
        offset-y: 4;
    }
    Toast.visible {
        display: block;
    }
    Toast.-warning {
        border: solid $warning 60%;
    }
    Toast.-error {
        border: solid $error 60%;
    }
    """

    def show(self, message: str, severity: str = "info", duration: float = 4.0) -> None:
        self.update(message)
        self.set_class(True, "visible")
        if severity == "warning":
            self.add_class("-warning")
        elif severity == "error":
            self.add_class("-error")
        self.set_timer(duration, self._dismiss)

    def _dismiss(self) -> None:
        self.set_class(False, "visible")
        self.remove_class("-warning")
        self.remove_class("-error")


class CommandPalette(Static):
    """Input for vim-style :commands."""

    DEFAULT_CSS = """
    CommandPalette {
        display: none;
        layer: overlay;
        background: $surface;
        border: solid $primary 40%;
        padding: 1 2;
        width: 60;
        height: auto;
        dock: bottom;
        offset-x: 10;
    }
    CommandPalette.visible {
        display: block;
    }
    """

    class Command(Message):
        def __init__(self, command: str) -> None:
            super().__init__()
            self.command = command

    def compose(self) -> ComposeResult:
        yield Input(placeholder=":spawn coding --task \"Fix auth bug\"", id="cmd-input")

    def show(self) -> None:
        self.set_class(True, "visible")
        try:
            self.query_one("#cmd-input", Input).focus()
        except NoMatches:
            pass

    def hide(self) -> None:
        self.set_class(False, "visible")

    @on(Input.Submitted, "#cmd-input")
    def on_command_submitted(self, event: Input.Submitted) -> None:
        if event.value.strip():
            self.post_message(self.Command(event.value.strip()))
        self.hide()
        try:
            self.query_one("#cmd-input", Input).value = ""
        except NoMatches:
            pass
