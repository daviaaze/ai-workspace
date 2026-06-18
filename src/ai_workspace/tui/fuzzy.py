"""
Fuzzy Finder — fzf-style search for the AI Workspace TUI.

Opened with Ctrl+F. Type to fuzzy-filter across multiple sources:
- Files in the current working directory
- Tasks (from DB or task panel)
- Agent sessions (from SessionStore)
- Commands (built-in command palette)

Uses difflib.SequenceMatcher for zero-dependency fuzzy matching.

Layout:
 Fuzzy Find 
 > auth mid                                                           [3/15]

   src/auth/middleware.py                              (score: 0.85)       
   Fix auth middleware bug          ongoing  coding     (score: 0.72)      
   session:abc123  "Fix auth..."   12 entries           (score: 0.68)      
   :spawn coding --task "Fix auth"                      (score: 0.55)      

 [↑↓] navigate  [Enter] open  [^F/Esc] close  [^N/^P] next/prev source     

"""

from __future__ import annotations

import difflib
import os
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


class ResultKind(Enum):
    FILE = auto()
    TASK = auto()
    SESSION = auto()
    COMMAND = auto()
    MEMORY = auto()
    KNOWLEDGE = auto()


RESULT_ICONS: dict[ResultKind, str] = {
    ResultKind.FILE: "",
    ResultKind.TASK: "",
    ResultKind.SESSION: "",
    ResultKind.COMMAND: "",
    ResultKind.MEMORY: "",
    ResultKind.KNOWLEDGE: "",
}


@dataclass
class FuzzyResult:
    """A single search result."""
    kind: ResultKind
    label: str                # Primary display text
    detail: str = ""          # Secondary info (path, status, etc.)
    score: float = 0.0        # Match score 0.0-1.0
    data: dict[str, Any] = field(default_factory=dict)  # For callback

    @property
    def icon(self) -> str:
        return RESULT_ICONS.get(self.kind, "•")


class FuzzyResultRow(Static):
    """A single row in the fuzzy finder results list."""

    DEFAULT_CSS = """
    FuzzyResultRow {
        height: 1;
        padding: 0 2;
    }
    FuzzyResultRow.selected {
        background: $accent 30%;
    }
    """

    result: FuzzyResult | None = None
    selected: reactive[bool] = reactive(False)

    def render(self) -> str:
        if not self.result:
            return ""
        r = self.result
        score_str = f"[dim]({r.score:.0%})[/]" if r.score > 0 else ""
        detail = f" [dim]{r.detail[:60]}[/]" if r.detail else ""
        return f" {r.icon} {r.label[:80]}{detail}  {score_str}"


