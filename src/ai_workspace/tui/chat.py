"""
Chat Screen — structured LLM conversation interface for the AI Workspace TUI.

Replaces the AgentLane's flat output stream with a proper chat UI:
- Structured Message model (user, agent, thinking, tool_call, tool_result, edit)
- Collapsible thinking blocks (inline, not separate stream)
- Collapsible tool call blocks with syntax highlighting and diffs
- Multi-line TextArea input with message history
- Inline permission requests (no modal overlay)
- Session history loaded on reconnect
- Keyboard-first with vim-style keybindings

Layout:
┌─ StatusBar ───────────────────────────────────────────────────────────┐
│ aiw  ws:personal  qwen3:14b  session:abc123  14:32                    │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─ Conversation ───────────────────────────────────────────────┐    │
│  │  ▸ You                                         14:30         │    │
│  │  Fix the auth middleware bug                                  │    │
│  │                                                               │    │
│  │  🤖 coding-agent                              14:30          │    │
│  │  I'll look at the auth middleware.                            │    │
│  │                                                               │    │
│  │  ── thinking ─────────────────────── [^T toggle]             │    │
│  │  The user wants me to fix a bug...                            │    │
│  │  ─────────────────────────────────────                        │    │
│  │                                                               │    │
│  │  🔧 read_file("src/auth.py")                 14:31            │    │
│  │  ┌─ Output ─────────────────────────── [hide ▲]              │    │
│  │  │  1 │ def validate_jwt(token):                             │    │
│  │  │ 15 │     raise ExpiredTokenError                          │    │
│  │  └──────────────────────────────────────                     │    │
│  │                                                               │    │
│  │  ✏️ edit_file("src/auth.py")                 14:32            │    │
│  │  ┌─ Diff ──────────────────────────── [hide ▲]               │    │
│  │  │ - raise ExpiredTokenError                                 │    │
│  │  │ + return False                                            │    │
│  │  └──────────────────────────────────────                     │    │
│  │                                                               │    │
│  │  🤖 coding-agent                              14:32          │    │
│  │  ✅ Fixed. Tests pass.                                       │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌─ Input ───────────────────────────────────────────────────────┐   │
│  │ > Also add a test for the expired token case                  │   │
│  │                                                       42/4000 │   │
│  │ [^Enter send] [^N newline] [^P history] [! interrupt]        │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─ Context Bar ─────────────────────────────────────────────────┐   │
│  │ Budget: [████████░░░░] 45%  12,340/128K  Blocks: 23  [^E wb] │   │
│  └───────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────────┘

Keybindings (ChatScreen):
  Ctrl+Enter  — send message
  Ctrl+N      — newline (in multi-line input)
  Ctrl+P      — previous message in history
  Ctrl+Shift+P — next message in history
  Ctrl+T      — toggle thinking visibility
  Ctrl+E      — open context workbench (overlay)
  Ctrl+L      — back to agent lanes (pop screen)
  Ctrl+Up     — scroll conversation up
  Ctrl+Down   — scroll conversation down
  Escape      — focus input
  q           — back to agent lanes

Integration:
  From AIWorkspaceApp, push ChatScreen via Ctrl+Enter when an agent lane
  is focused. ChatScreen receives the AgentWorker (or creates one) and
  the session_id for history loading.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any

from textual import on, work
from textual.app import ComposeResult, Screen
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import (
    Label,
    Static,
    TextArea,
)

from ai_workspace.agents.context_manager import (
    BlockType,
    ContextBlock,
    ContextManager,
)
from ai_workspace.tui.worker import AgentConfig, AgentWorker
from ai_workspace.tui.context_workbench import ContextWorkbench


# ═══════════════════════════════════════════════════════════════
# Structured Message Model
# ═══════════════════════════════════════════════════════════════

class MessageRole(Enum):
    USER = auto()
    AGENT = auto()
    THINKING = auto()
    TOOL_CALL = auto()
    TOOL_RESULT = auto()
    TOOL_EDIT = auto()  # edit_file with diff
    SYSTEM = auto()
    PERMISSION = auto()


@dataclass
class ChatMessage:
    """A single structured message in the conversation.

    Unlike the old AgentLane which stored flat strings in _output_lines,
    ChatMessage carries type, metadata, and structured content so the
    UI can render distinct blocks (collapsible tools, diffs, etc.).
    """
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    message_id: str = field(default_factory=lambda: f"msg-{id(object())}")

    # Agent-specific
    agent_name: str = ""
    agent_model: str = ""

    # Tool-specific
    tool_name: str = ""
    tool_args: dict[str, Any] = field(default_factory=dict)
    tool_output: str = ""
    tool_success: bool | None = None

    # Edit-specific
    edit_path: str = ""
    edit_old: str = ""
    edit_new: str = ""

    # Thinking
    thinking_collapsed: bool = True

    # Permission
    permission_request_id: str = ""
    permission_resolved: bool = False
    permission_verdict: str = ""  # "allow", "allow_always", "deny"


# ═══════════════════════════════════════════════════════════════
# Message Block Widgets
# ═══════════════════════════════════════════════════════════════

class MessageBlock(Static):
    """Base class for all message block widgets."""

    DEFAULT_CSS = """
    MessageBlock {
        width: 1fr;
        height: auto;
        padding: 1 2;
        margin: 0 0 1 0;
    }
    """

    message: ChatMessage | None = None

    def __init__(self, message: ChatMessage | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.message = message


class UserMessageBlock(MessageBlock):
    """A user message in the conversation."""

    DEFAULT_CSS = """
    UserMessageBlock {
        background: $boost 50%;
        border-left: solid $text-muted;
        padding: 1 2;
        margin: 0 0 1 0;
    }
    """

    def render(self) -> str:
        if not self.message:
            return ""
        ts = self.message.timestamp.strftime("%H:%M")
        content = self.message.content
        # Truncate for display (scrollable via parent VerticalScroll)
        return (
            f"[dim]▸ You[/] [dim italic]{ts}[/]\n"
            f"{content}"
        )


class AgentMessageBlock(MessageBlock):
    """An agent response in the conversation."""

    DEFAULT_CSS = """
    AgentMessageBlock {
        border-left: solid $primary;
        padding: 1 2;
        margin: 0 0 1 0;
    }
    """

    def render(self) -> str:
        if not self.message:
            return ""
        ts = self.message.timestamp.strftime("%H:%M")
        agent_label = self.message.agent_name or "agent"
        model_label = f" · {self.message.agent_model}" if self.message.agent_model else ""
        return (
            f"[bold]{agent_label}[/][dim]{model_label}[/] "
            f"[dim italic]{ts}[/]\n"
            f"{self.message.content}"
        )


class ThinkingMessageBlock(MessageBlock):
    """A collapsible thinking block (agent's internal reasoning)."""

    can_focus = True

    DEFAULT_CSS = """
    ThinkingMessageBlock {
        border: dashed $warning;
        padding: 1 2;
        margin: 0 0 1 0;
        height: auto;
        max-height: 40%;
        overflow-y: auto;
    }
    ThinkingMessageBlock.collapsed {
        height: 1;
        overflow: hidden;
    }
    """

    collapsed: reactive[bool] = reactive(True)

    def render(self) -> str:
        if not self.message:
            return ""
        if self.collapsed:
            preview = self.message.content[:80].replace("\n", " ")
            return (
                f"[dim italic]── thinking ── [bold]{preview}...[/] "
                "[^T expand][/]"
            )
        return (
            f"[dim italic]── thinking ── [^T collapse][/]\n"
            f"[dim italic]{self.message.content}[/]\n"
            f"[dim italic]──[/]"
        )

    def on_click(self) -> None:
        self.toggle()

    def toggle(self) -> None:
        self.collapsed = not self.collapsed
        self.set_class(self.collapsed, "collapsed")
        self.refresh()


class ToolCallMessageBlock(MessageBlock):
    """A collapsible tool call block with syntax-highlighted output."""

    can_focus = True

    DEFAULT_CSS = """
    ToolCallMessageBlock {
        border: solid $success 50%;
        padding: 1 2;
        margin: 0 0 1 0;
        height: auto;
        max-height: 40%;
    }
    ToolCallMessageBlock.collapsed {
        height: auto;
        max-height: 2;
        overflow: hidden;
    }
    ToolCallMessageBlock.-error {
        border: solid $error 50%;
    }
    ToolCallMessageBlock.-permission {
        border: solid $warning;
    }
    """

    collapsed: reactive[bool] = reactive(True)

    def render(self) -> str:
        if not self.message:
            return ""

        tool = self.message.tool_name or "tool"
        # Format tool args compactly
        args_str = ""
        if self.message.tool_args:
            parts = []
            for k, v in self.message.tool_args.items():
                if k == "command":
                    parts.append(f'"{v}"')
                elif k in ("path", "file_path"):
                    parts.append(f'"{v}"')
                elif k == "content":
                    parts.append(f"content({len(str(v))} chars)")
                elif k in ("old_text", "new_text"):
                    parts.append(f"{k}={len(str(v))} chars")
                else:
                    val_str = str(v)[:40]
                    parts.append(f"{k}={val_str}")
            args_str = ", ".join(parts)

        success_icon = {
            True: "[green]✓[/]",
            False: "[red]✗[/]",
            None: "[yellow]⏳[/]",
        }.get(self.message.tool_success, "")

        header = f"🔧 {tool}({args_str}) {success_icon}"

        if self.collapsed:
            return f"{header} [dim][Enter] expand[/]"

        # Expanded: show output
        output = self.message.tool_output or self.message.content
        if len(output) > 2000:
            output = output[:2000] + "\n... (truncated)"

        return f"{header} [dim][Enter] collapse[/]\n" + output

    def on_click(self) -> None:
        self.toggle()

    def toggle(self) -> None:
        self.collapsed = not self.collapsed
        self.set_class(self.collapsed, "collapsed")
        self.refresh()


class EditMessageBlock(MessageBlock):
    """A collapsible edit_file block with colored diff."""

    can_focus = True

    DEFAULT_CSS = """
    EditMessageBlock {
        border: solid $accent;
        padding: 1 2;
        margin: 0 0 1 0;
        height: auto;
        max-height: 40%;
    }
    EditMessageBlock.collapsed {
        height: auto;
        max-height: 2;
        overflow: hidden;
    }
    """

    collapsed: reactive[bool] = reactive(True)

    def render(self) -> str:
        if not self.message:
            return ""

        path = self.message.edit_path or "?"
        header = f"✏️ edit_file(\"{path}\")"

        if self.collapsed:
            return f"{header} [dim][Enter] expand[/]"

        # Render colored diff
        diff_lines = self._render_diff()
        return f"{header} [dim][Enter] collapse[/]\n" + diff_lines

    def _render_diff(self) -> str:
        """Render a simple colored diff from old/new text."""
        if not self.message:
            return ""

        import difflib

        old_lines = self.message.edit_old.splitlines(keepends=True)
        new_lines = self.message.edit_new.splitlines(keepends=True)

        diff = list(difflib.unified_diff(
            old_lines, new_lines,
            fromfile=self.message.edit_path,
            tofile=self.message.edit_path,
            lineterm="",
        ))

        lines = []
        for d in diff[:50]:  # Limit diff size
            d = d.rstrip("\n")
            if d.startswith("---") or d.startswith("+++"):
                lines.append(f"[dim]{d}[/]")
            elif d.startswith("@@"):
                lines.append(f"[bold cyan]{d}[/]")
            elif d.startswith("-"):
                lines.append(f"[red]{d}[/]")
            elif d.startswith("+"):
                lines.append(f"[green]{d}[/]")
            else:
                lines.append(f"[dim]{d}[/]")

        if len(diff) > 50:
            lines.append("[dim]... (diff truncated)[/]")

        return "\n".join(lines)

    def on_click(self) -> None:
        self.toggle()

    def toggle(self) -> None:
        self.collapsed = not self.collapsed
        self.set_class(self.collapsed, "collapsed")
        self.refresh()


class PermissionInlineBlock(MessageBlock):
    """An inline permission request (replaces the modal overlay)."""

    can_focus = True

    DEFAULT_CSS = """
    PermissionInlineBlock {
        border: thick $warning;
        background: $warning 10%;
        padding: 1 2;
        margin: 0 0 1 0;
    }
    """

    def render(self) -> str:
        if not self.message:
            return ""
        tool = self.message.tool_name or "tool"
        desc = self.message.content[:200]
        preview = self.message.tool_output[:300] if self.message.tool_output else ""
        body = (
            f"🔒 [bold yellow]Permission needed:[/] {tool}\n"
            f"[italic]{desc}[/]\n"
        )
        if preview:
            body += f"\n[dim]{preview}[/]\n"
        body += (
            "\n"
            "[bold][[a]][/] Allow Once    "
            "[bold][[A]][/] Always Allow    "
            "[bold][[d]][/] Deny"
        )
        return body


class SystemMessageBlock(MessageBlock):
    """A system notification (agent started, context injected, etc.)."""

    DEFAULT_CSS = """
    SystemMessageBlock {
        padding: 0 2;
        margin: 0 0 1 0;
        height: auto;
    }
    """

    def render(self) -> str:
        if not self.message:
            return ""
        return f"[dim italic]{self.message.content}[/]"


# ═══════════════════════════════════════════════════════════════
# Chat Input
# ═══════════════════════════════════════════════════════════════

class ChatInput(Static):
    """Multi-line chat input with message history and character counter.

    Uses Textual's TextArea widget for multi-line editing.
    History is stored in-memory and recycled with Ctrl+P / Ctrl+Shift+P.
    """

    DEFAULT_CSS = """
    ChatInput {
        dock: bottom;
        height: auto;
        min-height: 3;
        max-height: 12;
        background: $boost;
        border-top: solid $primary-background;
        padding: 1 2;
    }

    ChatInput > Vertical {
        height: auto;
    }

    #chat-textarea {
        height: auto;
        min-height: 1;
        max-height: 8;
        border: none;
        background: $surface;
    }

    #chat-textarea:focus {
        border: solid $primary;
    }

    #chat-hints {
        height: 1;
        padding: 0 1;
        text-style: dim;
    }

    #chat-counter {
        text-style: dim;
        text-align: right;
        width: 10;
    }
    """

    class Submitted(Message):
        """Posted when user sends a message (Ctrl+Enter)."""

        def __init__(self, text: str, is_interrupt: bool = False) -> None:
            super().__init__()
            self.text = text
            self.is_interrupt = is_interrupt

    MAX_LENGTH: int = 4000
    HISTORY_SIZE: int = 100

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._history: list[str] = []
        self._history_index: int = -1
        self._current_draft: str = ""

    def compose(self) -> ComposeResult:
        with Vertical():
            yield TextArea.code_editor(
                "",
                id="chat-textarea",
                language=None,
                show_line_numbers=False,
            )
            with Horizontal():
                yield Label(
                    "[dim][^Enter] send  [^N] newline  [^P] history  "
                    "[!] interrupt  [Esc] focus[/]",
                    id="chat-hints",
                )
                yield Label("0/4000", id="chat-counter")

    def on_mount(self) -> None:
        """Focus the textarea on mount."""
        try:
            self.query_one("#chat-textarea", TextArea).focus()
        except NoMatches:
            pass

    @on(TextArea.Changed, "#chat-textarea")
    def on_text_changed(self, event: TextArea.Changed) -> None:
        """Update character counter."""
        text = event.text_area.text
        count = len(text)
        try:
            counter = self.query_one("#chat-counter", Label)
            counter.update(f"{count}/{self.MAX_LENGTH}")
            if count > self.MAX_LENGTH * 0.9:
                counter.styles.color = "$warning"
            elif count > self.MAX_LENGTH:
                counter.styles.color = "$error"
            else:
                counter.styles.color = "$text-muted"
        except NoMatches:
            pass

    def action_submit(self) -> None:
        """Send the current text (bound to Ctrl+Enter)."""
        try:
            textarea = self.query_one("#chat-textarea", TextArea)
            text = textarea.text.strip()
        except NoMatches:
            return

        if not text:
            return

        # Check for interrupt prefix
        is_interrupt = text.startswith("!")
        if is_interrupt:
            text = text[1:].strip()
            if not text:
                return

        # Add to history
        if text not in self._history:
            self._history.append(text)
            if len(self._history) > self.HISTORY_SIZE:
                self._history.pop(0)
        self._history_index = -1
        self._current_draft = ""

        # Clear and post
        textarea.text = ""
        textarea.focus()
        self.post_message(self.Submitted(text, is_interrupt=is_interrupt))

    def navigate_history_prev(self) -> None:
        """Load previous message from history into the textarea."""
        if not self._history:
            return

        try:
            textarea = self.query_one("#chat-textarea", TextArea)
        except NoMatches:
            return

        # Save current draft on first navigation
        if self._history_index == -1:
            self._current_draft = textarea.text

        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            idx = len(self._history) - 1 - self._history_index
            textarea.text = self._history[idx]

    def navigate_history_next(self) -> None:
        """Load next message from history (or restore draft)."""
        try:
            textarea = self.query_one("#chat-textarea", TextArea)
        except NoMatches:
            return

        if self._history_index > 0:
            self._history_index -= 1
            idx = len(self._history) - 1 - self._history_index
            textarea.text = self._history[idx]
        elif self._history_index == 0:
            self._history_index = -1
            textarea.text = self._current_draft

    def action_focus_input(self) -> None:
        """Focus the textarea."""
        try:
            self.query_one("#chat-textarea", TextArea).focus()
        except NoMatches:
            pass

    def show_system_message(self, text: str) -> None:
        """Display a transient message below the hints bar (not persisted)."""
        try:
            hints = self.query_one("#chat-hints", Label)
            hints.update(f"[bold yellow]{text}[/]")
            # It will be overwritten on next render
        except NoMatches:
            pass


# ═══════════════════════════════════════════════════════════════
# Conversation View
# ═══════════════════════════════════════════════════════════════

class ConversationView(VerticalScroll):
    """Scrollable conversation showing all ChatMessage blocks.

    Messages are rendered as distinct block widgets (UserMessageBlock,
    AgentMessageBlock, ThinkingMessageBlock, ToolCallMessageBlock, etc.)
    instead of flat text lines like the old AgentLane._output_lines.
    """

    can_focus = True

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._messages: list[ChatMessage] = []
        self._message_widgets: list[MessageBlock] = []
        self.MAX_MESSAGES = 500

    def add_message(self, msg: ChatMessage) -> MessageBlock:
        """Add a message to the conversation and render its block.

        Returns the created widget so callers can update it for streaming.
        """
        self._messages.append(msg)
        if len(self._messages) > self.MAX_MESSAGES:
            self._messages = self._messages[-self.MAX_MESSAGES:]

        widget = self._create_widget(msg)
        self.mount(widget)
        self._message_widgets.append(widget)

        # Smart scroll: only auto-scroll if user is already at the bottom
        self._smart_scroll()

        return widget

    def update_last_message(self, content: str) -> MessageBlock | None:
        """Update the content of the last message (for streaming)."""
        if not self._messages:
            return None
        self._messages[-1].content = content
        if self._message_widgets:
            widget = self._message_widgets[-1]
            widget.message = self._messages[-1]
            widget.refresh()
            self._smart_scroll()
            return widget
        return None

    def _smart_scroll(self) -> None:
        """Auto-scroll to bottom only if the user hasn't scrolled up.

        If the user has scrolled up to read older messages, we don't
        want to yank them to the bottom when new content arrives.
        """
        # Check if we're near the bottom (within 2 lines of the end)
        if self.max_scroll_y is not None and self.scroll_y is not None:
            distance_from_bottom = self.max_scroll_y - self.scroll_y
            if distance_from_bottom > 2:
                return  # User is reading history, don't interrupt
        self.scroll_end(animate=False)

    def last_message(self) -> ChatMessage | None:
        """Get the last message."""
        return self._messages[-1] if self._messages else None

    def load_history(self, messages: list[dict]) -> None:
        """Load conversation history from session store.

        Args:
            messages: List of dicts with role, content, metadata.
        """
        for m in messages:
            role_str = m.get("role", "")
            content = m.get("content", "")
            ts = m.get("timestamp")

            if role_str == "user":
                msg = ChatMessage(role=MessageRole.USER, content=content)
            elif role_str == "assistant":
                msg = ChatMessage(
                    role=MessageRole.AGENT,
                    content=content,
                    agent_name=m.get("agent_name", ""),
                    agent_model=m.get("agent_model", ""),
                )
            elif role_str == "system":
                msg = ChatMessage(role=MessageRole.SYSTEM, content=content)
            elif role_str == "tool":
                msg = ChatMessage(
                    role=MessageRole.TOOL_CALL,
                    content=content,
                    tool_name=m.get("tool_name", ""),
                    tool_success=m.get("success", True),
                )
            else:
                msg = ChatMessage(role=MessageRole.SYSTEM, content=content)

            if ts:
                try:
                    msg.timestamp = datetime.fromisoformat(str(ts))
                except (ValueError, TypeError):
                    pass

            self.add_message(msg)

    def _create_widget(self, msg: ChatMessage) -> MessageBlock:
        """Create the appropriate widget for a message role."""
        role_map = {
            MessageRole.USER: UserMessageBlock,
            MessageRole.AGENT: AgentMessageBlock,
            MessageRole.THINKING: ThinkingMessageBlock,
            MessageRole.TOOL_CALL: ToolCallMessageBlock,
            MessageRole.TOOL_RESULT: ToolCallMessageBlock,
            MessageRole.TOOL_EDIT: EditMessageBlock,
            MessageRole.PERMISSION: PermissionInlineBlock,
            MessageRole.SYSTEM: SystemMessageBlock,
        }
        widget_class = role_map.get(msg.role, SystemMessageBlock)
        return widget_class(msg)


# ═══════════════════════════════════════════════════════════════
# Context Bar (token budget, always visible)
# ═══════════════════════════════════════════════════════════════

class ContextBar(Static):
    """Always-visible token budget bar at the bottom of the chat screen."""

    DEFAULT_CSS = """
    ContextBar {
        dock: bottom;
        height: 1;
        padding: 0 2;
        background: $boost;
        border-top: solid $primary-background;
    }
    """

    context_manager: ContextManager | None = None

    def render(self) -> str:
        if not self.context_manager:
            return "[dim]Context: —[/]"

        cm = self.context_manager
        pct = cm.budget_used_pct
        total = cm.total_tokens
        max_t = cm.context_window_tokens
        blocks = len(cm.get_active_blocks())

        # Mini progress bar (15 chars)
        width = 15
        filled = int((min(pct, 100) / 100) * width)
        bar = "█" * filled + "░" * (width - filled)

        if pct < 40:
            color = "green"
        elif pct < 70:
            color = "yellow"
        else:
            color = "red"

        return (
            f"Budget: [{color}]{bar}[/] "
            f"[{color}]{pct:.0f}%[/]  "
            f"{total:,}/{max_t:,}  "
            f"Blocks: {blocks}  "
            f"[dim][^E] Workbench[/]"
        )

    def refresh_from_manager(self) -> None:
        """Refresh the bar from the context manager."""
        self.refresh()


# ═══════════════════════════════════════════════════════════════
# ChatScreen — the full chat interface
# ═══════════════════════════════════════════════════════════════

class ChatScreen(Screen[None]):
    """Full-screen chat interface for interacting with a single agent.

    Push this screen from AIWorkspaceApp when the user wants to focus
    on a conversation with one agent (Ctrl+Enter on a focused lane).

    Args (passed via constructor):
        agent_name: str
        model: str
        session_id: str | None
        cwd: str
        agent_type: str = "general"
        worker: AgentWorker | None (if already running)
        context_manager: ContextManager | None
    """

    CSS = """
    ChatScreen {
        layers: base overlay;
    }

    #chat-conversation {
        height: 1fr;
        overflow-y: auto;
    }

    #chat-conversation:focus {
        border: none;
    }
    """

    BINDINGS = [
        ("ctrl+enter", "submit", "Send"),
        ("ctrl+n", "newline", "Newline"),
        ("ctrl+p", "history_prev", "Prev"),
        ("ctrl+shift+p", "history_next", "Next"),
        ("ctrl+t", "toggle_thinking", "Thinking"),
        ("ctrl+e", "context_workbench", "Context"),
        ("ctrl+l", "back_to_lanes", "Lanes"),
        ("ctrl+up", "scroll_up", "Scroll Up"),
        ("ctrl+down", "scroll_down", "Scroll Down"),
        ("escape", "focus_input", "Focus Input"),
        ("q", "back_to_lanes", "Back"),
    ]

    def __init__(
        self,
        agent_name: str = "agent",
        model: str = "qwen3:14b",
        session_id: str | None = None,
        cwd: str = ".",
        agent_type: str = "general",
        worker: AgentWorker | None = None,
        context_manager: ContextManager | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.agent_name = agent_name
        self.model = model
        self.session_id = session_id
        self.cwd = cwd
        self.agent_type = agent_type
        self._worker = worker
        self.context_manager = context_manager or ContextManager(
            context_window_tokens=128_000,
            session_id=session_id,
        )

        # If no worker provided, we'll create one on first message
        self._initial_task: str | None = None
        self._pending_tool_call: ChatMessage | None = None
        self._pending_thinking: ChatMessage | None = None
        self._thinking_visible: bool = True
        self._drain_timer = None  # SetInterval timer for worker output draining

    def compose(self) -> ComposeResult:
        """Build the chat screen layout."""
        # Status bar (simplified — reuse existing but could be custom)
        yield Static("", id="chat-status")

        # Conversation (main area)
        yield ConversationView(id="chat-conversation")

        # Chat input (bottom, above context bar)
        yield ChatInput(id="chat-input")

        # Context bar (bottom-most)
        yield ContextBar(id="chat-context-bar")

        # Context workbench overlay
        yield ContextWorkbench(
            id="chat-context-workbench",
            context_manager=self.context_manager,
        )

    def on_mount(self) -> None:
        """Initialize the chat screen."""
        # Update status
        try:
            status = self.query_one("#chat-status", Static)
            cwd_short = str(Path(self.cwd).expanduser())
            home = str(Path.home())
            if cwd_short.startswith(home):
                cwd_short = "~" + cwd_short[len(home):]
            status.update(
                f"[bold]Chat[/]  "
                f"[cyan]{cwd_short}[/]  "
                f"[dim]{self.model}[/]  "
                f"agent:[bold]{self.agent_name}[/]"
                + (f"  session:{self.session_id[:8]}" if self.session_id else "")
            )
        except NoMatches:
            pass

        # Link context manager
        try:
            bar = self.query_one(ContextBar)
            bar.context_manager = self.context_manager
            bar.refresh_from_manager()
        except NoMatches:
            pass

        # Load session history
        if self.session_id:
            self._load_session_history()

        # If worker doesn't exist yet, show a welcome message
        if not self._worker:
            self.query_one(ConversationView).add_message(ChatMessage(
                role=MessageRole.SYSTEM,
                content=(
                    f"Chat started with [bold]{self.agent_name}[/] "
                    f"({self.model}).\n"
                    f"Type a message and press [bold]Ctrl+Enter[/] to send."
                ),
            ))

        # Focus input
        try:
            self.query_one(ChatInput).action_focus_input()
        except NoMatches:
            pass

    def _load_session_history(self) -> None:
        """Load conversation history from the session store."""
        if not self.session_id:
            return

        try:
            from ai_workspace.core.sessions import SessionStore
            store = SessionStore()
            store.initialize()
            entries = store.get_entries(self.session_id, limit=100)
            store.close()

            if entries:
                conv = self.query_one(ConversationView)
                conv.load_history(entries)
                self.query_one(ConversationView).add_message(ChatMessage(
                    role=MessageRole.SYSTEM,
                    content=(
                        f"Loaded {len(entries)} messages from session "
                        f"[cyan]{self.session_id[:12]}…[/]"
                    ),
                ))
        except Exception as e:
            self.query_one(ConversationView).add_message(ChatMessage(
                role=MessageRole.SYSTEM,
                content=f"[dim]Could not load session history: {e}[/]",
            ))

    # ─── Message Handling ─────────────────────────────

    @on(ChatInput.Submitted)
    async def on_chat_submitted(self, event: ChatInput.Submitted) -> None:
        """Handle a submitted chat message."""
        text = event.text
        is_interrupt = event.is_interrupt

        conv = self.query_one(ConversationView)

        # Add user message to conversation
        user_msg = ChatMessage(
            role=MessageRole.USER,
            content=text,
        )
        conv.add_message(user_msg)

        # Save to session
        if self.session_id:
            try:
                from ai_workspace.core.sessions import SessionStore
                store = SessionStore()
                store.initialize()
                store.add_message(
                    session_id=self.session_id,
                    role="user",
                    content=text,
                )
                store.close()
            except Exception:
                pass

        # Register in context manager
        self.context_manager.add_block_sync(
            BlockType.USER_MESSAGE,
            text[:3000],
            summary=text[:80].replace("\n", " "),
            importance=0.9,
        )
        self._refresh_context_bar()

        # Create worker if needed (first message)
        if not self._worker:
            return await self._spawn_worker(text)

        # Send to existing worker
        if is_interrupt:
            priority = 10  # INTERRUPT priority
        else:
            priority = 0  # NORMAL priority

        await self._worker.send_message(text, priority=priority)

        # Start draining output
        self._start_draining()

    async def _spawn_worker(self, task: str) -> None:
        """Create a new AgentWorker on the first message."""
        from ai_workspace.core.sessions import SessionStore

        # Auto-create session if none exists
        if not self.session_id:
            store = SessionStore()
            store.initialize()
            s = store.create_session(
                cwd=self.cwd,
                model=self.model,
                label=f"{self.agent_type}: {task[:40]}",
            )
            store.close()
            self.session_id = s.id

        config = AgentConfig(
            lane_id=self.agent_name,
            agent_type=self.agent_type,
            model=self.model,
            session_id=self.session_id,
            cwd=self.cwd,
            context_manager=self.context_manager,
        )
        self._worker = AgentWorker(config)

        self.query_one(ConversationView).add_message(ChatMessage(
            role=MessageRole.SYSTEM,
            content=f"Spawned [bold]{self.agent_name}[/] ({self.model})…",
        ))

        await self._worker.start_loop(task)
        self._start_draining()

    def _start_draining(self) -> None:
        """Start draining the worker's output queue into the conversation."""
        if self._drain_timer is None:
            self._drain_timer = self.set_interval(0.05, self._drain_worker_queue)

    async def _drain_worker_queue(self) -> None:
        """Drain worker output into the conversation as structured messages."""
        if not self._worker:
            return

        for _ in range(20):
            try:
                line = self._worker.queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            conv = self.query_one(ConversationView)
            # Determine what type of message this line represents
            msg = self._parse_worker_line(line)

            if msg:
                conv.add_message(msg)

                # Register tool calls in context manager
                if msg.role == MessageRole.TOOL_CALL:
                    self.context_manager.add_block_sync(
                        BlockType.TOOL_CALL,
                        msg.content[:2000],
                        summary=f"{msg.tool_name}",
                        tool_name=msg.tool_name,
                        importance=0.5,
                    )
                elif msg.role == MessageRole.TOOL_EDIT:
                    self.context_manager.add_block_sync(
                        BlockType.FILE_EDIT,
                        f"{msg.edit_path}: {msg.edit_old[:200]} → {msg.edit_new[:200]}",
                        summary=f"edit: {msg.edit_path}",
                        file_path=msg.edit_path,
                        importance=0.6,
                    )

                self._refresh_context_bar()

        # Check for pending permissions
        if self._worker.pending_permission:
            perm = self._worker.pending_permission
            conv = self.query_one(ConversationView)
            perm_msg = ChatMessage(
                role=MessageRole.PERMISSION,
                content=perm.description,
                tool_name=perm.tool_name,
                tool_output=perm.preview[:500],
                permission_request_id=perm.request_id,
                agent_name=perm.agent_name,
            )
            conv.add_message(perm_msg)
            # Permission modal (old) is still handled by the parent app's poller
            # This adds an inline record too

    def _parse_worker_line(self, line: str) -> ChatMessage | None:
        """Parse a raw output line from the worker into a structured message.

        The worker writes lines like:
          "> You: Hello"              → USER
          "🤖 Agent response..."      → AGENT
          "  💭 thinking text"        → THINKING
          "🔧 tool_name(args)"        → TOOL_CALL
          "✏️ edit_file(path)"         → TOOL_EDIT
          "✅ result" or "🔴 error"   → SYSTEM (status)
          "🔒 Permission needed: ..." → PERMISSION
          "📁 Working dir: ..."       → SYSTEM
        """
        stripped = line.strip()
        if not stripped:
            return None

        # User message marker (from worker echo)
        if stripped.startswith("> You:") or stripped.startswith("> [bold]You:"):
            # Don't create duplicate — worker echoes what we sent
            return None

        # Thinking stream (from crewAI step callback)
        if "💭" in stripped[:10]:
            content = stripped.split("💭", 1)[-1].strip()
            return ChatMessage(
                role=MessageRole.THINKING,
                content=content,
                agent_name=self.agent_name,
            )

        # Tool call (from permission gate or step output)
        if any(stripped.startswith(prefix) for prefix in [
            "🔧", "read_file", "write_file", "edit_file", "shell_exec",
            "list_files", "search_files",
        ]):
            # Try to extract tool name and args
            tool_name = ""
            if "(" in stripped:
                tool_name = stripped.split("(")[0].replace("🔧", "").strip()
                args_str = stripped.split("(", 1)[1].rstrip(")")
            else:
                tool_name = stripped.split()[0].replace("🔧", "").strip()
                args_str = ""

            return ChatMessage(
                role=MessageRole.TOOL_CALL if "edit" not in tool_name.lower() else MessageRole.TOOL_EDIT,
                content=stripped,
                tool_name=tool_name,
            )

        # Status messages
        if any(stripped.startswith(s) for s in ["✅", "🔴", "🔄", "📁", "📋", "⚡", "⚠"]):
            return ChatMessage(role=MessageRole.SYSTEM, content=stripped)

        # Permission needed
        if "🔒" in stripped[:5] or "Permission" in stripped[:20]:
            return ChatMessage(role=MessageRole.PERMISSION, content=stripped)

        # Default: agent response
        if len(stripped) > 5:
            return ChatMessage(
                role=MessageRole.AGENT,
                content=stripped,
                agent_name=self.agent_name,
                agent_model=self.model,
            )

        return None

    def _refresh_context_bar(self) -> None:
        """Refresh the context bar."""
        try:
            bar = self.query_one(ContextBar)
            bar.refresh_from_manager()
        except NoMatches:
            pass

    # ─── Keybinding Actions ─────────────────────────

    def action_submit(self) -> None:
        """Send message (Ctrl+Enter)."""
        try:
            self.query_one(ChatInput).action_submit()
        except NoMatches:
            pass

    def action_newline(self) -> None:
        """Insert newline (Ctrl+N)."""
        try:
            textarea = self.query_one("#chat-textarea", TextArea)
            textarea.insert("\n")
        except NoMatches:
            pass

    def action_history_prev(self) -> None:
        """Previous message in history (Ctrl+P)."""
        try:
            self.query_one(ChatInput).navigate_history_prev()
        except NoMatches:
            pass

    def action_history_next(self) -> None:
        """Next message in history (Ctrl+Shift+P)."""
        try:
            self.query_one(ChatInput).navigate_history_next()
        except NoMatches:
            pass

    def action_toggle_thinking(self) -> None:
        """Toggle thinking visibility for all thinking blocks (Ctrl+T)."""
        self._thinking_visible = not self._thinking_visible
        try:
            conv = self.query_one(ConversationView)
            for widget in conv.children:
                if isinstance(widget, ThinkingMessageBlock):
                    widget.collapsed = not self._thinking_visible
                    widget.set_class(widget.collapsed, "collapsed")
                    widget.refresh()
        except NoMatches:
            pass

    def action_context_workbench(self) -> None:
        """Open context workbench overlay (Ctrl+E)."""
        try:
            wb = self.query_one("#chat-context-workbench", ContextWorkbench)
            wb.context_manager = self.context_manager
            wb.show()
        except NoMatches:
            pass

    def action_back_to_lanes(self) -> None:
        """Return to agent lanes view (Ctrl+L or q)."""
        # Stop drain timer to prevent background work after dismiss
        if self._drain_timer:
            self._drain_timer.stop()
            self._drain_timer = None
        self.dismiss(None)

    def action_scroll_up(self) -> None:
        """Scroll conversation up (Ctrl+Up)."""
        try:
            conv = self.query_one(ConversationView)
            conv.scroll_relative(y=-5, animate=False)
        except NoMatches:
            pass

    def action_scroll_down(self) -> None:
        """Scroll conversation down (Ctrl+Down)."""
        try:
            conv = self.query_one(ConversationView)
            conv.scroll_relative(y=5, animate=False)
        except NoMatches:
            pass

    def action_focus_input(self) -> None:
        """Focus the chat input (Escape)."""
        try:
            self.query_one(ChatInput).action_focus_input()
        except NoMatches:
            pass

    # ─── Permission Inline Keys ────────────────────

    def key_a(self) -> None:
        """Approve once (when permission block is focused)."""
        self._resolve_permission("allow")

    def key_A(self) -> None:
        """Approve always (Shift+A)."""
        self._resolve_permission("allow_always")

    def key_d(self) -> None:
        """Deny."""
        self._resolve_permission("deny")

    def _resolve_permission(self, verdict: str) -> None:
        """Resolve the current pending permission."""
        if not self._worker or not self._worker.pending_permission:
            return

        from ai_workspace.tui.permissions import PermissionVerdict
        verdict_map = {
            "allow": PermissionVerdict.ALLOW,
            "allow_always": PermissionVerdict.ALLOW_ALWAYS,
            "deny": PermissionVerdict.DENY,
        }
        v = verdict_map.get(verdict, PermissionVerdict.DENY)
        self._worker.pending_permission.resolve(v)
        self._worker.pending_permission = None

        conv = self.query_one(ConversationView)
        conv.add_message(ChatMessage(
            role=MessageRole.SYSTEM,
            content=f"Permission {verdict}ed.",
        ))

    # ─── Permission Modal Keys (from old system) ───

    def key_escape(self) -> None:
        """Escape: dismiss workbench or focus input."""
        try:
            wb = self.query_one("#chat-context-workbench", ContextWorkbench)
            if wb.has_class("visible"):
                wb.hide()
                return
        except NoMatches:
            pass
        self.action_focus_input()


# ═══════════════════════════════════════════════════════════════
# Integration hook for AIWorkspaceApp
# ═══════════════════════════════════════════════════════════════

def push_chat_screen(
    app,
    agent_name: str,
    model: str = "qwen3:14b",
    session_id: str | None = None,
    cwd: str = ".",
    agent_type: str = "general",
    worker: AgentWorker | None = None,
    context_manager: ContextManager | None = None,
) -> None:
    """Push a ChatScreen onto the app's screen stack.

    Call this from AIWorkspaceApp when the user wants to focus on a
    conversation with a specific agent (e.g., Ctrl+Enter on a focused lane).

    Example:
        from ai_workspace.tui.chat import push_chat_screen
        push_chat_screen(
            self,
            agent_name="coding-agent",
            model="qwen3:14b",
            session_id=worker.config.session_id,
            cwd=self.cwd,
            worker=worker,
            context_manager=self.context_manager,
        )
    """
    screen = ChatScreen(
        agent_name=agent_name,
        model=model,
        session_id=session_id,
        cwd=cwd,
        agent_type=agent_type,
        worker=worker,
        context_manager=context_manager,
    )
    app.push_screen(screen)
