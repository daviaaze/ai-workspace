"""
Task Table View — full-featured task management with DataTable.

Replaces the cramped sidebar task panel with a full-width view:
- Sortable columns: Status, Title, Agent, Progress, Priority, Schedule
- Inline filtering and search
- Bulk actions (complete, delete, assign)
- Better visibility for task metadata

Layout:
 Tasks
 [New] [Complete] [Delete]  Filter: [________]  Status: [all ]

 Status  Title                Agent      Progress  Priority  Schedule
        Fix auth middleware  coding     []   High    —
        Add TUI tests        coding     []   Med     —
       Set up CI/CD         devops     []   Low     —
       Daily knowledge sync sys        []   Med     0 9 * * *

 [^N] new  [Enter] detail  [^F] filter  [Space] toggle status

"""

from __future__ import annotations

from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import (
    Button,
    DataTable,
    Input,
    Select,
    Static,
)


class TaskTable(DataTable):
    """Sortable, filterable task table."""

    DEFAULT_CSS = """
    TaskTable {
        height: 1fr;
        border: solid $primary 20%;
        background: $panel;
    }
    TaskTable:focus {
        border: solid $accent;
    }
    TaskTable .datatable--header {
        background: $boost;
        text-style: bold;
    }
    TaskTable .datatable--cursor {
        background: $accent 30%;
    }
    """

    class Selected(Message):
        """Posted when a task row is selected."""

        def __init__(self, task_id: str, task: dict[str, Any]) -> None:
            super().__init__()
            self.task_id = task_id
            self.task = task

    class ToggleStatus(Message):
        """Posted when user toggles a task's status."""

        def __init__(self, task_id: str) -> None:
            super().__init__()
            self.task_id = task_id

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._tasks: list[dict[str, Any]] = []
        self._task_rows: dict[str, int] = {}  # task_id -> row key
        self.add_columns("Status", "Title", "Agent", "Progress", "Priority", "Schedule")
        self.cursor_type = "row"
        self.zebra_stripes = True

    def update_tasks(self, tasks: list[dict[str, Any]]) -> None:
        """Refresh the task table."""
        self._tasks = tasks
        self.clear()
        self._task_rows = {}

        priority_map = {0: " Low", 1: " Med", 2: " High", 3: " Urgent"}

        for t in tasks:
            task_id = t.get("id", "")
            status = t.get("status", "notstarted")
            title = t.get("title", "?")[:35]
            agent = t.get("agent", "—")
            progress = t.get("progress", 0)
            priority = t.get("priority", 0)
            schedule = t.get("schedule", "—")

            status_icons = {
                "ongoing": "[green][/]",
                "notstarted": "[dim][/]",
                "completed": "[green][/]",
                "blocked": "[yellow][/]",
                "rejected": "[red][/]",
                "cron": "[cyan][/]",
            }
            icon = status_icons.get(status, "?")

            progress_bar = ""
            if progress > 0:
                filled = int(progress / 10)
                bar = "" * filled + "" * (10 - filled)
                progress_bar = f"[{bar}] {progress:.0f}%"
            elif status == "notstarted":
                progress_bar = "[dim]—[/]"
            else:
                progress_bar = ""

            row_key = self.add_row(
                icon,
                title,
                agent,
                progress_bar,
                priority_map.get(priority, " Med"),
                schedule,
            )
            self._task_rows[task_id] = row_key

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Find task from row key and post message."""
        for task_id, key in self._task_rows.items():
            if key == event.row_key:
                task = next(
                    (t for t in self._tasks if t.get("id") == task_id),
                    {},
                )
                self.post_message(self.Selected(task_id, task))
                return

    def action_toggle_status(self) -> None:
        """Toggle status of the selected task."""
        if self.cursor_row is not None:
            # Find task_id by cursor row
            # DataTable cursor_row is an index, not a key
            try:
                row_key = self.get_row_at(self.cursor_row)
                for task_id, key in self._task_rows.items():
                    if key == row_key:
                        self.post_message(self.ToggleStatus(task_id))
                        return
            except Exception:
                pass


class TasksView(Vertical):
    """Full task management view."""

    DEFAULT_CSS = """
    TasksView {
        height: 1fr;
        padding: 1;
    }

    TasksView #tasks-toolbar {
        height: auto;
        padding: 0 0 1 0;
    }

    TasksView #tasks-toolbar Button {
        margin: 0 1 0 0;
    }

    TasksView #tasks-toolbar Input {
        width: 30;
        margin: 0 1 0 0;
    }

    TasksView #tasks-toolbar Select {
        width: 15;
        margin: 0;
    }

    TasksView #tasks-count {
        width: auto;
        text-style: dim;
        text-align: right;
    }

    TasksView #task-table {
        height: 1fr;
    }
    """

    tasks: reactive[list[dict[str, Any]]] = reactive([])

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._filtered_tasks: list[dict[str, Any]] = []
        self._status_filter: str = "all"

    def compose(self) -> ComposeResult:
        with Horizontal(id="tasks-toolbar"):
            yield Button(" New Task", id="tv-new", variant="primary")
            yield Button(" Toggle", id="tv-toggle", variant="default")
            yield Button(" Delete", id="tv-delete", variant="error")
            yield Input(placeholder="Filter tasks...", id="tv-filter")
            yield Select(
                [("All", "all"), ("Active", "ongoing"), ("Pending", "notstarted"),
                 ("Done", "completed"), ("Blocked", "blocked"), ("Scheduled", "cron")],
                value="all",
                id="tv-status-filter",
            )
            yield Static("", id="tasks-count")

        yield TaskTable(id="task-table")

    def update_tasks(self, tasks: list[dict[str, Any]]) -> None:
        self.tasks = tasks
        self._apply_filter()

    def _apply_filter(self) -> None:
        """Apply text and status filters."""
        try:
            filter_input = self.query_one("#tv-filter", Input)
            text_filter = filter_input.value.lower()
        except NoMatches:
            text_filter = ""

        filtered = self.tasks

        # Status filter
        if self._status_filter != "all":
            if self._status_filter == "active":
                filtered = [t for t in filtered if t.get("status") == "ongoing"]
            else:
                filtered = [t for t in filtered if t.get("status") == self._status_filter]

        # Text filter
        if text_filter:
            filtered = [
                t for t in filtered
                if text_filter in t.get("title", "").lower()
                or text_filter in t.get("agent", "").lower()
            ]

        self._filtered_tasks = filtered

        try:
            table = self.query_one("#task-table", TaskTable)
            table.update_tasks(filtered)
        except NoMatches:
            pass

        # Update count
        try:
            count_label = self.query_one("#tasks-count", Static)
            total = len(self.tasks)
            showing = len(filtered)
            if showing == total:
                count_label.update(f"[dim]{total} tasks[/]")
            else:
                count_label.update(f"[dim]{showing}/{total} tasks[/]")
        except NoMatches:
            pass

    @on(Input.Changed, "#tv-filter")
    def on_filter_changed(self, event: Input.Changed) -> None:
        self._apply_filter()

    @on(Select.Changed, "#tv-status-filter")
    def on_status_filter_changed(self, event: Select.Changed) -> None:
        self._status_filter = str(event.value) if event.value else "all"
        self._apply_filter()

    @on(TaskTable.Selected)
    def on_task_selected(self, event: TaskTable.Selected) -> None:
        """Handle task selection — could open detail or focus agent."""
        pass  # Parent app handles this

    @on(TaskTable.ToggleStatus)
    def on_task_toggle(self, event: TaskTable.ToggleStatus) -> None:
        """Handle task status toggle."""
        pass  # Parent app handles this

    def get_selected_task(self) -> dict[str, Any] | None:
        """Get the currently selected task."""
        try:
            table = self.query_one("#task-table", TaskTable)
            if table.cursor_row is not None:
                row_key = table.get_row_at(table.cursor_row)
                for task_id, key in table._task_rows.items():
                    if key == row_key:
                        return next(
                            (t for t in self.tasks if t.get("id") == task_id),
                            None,
                        )
        except Exception:
            pass
        return None
