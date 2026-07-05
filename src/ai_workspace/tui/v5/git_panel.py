"""
Git Panel (Ctrl+G) — show git status, branch, recent log.
Quick snapshot, not a full lazygit replacement.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static


class GitScreen(ModalScreen[None]):
    """Git status overlay — branch, status, recent log."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
        Binding("ctrl+g", "dismiss", "Close"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self, cwd: str | None = None) -> None:
        super().__init__()
        self._cwd = cwd or str(Path.cwd())

    def compose(self) -> ComposeResult:
        with Vertical(id="git-box"):
            yield Static("Git Status", id="git-title")
            yield Static("Loading...", id="git-output")

    def on_mount(self) -> None:
        self._refresh()

    def action_refresh(self) -> None:
        self._refresh()

    def action_dismiss(self) -> None:
        self.dismiss()

    def _refresh(self) -> None:
        lines = []
        try:
            # Branch
            r = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, cwd=self._cwd, timeout=3,
            )
            branch = r.stdout.strip() or "(detached)"
            lines.append(f"[bold $primary]Branch:[/] [$text]{branch}[/]")

            # Status
            r = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True, text=True, cwd=self._cwd, timeout=3,
            )
            if r.stdout.strip():
                lines.append("\n[bold $primary]Changes:[/]")
                for line in r.stdout.splitlines()[:30]:
                    color = "$error" if line.startswith(("M ", " D")) else "$warning"
                    lines.append(f"  [{color}]{line}[/]")
                if len(r.stdout.splitlines()) > 30:
                    lines.append("  [$text 40%]... truncated[/]")
            else:
                lines.append("\n[$success]Clean working tree[/]")

            # Recent log
            r = subprocess.run(
                ["git", "log", "--oneline", "-10"],
                capture_output=True, text=True, cwd=self._cwd, timeout=3,
            )
            if r.stdout.strip():
                lines.append("\n[bold $primary]Recent commits:[/]")
                for line in r.stdout.splitlines():
                    lines.append(f"  [$text 60%]{line}[/]")

        except FileNotFoundError:
            lines.append("[$error]git not found[/]")
        except subprocess.TimeoutExpired:
            lines.append("[$error]git timed out[/]")
        except Exception as e:
            lines.append(f"[$error]Error: {e}[/]")

        self.query_one("#git-output", Static).update("\n".join(lines))
