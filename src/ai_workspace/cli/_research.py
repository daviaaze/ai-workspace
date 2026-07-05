"""CLI commands — `aiw research`."""

import typer
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from ai_workspace.cli._app import app, console

# Research view commands

research_app = typer.Typer(help="View completed research results")
app.add_typer(research_app, name="research")


@research_app.command(name="list")
def research_list(
    limit: int = typer.Option(20, "--limit", "-l", help="Number of results"),
):
    """List completed research entries."""
    store = get_store(db_url=_get_db_url())
    store.initialize()
    entries = store.get_research_history(limit=limit)
    store.close()

    if not entries:
        console.print("[dim]No research entries yet[/]")
        return

    table = Table(title=" Research History")
    table.add_column("ID", style="dim")
    table.add_column("Query")
    table.add_column("Confidence", justify="right")
    table.add_column("When")

    for e in entries:
        created = e.get("created_at", "")
        if hasattr(created, "strftime"):
            created = created.strftime("%m-%d %H:%M")
        elif isinstance(created, str) and "T" in created:
            created = created[:16].replace("T", " ")

        table.add_row(
            str(e["id"]),
            e.get("query", "?")[:80],
            f"{e.get('confidence', 0):.0%}",
            str(created),
        )

    console.print(table)
    console.print("[dim]View details: aiw research view <id>[/]")


@research_app.command(name="view")
def research_view(
    research_id: int = typer.Argument(..., help="Research entry ID"),
):
    """View a completed research report."""
    store = get_store(db_url=_get_db_url())
    store.initialize()

    c = store.conn.cursor()
    c.execute(
        "SELECT id, query, summary, detailed_report, sources, confidence, sub_questions, created_at "
        "FROM research_entries WHERE id = %s",
        (research_id,),
    )
    row = c.fetchone()
    c.close()
    store.close()

    if not row:
        console.print(f"[red]Research #{research_id} not found[/]")
        return

    cols = ["id", "query", "summary", "detailed_report", "sources", "confidence", "sub_questions", "created_at"]
    entry = dict(zip(cols, row))

    created_str = entry.get("created_at", "")
    if hasattr(created_str, "strftime"):
        created_str = created_str.strftime("%Y-%m-%d %H:%M")
    elif isinstance(created_str, str) and "T" in created_str:
        created_str = created_str[:16].replace("T", " ")

    console.print(Panel(
        f"[bold cyan]{entry['query']}[/]\n\n"
        f"[dim]ID: {entry['id']} | Confidence: {entry.get('confidence', 0):.0%} | "
        f"Created: {created_str}[/]",
        title=" Research",
    ))

    console.print(Panel(
        f"[bold cyan]{entry['query']}[/]\n\n"
        f"[dim]ID: {entry['id']} | Confidence: {entry.get('confidence', 0):.0%} | "
        f"Created: {created_str}[/]",
        title=" Research",
    ))

    if entry.get("summary"):
        console.print()
        console.print(Panel(
            Markdown(entry["summary"]),
            title=" Summary",
            border_style="green",
        ))

    if entry.get("detailed_report"):
        console.print()
        console.print(Panel(
            Markdown(entry["detailed_report"][:5000]),
            title=" Detailed Report",
            border_style="blue",
        ))

    if entry.get("sub_questions"):
        console.print()
        table = Table(title=" Sub-questions")
        table.add_column("#", style="dim")
        table.add_column("Question")
        for i, sq in enumerate(entry["sub_questions"], 1):
            if isinstance(sq, dict):
                q = sq.get("question", str(sq))[:120]
            else:
                q = str(sq)[:120]
            table.add_row(str(i), q)
        console.print(table)
