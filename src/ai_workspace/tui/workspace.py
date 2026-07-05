"""
Workspace Switcher — quick project/directory switcher for the AI Workspace TUI.

Opened with Ctrl+W. Lists known directories, projects, and git worktrees.
Select to change the TUI's working directory and reload context.

Sources:
- Recent directories (from shell history + known paths)
- Git worktrees (from ProjectManager)
- Projects (from ProjectManager DB)
- Common dev directories (~/Projects, ~/src, ~/dev, etc.)

Layout:
 Switch Workspace
 > ai-workspace                                                    [3/12]

   ~/Projects/ai-workspace                    git:main  project
   ~/Projects/side-project                    git:feat/login
   ~/src/another-repo                         git:dev
   worktree: coding-agent-1                   ~/Projects/aiw/.aiw/wt...
   project: my-saas                          2 repos, 1 agent

 [↑↓] navigate  [Enter] switch  [^W/Esc] close  [^N] add current

"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Input, Label, Static


class WorkspaceKind(Enum):
    DIRECTORY = auto()
    WORKTREE = auto()
    PROJECT = auto()


@dataclass
class WorkspaceEntry:
    """A single workspace entry in the switcher."""
    kind: WorkspaceKind
    path: str
    label: str = ""
    detail: str = ""
    git_branch: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def icon(self) -> str:
        return {
            WorkspaceKind.DIRECTORY: "",
            WorkspaceKind.WORKTREE: "",
            WorkspaceKind.PROJECT: "",
        }.get(self.kind, "•")


class WorkspaceRow(Static):
    """A single row in the workspace switcher."""

    DEFAULT_CSS = """
    WorkspaceRow {
        height: 1;
        padding: 0 2;
    }
    WorkspaceRow.selected {
        background: $accent 30%;
    }
    """

    entry: WorkspaceEntry | None = None
    selected: reactive[bool] = reactive(False)

    def render(self) -> str:
        if not self.entry:
            return ""
        e = self.entry
        git_info = f" [dim]git:{e.git_branch}[/]" if e.git_branch else ""
        detail = f" [dim]{e.detail[:50]}[/]" if e.detail else ""
        path_display = self._shorten_path(e.path or e.label, 50)
        return f" {e.icon} {path_display}{git_info}{detail}"

    @staticmethod
    def _shorten_path(path: str, max_len: int) -> str:
        home = str(Path.home())
        result = path
        if result.startswith(home):
            result = "~" + result[len(home):]
        if len(result) > max_len:
            result = "…" + result[-(max_len - 1):]
        return result


class WorkspaceSwitcher(Static):
    """Workspace switcher overlay — quick directory/project switching."""

    can_focus = True

    DEFAULT_CSS = """
    WorkspaceSwitcher {
        display: none;
        layer: overlay;
        background: $surface;
        border: thick $primary;
        padding: 0 0;
        width: 70%;
        height: 50%;
        dock: top;
        offset-x: 15%;
        offset-y: 4;
        overflow: hidden;
    }
    WorkspaceSwitcher.visible {
        display: block;
    }

    #ws-container {
        height: 1fr;
    }

    #ws-input {
        dock: top;
        height: 2;
        padding: 0 2;
        background: $boost;
        border-bottom: solid $primary 20%;
    }

    #ws-input > Input {
        background: $surface;
        border: solid $primary;
        width: 1fr;
    }

    #ws-results {
        height: 1fr;
        overflow-y: auto;
    }

    #ws-help {
        dock: bottom;
        height: 1;
        padding: 0 2;
        background: $boost;
        border-top: solid $primary 20%;
        text-style: dim;
    }

    #ws-empty {
        padding: 2 4;
        text-style: dim;
        text-align: center;
    }
    """

    class Selected(Message):
        """Posted when a workspace is selected (Enter)."""

        def __init__(self, entry: WorkspaceEntry) -> None:
            super().__init__()
            self.entry = entry

    class Closed(Message):
        """Posted when the switcher is dismissed."""

    def __init__(self, cwd: str = ".", **kwargs) -> None:
        super().__init__(**kwargs)
        self._cwd = cwd
        self._entries: list[WorkspaceEntry] = []
        self._filtered: list[WorkspaceEntry] = []
        self._selected_idx: int = 0
        self._dismissed: bool = False

    def compose(self) -> ComposeResult:
        with Vertical(id="ws-container"):
            with Container(id="ws-input"):
                yield Input(
                    placeholder="Search directories, projects, worktrees...",
                    id="ws-search",
                )
            yield VerticalScroll(id="ws-results")
            yield Label(
                "[dim][↑↓] navigate  [Enter] switch  [^W/Esc] close  [^N] add current[/]",
                id="ws-help",
            )

    def show(self, cwd: str = ".") -> None:
        """Open the workspace switcher with all discovered entries."""
        self._cwd = cwd
        self._dismissed = False
        self.set_class(True, "visible")
        # Build entries (directory scans may be slow for large trees)
        try:
            container = self.query_one("#ws-results", VerticalScroll)
            container.mount(Label("Scanning directories…", id="ws-loading"))
        except NoMatches:
            pass
        self.call_later(self._do_show)

    def hide(self) -> None:
        """Close the switcher."""
        self._dismissed = True
        self.set_class(False, "visible")
        self.post_message(self.Closed())

    def _do_show(self) -> None:
        """Perform actual entry discovery and rendering (deferred)."""
        if self._dismissed:
            return
        # Remove loading indicator
        try:
            container = self.query_one("#ws-results", VerticalScroll)
            for child in list(container.children):
                if hasattr(child, 'id') and child.id == "ws-loading":
                    child.remove()
        except NoMatches:
            pass
        self._build_entries()
        self._filter("")
        try:
            self.query_one("#ws-search", Input).focus()
        except NoMatches:
            pass


    def _build_entries(self) -> None:
        """Discover all workspace entries."""
        self._entries = []

        # 1. Current directory
        cwd_abs = str(Path(self._cwd).expanduser().resolve())
        self._entries.append(WorkspaceEntry(
            kind=WorkspaceKind.DIRECTORY,
            path=cwd_abs,
            git_branch=self._detect_git_branch(cwd_abs),
            label=cwd_abs,
        ))

        # 2. Common dev directories
        common = [
            os.path.expanduser("~/Projects"),
            os.path.expanduser("~/src"),
            os.path.expanduser("~/dev"),
            os.path.expanduser("~/code"),
            os.path.expanduser("~/workspace"),
        ]
        seen = {cwd_abs}
        for base in common:
            if not os.path.isdir(base):
                continue
            try:
                for entry in os.scandir(base):
                    if entry.is_dir() and not entry.name.startswith('.'):
                        abs_path = os.path.abspath(entry.path)
                        if abs_path not in seen:
                            seen.add(abs_path)
                            branch = self._detect_git_branch(abs_path)
                            detail = ""
                            if branch:
                                detail = f"git:{branch}"
                            self._entries.append(WorkspaceEntry(
                                kind=WorkspaceKind.DIRECTORY,
                                path=abs_path,
                                git_branch=branch,
                                label=abs_path,
                                detail=detail,
                            ))
            except PermissionError:
                pass

        # 3. Git worktrees
        self._entries.extend(self._scan_worktrees())

        # 4. Projects from ProjectManager
        self._entries.extend(self._scan_projects())

    def _detect_git_branch(self, directory: str) -> str:
        """Detect the current git branch for a directory."""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True,
                cwd=directory, timeout=2,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass
        return ""

    def _scan_worktrees(self) -> list[WorkspaceEntry]:
        """Scan for git worktrees in common locations."""
        entries: list[WorkspaceEntry] = []
        # Check .aiw/worktrees in common directories
        common_bases = [
            os.path.expanduser("~/Projects"),
            os.path.expanduser("~/src"),
            os.path.expanduser("~"),
        ]
        seen = set()
        for base in common_bases:
            wt_dir = os.path.join(base, ".aiw", "worktrees")
            if not os.path.isdir(wt_dir):
                continue
            try:
                for entry in os.scandir(wt_dir):
                    if entry.is_dir():
                        abs_path = os.path.abspath(entry.path)
                        if abs_path not in seen:
                            seen.add(abs_path)
                            branch = self._detect_git_branch(abs_path)
                            entries.append(WorkspaceEntry(
                                kind=WorkspaceKind.WORKTREE,
                                path=abs_path,
                                label=entry.name,
                                git_branch=branch,
                                detail=abs_path,
                            ))
            except PermissionError:
                pass
        return entries

    def _scan_projects(self) -> list[WorkspaceEntry]:
        """Scan for projects from the ProjectManager database."""
        entries: list[WorkspaceEntry] = []
        try:
            from ai_workspace.core.projects import ProjectManager
            pm = ProjectManager()
            pm.initialize()
            projects = pm.list_projects()
            for p in projects:
                repo_count = len(p.repos)
                agent_count = len(p.agents)
                detail_parts = []
                if repo_count:
                    detail_parts.append(f"{repo_count} repos")
                if agent_count:
                    detail_parts.append(f"{agent_count} agents")
                entries.append(WorkspaceEntry(
                    kind=WorkspaceKind.PROJECT,
                    path=p.repos[0].path if p.repos else "",
                    label=p.name,
                    detail=", ".join(detail_parts) if detail_parts else p.description[:60],
                    data={"project": p},
                ))
        except Exception:
            pass
        return entries


    def _filter(self, query: str) -> None:
        """Filter entries by query string."""
        q = query.strip().lower()

        if not q:
            self._filtered = list(self._entries)
        else:
            self._filtered = []
            for e in self._entries:
                search_text = f"{e.label} {e.path} {e.detail} {e.git_branch}".lower()
                if q in search_text:
                    self._filtered.append(e)

        self._selected_idx = 0
        self._render_results()

    def _render_results(self) -> None:
        """Render the filtered results."""
        try:
            container = self.query_one("#ws-results", VerticalScroll)
        except NoMatches:
            return

        # Remove old rows
        for child in list(container.children):
            if isinstance(child, WorkspaceRow):
                child.remove()

        try:
            container.query_one("#ws-empty").remove()
        except NoMatches:
            pass

        if not self._filtered:
            container.mount(Label(
                "No workspaces found. Type to filter, or Ctrl+N to add current directory.",
                id="ws-empty",
            ))
            return

        for i, e in enumerate(self._filtered[:50]):
            row = WorkspaceRow()
            row.entry = e
            row.selected = (i == self._selected_idx)
            container.mount(row)


    @on(Input.Changed, "#ws-search")
    def on_search_changed(self, event: Input.Changed) -> None:
        self._filter(event.value)

    @on(Input.Submitted, "#ws-search")
    def on_search_submitted(self, event: Input.Submitted) -> None:
        if self._filtered:
            self._select(0)

    def key_up(self) -> None:
        if self._filtered:
            self._selected_idx = max(0, self._selected_idx - 1)
            self._render_results()

    def key_down(self) -> None:
        if self._filtered:
            self._selected_idx = min(len(self._filtered) - 1, self._selected_idx + 1)
            self._render_results()

    def key_enter(self) -> None:
        self._select(self._selected_idx)

    def key_escape(self) -> None:
        self.hide()

    def _select(self, idx: int) -> None:
        """Select a workspace entry."""
        if 0 <= idx < len(self._filtered):
            self.post_message(self.Selected(self._filtered[idx]))
            self.hide()
