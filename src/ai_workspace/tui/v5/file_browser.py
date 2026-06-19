"""
File Browser (Ctrl+O) — browse project files with DirectoryTree.
"""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import DirectoryTree, Static


class FilesScreen(ModalScreen[str | None]):
    """Browse project files. Returns the selected file path on Enter."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
        Binding("ctrl+o", "dismiss", "Close"),
        Binding("enter", "select", "Open"),
    ]

    def __init__(self, root: str | None = None) -> None:
        super().__init__()
        self._root = root or str(Path.cwd())

    def compose(self) -> ComposeResult:
        with Vertical(id="files-box"):
            yield Static("File Browser", id="files-title")
            yield Static(f"Path: {self._root}", id="files-path")
            yield DirectoryTree(self._root, id="files-tree")

    def on_mount(self) -> None:
        self.query_one("#files-tree", DirectoryTree).focus()

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        self.dismiss(str(event.path))

    def action_select(self) -> None:
        tree = self.query_one("#files-tree", DirectoryTree)
        if tree.cursor_node and tree.cursor_node.is_file:
            self.dismiss(str(tree.cursor_node.path))

    def action_dismiss(self) -> None:
        self.dismiss(None)
