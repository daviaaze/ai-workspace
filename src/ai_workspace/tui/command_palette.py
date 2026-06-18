"""
Command palette — slash-command autocomplete with descriptions.

Appears above the input when typing "/". Filters commands as you type.
↑/↓ navigate · Tab completes · Escape dismisses · Enter completes and submits.
"""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Label, Static

# ── Registry ───────────────────────────────────────────────────────

COMMANDS: list[tuple[str, str]] = [
    ("/help", "Show command reference and key bindings"),
    ("/model ", "Switch LLM model (e.g. /model qwen3:14b)"),
    ("/research ", "Run deep research on a query"),
    ("/tasks", "List all tasks with status"),
    ("/clear", "Clear agent output area"),
    ("/cost", "Show budget and cache statistics"),
    ("/quit", "Exit the TUI"),
]

C_DIM = "#7C8DB5"
C_PRIMARY = "#5B8DEE"
C_TEXT = "#A0A5B8"
C_SURFACE = "#161822"
C_HIGHLIGHT = "#5B8DEE 25%"


class CommandPalette(Vertical):
    """Dropdown showing matching slash commands."""

    DEFAULT_CSS = """
    CommandPalette {
        display: none;
        height: auto;
        max-height: 14;
        background: $surface;
        border: solid $primary 30%;
        margin: 0 2;
    }
    CommandPalette.visible {
        display: block;
    }
    CommandPalette Label {
        padding: 0 2;
        width: 1fr;
    }
    """

    class Selected(Message):
        """User selected a command via Tab."""

        def __init__(self, command: str) -> None:
            super().__init__()
            self.command = command

    matching: reactive[list[tuple[str, str]]] = reactive([])
    highlight_index: reactive[int] = reactive(0)

    def compose(self) -> ComposeResult:
        yield Label("", id="palette-hint")
        yield Static("", id="palette-items")

    def show_all(self) -> None:
        """Show all commands."""
        self.matching = list(COMMANDS)
        self.highlight_index = 0
        self.set_class(True, "visible")

    def hide(self) -> None:
        self.set_class(False, "visible")
        self.matching = []

    def filter(self, text: str) -> None:
        """Filter by typed prefix."""
        if not text.startswith("/"):
            self.hide()
            return
        self.matching = [
            (c, d) for c, d in COMMANDS if c.startswith(text)
        ]
        self.highlight_index = 0
        if self.matching:
            self.set_class(True, "visible")
        else:
            self.hide()

    def watch_matching(self, matching: list) -> None:
        """Render the command list when it changes."""
        try:
            items = self.query_one("#palette-items", Static)
            hint = self.query_one("#palette-hint", Label)
        except Exception:
            return  # Not mounted yet (unit tests)

        if not matching:
            items.update("")
            hint.update("")
            return

        hint.update(
            f"[{C_DIM}]↑↓ navigate  [/][{C_PRIMARY}]Tab[/][{C_DIM}] complete  [/]"
            f"[{C_DIM}]Esc[/][{C_DIM}] dismiss[/]"
        )

        lines: list[str] = []
        for i, (cmd, desc) in enumerate(matching):
            if i == self.highlight_index:
                lines.append(
                    f"[{C_HIGHLIGHT}]"
                    f"[bold {C_PRIMARY}]{cmd}[/]  [{C_DIM}]{desc}[/]"
                    f"[/]"
                )
            else:
                lines.append(
                    f"  [{C_PRIMARY}]{cmd}[/]  [{C_DIM}]{desc}[/]"
                )
        items.update("\n".join(lines))

    def watch_highlight_index(self, idx: int) -> None:
        """Re-render when highlight moves."""
        self.watch_matching(self.matching)

    def move_up(self) -> None:
        if self.highlight_index > 0:
            self.highlight_index -= 1

    def move_down(self) -> None:
        if self.highlight_index < len(self.matching) - 1:
            self.highlight_index += 1

    @property
    def selected_command(self) -> str | None:
        if 0 <= self.highlight_index < len(self.matching):
            return self.matching[self.highlight_index][0]
        return None
