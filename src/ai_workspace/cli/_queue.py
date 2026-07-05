"""CLI commands — ``aiw queue``."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

import typer
from rich.panel import Panel
from rich.table import Table

from ai_workspace.cli._app import app, console
from ai_workspace.queue import JobQueue

queue_app = typer.Typer(help="PostgreSQL job queue management")
app.add_typer(queue_app, name="queue")


def _get_dsn() -> str:
    import os
    return os.environ.get("AIW_DB_URL", "postgresql:///ai_workspace")


@queue_app.command()
def stats():
    """Show queue depth by status."""
    async def _run():
        q = JobQueue(_get_dsn())
        await q.connect()
        try:
            s = await q.queue_stats()
            console.print(Panel(
                f"[bold]Pending:[/]     {s['pending']}\n"
                f"[bold]Scheduled:[/]   {s['scheduled']}\n"
                f"[bold]Available:[/]   {s['available']}\n"
                f"[bold]Running:[/]     {s['running']}\n"
                f"[bold]Completed:[/]   {s['completed']}\n"
                f"[bold]Failed:[/]      {s['failed']}\n"
                f"[bold]Cancelled:[/]   {s['cancelled']}",
                title=" Queue Stats ",
            ))
        finally:
            await q.close()
    asyncio.run(_run())


@queue_app.command(name="list")
def queue_list(
    queue: str = typer.Option(None, "--queue", "-q", help="Filter by queue name"),
    status: str = typer.Option(None, "--status", "-s", help="Filter by status"),
    limit: int = typer.Option(20, "--limit", "-l", help="Max results"),
):
    """List jobs in the queue."""
    async def _run():
        q = JobQueue(_get_dsn())
        await q.connect()
        try:
            jobs = await q.list_jobs(queue=queue, status=status, limit=limit)
            table = Table(title=f" Jobs ({len(jobs)}) ")
            table.add_column("ID", style="dim")
            table.add_column("Type")
            table.add_column("Queue")
            table.add_column("Status")
            table.add_column("Age")
            table.add_column("Retries")

            status_colors = {
                "pending": "yellow",
                "scheduled": "blue",
                "available": "cyan",
                "running": "green",
                "completed": "white",
                "failed": "red",
                "cancelled": "dim",
            }

            now = datetime.now(UTC)

            for j in jobs:
                age = now - j.created_at
                age_str = f"{int(age.total_seconds() // 60)}m" if age.total_seconds() < 3600 else f"{int(age.total_seconds() // 3600)}h"
                table.add_row(
                    str(j.id),
                    j.job_type[:30],
                    j.queue,
                    f"[{status_colors.get(j.status, 'white')}]{j.status}[/]",
                    age_str,
                    f"{j.retry_count}/{j.max_retries}" if j.retry_count > 0 else "0",
                )
            console.print(table)
        finally:
            await q.close()
    asyncio.run(_run())


@queue_app.command()
def inspect(job_id: int = typer.Argument(..., help="Job ID")):
    """Show full details of a job."""
    async def _run():
        q = JobQueue(_get_dsn())
        await q.connect()
        try:
            job = await q.get_job(job_id)
            if not job:
                console.print(f"[red]Job #{job_id} not found[/]")
                return

            info = {
                "ID": job.id,
                "Type": job.job_type,
                "Queue": job.queue,
                "Handler": job.handler,
                "Status": job.status,
                "Priority": job.priority,
                "Created": job.created_at.isoformat() if job.created_at else "",
                "Started": job.started_at.isoformat() if job.started_at else "",
                "Completed": job.completed_at.isoformat() if job.completed_at else "",
                "Retries": f"{job.retry_count}/{job.max_retries}",
                "Timeout": f"{job.timeout_seconds}s",
                "Depends On": str(job.depends_on) if job.depends_on else "",
                "Error": job.last_error or "",
            }

            lines = "\n".join(f"[bold]{k}:[/]  {v}" for k, v in info.items() if v)
            console.print(Panel(lines, title=f" Job #{job.id} "))

            if job.payload:
                console.print(Panel(
                    json.dumps(job.payload, indent=2, default=str)[:2000],
                    title=" Payload ",
                ))
            if job.result:
                console.print(Panel(
                    json.dumps(job.result, indent=2, default=str)[:2000],
                    title=" Result ",
                ))
        finally:
            await q.close()
    asyncio.run(_run())


@queue_app.command()
def cancel(job_id: int = typer.Argument(..., help="Job ID")):
    """Cancel a pending or running job."""
    async def _run():
        q = JobQueue(_get_dsn())
        await q.connect()
        try:
            ok = await q.cancel(job_id)
            if ok:
                console.print(f"[green]Job #{job_id} cancelled[/]")
            else:
                console.print(f"[yellow]Job #{job_id} not found or already in terminal state[/]")
        finally:
            await q.close()
    asyncio.run(_run())


@queue_app.command()
def retry(job_id: int = typer.Argument(..., help="Job ID")):
    """Retry a failed job."""
    async def _run():
        q = JobQueue(_get_dsn())
        await q.connect()
        try:
            ok = await q.retry_job(job_id)
            if ok:
                console.print(f"[green]Job #{job_id} re-queued for retry[/]")
            else:
                console.print(f"[yellow]Job #{job_id} not found or not in 'failed' state[/]")
        finally:
            await q.close()
    asyncio.run(_run())


@queue_app.command()
def worker(
    concurrency: int = typer.Option(4, "--concurrency", "-c", help="Number of concurrent workers"),
):
    """Start the job queue worker daemon."""
    from ai_workspace.queue.worker import start_worker_sync
    start_worker_sync(concurrency=concurrency, dsn=_get_dsn())


@queue_app.command()
def schedule():
    """Show recurring schedule status."""
    async def _run():
        q = JobQueue(_get_dsn())
        await q.connect()
        try:
            schedules = await q.list_schedules()
            table = Table(title=f" Schedules ({len(schedules)}) ")
            table.add_column("Name", style="cyan")
            table.add_column("Type")
            table.add_column("Cadence")
            table.add_column("Enabled")
            table.add_column("Last Run")
            table.add_column("Next Run")

            now = datetime.now(UTC)

            for s in schedules:
                cadence = s.cron_expr or (f"{s.interval_seconds}s" if s.interval_seconds else "?")
                enabled = "[green]✓[/]" if s.enabled else "[red]✗[/]"
                if s.paused:
                    enabled = "[yellow]⏸[/]"

                last = s.last_run_at.strftime("%H:%M") if s.last_run_at else "-"
                next_r = s.next_run_at.strftime("%H:%M") if s.next_run_at else "-"

                table.add_row(
                    s.name,
                    s.schedule_type,
                    str(cadence),
                    enabled,
                    last,
                    next_r,
                )
            console.print(table)
        finally:
            await q.close()
    asyncio.run(_run())


# ── Aliases for convenience ─────────────────────────────


@queue_app.command(name="ls")
def queue_ls():
    """Alias for ``queue list``."""
    queue_list()