class FuzzyFinder(Static):
    """Fuzzy search modal — fzf-style search across files, tasks, sessions.

    Overlays the main UI. Type to filter results in real-time.
    Enter opens the selected result. Escape closes.
    """

    can_focus = True

    DEFAULT_CSS = """
    FuzzyFinder {
        display: none;
        layer: overlay;
        background: $surface;
        border: thick $primary;
        padding: 0 0;
        width: 70%;
        height: 60%;
        dock: top;
        offset-x: 15%;
        offset-y: 3;
        overflow: hidden;
    }
    FuzzyFinder.visible {
        display: block;
    }

    #fuzzy-container {
        height: 1fr;
    }

    #fuzzy-input {
        dock: top;
        height: 3;
        padding: 0 2;
        background: $boost;
        border-bottom: solid $primary 20%;
    }

    #fuzzy-input > Input {
        background: $surface;
        border: solid $primary;
        width: 1fr;
    }

    #fuzzy-input > Label {
        height: 1;
        padding: 0 1;
        text-style: dim;
    }

    #fuzzy-results {
        height: 1fr;
        overflow-y: auto;
    }

    #fuzzy-help {
        dock: bottom;
        height: 1;
        padding: 0 2;
        background: $boost;
        border-top: solid $primary 20%;
        text-style: dim;
    }

    #fuzzy-empty {
        padding: 2 4;
        text-style: dim;
        text-align: center;
    }
    """

    class Selected(Message):
        """Posted when a result is selected (Enter)."""

        def __init__(self, result: FuzzyResult) -> None:
            super().__init__()
            self.result = result

    class Closed(Message):
        """Posted when the finder is dismissed."""

    def __init__(
        self,
        cwd: str = ".",
        tasks: list[dict] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._cwd = cwd
        self._tasks = tasks or []
        self._all_results: list[FuzzyResult] = []
        self._filtered_results: list[FuzzyResult] = []
        self._selected_idx: int = 0
        self._source_filter: ResultKind | None = None
        self._dismissed: bool = False

    def compose(self) -> ComposeResult:
        with Vertical(id="fuzzy-container"):
            with Container(id="fuzzy-input"):
                yield Input(
                    placeholder="Search files, tasks, sessions, commands...",
                    id="fuzzy-search",
                )
                yield Label(
                    "[dim][↑↓] navigate  [Enter] open  [^F/Esc] close  "
                    "[^N] next source  [^P] prev source[/]",
                )
            yield VerticalScroll(id="fuzzy-results")
            yield Label(
                "[dim]Sources: all  [^N/^P] filter by source[/]",
                id="fuzzy-help",
            )


    def show(self, cwd: str = ".", tasks: list[dict] | None = None) -> None:
        """Open the fuzzy finder and build the initial result set."""
        self._cwd = cwd
        self._tasks = tasks or []
        self._source_filter = None
        self._dismissed = False
        self.set_class(True, "visible")
        # Build results (file scan + DB queries may take a moment)
        self._build_all_results()
        self._filter("")
        try:
            self.query_one("#fuzzy-search", Input).focus()
        except NoMatches:
            pass

    def hide(self) -> None:
        """Close the fuzzy finder."""
        self._dismissed = True
        self.set_class(False, "visible")
        self.post_message(self.Closed())

    def refresh_sources(self, cwd: str = "", tasks: list[dict] | None = None) -> None:
        """Refresh data sources without reopening."""
        if cwd:
            self._cwd = cwd
        if tasks is not None:
            self._tasks = tasks
        if self.has_class("visible"):
            self._build_all_results()
            try:
                query = self.query_one("#fuzzy-search", Input).value
            except NoMatches:
                query = ""
            self._filter(query)


    def _build_all_results(self) -> None:
        """Build the full result set from all enabled sources."""
        self._all_results = []

        # 1. Files in CWD
        self._all_results.extend(self._scan_files())

        # 2. Tasks
        self._all_results.extend(self._scan_tasks())

        # 3. Sessions
        self._all_results.extend(self._scan_sessions())

        # 4. Commands
        self._all_results.extend(self._scan_commands())

    def _scan_files(self, max_depth: int = 3, max_files: int = 500) -> list[FuzzyResult]:
        """Scan files in the current working directory."""
        results: list[FuzzyResult] = []
        cwd_path = Path(self._cwd).expanduser().resolve()
        if not cwd_path.is_dir():
            return results

        # Ignore patterns
        ignore_dirs = {'.git', '__pycache__', '.venv', 'node_modules', '.mypy_cache',
                       '.pytest_cache', '.ruff_cache', 'dist', 'build', '.direnv',
                       'result', 'data', '.agents'}
        ignore_extensions = {'.pyc', '.pyo', '.so', '.o', '.dylib', '.bin'}

        count = 0
        for root, dirs, files in os.walk(cwd_path):
            # Filter dirs in-place
            dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]

            depth = len(Path(root).relative_to(cwd_path).parts)
            if depth > max_depth:
                dirs[:] = []
                continue

            for f in files:
                if count >= max_files:
                    return results
                file_path = Path(root) / f
                if file_path.suffix in ignore_extensions:
                    continue
                rel_path = str(file_path.relative_to(cwd_path))
                results.append(FuzzyResult(
                    kind=ResultKind.FILE,
                    label=f,
                    detail=rel_path,
                    data={"path": str(file_path), "rel_path": rel_path},
                ))
                count += 1

        return results

    def _scan_tasks(self) -> list[FuzzyResult]:
        """Scan tasks from the provided task list."""
        results: list[FuzzyResult] = []
        for t in self._tasks:
            title = t.get("title", "")
            status = t.get("status", "")
            agent = t.get("agent", "")
            detail_parts = []
            if status:
                detail_parts.append(status)
            if agent:
                detail_parts.append(agent)
            results.append(FuzzyResult(
                kind=ResultKind.TASK,
                label=title,
                detail=" · ".join(detail_parts),
                data={"task_id": t.get("id", ""), "task": t},
            ))
        return results

    def _scan_sessions(self, limit: int = 50) -> list[FuzzyResult]:
        """Scan recent sessions from the session store."""
        results: list[FuzzyResult] = []
        try:
            from ai_workspace.core.sessions import SessionStore
            store = SessionStore()
            store.initialize()
            sessions = store.list_sessions(limit=limit)
            store.close()
            for s in sessions:
                label = s.get("label", "") or "Untitled"
                sid = s.get("id", "")
                entries = s.get("entry_count", 0)
                results.append(FuzzyResult(
                    kind=ResultKind.SESSION,
                    label=label,
                    detail=f"session:{sid[:8]}… {entries}e",
                    data={"session_id": sid, "session": s},
                ))
        except Exception:
            pass
        return results

    def _scan_commands(self) -> list[FuzzyResult]:
        """Built-in command palette entries."""
        commands = [
            ("spawn coding --task \"...\"", "Spawn a coding agent"),
            ("spawn research --task \"...\"", "Spawn a research agent"),
            ("spawn general --task \"...\"", "Spawn a general agent"),
            ("task \"New task title\"", "Create a new task"),
            ("cd ~/projects/...", "Change working directory"),
            ("model qwen3:14b", "Switch model"),
            ("sessions", "List recent sessions"),
            ("thinking on", "Show all thinking"),
            ("thinking off", "Hide all thinking"),
            ("export", "Export current session"),
            ("costs", "Show cost dashboard"),
            ("graph", "Open knowledge graph"),
            ("quit", "Exit AI Workspace"),
        ]
        return [
            FuzzyResult(
                kind=ResultKind.COMMAND,
                label=cmd,
                detail=desc,
                data={"command": cmd},
            )
            for cmd, desc in commands
        ]


    def _filter(self, query: str) -> None:
        """Fuzzy filter results by query and source filter."""
        q = query.strip().lower()

        # Apply source filter
        if self._source_filter:
            candidates = [r for r in self._all_results if r.kind == self._source_filter]
        else:
            candidates = list(self._all_results)

        if not q:
            # No query: show all candidates, sorted by kind
            self._filtered_results = sorted(candidates, key=lambda r: (
                list(ResultKind).index(r.kind), r.label.lower()
            ))
        else:
            # Fuzzy match
            scored: list[tuple[float, FuzzyResult]] = []
            for r in candidates:
                score = self._fuzzy_score(q, r.label.lower())
                if r.detail:
                    detail_score = self._fuzzy_score(q, r.detail.lower())
                    score = max(score, detail_score * 0.8)  # Detail matches counted lower
                if score > 0.15:  # Minimum threshold
                    scored.append((score, r))

            scored.sort(key=lambda x: (-x[0], x[1].label.lower()))
            self._filtered_results = [r for _, r in scored]

        self._selected_idx = 0
        self._render_results()

    def _fuzzy_score(self, query: str, target: str) -> float:
        """Calculate fuzzy match score using SequenceMatcher.

        Also rewards:
        - Prefix matches (query at start of word boundaries)
        - Consecutive character matches (like fzf)
        """
        if not query or not target:
            return 0.0

        # Exact match
        if query == target:
            return 1.0

        # Contains match
        if query in target:
            return 0.7 + 0.3 * (len(query) / len(target))

        # SequenceMatcher
        score = difflib.SequenceMatcher(None, query, target).ratio()

        # Bonus for matching word starts (like fzf)
        words = target.split()
        word_starts = " ".join(w[:len(query)] for w in words)
        if query in word_starts:
            score = max(score, 0.5)

        return score

    def _render_results(self) -> None:
        """Render the filtered results list."""
        try:
            container = self.query_one("#fuzzy-results", VerticalScroll)
        except NoMatches:
            return

        # Remove old rows
        for child in list(container.children):
            if isinstance(child, FuzzyResultRow):
                child.remove()

        # Remove empty message
        try:
            container.query_one("#fuzzy-empty").remove()
        except NoMatches:
            pass

        if not self._filtered_results:
            container.mount(Label(
                f"No results. Type to search across files, tasks, sessions, and commands.",
                id="fuzzy-empty",
            ))
            # Update count
            self._update_count(0)
            return

        # Show up to 100 results
        for i, r in enumerate(self._filtered_results[:100]):
            row = FuzzyResultRow()
            row.result = r
            row.selected = (i == self._selected_idx)
            container.mount(row)

        self._update_count(len(self._filtered_results))

        # Scroll to selected
        try:
            rows = [c for c in container.children if isinstance(c, FuzzyResultRow)]
            if rows and self._selected_idx < len(rows):
                # The container will handle scrolling naturally
                pass
        except Exception:
            pass

    def _update_count(self, total: int) -> None:
        """Update the result count display."""
        try:
            query = self.query_one("#fuzzy-search", Input).value
            count_text = f"{total} results"
            if query:
                count_text = f"{total} results for \"{query[:20]}\""
            source_text = ""
            if self._source_filter:
                source_text = f" [{self._source_filter.name.lower()}]"
            # Find the Label in fuzzy-input and update
            label = self.query_one("#fuzzy-input > Label", Label)
            label.update(f"[dim]{count_text}{source_text}[/]")
        except NoMatches:
            pass


    @on(Input.Changed, "#fuzzy-search")
    def on_search_changed(self, event: Input.Changed) -> None:
        """Re-filter on every keystroke."""
        self._filter(event.value)

    @on(Input.Submitted, "#fuzzy-search")
    def on_search_submitted(self, event: Input.Submitted) -> None:
        """Enter on the input selects the first result."""
        if self._filtered_results:
            self._select_result(0)

    def key_up(self) -> None:
        """Move selection up."""
        if self._filtered_results:
            self._selected_idx = max(0, self._selected_idx - 1)
            self._render_results()

    def key_down(self) -> None:
        """Move selection down."""
        if self._filtered_results:
            self._selected_idx = min(
                len(self._filtered_results) - 1, self._selected_idx + 1
            )
            self._render_results()

    def key_enter(self) -> None:
        """Select the highlighted result."""
        self._select_result(self._selected_idx)

    def key_escape(self) -> None:
        """Close the finder."""
        self.hide()

    def key_f3(self) -> None:
        """Close (alternative to Escape)."""
        self.hide()

    def _select_result(self, idx: int) -> None:
        """Select a result and post the Selected message."""
        if 0 <= idx < len(self._filtered_results):
            result = self._filtered_results[idx]
            self.post_message(self.Selected(result))
            self.hide()

    # Source filter cycling
    def _cycle_source(self, direction: int = 1) -> None:
        """Cycle through source filters: all → file → task → session → command → all."""
        kinds = [None] + list(ResultKind)  # None = all
        if self._source_filter is None:
            current_idx = 0
        else:
            current_idx = kinds.index(self._source_filter) if self._source_filter in kinds else 0

        new_idx = (current_idx + direction) % len(kinds)
        self._source_filter = kinds[new_idx]

        # Re-filter with current query
        try:
            query = self.query_one("#fuzzy-search", Input).value
        except NoMatches:
            query = ""
        self._filter(query)

    # These are bound by the parent app, not directly on FuzzyFinder
    # They're called from app's action handlers
    def cycle_source_next(self) -> None:
        self._cycle_source(1)

    def cycle_source_prev(self) -> None:
        self._cycle_source(-1)
