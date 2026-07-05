"""CLI commands — `aiw docs`."""

from __future__ import annotations

import typer
from rich.panel import Panel

from ai_workspace.cli._app import app, console

docs_app = typer.Typer(help="Index and search external documentation")
app.add_typer(docs_app, name="docs")


@docs_app.command(name="index")
def docs_index(
    url: str = typer.Argument(..., help="Documentation URL to index"),
    name: str = typer.Option("", "--name", "-n", help="Short name for this doc source"),
    review: bool = typer.Option(False, "--review", "-r", help="Use LLM to review extraction quality"),
    max_depth: int = typer.Option(2, "--depth", "-d", help="Max crawl depth (1-5)"),
    max_pages: int = typer.Option(50, "--max-pages", "-m", help="Max pages to fetch"),
):
    """Crawl and index external documentation.

    Fetches pages recursively (same domain, max-depth), extracts
    text with BeautifulSoup, chunks, and indexes via the RAG pipeline
    (pgvector for semantic search).

    Use --review to let an LLM inspect the first page and suggest
    extraction rules for tricky doc sites.
    """
    import asyncio

    from ai_workspace.knowledge.doc_indexer import DocIndexer

    indexer = DocIndexer()
    result = asyncio.run(indexer.index(url, name=name, review=review, max_depth=max_depth, max_pages=max_pages))

    console.print(f"[green] Indexed[/] {result['name']}")
    console.print(f"  Pages:  {result['pages']}")
    console.print(f"  Chunks: {result['chunks']}")
    if result.get("skipped"):
        console.print(f"  [dim]Skipped (unchanged): {result['skipped']}[/]")
    if result["errors"]:
        console.print(f"  [yellow]Errors: {result['errors']}[/]")
    if result["suggestions"]:
        console.print(f"  [dim]LLM suggestions: {len(result['suggestions'])}[/]")
        for s in result["suggestions"]:
            console.print(f"    - {s.get('reason', str(s)[:80])}")


@docs_app.command(name="search")
def docs_search(
    query: str = typer.Argument(..., help="Search query"),
    doc: str = typer.Option("", "--doc", "-d", help="Narrow to specific doc source"),
    count: int = typer.Option(5, "--count", "-c", help="Number of results"),
):
    """Search indexed documentation.

    Uses pgvector cosine similarity over indexed doc chunks.
    """
    from ai_workspace.knowledge.doc_indexer import DocIndexer

    indexer = DocIndexer()
    results = indexer.search(query, k=count, doc_name=doc)

    if not results:
        console.print("[yellow]No results found.[/]")
        console.print("Tip: use 'aiw docs index <url>' to index a documentation source first.")
        return

    for r in results:
        title = r["page_title"] or r["doc_name"] or "Untitled"
        source = r["source_url"] or ""
        score = r.get("score", 0.0)
        console.print(Panel(
            r["content"][:500],
            title=f" {title}",
            subtitle=f"[dim]{source} · {score:.1%}[/]" if source else f"[dim]{score:.1%}[/]",
        ))


@docs_app.command(name="list")
def docs_list():
    """List all indexed documentation sources."""
    from ai_workspace.knowledge.doc_indexer import DocIndexer

    indexer = DocIndexer()
    sources = indexer.list_sources()

    if not sources:
        console.print("[yellow]No documentation sources indexed yet.[/]")
        console.print("Tip: use 'aiw docs index <url>' to index documentation.")
        return

    console.print("[bold cyan]Indexed documentation sources:[/]")
    console.print()
    for src in sources:
        console.print(f"  [green]{src['name']}[/]")
        console.print(f"    Chunks: {src['chunk_count']}  |  Indexed: {src['first_indexed'][:10]}")


@docs_app.command(name="remove")
def docs_remove(
    name: str = typer.Argument(..., help="Doc source name to remove"),
):
    """Remove an indexed documentation source."""
    from ai_workspace.knowledge.doc_indexer import DocIndexer

    indexer = DocIndexer()
    removed = indexer.remove_source(name)
    if removed:
        console.print(f"[green] Removed {removed} chunks for '{name}'[/]")
    else:
        console.print(f"[yellow]No data found for '{name}'[/]")
