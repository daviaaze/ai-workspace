"""
InputBar — task input with slash command support and context-aware help.

Refs: SPEC_TUI_V5.md
"""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Container
from textual.reactive import reactive
from textual.widgets import Input, Label


SLASH_COMMANDS: dict[str, str] = {
    "/help": "Show command reference",
    "/model <name>": "Switch model (e.g. /model qwen3:14b)",
    "/clear": "Clear conversation",
    "/sessions": "List and manage saved sessions",
    "/export": "Export current session to text",
    "/cost": "Show budget and cache stats",
    "/git": "Show git status",
    "/ctx": "Open context inspector",
    "/ctx stats": "Show context statistics",
    "/ctx add <path>": "Add file to context",
    "/ctx remove <path>": "Remove file from context",
    "/ctx list": "List context files",
    "/quit": "Exit",
}


class InputBar(Horizontal):
    """Combined input area with help bar.

    Layout:
      /commands row
      [input field................................] [send]
    """

    DEFAULT_CSS = """
    InputBar {
        dock: bottom;
        height: auto;
        padding: 0 1;
        background: $surface;
        border-top: solid $primary 25%;
        layout: vertical;
    }

    InputBar #help-row {
        height: 1;
        padding: 0 1;
    }

    InputBar #input-row {
        height: auto;
        padding: 0 1;
    }

    InputBar Input {
        width: 1fr;
        background: $background;
        border: solid $primary 20%;
    }

    InputBar Input:focus {
        border: solid $primary 50%;
    }

    InputBar #send-hint {
        width: auto;
        padding: 0 1;
        content-align: right middle;
        color: $text 40%;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "clear_input", "Clear", show=False),
    ]

    agent_running: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        with Container(id="help-row"):
            yield Label(
                "  /help  /model  /clear  /cost  /git  /ctx  /quit  ",
                id="help-label",
            )
        with Horizontal(id="input-row"):
            yield Input(
                placeholder="Type a task or /command...",
                id="task-input",
            )
            yield Label("Enter send", id="send-hint")

    def watch_agent_running(self, running: bool) -> None:
        """Update help bar context based on agent state."""
        if running:
            self.query_one("#help-label", Label).update(
                " Space=pause  Ctrl+K=kill  F2=chat  F3=dashboard  /help"
            )
        else:
            self.query_one("#help-label", Label).update(
                "  /help  /model  /clear  /cost  /git  /ctx  /quit  "
            )

    def action_clear_input(self) -> None:
        """Clear the input field."""
        inp = self.query_one("#task-input", Input)
        inp.value = ""
        inp.focus()

    def focus_input(self) -> None:
        """Focus the task input."""
        self.query_one("#task-input", Input).focus()

    @property
    def input_value(self) -> str:
        return self.query_one("#task-input", Input).value

    @input_value.setter
    def input_value(self, value: str) -> None:
        self.query_one("#task-input", Input).value = value
