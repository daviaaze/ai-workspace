"""CLI commands — ``aiw loop``."""

from __future__ import annotations

import asyncio
import json

import typer
from rich.table import Table
from rich.panel import Panel

from ai_workspace.cli._app import app, console
from ai_workspace.queue import JobQueue


loop_app = typer.Typer(help="Production agent loop patterns")
app.add_typer(loop_app, name="loop")


def _get_dsn() -> str:
    import os
    return os.environ.get("AIW_DB_URL", "postgresql:///ai_workspace")


@loop_app.command(name="list")
def loop_list():
    """List available loop patterns."""
    async def _run():
        q = JobQueue(_get_dsn())
        await q.connect()
        try:
            async with q._pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM loop_patterns ORDER BY id"
                )

            table = Table(title=" Loop Patterns ")
            table.add_column("Pattern", style="cyan")
            table.add_column("Title")
            table.add_column("Cadence")
            table.add_column("Level")
            table.add_column("Verifier")
            table.add_column("Worktree")
            table.add_column("Enabled")

            for row in rows:
                cadence = row["cadence"]
                if cadence >= 86400:
                    cadence_str = f"{cadence // 86400}d"
                elif cadence >= 3600:
                    cadence_str = f"{cadence // 3600}h"
                else:
                    cadence_str = f"{cadence // 60}m"

                level = f"[green]{row['readiness']}[/]"
                enabled = "[green]✓[/]" if row["enabled"] else "[red]✗[/]"
                verifier = "[green]✓[/]" if row["verifier"] else ""
                worktree = "[green]✓[/]" if row["worktree"] else ""

                table.add_row(
                    row["id"],
                    row["title"],
                    cadence_str,
                    level,
                    verifier,
                    worktree,
                    enabled,
                )
            console.print(table)
        finally:
            await q.close()
    asyncio.run(_run())


@loop_app.command()
def show(pattern_id: str = typer.Argument(..., help="Pattern ID")):
    """Show pattern details."""
    async def _run():
        q = JobQueue(_get_dsn())
        await q.connect()
        try:
            async with q._pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM loop_patterns WHERE id = $1", pattern_id
                )

            if not row:
                console.print(f"[red]Pattern '{pattern_id}' not found[/]")
                return

            lines = "\n".join(
                f"[bold]{k}:[/]  {v}" for k, v in dict(row).items()
                if v is not None and str(v)
            )
            console.print(Panel(lines, title=f" Pattern: {pattern_id} "))
        finally:
            await q.close()
    asyncio.run(_run())


@loop_app.command()
def enable(
    pattern_id: str = typer.Argument(..., help="Pattern ID"),
    level: str = typer.Option("L1", "--level", "-l", help="Readiness level (L0-L3)"),
):
    """Enable a loop pattern at a readiness level.

    This enables the pattern and sets its readiness level.
    Also seeds the recurring schedule if not already present.
    """
    async def _run():
        q = JobQueue(_get_dsn())
        await q.connect()
        try:
            async with q._pool.acquire() as conn:
                await conn.execute(
                    "UPDATE loop_patterns SET enabled = TRUE, readiness = $2, updated_at = NOW() WHERE id = $1",
                    pattern_id, level,
                )

            # Seed the schedule
            from ai_workspace.loops import seed_default_schedules
            await seed_default_schedules(_get_dsn())

            console.print(f"[green]Pattern '{pattern_id}' enabled at {level}[/]")
        finally:
            await q.close()
    asyncio.run(_run())


@loop_app.command()
def disable(pattern_id: str = typer.Argument(..., help="Pattern ID")):
    """Disable a loop pattern."""
    async def _run():
        q = JobQueue(_get_dsn())
        await q.connect()
        try:
            async with q._pool.acquire() as conn:
                await conn.execute(
                    "UPDATE loop_patterns SET enabled = FALSE, updated_at = NOW() WHERE id = $1",
                    pattern_id,
                )
            # Also pause the schedule
            await q.pause_schedule(pattern_id, reason="Disabled via CLI")
            console.print(f"[yellow]Pattern '{pattern_id}' disabled[/]")
        finally:
            await q.close()
    asyncio.run(_run())


