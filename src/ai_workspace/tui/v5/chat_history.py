"""
Chat History (F2) — list recent sessions from JSON storage.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

from ai_workspace.tui.v5 import sessions as tui_sessions


class ChatScreen(ModalScreen[str | None]):
    """Recent conversation sessions. Click to load, or press L to load."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
        Binding("f2", "dismiss", "Close"),
        Binding("r", "refresh", "Refresh"),
        Binding("d", "delete", "Delete"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="chat-box"):
            yield Static("Chat History", id="chat-title")
            yield Static("Loading...", id="chat-list")

    def on_mount(self) -> None:
        self._load()

    def action_refresh(self) -> None:
        self._load()

    def action_delete(self) -> None:
        """Delete selected session."""
        # For now, delete the oldest session
        sessions = tui_sessions.list_sessions(limit=1)
        if sessions:
            tui_sessions.delete_session(sessions[0]["id"])
            self._load()

    def action_dismiss(self) -> None:
        self.dismiss()

    def _load(self) -> None:
        lines = []
        try:
            sessions = tui_sessions.list_sessions(limit=20)
            if not sessions:
                self.query_one("#chat-list", Static).update("  [$text 50%]No saved sessions[/]")
                return

            for s in sessions:
                sid = s.get("id", "?")[:8]
                summary = s.get("summary", "?")[:70]
                model = s.get("model", "?")
                count = s.get("entry_count", 0)
                lines.append(
                    f"  [$text 70%]{sid}[/] "
                    f"[$text 80%]{summary}[/] "
                    f"[$text 40%]{model} ({count} msgs)[/]"
                )
        except Exception as e:
            lines.append(f"  [$error]Error: {e}[/]")

        self.query_one("#chat-list", Static).update(
            "\n".join(lines) if lines else "  [$text 50%]No sessions[/]"
        )
