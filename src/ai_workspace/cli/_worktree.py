"""CLI commands — ``aiw worktree``."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import typer
from rich.table import Table
from rich.panel import Panel

from ai_workspace.cli._app import app, console
from ai_workspace.worktree import WorktreeManager, WorktreeConfig


worktree_app = typer.Typer(help="Parallel agent isolation via git worktrees")
app.add_typer(worktree_app, name="worktree")


def _get_dsn() -> str:
    import os
    return os.environ.get("AIW_DB_URL", "postgresql:///ai_workspace")


@worktree_app.command(name="list")
def wt_list(
    pattern: str = typer.Option(None, "--pattern", "-p", help="Filter by pattern ID"),
    status: str = typer.Option(None, "--status", "-s", help="Filter by status"),
):
    """List registered worktrees."""
    async def _run():
        async with WorktreeManager(_get_dsn()) as wtm:
            worktrees = await wtm.list_worktrees(
                pattern_id=pattern,
                status=status,
            )

        if not worktrees:
            console.print("[dim]No worktrees found[/]")
            return

        table = Table(title=f" Worktrees ({len(worktrees)}) ")
        table.add_column("ID", style="dim")
        table.add_column("Pattern")
        table.add_column("Item")
        table.add_column("Branch")
        table.add_column("Status")
        table.add_column("Age")

        for wt in worktrees:
            age = ""
            if wt.get("created_at"):
                delta = datetime.now(timezone.utc) - wt["created_at"]
                age = f"{int(delta.total_seconds() // 60)}m" if delta.total_seconds() < 3600 else f"{int(delta.total_seconds() // 3600)}h"

            table.add_row(
                str(wt["id"])[:8],
                wt.get("pattern_id", ""),
                wt.get("item_id", ""),
                wt.get("branch", ""),
                wt.get("status", ""),
                age,
            )
        console.print(table)

    asyncio.run(_run())


@worktree_app.command()
def show(worktree_id: str = typer.Argument(..., help="Worktree UUID")):
    """Show worktree details."""
    async def _run():
        async with WorktreeManager(_get_dsn()) as wtm:
            rows = await wtm.list_worktrees()
            row = next((r for r in rows if str(r.get("id", ""))[:8] == worktree_id or str(r.get("id", "")) == worktree_id), None)

        if not row:
            console.print(f"[red]Worktree {worktree_id} not found[/]")
            return

        lines = "\n".join(
            f"[bold]{k}:[/]  {v}" for k, v in row.items()
            if v is not None and str(v)
        )
        console.print(Panel(lines, title=f" Worktree {worktree_id} "))

    asyncio.run(_run())


@worktree_app.command()
def release(
    worktree_id: str = typer.Argument(..., help="Worktree UUID"),
    keep: bool = typer.Option(False, "--keep", help="Keep worktree on disk"),
):
    """Release a worktree."""
    async def _run():
        async with WorktreeManager(_get_dsn()) as wtm:
            ok = await wtm.release(worktree_id, delete=not keep)
            if ok:
                console.print(f"[green]Worktree {worktree_id} released[/]")
            else:
                console.print(f"[yellow]Worktree {worktree_id} not found[/]")

    asyncio.run(_run())


@worktree_app.command()
def cleanup(
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be cleaned"),
    max_age: int = typer.Option(24, "--max-age", "-a", help="Max age in hours"),
):
    """Clean up stale/abandoned worktrees."""
    async def _run():
        async with WorktreeManager(_get_dsn()) as wtm:
            cleaned = await wtm.cleanup_stale(
                max_age_hours=max_age,
                dry_run=dry_run,
            )

        if cleaned:
            console.print(f"[green]{'Would clean' if dry_run else 'Cleaned'} {len(cleaned)} stale worktrees[/]")
            for wt_id in cleaned:
                console.print(f"  {wt_id}")
        else:
            console.print("[dim]No stale worktrees found[/]")

    asyncio.run(_run())


@worktree_app.command()
def stats():
    """Show worktree usage statistics."""
    async def _run():
        async with WorktreeManager(_get_dsn()) as wtm:
            s = await wtm.stats()

        console.print(Panel(
            f"[bold]Active:[/]    {s.get('active', 0)}\n"
            f"[bold]Locked:[/]    {s.get('locked', 0)}\n"
            f"[bold]Stale:[/]     {s.get('stale', 0)}\n"
            f"[bold]Released:[/]  {s.get('released', 0)}\n"
            f"[bold]Orphaned:[/]  {s.get('orphaned', 0)}",
            title=" Worktree Stats ",
        ))

    asyncio.run(_run())


@worktree_app.command(name="ls")
def wt_ls():
    """Alias for ``worktree list``."""
    wt_list()
