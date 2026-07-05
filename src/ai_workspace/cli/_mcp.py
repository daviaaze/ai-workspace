"""CLI commands — `aiw mcp`."""

from __future__ import annotations

import typer
from rich.table import Table

from ai_workspace.cli._app import app, console

# MCP server command


mcp_app = typer.Typer(help="MCP server for AI Workspace (expose aiw as tools)")
app.add_typer(mcp_app, name="mcp")


@mcp_app.command(name="serve")
def mcp_serve(
    transport: str = typer.Option("stdio", "--transport", "-t", help="Transport: stdio, http"),
    port: int = typer.Option(8765, "--port", "-p", help="Port for HTTP transport"),
):
    """Run the MCP server, exposing aiw as a tool provider.

    stdio transport is what Claude Desktop / Cursor / Cline / Continue expect.
    HTTP transport is useful for remote clients.

    Example claude_desktop_config.json entry:

        {
          "mcpServers": {
            "aiw": {
              "command": "aiw",
              "args": ["mcp", "serve"]
            }
          }
        }
    """
    from ai_workspace.mcp_server import TOOL_REGISTRY, run_stdio_server

    console.print("[bold cyan]AIW MCP Server[/]")
    console.print(f"  Transport: {transport}")
    console.print(f"  Tools exposed: {len(TOOL_REGISTRY)}")
    for name in TOOL_REGISTRY:
        console.print(f"    • {name}")
    console.print()

    if transport == "stdio":
        run_stdio_server()
    elif transport == "http":
        console.print("[yellow]HTTP transport not yet implemented; use stdio[/]")
        raise typer.Exit(1)
    else:
        console.print(f"[red]Unknown transport: {transport}[/]")
        raise typer.Exit(1)


@mcp_app.command(name="list")
def mcp_list():
    """List the tools that the MCP server exposes."""
    from ai_workspace.mcp_server import TOOL_REGISTRY

    table = Table(title=" MCP Tools Exposed by aiw")
    table.add_column("Tool", style="cyan")
    table.add_column("Description")

    for name, spec in TOOL_REGISTRY.items():
        desc = spec["schema"].get("description", "")
        table.add_row(name, desc[:120] + ("..." if len(desc) > 120 else ""))

    console.print(table)
