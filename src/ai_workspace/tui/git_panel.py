"""
Git Panel — integrated git workflow for the AI Workspace TUI.

Provides:
- Working tree status (modified, staged, untracked files)
- Diff view for selected file
- Commit history log
- Branch info with ahead/behind
- Quick actions: commit, push, pull, stash, checkout

Layout:
┌─ Git ─────────────────────────────────────────────────────────────────┐
│ main ↑2 ↓1  abc1234  [pull] [push] [stash] [commit]                   │
├─────────────────────────────┬─────────────────────────────────────────┤
│ Working Tree (3)            │  Diff: src/auth.py                      │
│  M  src/auth.py             │  ─────────────────────────────────────  │
│  M  src/middleware.py       │  - raise ExpiredTokenError              │
│  ?? tests/test_new.py       │  + return False                         │
│                             │                                         │
│ Staged (1)                  │                                         │
│  A  README.md               │                                         │
│                             │                                         │
│ Recent Commits              │                                         │
│  abc1234 Fix auth bug       │                                         │
│  def5678 Add tests          │                                         │
├─────────────────────────────┴─────────────────────────────────────────┤
│ [^R] refresh  [Enter] diff  [c] commit  [p] push  [l] pull  [s] stash │
└───────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import (
    Button,
    DataTable,
    Input,
    Label,
    Select,
    Static,
)


@dataclass
class GitFile:
    """A single file in the working tree."""
    status: str  # M, A, D, ??, etc.
    path: str
    staged: bool = False


@dataclass
class GitCommit:
    """A single commit."""
    hash: str
    short_hash: str
    message: str
    author: str
    date: str
    refs: str = ""


@dataclass
class GitStatus:
    """Complete git status snapshot."""
    branch: str = ""
    upstream: str = ""
    ahead: int = 0
    behind: int = 0
    detached: bool = False
    commit_hash: str = ""
    modified: list[GitFile] = field(default_factory=list)
    staged: list[GitFile] = field(default_factory=list)
    untracked: list[GitFile] = field(default_factory=list)
    conflicted: list[GitFile] = field(default_factory=list)


class GitDiffView(Static):
    """Right panel showing diff for selected file."""

    DEFAULT_CSS = """
    GitDiffView {
        height: 1fr;
        border: solid $primary-background;
        background: $panel;
        padding: 0 1;
        overflow-y: auto;
    }
    GitDiffView .diff-header {
        text-style: bold;
        background: $boost;
        padding: 0 1;
    }
    GitDiffView .diff-hunk {
        color: $text;
    }
    GitDiffView .diff-add {
        color: $success;
        background: $success 10%;
    }
    GitDiffView .diff-del {
        color: $error;
        background: $error 10%;
    }
    GitDiffView .diff-meta {
        color: $primary;
        text-style: bold;
    }
    """

    file_path: reactive[str] = reactive("")
    diff_content: reactive[str] = reactive("")
    cwd: reactive[str] = reactive(".")

    def render(self) -> Text:
        if not self.file_path:
            return Text.from_markup(
                "[dim]Select a modified file to view diff.[/]\n"
                "[dim]Use [bold]↑↓[/] to navigate the file list.[/]"
            )

        lines = [f"[bold]Diff: {self.file_path}[/]", ""]

        if self.diff_content:
            lines.extend(self._format_diff(self.diff_content))
        else:
            lines.append("[dim]No diff available.[/]")

        return Text.from_markup("\n".join(lines))

    def _format_diff(self, diff: str) -> list[str]:
        """Format diff with colors."""
        result = []
        for line in diff.split("\n")[:200]:  # Limit lines
            if line.startswith("+++") or line.startswith("---"):
                result.append(f"[dim]{line}[/]")
            elif line.startswith("@@"):
                result.append(f"[bold cyan]{line}[/]")
            elif line.startswith("+"):
                result.append(f"[green]{line}[/]")
            elif line.startswith("-"):
                result.append(f"[red]{line}[/]")
            else:
                result.append(f"[dim]{line}[/]")
        if len(diff.split("\n")) > 200:
            result.append("[dim]... (diff truncated)[/]")
        return result

    def load_diff(self, file_path: str, cwd: str = ".") -> None:
        """Load diff for a file."""
        self.file_path = file_path
        self.cwd = cwd
        self.diff_content = self._get_diff(file_path, cwd)
        self.refresh()

    def _get_diff(self, file_path: str, cwd: str) -> str:
        """Run git diff for a file."""
        try:
            result = subprocess.run(
                ["git", "diff", "--no-color", file_path],
                capture_output=True, text=True, cwd=cwd, timeout=5,
            )
            if result.returncode == 0:
                return result.stdout
        except Exception:
            pass
        return ""


class GitFileTable(DataTable):
    """Table of working tree files."""

    DEFAULT_CSS = """
    GitFileTable {
        height: auto;
        max-height: 12;
        border: solid $primary-background;
        background: $panel;
    }
    GitFileTable .datatable--header {
        background: $boost;
        text-style: bold;
    }
    GitFileTable .datatable--cursor {
        background: $accent 30%;
    }
    """

    class Selected(Message):
        def __init__(self, file_path: str, status: str) -> None:
            super().__init__()
            self.file_path = file_path
            self.status = status

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.add_columns("Status", "File")
        self.cursor_type = "row"
        self.zebra_stripes = True

    def update_files(self, files: list[GitFile]) -> None:
        self.clear()
        for f in files:
            status_color = {
                "M": "[yellow]",
                "A": "[green]",
                "D": "[red]",
                "??": "[dim]",
                "R": "[cyan]",
                "C": "[cyan]",
                "U": "[bold red]",
            }.get(f.status, "")
            self.add_row(f"{status_color}{f.status}[/]", f.path)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        try:
            row = self.get_row_at(event.cursor_row)
            if row:
                status = str(row[0]).strip()
                path = str(row[1]).strip()
                self.post_message(self.Selected(path, status))
        except Exception:
            pass


class GitCommitLog(Static):
    """Scrollable commit history."""

    DEFAULT_CSS = """
    GitCommitLog {
        height: 1fr;
        border: solid $primary-background;
        background: $panel;
        padding: 0 1;
        overflow-y: auto;
    }
    GitCommitLog .commit-row {
        height: 1;
        padding: 0 1;
    }
    GitCommitLog .commit-hash {
        color: $primary;
        text-style: bold;
    }
    GitCommitLog .commit-msg {
        color: $text;
    }
    GitCommitLog .commit-author {
        color: $text-disabled;
    }
    """

    commits: reactive[list[GitCommit]] = reactive([])
    max_display: int = 20

    def render(self) -> Text:
        if not self.commits:
            return Text.from_markup("[dim]No commits yet.[/]")

        lines = ["[bold]Recent Commits[/]", ""]
        for c in self.commits[:self.max_display]:
            refs = f" [cyan]{c.refs}[/]" if c.refs else ""
            lines.append(
                f"  [bold]{c.short_hash}[/]  {c.message[:50]}{refs}\n"
                f"     [dim]{c.author}  {c.date}[/]"
            )

        if len(self.commits) > self.max_display:
            lines.append(f"[dim]  ... and {len(self.commits) - self.max_display} more[/]")

        return Text.from_markup("\n".join(lines))


class GitStatusBar(Static):
    """Compact git status header."""

    branch: reactive[str] = reactive("")
    upstream: reactive[str] = reactive("")
    ahead: reactive[int] = reactive(0)
    behind: reactive[int] = reactive(0)
    commit_hash: reactive[str] = reactive("")
    modified_count: reactive[int] = reactive(0)
    staged_count: reactive[int] = reactive(0)
    untracked_count: reactive[int] = reactive(0)

    def render(self) -> Text:
        parts = []

        if self.branch:
            parts.append(f"[bold cyan] {self.branch}[/]")
        if self.commit_hash:
            parts.append(f"[dim] {self.commit_hash[:7]}[/]")

        if self.ahead > 0 or self.behind > 0:
            sync = []
            if self.ahead > 0:
                sync.append(f"[green]↑{self.ahead}[/]")
            if self.behind > 0:
                sync.append(f"[red]↓{self.behind}[/]")
            parts.append(" ".join(sync))

        if self.upstream:
            parts.append(f"[dim]→ {self.upstream}[/]")

        changes = []
        if self.modified_count > 0:
            changes.append(f"[yellow]~{self.modified_count}[/]")
        if self.staged_count > 0:
            changes.append(f"[green]+{self.staged_count}[/]")
        if self.untracked_count > 0:
            changes.append(f"[dim]?{self.untracked_count}[/]")
        if changes:
            parts.append(" ".join(changes))

        return Text.from_markup("  ".join(parts)) if parts else Text.from_markup("[dim]Not a git repository[/]")


class GitPanel(Vertical):
    """Full git integration view."""

    DEFAULT_CSS = """
    GitPanel {
        height: 1fr;
        padding: 1;
    }

    GitPanel #git-toolbar {
        height: auto;
        padding: 0 0 1 0;
    }

    GitPanel #git-toolbar Button {
        margin: 0 1 0 0;
    }

    GitPanel #git-body {
        height: 1fr;
    }

    GitPanel #git-left {
        width: 45%;
        height: 1fr;
    }

    GitPanel #git-right {
        width: 55%;
        height: 1fr;
    }
    """

    cwd: reactive[str] = reactive(".")
    git_status: reactive[GitStatus | None] = reactive(None)

    def __init__(self, cwd: str = ".", **kwargs) -> None:
        super().__init__(**kwargs)
        self.cwd = cwd

    def compose(self) -> ComposeResult:
        with Horizontal(id="git-toolbar"):
            yield GitStatusBar(id="git-status-bar")
            yield Button("🔄 Pull", id="git-pull", variant="default")
            yield Button("⬆ Push", id="git-push", variant="default")
            yield Button("💾 Stash", id="git-stash", variant="default")
            yield Button("📝 Commit", id="git-commit", variant="primary")
            yield Button("🔄 Refresh", id="git-refresh", variant="default")

        with Horizontal(id="git-body"):
            with Vertical(id="git-left"):
                yield Label("[bold]Modified[/]")
                yield GitFileTable(id="git-modified")
                yield Label("[bold]Staged[/]")
                yield GitFileTable(id="git-staged")
                yield Label("[bold]Untracked[/]")
                yield GitFileTable(id="git-untracked")
                yield GitCommitLog(id="git-commits")

            with Vertical(id="git-right"):
                yield GitDiffView(id="git-diff")

    def on_mount(self) -> None:
        self.refresh_git()

    def refresh_git(self) -> None:
        """Load current git status."""
        status = self._get_git_status(self.cwd)
        self.git_status = status

        # Update status bar
        try:
            bar = self.query_one("#git-status-bar", GitStatusBar)
            bar.branch = status.branch
            bar.upstream = status.upstream
            bar.ahead = status.ahead
            bar.behind = status.behind
            bar.commit_hash = status.commit_hash
            bar.modified_count = len(status.modified)
            bar.staged_count = len(status.staged)
            bar.untracked_count = len(status.untracked)
        except NoMatches:
            pass

        # Update file tables
        try:
            self.query_one("#git-modified", GitFileTable).update_files(status.modified)
        except NoMatches:
            pass
        try:
            self.query_one("#git-staged", GitFileTable).update_files(status.staged)
        except NoMatches:
            pass
        try:
            self.query_one("#git-untracked", GitFileTable).update_files(status.untracked)
        except NoMatches:
            pass

        # Update commits
        try:
            commits = self._get_commits(self.cwd)
            self.query_one("#git-commits", GitCommitLog).commits = commits
        except NoMatches:
            pass

    def _get_git_status(self, cwd: str) -> GitStatus:
        """Parse git status."""
        result = GitStatus()

        # Branch info
        try:
            r = subprocess.run(
                ["git", "status", "--branch", "--porcelain"],
                capture_output=True, text=True, cwd=cwd, timeout=5,
            )
            if r.returncode != 0:
                return result

            lines = r.stdout.strip().split("\n")
            for line in lines:
                if line.startswith("## "):
                    # Parse branch line: ## main...origin/main [ahead 2, behind 1]
                    branch_info = line[3:]
                    if "..." in branch_info:
                        result.branch, rest = branch_info.split("...", 1)
                        if " [" in rest:
                            result.upstream, ahead_behind = rest.split(" [", 1)
                            ahead_behind = ahead_behind.rstrip("]")
                            if "ahead " in ahead_behind:
                                try:
                                    result.ahead = int(ahead_behind.split("ahead ")[1].split(",")[0].split("]")[0])
                                except (ValueError, IndexError):
                                    pass
                            if "behind " in ahead_behind:
                                try:
                                    result.behind = int(ahead_behind.split("behind ")[1].split(",")[0].split("]")[0])
                                except (ValueError, IndexError):
                                    pass
                        else:
                            result.upstream = rest
                    else:
                        result.branch = branch_info
                elif line.startswith("?? "):
                    result.untracked.append(GitFile("??", line[3:]))
                elif len(line) >= 2:
                    index_status = line[0]
                    worktree_status = line[1]
                    path = line[3:]
                    if index_status != " " and index_status != "?":
                        result.staged.append(GitFile(index_status, path, staged=True))
                    if worktree_status != " " and worktree_status != "?":
                        result.modified.append(GitFile(worktree_status, path))

        except Exception:
            pass

        # Current commit hash
        try:
            r = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, cwd=cwd, timeout=2,
            )
            if r.returncode == 0:
                result.commit_hash = r.stdout.strip()
        except Exception:
            pass

        return result

    def _get_commits(self, cwd: str, limit: int = 20) -> list[GitCommit]:
        """Get recent commits."""
        commits = []
        try:
            r = subprocess.run(
                ["git", "log", f"--pretty=format:%H|%h|%s|%an|%ar|%D", f"-n{limit}"],
                capture_output=True, text=True, cwd=cwd, timeout=5,
            )
            if r.returncode == 0:
                for line in r.stdout.strip().split("\n"):
                    parts = line.split("|", 5)
                    if len(parts) >= 5:
                        commits.append(GitCommit(
                            hash=parts[0],
                            short_hash=parts[1],
                            message=parts[2],
                            author=parts[3],
                            date=parts[4],
                            refs=parts[5] if len(parts) > 5 else "",
                        ))
        except Exception:
            pass
        return commits

    @on(GitFileTable.Selected)
    def on_file_selected(self, event: GitFileTable.Selected) -> None:
        """Show diff for selected file."""
        try:
            diff_view = self.query_one("#git-diff", GitDiffView)
            diff_view.load_diff(event.file_path, self.cwd)
        except NoMatches:
            pass

    @on(Button.Pressed, "#git-refresh")
    def on_refresh(self, event: Button.Pressed) -> None:
        self.refresh_git()
        self.notify("Git status refreshed", severity="information")

    @on(Button.Pressed, "#git-pull")
    def on_pull(self, event: Button.Pressed) -> None:
        self._run_git_cmd(["git", "pull"], "Pulled latest changes")

    @on(Button.Pressed, "#git-push")
    def on_push(self, event: Button.Pressed) -> None:
        self._run_git_cmd(["git", "push"], "Pushed commits")

    @on(Button.Pressed, "#git-stash")
    def on_stash(self, event: Button.Pressed) -> None:
        self._run_git_cmd(["git", "stash", "push", "-m", "aiw stash"], "Stashed changes")

    @on(Button.Pressed, "#git-commit")
    def on_commit(self, event: Button.Pressed) -> None:
        """Open commit dialog or quick commit."""
        # For now, just notify — full commit UI would need a modal
        self.notify("Use terminal to commit: git commit -m '...'", severity="warning")

    def _run_git_cmd(self, cmd: list[str], success_msg: str) -> None:
        """Run a git command and notify result."""
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=self.cwd, timeout=30,
            )
            if result.returncode == 0:
                self.notify(success_msg, severity="information")
                self.refresh_git()
            else:
                err = result.stderr.strip()[:100] if result.stderr else "Unknown error"
                self.notify(f"Git error: {err}", severity="error")
        except Exception as e:
            self.notify(f"Git error: {e}", severity="error")

    def action_refresh(self) -> None:
        self.refresh_git()
