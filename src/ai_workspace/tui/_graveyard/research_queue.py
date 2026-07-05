"""
Research Queue Panel — bottom-docked panel for long-running and recurring tasks.

Shows scheduled jobs, active research, and queued tasks:
  - Cron-scheduled recurring jobs
  - Running research tasks with progress
  - Queued tasks waiting to start
  - Completed results with links to sessions

Design (inspired by job queues like Sidekiq/Bull):
[  Research Queue ]

  Scheduled    Running    Queued    Completed

   [0 9 *]    MCP       Rust     TUI
  Daily sync   tools      async     frameworks
  next: 9h     45%        queued    2026-06-15

   [0 */6]                         Textual
  Market chk                        widgets
  next: 3h                          2026-06-14

  [^N New] [ Start] [ Pause] [ Remove] [ View Results]

"""

from __future__ import annotations

from dataclasses import dataclass

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Label, Static


@dataclass
class QueueJob:
    """A job in the research queue."""
    job_id: str
    title: str
    status: str = "queued"  # queued, running, completed, failed, paused, scheduled
    progress: float = 0.0
    schedule: str = ""  # Cron expression if recurring
    next_run: str = ""
    created_at: str = ""
    session_id: str = ""
    agent_type: str = "research"
    result_summary: str = ""


class JobRow(Static):
    """A single job row in the queue."""

    DEFAULT_CSS = """
    JobRow {
        height: auto;
        padding: 1 2;
        border-bottom: solid $primary 20%;
    }
    JobRow:hover {
        background: $boost;
    }
    JobRow.-selected {
        background: $accent 25%;
    }
    JobRow.-running {
        border-left: solid $success;
    }
    JobRow.-scheduled {
        border-left: solid $primary 40%;
    }
    JobRow.-queued {
        border-left: solid $boost;
    }
    JobRow.-completed {
        border-left: solid $success 40%;
        opacity: 70%;
    }
    JobRow.-failed {
        border-left: solid $error;
    }
    """

    job: QueueJob | None = None

    def render(self) -> str:
        if not self.job:
            return ""

        j = self.job

        # Status icon + label
        status_map = {
            "running": ("", "RUNNING", "green"),
            "queued": ("", "QUEUED", "dim"),
            "completed": ("", "DONE", "green"),
            "failed": ("", "FAILED", "red"),
            "paused": ("", "PAUSED", "yellow"),
            "scheduled": ("", "SCHEDULED", "cyan"),
        }
        icon, label, color = status_map.get(j.status, ("?", j.status.upper(), "white"))

        lines = [f"[{color}]{icon} {label}[/]  [bold]{j.title[:50]}[/]"]

        # Progress bar for running jobs
        if j.status == "running" and j.progress > 0:
            width = 12
            filled = int((j.progress / 100) * width)
            bar = "" * filled + "" * (width - filled)
            lines.append(f"  [{color}]{bar}[/] {j.progress:.0f}%")

        # Schedule info
        if j.schedule:
            next_str = f" next: {j.next_run}" if j.next_run else ""
            lines.append(f"  [dim]cron: {j.schedule}{next_str}[/]")

        # Result summary for completed
        if j.status == "completed" and j.result_summary:
            lines.append(f"  [dim]{j.result_summary[:60]}[/]")

        return "\n".join(lines)


