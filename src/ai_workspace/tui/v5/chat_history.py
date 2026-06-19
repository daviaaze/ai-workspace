"""
Chat History (F2) — list recent sessions with preview.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static


class ChatScreen(ModalScreen[None]):
    """Recent chat sessions overlay."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
        Binding("f2", "dismiss", "Close"),
        Binding("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="chat-box"):
            yield Static("Chat History", id="chat-title")
            yield Static("Loading...", id="chat-list")

    def on_mount(self) -> None:
        self._load()

    def action_refresh(self) -> None:
        self._load()

    def action_dismiss(self) -> None:
        self.dismiss()

    def _load(self) -> None:
        lines = []
        try:
            from ai_workspace.core.sessions import SessionStore
            store = SessionStore()
            store.initialize()
            sessions = store.list_sessions(limit=20)
            store.close()

            if not sessions:
                self.query_one("#chat-list", Static).update(
                    "  [$text 50%]No sessions yet[/]"
                )
                return

            for s in sessions:
                sid = (s.get("id") or "?")[:8]
                label = (s.get("label") or s.get("task_summary") or "?")[:60]
                model = s.get("model") or "?"
                lines.append(
                    f"  [$text 70%]{sid}[/] "
                    f"[$text 80%]{label}[/] "
                    f"[$text 40%]{model}[/]"
                )
        except Exception as e:
            lines.append(f"  [$error]Error: {e}[/]")

        self.query_one("#chat-list", Static).update("\n".join(lines) if lines else "  [$text 50%]No sessions[/]")
