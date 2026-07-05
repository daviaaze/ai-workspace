"""
Command palette — slash-command autocomplete with descriptions.

Appears above the input when typing "/".  ↑↓ navigate · Tab complete · Esc dismiss.
Height-collapse approach: always in layout tree, height:0 when hidden, height:auto
when visible.  Avoids display:none vs display:block layout bugs.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Label, Static

from ai_workspace.tui.command_registry import registry


def _build_commands() -> list[tuple[str, str]]:
    """Build the COMMANDS list lazily from the registry.

    Re-exported for backward compatibility — tests and external code
    reference ``ai_workspace.tui.command_palette.COMMANDS`` as a static
    list of ``(name, description)`` tuples.
    """
    return [(c.name, c.description) for c in registry.all()]


# Lazily-computed COMMANDS tuple list (backward-compat export).
# Accessed via the module attribute; recomputed on first import.
COMMANDS: list[tuple[str, str]] = _build_commands()

C_DIM = "#7C8DB5"
C_PRIMARY = "#5B8DEE"
C_TEXT = "#A0A5B8"
C_HIGHLIGHT = "#5B8DEE 25%"


class CommandPalette(Vertical):
    """Dropdown showing matching slash commands.

    Uses height-collapse for visibility instead of display:none
    to guarantee layout recalculation works correctly.

    Public API:
        filter(text)      — called on Input.Changed; shows/hides/filters
        hide()            — force hide
        selected_command  — currently highlighted command or None
        move_up / move_down — navigate with arrow keys
    """

    DEFAULT_CSS = """
    CommandPalette {
        height: 0;
        min-height: 0;
        max-height: 14;
        border: none;
        margin: 0 2;
        padding: 0;
        overflow: hidden;
    }
    CommandPalette.-visible {
        height: auto;
        border: solid $primary 30%;
        background: $surface;
    }
    CommandPalette Label {
        padding: 0 2;
        width: 1fr;
    }
    """

    matching: reactive[list[tuple[str, str]]] = reactive([], layout=True)
    highlight_index: reactive[int] = reactive(0)

    @property
    def visible(self) -> bool:
        return self.has_class("-visible")

    @visible.setter
    def visible(self, v: bool) -> None:
        self.set_class(v, "-visible")

    def compose(self) -> ComposeResult:
        yield Label("", id="palette-hint")
        yield Static("", id="palette-items")

    # ── Public API ─────────────────────────────────────────────

    def show_all(self) -> None:
        self.matching = [(c.name, c.description) for c in registry.all()]
        self.highlight_index = 0

    def hide(self) -> None:
        self.visible = False
        self.matching = []

    def filter(self, text: str) -> None:
        """Filter by typed prefix.  Call on every keystroke in the input."""
        if not text.startswith("/"):
            self.hide()
            return

        filtered = [(c.name, c.description) for c in registry.filter(text)]
        self.highlight_index = 0
        self.matching = filtered

    @property
    def selected_command(self) -> str | None:
        if 0 <= self.highlight_index < len(self.matching):
            return self.matching[self.highlight_index][0]
        return None

    def dispatch_selected(self) -> str | None:
        """Dispatch the currently selected command and return any error."""
        cmd_name = self.selected_command
        if cmd_name is None:
            return None
        return registry.dispatch(cmd_name)

    def move_up(self) -> None:
        if self.highlight_index > 0:
            self.highlight_index -= 1

    def move_down(self) -> None:
        if self.highlight_index < len(self.matching) - 1:
            self.highlight_index += 1

    # ── Reactives ──────────────────────────────────────────────

    def watch_matching(self, matching: list) -> None:
        if not matching:
            self.visible = False
            return
        self.visible = True
        self._render_items()

    def watch_highlight_index(self, idx: int) -> None:
        self._render_items()

    def _render_items(self) -> None:
        try:
            hint = self.query_one("#palette-hint", Label)
            items = self.query_one("#palette-items", Static)
        except Exception:
            return

        hint.update(
            f"[{C_DIM}]↑↓ navigate  [/][{C_PRIMARY}]Tab[/][{C_DIM}] complete  [/]"
            f"[{C_DIM}]Esc[/][{C_DIM}] dismiss[/]"
        )

        lines: list[str] = []
        for i, (cmd, desc) in enumerate(self.matching):
            if i == self.highlight_index:
                lines.append(
                    f"[on {C_HIGHLIGHT}]"
                    f"[bold {C_PRIMARY}]{cmd}[/]  [{C_DIM}]{desc}[/]"
                )
            else:
                lines.append(
                    f"  [{C_PRIMARY}]{cmd}[/]  [{C_DIM}]{desc}[/]"
                )
        items.update("\n".join(lines))