class ResearchQueuePanel(VerticalScroll):
    """Bottom panel for the research job queue."""

    DEFAULT_CSS = """
    ResearchQueuePanel {
        height: 1fr;
        padding: 1;
    }

    ResearchQueuePanel #rq-header {
        dock: top;
        height: auto;
        padding: 0 0 1 0;
    }

    ResearchQueuePanel #rq-header-row {
        height: auto;
        padding: 0 0 1 0;
    }

    ResearchQueuePanel #rq-header Label {
        text-style: bold;
    }

    ResearchQueuePanel #rq-header Button {
        margin: 0 1 0 0;
        min-width: 8;
    }

    ResearchQueuePanel #rq-columns {
        height: 1fr;
    }

    ResearchQueuePanel #rq-col-scheduled {
        width: 1fr;
        border-right: solid $primary 20%;
        padding: 0 1 0 0;
    }

    ResearchQueuePanel #rq-col-running {
        width: 1fr;
        border-right: solid $primary 20%;
        padding: 0 1;
    }

    ResearchQueuePanel #rq-col-queued {
        width: 1fr;
        border-right: solid $primary 20%;
        padding: 0 1;
    }

    ResearchQueuePanel #rq-col-completed {
        width: 1fr;
        padding: 0 0 0 1;
    }

    ResearchQueuePanel .rq-col-title {
        height: 1;
        padding: 0 1;
        text-style: bold;
        border-bottom: solid $primary 20%;
        background: $boost;
    }

    ResearchQueuePanel .rq-empty {
        padding: 1 1;
        text-style: dim;
    }

    ResearchQueuePanel #rq-help {
        dock: bottom;
        height: 1;
        padding: 1 1 0 1;
        text-style: dim;
        border-top: solid $primary 20%;
    }
    """

    class NewJobRequested(Message):
        """Posted when user wants to create a new research job."""
        pass

    jobs: reactive[list[QueueJob]] = reactive([])

    def compose(self) -> ComposeResult:
        with Vertical(id="rq-header"):
            with Horizontal(id="rq-header-row"):
                yield Label(" Research Queue")
            with Horizontal():
                yield Button(" New Job", id="rq-new", variant="primary")
                yield Button(" Start", id="rq-start", variant="default")
                yield Button(" Pause", id="rq-pause", variant="default")
                yield Button(" Remove", id="rq-remove", variant="error")
                yield Button(" Refresh", id="rq-refresh", variant="default")

        with Horizontal(id="rq-columns"):
            with VerticalScroll(id="rq-col-scheduled"):
                yield Label(" Scheduled", classes="rq-col-title")
            with VerticalScroll(id="rq-col-running"):
                yield Label(" Running", classes="rq-col-title")
            with VerticalScroll(id="rq-col-queued"):
                yield Label(" Queued", classes="rq-col-title")
            with VerticalScroll(id="rq-col-completed"):
                yield Label(" Completed", classes="rq-col-title")

        yield Label(
            "[^N] New  [] Start  [] Pause  [] Remove  [] Refresh",
            id="rq-help",
        )

    def update_jobs(self, jobs: list[QueueJob]) -> None:
        """Refresh the job queue display."""
        self.jobs = jobs

        # Clear existing rows
        for col_id in ["rq-col-scheduled", "rq-col-running", "rq-col-queued", "rq-col-completed"]:
            try:
                col = self.query_one(f"#{col_id}", VerticalScroll)
                for child in list(col.children):
                    if isinstance(child, JobRow):
                        child.remove()
            except NoMatches:
                pass

        if not jobs:
            # Show empty state
            try:
                col = self.query_one("#rq-col-queued", VerticalScroll)
                col.mount(Label(
                    "No research jobs.\n\n[dim]Create one with[/]\n[dim]'New Job' above or via[/]\n[dim]the quick input: /research[/]",
                    classes="rq-empty",
                ))
            except NoMatches:
                pass
            return

        # Distribute jobs to columns
        for j in jobs:
            col_map = {
                "scheduled": "rq-col-scheduled",
                "running": "rq-col-running",
                "queued": "rq-col-queued",
                "completed": "rq-col-completed",
                "failed": "rq-col-completed",
                "paused": "rq-col-scheduled",
            }
            col_id = col_map.get(j.status, "rq-col-queued")

            try:
                col = self.query_one(f"#{col_id}", VerticalScroll)
                row = JobRow()
                row.job = j
                row.add_class(f"-{j.status}")
                col.mount(row)
            except NoMatches:
                pass

    @on(Button.Pressed, "#rq-new")
    def on_new(self, event: Button.Pressed) -> None:
        event.stop()
        self.post_message(self.NewJobRequested())

    @on(Button.Pressed, "#rq-refresh")
    def on_refresh(self, event: Button.Pressed) -> None:
        event.stop()
        # Re-render with current data
        self.update_jobs(list(self.jobs))
