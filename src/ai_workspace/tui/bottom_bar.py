"""
Bottom Bar — context-aware status and keybinding hints.

Replaces the old single-line command bar with:
- Left: Agent status summary (always visible)
- Center: Context-aware keybinding hints (changes per tab)
- Right: Notification / quick input area

The hints change based on which tab is active, so users always see
relevant shortcuts without memorizing everything.
"""

from __future__ import annotations

from typing import Any

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Input, Static


class BottomBar(Horizontal):
    """Context-aware bottom bar with agent status and key hints."""

    DEFAULT_CSS = """
    BottomBar {
        dock: bottom;
        height: auto;
        background: $boost;
        border-top: solid $primary-background;
    }

    BottomBar #bb-status {
        width: auto;
        padding: 0 2;
        text-style: bold;
    }

    BottomBar #bb-hints {
        width: 1fr;
        padding: 0 2;
        text-style: dim;
        text-align: center;
    }

    BottomBar #bb-input {
        width: 40;
        background: $surface;
        border: solid $primary-background;
    }

    BottomBar #bb-input:focus {
        border: solid $primary;
    }
    """

    # Agent status reactives
    agents_online: reactive[int] = reactive(0)
    agents_total: reactive[int] = reactive(0)
    pending_messages: reactive[int] = reactive(0)
    pending_permissions: reactive[int] = reactive(0)

    # Context
    current_tab: reactive[str] = reactive("dashboard")

    # Hint templates per tab
    HINTS: dict[str, str] = {
        "dashboard": "[^S] spawn  [^N] task  [^F] find  [^W] workspace  [^Q] quit",
        "agents": "[↑↓] select  [^S] spawn  [Space] pause  [^X] kill  [^Enter] chat  [^D] detail",
        "tasks": "[↑↓] select  [^N] new  [Enter] detail  [Space] toggle  [^F] filter",
        "git": "[↑↓] select  [Enter] diff  [^R] refresh  [p] pull  [P] push  [c] commit",
        "chat": "[^Enter] send  [^N] newline  [^P] history  [^E] context  [^L] back",
        "search": "[↑↓] select  [Enter] open  [^N/^P] source  [Esc] close",
        "metrics": "[↑↓] scroll  [^M/Esc] close  [r] refresh",
    }

    def compose(self) -> ComposeResult:
        yield Static(self._render_status(), id="bb-status")
        yield Static(self._render_hints(), id="bb-hints")
        yield Input(placeholder="Quick command...", id="bb-input")

    def _render_status(self) -> Text:
        """Render agent status on the left."""
        if self.agents_total == 0:
            return Text.from_markup("[dim]○ No agents[/]")

        icon = "⚡" if self.agents_online == self.agents_total else (
            "🟡" if self.agents_online > 0 else "○"
        )

        parts = [f"{icon} {self.agents_online}/{self.agents_total} agents"]

        if self.pending_messages > 0:
            parts.append(f"[cyan]📨 {self.pending_messages}[/]")
        if self.pending_permissions > 0:
            parts.append(f"[bold orange1]🔒 {self.pending_permissions}[/]")

        return Text.from_markup("  ".join(parts))

    def _render_hints(self) -> Text:
        """Render context-aware keybinding hints."""
        hints = self.HINTS.get(self.current_tab, self.HINTS["dashboard"])
        return Text.from_markup(f"[dim]{hints}[/]")

    def watch_agents_online(self) -> None:
        self._refresh_status()

    def watch_agents_total(self) -> None:
        self._refresh_status()

    def watch_pending_messages(self) -> None:
        self._refresh_status()

    def watch_pending_permissions(self) -> None:
        self._refresh_status()

    def watch_current_tab(self) -> None:
        self._refresh_hints()

    def _refresh_status(self) -> None:
        try:
            self.query_one("#bb-status", Static).update(self._render_status())
        except Exception:
            pass

    def _refresh_hints(self) -> None:
        try:
            self.query_one("#bb-hints", Static).update(self._render_hints())
        except Exception:
            pass

    def set_tab(self, tab_id: str) -> None:
        """Update hints for the given tab."""
        self.current_tab = tab_id