@loop_app.command()
def run(pattern_id: str = typer.Argument(..., help="Pattern ID")):
    """Trigger an immediate run of a loop pattern."""
    async def _run():
        q = JobQueue(_get_dsn())
        await q.connect()
        try:
            job = await q.trigger_schedule(pattern_id)
            if job:
                console.print(f"[green]Triggered run: job #{job.id} ({job.job_type})[/]")
            else:
                console.print(f"[yellow]No schedule found for '{pattern_id}'[/]")
        finally:
            await q.close()
    asyncio.run(_run())


@loop_app.command()
def state(pattern_id: str = typer.Argument(..., help="Pattern ID")):
    """Show the current state for a loop pattern."""
    async def _run():
        q = JobQueue(_get_dsn())
        await q.connect()
        try:
            async with q._pool.acquire() as conn:
                row = await conn.fetchrow(
                    """SELECT * FROM loop_state
                       WHERE pattern_id = $1
                       ORDER BY created_at DESC LIMIT 1""",
                    pattern_id,
                )

            if not row:
                console.print(f"[dim]No state for '{pattern_id}'[/]")
                return

            # Show active items
            active = row.get("items_active") or []
            watch = row.get("items_watch") or []
            noise = row.get("items_noise") or []

            console.print(Panel(
                f"[bold]Last run:[/] {row.get('last_run', 'never')}\n"
                f"[bold]Active:[/] {len(active)}\n"
                f"[bold]Watch:[/] {len(watch)}\n"
                f"[bold]Noise:[/] {len(noise)}",
                title=f" State: {pattern_id} ",
            ))

            if active:
                active_table = Table(title=" Active Items ")
                active_table.add_column("ID")
                active_table.add_column("Title")
                active_table.add_column("Status")
                active_table.add_column("Attempts")
                for item in active[:10]:
                    active_table.add_row(
                        item.get("id", ""),
                        str(item.get("title", ""))[:40],
                        item.get("status", ""),
                        str(item.get("attempts", 0)),
                    )
                console.print(active_table)
        finally:
            await q.close()
    asyncio.run(_run())


@loop_app.command()
def log(
    pattern_id: str = typer.Argument(..., help="Pattern ID"),
    limit: int = typer.Option(10, "--limit", "-l", help="Max results"),
):
    """Show run log for a loop pattern."""
    async def _run():
        q = JobQueue(_get_dsn())
        await q.connect()
        try:
            async with q._pool.acquire() as conn:
                rows = await conn.fetch(
                    """SELECT * FROM loop_run_log
                       WHERE pattern_id = $1
                       ORDER BY started_at DESC LIMIT $2""",
                    pattern_id, limit,
                )

            if not rows:
                console.print(f"[dim]No runs for '{pattern_id}'[/]")
                return

            table = Table(title=f" Run Log: {pattern_id} ")
            table.add_column("Time")
            table.add_column("Outcome")
            table.add_column("Found")
            table.add_column("Actions")
            table.add_column("Esc.")
            table.add_column("Tokens")
            table.add_column("Error")

            outcome_colors = {
                "success": "green",
                "noop": "blue",
                "escalated": "yellow",
                "failed": "red",
                "error": "red",
            }

            for row in rows:
                time_str = row["started_at"].strftime("%H:%M %d/%m") if row["started_at"] else ""
                outcome = row.get("outcome", "")
                color = outcome_colors.get(outcome, "white")

                table.add_row(
                    time_str,
                    f"[{color}]{outcome}[/]",
                    str(row.get("items_found", 0)),
                    str(row.get("actions_taken", 0)),
                    str(row.get("escalations", 0)),
                    str(row.get("tokens_estimate", 0)),
                    (row.get("error") or "")[:30],
                )
            console.print(table)
        finally:
            await q.close()
    asyncio.run(_run())


