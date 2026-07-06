"""CLI commands — `aiw leilao`."""

from __future__ import annotations

import json

import typer
from rich.panel import Panel
from rich.table import Table

from ai_workspace.cli._app import app, console

leilao_app = typer.Typer(help="Leilão Radar — auction scraping and management")
app.add_typer(leilao_app, name="leilao")


@leilao_app.command(name="setup-schedule")
def setup_schedule(
    schedule: str = typer.Option(
        "0 */3 * * *",
        "--schedule", "-s",
        help="Cron expression for the pipeline (default: every 3 hours)",
    ),
    db_url: str | None = typer.Option(
        None, "--db-url", "-d",
        help="PostgreSQL URL (default: from env DATABASE_URL or ~/.ai-workspace/*.db)",
    ),
):
    """Register the leilão pipeline as a recurring DB task.

    Creates an entry in the ``tasks`` table with ``type = leilao_pipeline``.
    Once registered, ``periodic_check_db_tasks`` (which runs every hour) will
    pick it up and dispatch ``leilao_pipeline_task`` when due.

    Safe to run multiple times — skips if a similar task already exists.
    """
    from ai_workspace.knowledge import KnowledgeStore

    store = KnowledgeStore(db_url=db_url)
    store.initialize()

    # Check if already registered
    existing = store.get_tasks(limit=500)
    for t in existing:
        meta = t.get("metadata") or {}
        if meta.get("type") == "leilao_pipeline":
            console.print(Panel(
                f"[yellow]Leilão pipeline already registered[/] (task id {t['id']}) "
                f"with schedule [cyan]{t.get('schedule')}[/]",
            ))
            return

    tid = store.add_task(
        title="Leilão Pipeline",
        description="Scrapes all due auction sources and stores results",
        priority=10,
        tags=["leilao", "scraping"],
        schedule=schedule,
        metadata={"type": "leilao_pipeline"},
    )

    console.print(Panel(
        f"[green]✓[/] Leilão pipeline registered as task [bold]#{tid}[/]\n"
        f"    Schedule: [cyan]{schedule}[/]\n"
        f"    The worker will pick it up at the next hourly check.",
    ))


@leilao_app.command(name="pipeline")
def run_pipeline():
    """Run the leilão pipeline immediately (for testing)."""
    from ai_workspace.leilao_radar.tasks import leilao_pipeline_task

    with console.status("[green]Running leilão pipeline..."):
        result = leilao_pipeline_task()

    table = Table(title=" Pipeline Result ")
    table.add_column("Source", style="cyan")
    table.add_column("Status")
    table.add_column("Lots")
    table.add_column("Errors")

    for r in result.get("details", []):
        table.add_row(
            r.get("source", "?"),
            "🟢" if r.get("status") == "success" else "🟡" if r.get("status") == "partial" else "🔴",
            str(r.get("lots", 0)),
            str(r.get("errors", 0) or ""),
        )

    console.print(table)
    console.print(f"\n[bold]Total sources due:[/] {result.get('sources_scraped', 0)}")
    console.print(f"[bold]Total lots:[/] {result.get('total_lots', 0)}")
    console.print(f"[bold]Total errors:[/] {result.get('total_errors', 0)}")


@leilao_app.command(name="sources")
def list_sources():
    """List registered leilão sources and their scrape cadence."""
    from ai_workspace.leilao_radar import Config
    from ai_workspace.leilao_radar.storage.database import Database

    config = Config.from_env()
    db = Database(config)

    rows = db.get_active_sources()

    table = Table(title=" Active Sources ")
    table.add_column("ID")
    table.add_column("Name", style="cyan")
    table.add_column("Interval (h)")
    table.add_column("Last Scraped")
    table.add_column("Due Now?")

    for r in rows:
        table.add_row(
            str(r["id"]),
            r["name"],
            str(r.get("check_interval_hours", 0)),
            str(r.get("last_scraped_at", "never")),
            "✅" if r.get("last_scraped_at") else "🔴 (never)",
        )

    console.print(table)


@leilao_app.command(name="mirror")
def run_mirror(
    limit: int = typer.Option(200, "--limit", "-n", help="Max lots to mirror"),
):
    """Mirror closed lots from SQLite to pgvector for semantic search."""
    from ai_workspace.leilao_radar.knowledge_mirror import mirror_closed_lots

    with console.status("[green]Mirroring lots to pgvector..."):
        result = mirror_closed_lots(limit=limit)

    console.print(Panel(
        f"[green]✓[/] Mirrored [bold]{result['mirrored']}[/] of {result['total']} lots"
    ))
