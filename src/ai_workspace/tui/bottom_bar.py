"""
Bottom Bar — single-line status + hints + quick input for TUI v3.

Merges the old Footer, bottom status, and command bar into one line:
   2 agents  |  [^S] spawn  [^F] find  [^W] ws  [^G] git  [^Q] quit  |  > _

Design principle (from Posting.sh): "Help bar always visible with
current context actions" — but simplified to one line.
"""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Input, Static


class BottomBar(Horizontal):
    """Single-line bottom bar with status, hints, and quick input."""

    DEFAULT_CSS = """
    BottomBar {
        dock: bottom;
        height: 1;
        background: $surface;
        border-top: solid $primary;
    }

    BottomBar #bb-status {
        width: auto;
        padding: 0 2;
    }

    BottomBar #bb-hints {
        width: 1fr;
        padding: 0 1;
        text-style: dim;
        text-align: center;
    }

    BottomBar #bb-input {
        width: 35;
        background: $panel;
        border: none;
        padding: 0 1;
    }

    BottomBar #bb-input:focus {
        border: none;
        background: $boost;
    }
    """

    agents_online: reactive[int] = reactive(0)
    agents_total: reactive[int] = reactive(0)
    pending_messages: reactive[int] = reactive(0)
    pending_permissions: reactive[int] = reactive(0)

    HINTS = (
        "[^S] spawn  [^F] find  [^W] workspace  "
        "[^G] git  [^D] detail  [^Enter] chat  "
        "[Space] pause  [^X] kill  [^Q] quit"
    )

    def compose(self) -> ComposeResult:
        yield Static(self._render_status(), id="bb-status")
        yield Static(self._render_hints(), id="bb-hints")
        yield Input(placeholder="Task or :command...", id="bb-input")

    def _render_status(self) -> Text:
        if self.agents_total == 0:
            return Text.from_markup("[dim][/]")

        icon = "" if self.agents_online == self.agents_total else (
            "" if self.agents_online > 0 else ""
        )
        parts = [f"{icon} {self.agents_online}/{self.agents_total}"]

        if self.pending_messages > 0:
            parts.append(f"[cyan]{self.pending_messages}[/]")
        if self.pending_permissions > 0:
            parts.append(f"[bold orange1]{self.pending_permissions}[/]")

        return Text.from_markup(" ".join(parts))

    def _render_hints(self) -> str:
        return self.HINTS


    def watch_agents_online(self) -> None:
        self._refresh_status()

    def watch_agents_total(self) -> None:
        self._refresh_status()

    def watch_pending_messages(self) -> None:
        self._refresh_status()

    def watch_pending_permissions(self) -> None:
        self._refresh_status()

    def _refresh_status(self) -> None:
        try:
            self.query_one("#bb-status", Static).update(self._render_status())
        except Exception:
            pass
