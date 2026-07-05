"""CLI commands — `aiw kb`."""

from __future__ import annotations

import typer
from rich.panel import Panel

from ai_workspace.cli._app import app, console
from ai_workspace.core.db import get_store

# Knowledge Base commands

kb_app = typer.Typer(help="Knowledge base operations")
app.add_typer(kb_app, name="kb")


@kb_app.command()
def seed():
    """Index the aiw codebase into the knowledge graph for agent context."""
    from ai_workspace.knowledge.seed import seed as run_seed
    console.print("[bold cyan]Seeding aiw knowledge graph...[/]\n")
    indexed, skipped = run_seed(verbose=True)
    console.print(f"\n[green] {indexed} files indexed, {skipped} skipped[/]")
    console.print("[dim]Agents can now search the codebase via the MCP search_knowledge tool.[/]")


@kb_app.command(name="index")
def kb_index(
    path: str = typer.Option(".", "--path", "-p", help="Directory to index"),
    glob: str = typer.Option("**/*.{py,md}", "--glob", "-g", help="File pattern"),
):
    """Index workspace files into pgvector for RAG retrieval.

    Chunks Python files by def/class, Markdown by headings, and generic
    files with fixed-size overlapping windows. Embeddings use Ollama's
    nomic-embed-text (768-dim).
    """
    from ai_workspace.knowledge import index_workspace, setup_schema

    console.print(f"[bold cyan]Indexing {path} ({glob})...[/]\n")

    setup_schema()
    count = index_workspace(Path(path), glob=glob)

    console.print(f"\n[green] {count} chunks indexed into pgvector[/]")
    console.print("[dim]Use 'aiw kb rag-search' to query the knowledge base.[/]")


@kb_app.command()
def add(
    content: str = typer.Argument(..., help="Content to add"),
    title: str | None = typer.Option(None, "--title", "-t"),
    content_type: str = typer.Option("note", "--type"),
    tags: list[str] | None = typer.Option(None, "--tag"),
):
    """Add a knowledge entry."""
    store = get_store()
    store.initialize()
    kid = store.add_knowledge(content, content_type, title, tags=tags)
    store.close()
    console.print(f"[green] Knowledge entry #{kid} added[/]")


@kb_app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    content_type: str | None = typer.Option(None, "--type", "-t"),
    limit: int = typer.Option(10, "--limit", "-l"),
):
    """Search knowledge entries (legacy text search)."""
    store = get_store()
    store.initialize()
    entries = store.search_knowledge(query, content_type=content_type, limit=limit)
    store.close()

    if not entries:
        console.print("[dim]No entries found[/]")
        return

    for e in entries:
        console.print(Panel(
            e["content"][:300],
            title=f" {e.get('title', '#' + str(e.get('id', '?')))} [{e.get('content_type', 'note')}]",
            subtitle=f"ID: {e['id']} | {e.get('created_at', '')}",
        ))


@kb_app.command(name="rag-search")
def kb_rag_search(
    query: str = typer.Argument(..., help="Search query"),
    k: int = typer.Option(5, "--top", "-k", help="Number of results"),
    strategy: str = typer.Option("hybrid", "--strategy", "-s", help="Search: hybrid, dense, or sparse"),
):
    """Hybrid RAG search (dense vector + BM25 + RRF merge).

    Uses pgvector for vector similarity and PostgreSQL tsvector
    for keyword search. Results are merged via Reciprocal Rank Fusion.
    """
    from ai_workspace.knowledge import search_knowledge as rag_search

    console.print(f"[bold cyan]RAG Search[/]: {query}")
    console.print(f"[dim]Strategy: {strategy} | Top-k: {k}[/]\n")

    results = rag_search(query, k=k, strategy=strategy)

    if not results:
        console.print("[dim]No results found. Try 'aiw kb index' first.[/]")
        return

    for r in results:
        source = f"{r['source_file']}"
        if r.get("start_line"):
            source += f":L{r['start_line']}"
        console.print(Panel(
            r["content"][:500],
            title=f" {source} [score: {r['score']:.3f}]",
        ))


# Worker command (Huey consumer)

@app.command()
def worker():
    """Start the task worker (Huey consumer) to process tasks and periodic schedules."""
    from ai_workspace.tasks import start_worker

    console.print("[bold cyan]Starting AI Workspace task worker...[/]")
    console.print("[dim]Handles periodic tasks + enqueued jobs. Press Ctrl+C to stop.[/]")
    console.print()

    start_worker()
