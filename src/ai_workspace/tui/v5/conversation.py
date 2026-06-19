"""
Conversation widget — custom chat display for agent interaction.

Each message type is a separate widget, allowing:
- Independent styling (tool calls as cards, errors as alerts)
- In-place streaming for agent responses
- Collapsible tool results
- Clean separation from RichLog's log-output limitations
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Static

# ── Message types ───────────────────────────────────────────


class UserMessage(Static):
    """A message from the user."""

    DEFAULT_CSS = """
    UserMessage {
        padding: 0 2;
        color: $primary;
        text-style: bold;
        width: 100%;
        height: auto;
    }
    """

    def __init__(self, text: str) -> None:
        super().__init__(f"▸ {text}")


class AgentThought(Static):
    """An agent thinking step."""

    DEFAULT_CSS = """
    AgentThought {
        padding: 0 2;
        color: $text 60%;
        text-style: italic;
        width: 100%;
        height: auto;
    }
    """

    def __init__(self, text: str, step: int = 0) -> None:
        label = "Thinking..." if not step else f"Step {step}"
        super().__init__(f"  {label}: {text}")


class ToolCall(Container):
    """A tool invocation with collapsible result."""

    tool_name: reactive[str] = reactive("")
    tool_args: reactive[str] = reactive("")
    tool_result: reactive[str] = reactive("")
    expanded: reactive[bool] = reactive(False)

    DEFAULT_CSS = """
    ToolCall {
        padding: 0 2;
        margin: 0 0 0 2;
        width: 100%;
        height: auto;
        border-left: solid $warning;
        background: $panel 30%;
    }
    ToolCall Static.tool-header {
        color: $warning;
        text-style: bold;
        padding: 0 0 0 1;
        width: 100%;
        height: auto;
    }
    ToolCall Static.tool-result {
        color: $text 80%;
        padding: 0 0 0 2;
        display: none;
        height: auto;
        max-height: 12;
        overflow-y: auto;
        border-top: dashed $primary 15%;
        margin: 0 0 0 1;
        width: auto;
    }
    ToolCall.-expanded Static.tool-result {
        display: block;
    }
    """

    def __init__(self, name: str, args: str = "") -> None:
        super().__init__()
        self.tool_name = name
        self.tool_args = args
        self._has_result = False

    def compose(self) -> ComposeResult:
        yield Static(f"🔧 {self.tool_name}({self.tool_args[:80]})", classes="tool-header")
        yield Static("", classes="tool-result")

    def set_result(self, text: str) -> None:
        self.tool_result = text[:800]
        self._has_result = True
        try:
            result = self.query_one(".tool-result", Static)
            lines = text[:800].count("\n") + 1
            result.update(f"▼ result ({lines} lines):\n{text[:800]}")
            self.add_class("-expanded")
            # Update header to show expand hint
            header = self.query_one(".tool-header", Static)
            hdr = f"🔧 {self.tool_name}({self.tool_args[:60]})"
            header.update(f"{hdr}  [dim]▼ {lines} lines[/]")
        except Exception:
            pass

    def on_click(self) -> None:
        self.toggle_class("-expanded")


class AgentResponse(Static):
    """Streaming agent response — updates in-place as tokens arrive."""

    content: reactive[str] = reactive("")

    DEFAULT_CSS = """
    AgentResponse {
        padding: 0 2;
        color: $text;
        width: 100%;
        height: auto;
        text-style: none;
    }
    """

    def __init__(self) -> None:
        super().__init__("")

    def watch_content(self, value: str) -> None:
        self.update(value)

    def append_token(self, text: str) -> None:
        self.content += text

    def finalize(self) -> None:
        """Called when streaming completes."""
        pass


class AgentError(Static):
    """An error from the agent."""

    DEFAULT_CSS = """
    AgentError {
        padding: 0 2;
        color: $error;
        text-style: bold;
        width: 100%;
        height: auto;
    }
    """

    def __init__(self, text: str) -> None:
        super().__init__(f"✗ {text}")


class SystemMessage(Static):
    """Non-agent status messages (help, cost, etc.)"""

    DEFAULT_CSS = """
    SystemMessage {
        padding: 0 2;
        color: $text 50%;
        width: 100%;
        height: auto;
    }
    """

    def __init__(self, text: str) -> None:
        super().__init__(f"-- {text}")


# ── Conversation container ──────────────────────────────────


class Conversation(VerticalScroll):
    """Scrollable conversation with typed message widgets."""

    DEFAULT_CSS = """
    Conversation {
        height: 1fr;
        width: 100%;
        padding: 1 0;
        background: $background;
    }
    """

    # Current streaming response (if any)
    _current_response: AgentResponse | None = None

    def add_user(self, text: str) -> None:
        self.mount(UserMessage(text))

    def add_thought(self, text: str, step: int = 0) -> None:
        self.mount(AgentThought(text, step))

    def add_tool_call(self, name: str, args: str = "") -> ToolCall:
        tc = ToolCall(name, args)
        self.mount(tc)
        return tc

    def add_tool_result(self, tc: ToolCall, result: str) -> None:
        tc.set_result(result)

    def start_response(self) -> AgentResponse:
        """Begin streaming agent response. Returns widget to append tokens to."""
        self._current_response = AgentResponse()
        self.mount(self._current_response)
        return self._current_response

    def append_token(self, text: str) -> None:
        """Append token to current streaming response."""
        if self._current_response:
            # Escape Rich markup brackets in user content
            safe = text.replace("[", "[[")
            self._current_response.append_token(safe)

    def finish_response(self) -> None:
        """Finalize the current streaming response."""
        if self._current_response:
            self._current_response.finalize()
            self._current_response = None

    def add_error(self, text: str) -> None:
        self.mount(AgentError(text))

    def add_system(self, text: str) -> None:
        self.mount(SystemMessage(text))

    def clear(self) -> None:
        for child in list(self.children):
            if isinstance(child, (UserMessage, AgentThought, ToolCall,
                                  AgentResponse, AgentError, SystemMessage)):
                child.remove()