@loop_app.command()
def budget(pattern_id: str = typer.Argument(..., help="Pattern ID")):
    """Show budget for a loop pattern."""
    async def _run():
        q = JobQueue(_get_dsn())
        await q.connect()
        try:
            async with q._pool.acquire() as conn:
                row = await conn.fetchrow(
                    """SELECT * FROM loop_budget
                       WHERE pattern_id = $1 AND budget_date = CURRENT_DATE""",
                    pattern_id,
                )

            if not row:
                console.print(f"[dim]No budget for '{pattern_id}' today[/]")
                return

            daily_cap = row["daily_cap"]
            spent = row.get("daily_spent", 0)
            pct = (spent / daily_cap * 100) if daily_cap > 0 else 0

            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            color = "green" if pct < 60 else ("yellow" if pct < 80 else "red")

            console.print(Panel(
                f"[bold]Daily cap:[/] {daily_cap:,} tokens\n"
                f"[bold]Spent:[/]     {spent:,} tokens\n"
                f"[bold]{bar}[/] [{color}]{pct:.0f}%[/]\n"
                f"[bold]Paused:[/]    {'[yellow]yes[/]' if row.get('paused') else '[green]no[/]'}\n"
                f"[bold]Kill switch:[/] {'[red]ACTIVE[/]' if row.get('kill_switch') else '[green]off[/]'}",
                title=f" Budget: {pattern_id} ",
            ))
        finally:
            await q.close()
    asyncio.run(_run())


@loop_app.command()
def pause(pattern_id: str = typer.Argument(..., help="Pattern ID")):
    """Pause a loop pattern."""
    async def _run():
        q = JobQueue(_get_dsn())
        await q.connect()
        try:
            await q.pause_schedule(pattern_id, "Paused via CLI")
            async with q._pool.acquire() as conn:
                await conn.execute(
                    "UPDATE loop_budget SET paused = TRUE, pause_reason = 'CLI pause' WHERE pattern_id = $1 AND budget_date = CURRENT_DATE",
                    pattern_id,
                )
            console.print(f"[yellow]Pattern '{pattern_id}' paused[/]")
        finally:
            await q.close()
    asyncio.run(_run())


@loop_app.command()
def resume(pattern_id: str = typer.Argument(..., help="Pattern ID")):
    """Resume a paused loop pattern."""
    async def _run():
        q = JobQueue(_get_dsn())
        await q.connect()
        try:
            await q.resume_schedule(pattern_id)
            async with q._pool.acquire() as conn:
                await conn.execute(
                    "UPDATE loop_budget SET paused = FALSE WHERE pattern_id = $1 AND budget_date = CURRENT_DATE",
                    pattern_id,
                )
            console.print(f"[green]Pattern '{pattern_id}' resumed[/]")
        finally:
            await q.close()
    asyncio.run(_run())


@loop_app.command()
def kill(pattern_id: str = typer.Argument(..., help="Pattern ID")):
    """Kill a loop pattern (disable + kill switch + pause)."""
    async def _run():
        q = JobQueue(_get_dsn())
        await q.connect()
        try:
            await q.pause_schedule(pattern_id, "Killed via CLI")
            async with q._pool.acquire() as conn:
                await conn.execute(
                    "UPDATE loop_patterns SET enabled = FALSE, updated_at = NOW() WHERE id = $1",
                    pattern_id,
                )
                await conn.execute(
                    "UPDATE loop_budget SET kill_switch = TRUE, paused = TRUE WHERE pattern_id = $1 AND budget_date = CURRENT_DATE",
                    pattern_id,
                )
            console.print(f"[red]Pattern '{pattern_id}' killed[/]")
        finally:
            await q.close()
    asyncio.run(_run())


@loop_app.command()
def seed():
    """Seed default schedules for all patterns.

    Registers all patterns in the job_schedule table.
    Patterns start disabled — enable them with ``aiw loop enable``.
    """
    async def _run():
        from ai_workspace.loops import seed_default_schedules
        results = await seed_default_schedules(_get_dsn())

        table = Table(title=" Seeded Schedules ")
        table.add_column("Name")
        table.add_column("Enabled")
        table.add_column("Paused")

        for r in results:
            enabled = "[green]✓[/]" if r["enabled"] else "[red]✗[/]"
            paused = "[yellow]⏸[/]" if r.get("paused") else ""
            table.add_row(r["name"], enabled, paused)
        console.print(table)

    asyncio.run(_run())


@loop_app.command(name="ls")
def loop_ls():
    """Alias for ``loop list``."""
    loop_list()
