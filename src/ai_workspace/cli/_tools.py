"""CLI commands — `aiw tools`."""

import typer
from rich.panel import Panel

from ai_workspace.cli._app import app, console

# Tool commands (web fetch, browser, marketplace search)

tool_app = typer.Typer(help="Web research tools (fetch, browser, marketplace)")
app.add_typer(tool_app, name="tool")


@tool_app.command()
def fetch(
    url: str = typer.Argument(..., help="URL to fetch and extract text from"),
    max_length: int = typer.Option(5000, "--max-length", "-l", help="Max chars to return"),
):
    """Fetch a URL and extract readable text."""
    from ai_workspace.tools import WebFetchTool
    tool = WebFetchTool()
    result = tool._run(url=url, max_length=max_length)
    console.print(Panel(str(result), title=f" {url[:60]}", border_style="blue"))


@tool_app.command()
def browser(
    url: str = typer.Argument(..., help="URL to open in headless browser (for SPA/JS pages)"),
    max_length: int = typer.Option(8000, "--max-length", "-l", help="Max chars to return"),
    wait_selector: str = typer.Option("", "--wait", "-w", help="CSS selector to wait for"),
    wait_time: int = typer.Option(3, "--wait-time", "-t", help="Extra seconds to wait after page loads"),
):
    """Render a JavaScript SPA page in a headless browser."""
    console.print("[dim]Opening browser...[/]")
    from ai_workspace.tools import HeadlessBrowserTool
    tool = HeadlessBrowserTool()
    result = tool._run(url=url, max_length=max_length, wait_selector=wait_selector, wait_time=wait_time)
    console.print(Panel(str(result)[:max_length], title=f" {url[:60]}", border_style="blue"))


@tool_app.command(name="scrape")
def scrape(
    url: str = typer.Argument(..., help="URL of the first page to scrape"),
    max_pages: int = typer.Option(20, "--max-pages", "-p", help="Maximum pages to scrape"),
    next_button: str = typer.Option("Próximo", "--next", "-n", help="Text on the next-page button"),
):
    """Scrape a multi-page SPA by clicking 'next page'."""
    console.print(f"[dim]Scraping up to {max_pages} pages...[/]")
    from ai_workspace.tools import PaginatedScraperTool
    tool = PaginatedScraperTool()
    result = tool._run(url=url, max_pages=max_pages, next_button_text=next_button)
    console.print(Panel(str(result)[:10000], title=f" {url[:60]}", border_style="blue"))


@tool_app.command(name="ml")
def mercado_livre(
    query: str = typer.Argument(..., help="Search query for Mercado Livre"),
    max_results: int = typer.Option(10, "--max-results", "-n", help="Max results"),
    max_price: float | None = typer.Option(None, "--max-price", help="Max price filter (BRL)"),
):
    """Search Mercado Livre for product prices."""
    from ai_workspace.tools import MercadoLivreSearchTool
    tool = MercadoLivreSearchTool()
    result = tool._run(query=query, max_results=max_results, max_price=max_price)
    console.print(Panel(str(result), title=f" Mercado Livre: {query}", border_style="green"))


@tool_app.command(name="olx")
def olx(
    query: str = typer.Argument(..., help="Search query for OLX"),
    max_results: int = typer.Option(10, "--max-results", "-n", help="Max results"),
    max_price: float | None = typer.Option(None, "--max-price", help="Max price filter (BRL)"),
):
    """Search OLX for product prices."""
    from ai_workspace.tools import OLXSearchTool
    tool = OLXSearchTool()
    result = tool._run(query=query, max_results=max_results, max_price=max_price)
    console.print(Panel(str(result), title=f" OLX: {query}", border_style="yellow"))
