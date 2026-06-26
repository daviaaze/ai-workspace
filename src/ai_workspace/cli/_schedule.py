"""CLI commands — `aiw schedule`."""

from ai_workspace.cli._app import app, console
from rich.table import Table
import typer


# Schedule commands (Huey-based)

schedule_app = typer.Typer(help="Manage recurring tasks (Huey)")
app.add_typer(schedule_app, name="schedule")


@schedule_app.command(name="run")
def schedule_run(
    name: str = typer.Argument(..., help="Periodic task: morning, research, learning, check, telemetry"),
):
    """Run a periodic task immediately for testing."""
    from ai_workspace.tasks import (
        periodic_morning_briefing,
        periodic_daily_research,
        periodic_continuous_learning,
        periodic_check_db_tasks,
        periodic_telemetry_report,
    )

    tasks_map = {
        "morning": periodic_morning_briefing,
        "briefing": periodic_morning_briefing,
        "research": periodic_daily_research,
        "daily": periodic_daily_research,
        "learning": periodic_continuous_learning,
        "continuous": periodic_continuous_learning,
        "check": periodic_check_db_tasks,
        "db-tasks": periodic_check_db_tasks,
        "telemetry": periodic_telemetry_report,
        "report": periodic_telemetry_report,
    }

    if name not in tasks_map:
        valid = ", ".join(sorted(set(tasks_map.keys())))
        console.print(f"[red]Unknown task: {name}[/]\nAvailable: {valid}")
        raise typer.Exit(1)

    console.print(f"[cyan]Running task: {name}...[/]")
    result = tasks_map[name]()
    console.print(json.dumps(result, indent=2, default=str))


@schedule_app.command()
def status():
    """Show schedule status and periodic task configuration."""
    from ai_workspace.tasks import huey

    try:
        pending = huey.pending_count()
        scheduled = huey.scheduled_count()
    except Exception:
        pending = scheduled = "n/a (worker not running)"

    table = Table(title=" Schedule Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Value")

    table.add_row("Pending tasks", str(pending))
    table.add_row("Scheduled tasks", str(scheduled))
    table.add_row("Task DB", str(Path.home() / ".ai-workspace" / "tasks.db"))
    table.add_row("Worker", "Use: aiw worker")

    console.print(table)
    console.print()
    console.print("[bold]Periodic schedules (BRT timezone):[/]")
    console.print("  07:00  [cyan]morning_briefing[/]      - sync Obsidian + daily briefing")
    console.print("  08:00  [cyan]daily_research[/]        - automated topic research")
    console.print("  02:00  [cyan]continuous_learning[/]   - pattern extraction")
    console.print("  09:00  [cyan]telemetry_report[/]      - metrics snapshot")
    console.print("  **:00  [cyan]db_task_checker[/]       - run due DB tasks")
