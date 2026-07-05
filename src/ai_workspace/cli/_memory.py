"""CLI commands for memory management — `aiw memory`."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import typer
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from ai_workspace.cli._app import app, console
from ai_workspace.core.db import get_store

memory_app = typer.Typer(
    help="Inspect and manage persistent memory (L1/L2/L3 traces, agent memories)",
)
app.add_typer(memory_app, name="memory")


# ── Persistent memory inspection (L1/L2/L3) ─────────────────────


@memory_app.command("stats")
def memory_stats_cmd():
    """Show persistent memory statistics and summary."""
    from ai_workspace.agents.memory import PersistentMemory

    mem = PersistentMemory()
    stats = mem.stats()

    console.print(Panel(
        f"[bold]Persistent Memory[/]  —  {stats.memory_dir}\n"
        f"L1: {stats.l1_files} files, {stats.l1_events} events  |  "
        f"L2: {stats.l2_facts} facts across {len(mem.list_l2_surfaces())} surfaces  |  "
        f"L3: {stats.l3_files} files  |  "
        f"Sessions: {stats.total_sessions}  |  "
        f"Storage: {mem._format_bytes(stats.storage_bytes)}",
    ))

    # L2 surfaces
    surfaces = mem.list_l2_surfaces()
    if surfaces:
        table = Table(title="L2 Surfaces")
        table.add_column("Surface", style="cyan")
        table.add_column("Facts")
        table.add_column("File")
        for surface in surfaces:
            facts = mem.read_l2_facts(surface)
            table.add_row(surface, str(len(facts)), f"l2/{surface}.md")
        console.print(table)

    # L3 files
    l3_files = mem.list_l3_files()
    if l3_files:
        l3_table = Table(title="L3 Synthesis Files")
        l3_table.add_column("Name", style="cyan")
        l3_table.add_column("Size")
        for path in l3_files:
            size = len(path.read_text()) if path.exists() else 0
            l3_table.add_row(path.stem, f"{size} bytes")
        console.print(l3_table)

    if not surfaces and not l3_files:
        console.print("\n[yellow]No memory data yet. Run sessions to build memory.[/]")
        console.print("  Try: aiw improve")


@memory_app.command("show")
def memory_show_cmd(
    surface: str = typer.Argument(None, help="Surface name (coding, research, operations, decisions)"),
    l3: str = typer.Option(None, "--l3", "-3", help="L3 file name (profile, recent, scope)"),
):
    """Show memory contents for a surface or L3 synthesis."""
    from ai_workspace.agents.memory import PersistentMemory

    mem = PersistentMemory()

    if l3:
        content = mem.read_l3(l3)
        if content:
            console.print(Markdown(content))
        else:
            console.print(f"[yellow]No L3 file found: {l3}[/]")
        return

    if surface:
        facts = mem.read_l2_facts(surface)
        if facts:
            console.print(f"[bold]L2 Facts — {surface}[/]\n")
            for fact in facts:
                console.print(f"[cyan]## {fact['title']}[/]")
                console.print(fact["body"][:500])
                if fact.get("tags"):
                    console.print(f"[dim]Tags: {', '.join(fact['tags'])}[/]")
                if fact.get("source"):
                    console.print(f"[dim]{fact['source']}[/]")
                console.print()
        else:
            console.print(f"[yellow]No facts for surface: {surface}[/]")
        return

    # Default: show everything
    console.print(mem.summary())


@memory_app.command("l1")
def memory_l1_cmd(
    session_id: str = typer.Option(None, "--session", "-s", help="Filter by session ID"),
    limit: int = typer.Option(20, "--limit", "-l", help="Max events"),
    days: int = typer.Option(1, "--days", "-d", help="Days back"),
):
    """Show recent L1 trace events."""
    from datetime import timedelta

    from ai_workspace.agents.memory import PersistentMemory

    mem = PersistentMemory()

    since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    events = mem.read_l1_events(
        session_id=session_id,
        since=since_date,
        limit=limit,
    )

    if not events:
        console.print(f"[yellow]No L1 events found (since {since_date})[/]")
        return

    table = Table(title=f"L1 Events (last {days}d)")
    table.add_column("Time", style="dim")
    table.add_column("Type")
    table.add_column("Tool")
    table.add_column("Content")

    for event in events:
        ts = event.get("timestamp", "")[11:19] if len(event.get("timestamp", "")) > 19 else event.get("timestamp", "")
        content = event.get("content", "")[:80]
        table.add_row(
            ts,
            event.get("type", ""),
            event.get("tool", ""),
            content,
        )

    console.print(table)
    console.print(f"[dim]Showing {len(events)} events[/]")


@memory_app.command("consolidate")
def memory_consolidate_cmd():
    """Run L3 consolidation from current L2 facts."""
    from ai_workspace.agents.memory import PersistentMemory

    mem = PersistentMemory()
    console.print("[cyan]Running L3 consolidation...[/]")
    result = mem.consolidate_l3()
    for name, content in result.items():
        lines = content.strip().split("\n")
        first_line = lines[0] if lines else "(empty)"
        console.print(f"  [green]✓[/] L3/{name}.md — {first_line}")
    console.print("[green]Consolidation complete.[/]")


# ── Agent memory operations (DB-backed) ─────────────────────────


@memory_app.command()
def add(
    content: str = typer.Argument(..., help="What to remember"),
    agent: str = typer.Option("default", "--agent", "-a"),
    memory_type: str = typer.Option("fact", "--type", "-t"),
    importance: float = typer.Option(0.5, "--importance", "-i", min=0.0, max=1.0),
):
    """Remember a fact or learning."""
    store = get_store()
    store.initialize()
    mid = store.remember(agent, content, memory_type, importance)
    store.close()
    console.print(f"[green] Memory #{mid} stored for agent '{agent}'[/]")


@memory_app.command()
def recall(
    query: str = typer.Argument(..., help="Search query"),
    agent: str = typer.Option("default", "--agent", "-a"),
    limit: int = typer.Option(10, "--limit", "-l"),
):
    """Recall agent memories."""
    store = get_store()
    store.initialize()
    memories = store.recall(agent, query, limit=limit)
    store.close()

    if not memories:
        console.print("[dim]No memories found[/]")
        return

    for m in memories:
        console.print(Panel(
            f"{m['content'][:500]}",
            title=f" {m['memory_type']} (importance: {m.get('importance', 0):.0%})",
            subtitle=f"ID: {m['id']} | {m.get('created_at', '')}",
        ))


@memory_app.command(name="list")
def memory_list(
    limit: int = typer.Option(20, "--limit", "-l", help="Max entries to show"),
):
    """List recent memories from markdown files and database."""

    store = get_store()
    entries: list[dict[str, Any]] = []

    # Try PostgreSQL first
    try:
        store.initialize()
        raw = store.recall("%", "%", limit=limit)
        for r in raw:
            entries.append({
                "source": "db",
                "title": r.get("content", "")[:80],
                "type": r.get("memory_type", "?"),
                "importance": r.get("importance", 0),
                "date": str(r.get("created_at", ""))[:19],
            })
    except Exception:
        pass

    if store._conn:
        store.close()

    # Fallback: read markdown memory files
    mem_files = store.list_memory_files()
    for mf in mem_files:
        content = store.read_memory_markdown(mf["type"])
        if content:
            entries.append({
                "source": mf["path"],
                "title": f"{mf['entries']} entries",
                "type": mf["type"],
                "importance": 0,
                "date": "",
            })

    if not entries:
        console.print("[dim]No memories found (no DB connected, no markdown files)[/]")
        console.print("[dim]Run 'aiw wf run learn --observation \"...\"' to create one[/]")
        return

    table = Table(title=" Memory")
    table.add_column("Source", style="dim")
    table.add_column("Type", style="cyan")
    table.add_column("Content / Stats", style="green")
    table.add_column("Date", style="dim")

    for e in entries[:limit]:
        table.add_row(
            e["source"],
            e["type"],
            e["title"][:100],
            e["date"],
        )

    console.print(table)


@memory_app.command(name="search")
def memory_search(
    query: str = typer.Argument(..., help="Search term"),
    limit: int = typer.Option(10, "--limit", "-l"),
):
    """Search memories across database and markdown files."""

    store = get_store()
    results: list[dict[str, Any]] = []

    # Try PostgreSQL
    try:
        store.initialize()
        db_results = store.recall("%", query, limit=limit)
        for r in db_results:
            results.append({
                "source": "db",
                "content": r["content"][:300],
                "type": r.get("memory_type", "?"),
                "importance": r.get("importance", 0),
                "date": str(r.get("created_at", ""))[:19],
            })
    except Exception:
        pass

    if store._conn:
        store.close()

    # Search markdown files
    for mem_type in ["convention", "pattern", "learning"]:
        content = store.read_memory_markdown(mem_type)
        if content and query.lower() in content.lower():
            # Extract the matching section
            sections = content.split("\n## ")
            for section in sections:
                if query.lower() in section.lower():
                    first_line = section.strip().split("\n")[0]
                    results.append({
                        "source": f"memory/{mem_type}s.md",
                        "content": first_line[:200],
                        "type": mem_type,
                        "importance": 0,
                        "date": "",
                    })

    if not results:
        console.print(f"[dim]No results for '{query}'[/]")
        return

    console.print(f"[bold] Results for '{query}':[/]\n")
    for r in results[:limit]:
        console.print(Panel(
            r["content"],
            title=f" {r['source']} — {r['type']}",
            subtitle=r["date"] if r["date"] else "",
        ))
