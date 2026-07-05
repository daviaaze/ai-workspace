"""CLI commands — `aiw task`."""

from __future__ import annotations

import typer
from rich.table import Table

from ai_workspace.cli._app import app, console
from ai_workspace.core.db import get_store

# Task commands

task_app = typer.Typer(help="Manage tasks")
app.add_typer(task_app, name="task")


@task_app.command(name="list")
def task_list(
    status: str | None = typer.Option(None, "--status", "-s", help="Filter by status"),
    tags: list[str] | None = typer.Option(None, "--tag", "-t", help="Filter by tags"),
    limit: int = typer.Option(50, "--limit", "-l"),
):
    """List tasks."""
    store = get_store()
    store.initialize()
    tasks = store.get_tasks(status=status, tags=tags, limit=limit)
    store.close()

    if not tasks:
        console.print("[dim]No tasks found[/]")
        return

    table = Table(title=" Tasks")
    table.add_column("ID", style="dim")
    table.add_column("Status")
    table.add_column("Priority")
    table.add_column("Title")
    table.add_column("Tags")
    table.add_column("Schedule")

    for t in tasks:
        status_style = {
            "pending": "yellow",
            "in_progress": "cyan",
            "completed": "green",
            "blocked": "red",
        }.get(t.get("status", ""), "white")

        table.add_row(
            str(t["id"]),
            f"[{status_style}]{t['status']}[/]",
            "" if t.get("priority", 0) > 7 else "" if t.get("priority", 0) > 3 else "",
            t["title"][:60],
            ", ".join(t.get("tags", []) or [])[:30],
            t.get("schedule") or "-",
        )

    console.print(table)


@task_app.command()
def add(
    title: str = typer.Argument(..., help="Task title"),
    description: str = typer.Option("", "--description", "-d"),
    priority: int = typer.Option(5, "--priority", "-p", min=0, max=10),
    tags: list[str] | None = typer.Option(None, "--tag", "-t"),
    schedule: str | None = typer.Option(None, "--schedule", "-s", help="Cron expression (e.g. '0 9 * * *')"),
):
    """Add a new task (optionally recurring with cron schedule)."""

    store = get_store()
    store.initialize()
    tid = store.add_task(title, description, priority, tags, schedule)

    # If scheduled, enqueue for processing
    if schedule:
        console.print("[dim]Scheduled task will be picked up by the worker[/]")

    store.close()
    console.print(f"[green] Task #{tid} created:[/] {title}")


@task_app.command()
def update(
    task_id: int = typer.Argument(..., help="Task ID"),
    status: str = typer.Option(..., "--status", "-s", help="New status"),
):
    """Update task status."""
    store = get_store()
    store.initialize()
    store.update_task_status(task_id, status)
    store.close()
    console.print(f"[green] Task #{task_id} → {status}[/]")


@task_app.command()
def due():
    """List tasks that are due to run."""
    store = get_store()
    store.initialize()
    tasks = store.get_due_tasks()
    store.close()

    if not tasks:
        console.print("[dim]No due tasks[/]")
        return

    table = Table(title=" Due Tasks")
    table.add_column("ID", style="dim")
    table.add_column("Title")
    table.add_column("Schedule")

    for t in tasks:
        table.add_row(str(t["id"]), t["title"], t.get("schedule", "-"))

    console.print(table)
