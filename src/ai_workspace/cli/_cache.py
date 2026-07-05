"""CLI commands — `aiw cache`."""

import typer
from rich.panel import Panel

from ai_workspace.cli._app import app, console

# Cache commands

cache_app = typer.Typer(help="Manage semantic cache")
app.add_typer(cache_app, name="cache")


@cache_app.command()
def stats():
    """Show semantic cache statistics."""
    from ai_workspace.core.cost import CostLog, SemanticCache

    cache = SemanticCache()
    cost_log = CostLog()

    try:
        s = cache.stats()
        today = cost_log.today_cost()
        month = cost_log.month_cost()

        console.print(Panel(
            f"[bold]Entries:[/] {s['total_entries']}\n"
            f"[bold]Total hits:[/] {s['total_hits']}\n"
            f"[bold]Tokens saved:[/] {s['tokens_saved']:,}\n"
            f"[bold]Cost saved:[/] ${s['cost_saved']:.4f}\n"
            f"[bold]Today's spend:[/] ${today:.4f}\n"
            f"[bold]Month's spend:[/] ${month:.4f}",
            title=" Cache Statistics",
            border_style="cyan",
        ))

        if s['total_entries'] > 0 and s['total_hits'] > 0:
            hit_rate = s['total_hits'] / (s['total_hits'] + s['total_entries']) * 100
            console.print(f"[dim]Estimated hit rate: {hit_rate:.0f}%[/]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/]")


@cache_app.command()
def clear(
    response_type: str | None = typer.Option(None, "--type", "-t", help="Clear only: chat, search, research"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Clear semantic cache entries."""
    from ai_workspace.core.cost import SemanticCache

    if not force:
        label = response_type or "ALL"
        confirm = typer.confirm(f"Clear {label} cache entries?")
        if not confirm:
            console.print("[dim]Cancelled.[/]")
            return

    cache = SemanticCache()
    try:
        deleted = cache.clear(response_type=response_type)
        console.print(f"[green] Cleared {deleted} cache entries[/]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
