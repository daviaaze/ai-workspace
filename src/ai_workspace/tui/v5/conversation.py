"""
Conversation — scrollable chat display for agent steps and messages.

Uses RichLog. All markup uses hex colors (Rich's parser doesn't
resolve Textual $theme variables — RichLog.write() calls
Rich's Text.from_markup(), not Textual's markup resolver).
"""

from __future__ import annotations

from textual.containers import Vertical
from textual.widgets import RichLog

# Hex colors matching the "workstation" theme
P = "#5B8DEE"  # primary
S = "#5FA874"  # success
W = "#D4A853"  # warning
E = "#E0556A"  # error
T = "#A0A5B8"  # text
D = "#7C8DB5"  # dim

INDENT = "  "


class ConversationEntry:
    """A single entry with role-based rendering to Rich-compatible markup."""

    def __init__(
        self,
        role: str,
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
        c = self.content

        if self.role == "user":
            return f"\n[bold {P}]You:[/] {c}"

        if self.role in ("agent", "result"):
            prefix = f"[bold {S}]{self.agent_name or 'Agent'}[/]"
            return f"\n{prefix}: {c}"

        if self.role == "thought":
            label = f"Step {self.step}" if self.step else "Thinking"
            return f"{INDENT}[{D}]{label}:[/] {c}"

        if self.role == "action":
            tool = f"[{W}]{self.tool_name or 'tool'}[/]"
            args = (c[:57] + "...") if len(c) > 60 else c
            label = f"Step {self.step}" if self.step else "Action"
            return f"{INDENT}[{D}]{label}:[/] {tool}({args})"

        if self.role == "observation":
            obs = (c[:497] + "...") if len(c) > 500 else c
            label = f"Step {self.step}" if self.step else "Result"
            return f"{INDENT}[{D}]{label}:[/] {obs}"

        if self.role == "error":
            return f"{INDENT}[{E}]Error:[/] {c}"

        if self.role == "system":
            return f"{INDENT}[{D}]{c}[/]"

        return c


class Conversation(Vertical):
    """Scrollable conversation view. Append-only with RichLog."""

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
        self.log.clear()
