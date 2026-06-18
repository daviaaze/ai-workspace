"""
Conversation — infinite-scroll chat display for agent steps and messages.

Shows the agent's thought process (ReAct steps) in a readable format:
- User messages
- Agent thoughts (what the agent is reasoning about)
- Tool calls (action + arguments)
- Tool results (observation)
- Final responses

Refs: SPEC_TUI_V5.md
"""

from __future__ import annotations

from textual.containers import Vertical
from textual.widgets import RichLog


# ---------------------------------------------------------------------------
# Rich-compatible styles (RichLog uses Rich's Text.from_markup, not Textual's
# Content.from_markup, so $variables from the theme are not resolved here.)
# ---------------------------------------------------------------------------

_PRIMARY = "#5B8DEE"
_SECONDARY = "#7C8DB5"
_SUCCESS = "#5FA874"
_WARNING = "#D4A853"
_ERROR = "#E0556A"
_TEXT_DIM = "#7C8DB5"
_TEXT_BODY = "#A0A5B8"


class ConversationEntry:
    """A single entry in the conversation."""

    def __init__(
        self,
        role: str,  # user, agent, thought, action, observation, result, error, system
        content: str,
        agent_name: str = "",
        step: int = 0,
        tool_name: str = "",
    ) -> None:
        self.role = role
        self.content = content
        self.agent_name = agent_name
        self.step = step
        self.tool_name = tool_name

    def render(self) -> str:
        """Render a single conversation entry as Rich-compatible markup."""
        indent = "  "

        if self.role == "user":
            return f"\n[bold {_PRIMARY}]You:[/] {self.content}"

        elif self.role == "agent" or self.role == "result":
            prefix = f"[bold {_SUCCESS}]{self.agent_name}[/]" if self.agent_name else f"[bold {_SUCCESS}]Agent[/]"
            return f"\n{prefix}: {self.content}"

        elif self.role == "thought":
            prefix = f"Step {self.step}" if self.step else "Thinking"
            return f"{indent}[{_TEXT_DIM}]{prefix}:[/] [{_TEXT_BODY}]{self.content}[/]"

        elif self.role == "action":
            tool_str = f"[{_WARNING}]{self.tool_name}[/]" if self.tool_name else "unknown tool"
            args_str = self.content if self.content else ""
            if len(args_str) > 60:
                args_str = args_str[:57] + "..."
            prefix = f"Step {self.step}" if self.step else "Action"
            return f"{indent}[{_TEXT_DIM}]{prefix}:[/] {tool_str}({args_str})"

        elif self.role == "observation":
            obs = self.content
            if len(obs) > 500:
                obs = obs[:497] + "..."
            prefix = f"Step {self.step}" if self.step else "Result"
            return f"{indent}[{_TEXT_DIM}]{prefix}:[/] [{_TEXT_BODY}]{obs}[/]"

        elif self.role == "error":
            return f"{indent}[{_ERROR}]Error:[/] {self.content}"

        elif self.role == "system":
            return f"{indent}[{_TEXT_DIM}]{self.content}[/]"

        else:
            return self.content


class Conversation(Vertical):
    """Scrollable conversation view.

    Uses RichLog for efficient append-only rendering with scrollback.
    """

    DEFAULT_CSS = """
    Conversation {
        height: 1fr;
        padding: 1 2;
        background: $background;
    }

    Conversation RichLog {
        height: 1fr;
        background: $background;
    }
    """

    def compose(self):
        yield RichLog(
            id="conversation-log",
            highlight=True,
            markup=True,
            wrap=True,
            max_lines=5000,
        )

    @property
    def log(self) -> RichLog:
        return self.query_one("#conversation-log", RichLog)

    def append(self, entry: ConversationEntry) -> None:
        """Add a rendered entry to the conversation."""
        rendered = entry.render()
        if rendered:
            self.log.write(rendered)

    def add_user_message(self, text: str) -> None:
        self.append(ConversationEntry(role="user", content=text))

    def add_agent_thought(self, text: str, agent_name: str = "", step: int = 0) -> None:
        self.append(ConversationEntry(role="thought", content=text, agent_name=agent_name, step=step))

    def add_agent_action(self, tool_name: str, args: str, agent_name: str = "", step: int = 0) -> None:
        self.append(ConversationEntry(role="action", content=args, agent_name=agent_name, step=step, tool_name=tool_name))

    def add_agent_observation(self, text: str, agent_name: str = "", step: int = 0) -> None:
        self.append(ConversationEntry(role="observation", content=text, agent_name=agent_name, step=step))

    def add_agent_result(self, text: str, agent_name: str = "") -> None:
        self.append(ConversationEntry(role="result", content=text, agent_name=agent_name))

    def add_error(self, text: str) -> None:
        self.append(ConversationEntry(role="error", content=text))

    def add_system(self, text: str) -> None:
        self.append(ConversationEntry(role="system", content=text))

    def clear(self) -> None:
        """Clear the conversation log."""
        self.log.clear()
