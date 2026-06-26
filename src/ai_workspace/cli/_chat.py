"""CLI commands — `aiw chat`, `aiw trace`.

`aiw chat` is the daily driver REPL; `aiw trace` provides execution-trace inspection.
"""

from __future__ import annotations

import asyncio
from typing import Any

import typer
from rich.panel import Panel
from rich.table import Table


from ai_workspace.cli._app import app, console

# ── Trace commands (observability) ───────────────────────


trace_app = typer.Typer(help="Agent execution traces")
app.add_typer(trace_app, name="trace")


@trace_app.command(name="list")
def trace_list(
    limit: int = typer.Option(20, "--limit", "-l", help="Max sessions"),
):
    """List recent agent execution traces."""
    from ai_workspace.observability import TraceStore

    store = TraceStore()
    sessions = store.list_sessions(limit=limit)

    if not sessions:
        console.print("[dim]No traces yet. Run an agent to create traces.[/]")
        return

    table = Table(title=" Agent Traces", show_header=True)
    table.add_column("Session ID", style="cyan")
    table.add_column("Task")
    table.add_column("Model", style="dim")
    table.add_column("Steps", justify="right")
    table.add_column("Tokens", justify="right")
    table.add_column("Errors", justify="right")
    table.add_column("Duration", justify="right")

    for s in sessions:
        table.add_row(
            s["session_id"][:20],
            s["task"][:50],
            s["model"][:15],
            str(s["steps"]),
            str(s["tokens"]),
            str(s["errors"]),
            f"{s['duration_ms']:.0f}ms",
        )

    console.print(table)


@trace_app.command(name="show")
def trace_show(
    session_id: str = typer.Argument(..., help="Session ID to inspect"),
    steps: bool = typer.Option(False, "--steps", "-s", help="Show full timeline"),
    diff: bool = typer.Option(False, "--diff", "-d", help="Show file diffs"),
):
    """Show details of an agent execution trace."""
    from ai_workspace.observability import TraceStore, DiffTracker

    store = TraceStore()
    trace = store.load(session_id)

    if trace is None:
        console.print(f"[red]Trace not found: {session_id}[/]")
        raise typer.Exit(1)

    # Summary
    console.print(Panel(
        f"Task: {trace.task[:200]}\n"
        f"Model: {trace.model} | Provider: {trace.provider}\n"
        f"Steps: {len(trace.steps)} | Tokens: {trace.tokens_used} | "
        f"Duration: {trace.duration_ms:.0f}ms",
        title=f" Trace: {session_id[:30]}",
    ))

    # Tools summary
    if trace.tools_called:
        console.print("\n[bold]Tools Called:[/]")
        for tool, count in sorted(trace.tools_called.items()):
            console.print(f"  {tool}: {count} calls")

    # Errors
    if trace.errors:
        console.print(f"\n[bold red]Errors: {len(trace.errors)}[/]")
        for err in trace.errors[:5]:
            console.print(f"  [red]{err.get('message', str(err))[:120]}[/]")

    # Timeline
    if steps:
        timeline_header = f"\n[bold]Timeline ({len(trace.steps)} steps):[/]"
        timeline_icon = {
            "token": "",        "tool_call": "",           "tool_result": "",
            "error": "",        "phase": "",            "done": "",
        }
        console.print(timeline_header)
        for i, step in enumerate(trace.steps):
            icon = timeline_icon.get(step.get("type", ""), "")
            detail = str(step.get("data", ""))[:100]
            console.print(f"  {i:3d} {icon} [{step.get('type', '?')}]{' ' + detail if detail else ''}")

    # Diffs
    if diff and trace.diff_tracker_data:
        tracker = DiffTracker.from_dict(trace.diff_tracker_data)
        summary = tracker.get_summary()
        console.print(f"\n[bold]File Changes: {summary['files_modified']} files[/]")
        for path, count in summary["changes"].items():
            console.print(f"  {path}: {count} changes")


# ── Chat v2 command (primary daily-driver interface) ───────────────


@app.command()
def chat(
    workspace: str = typer.Option("personal", "--workspace", "-w", help="Workspace context (personal, work, etc.)"),
    agent: str = typer.Option("default", "--persona", "-p", help="Persona: default, coder, researcher, planner"),
    provider: str = typer.Option(
        "ollama", "--provider", help="LLM provider: ollama, deepseek, nvidia, openrouter"
    ),
    model: str | None = typer.Option(None, "--model", "-m", help="Model name (uses provider default if not set)"),
    no_recall: bool = typer.Option(False, "--no-recall", help="Disable auto-recall of past context"),
):
    """Start an interactive chat session with persistent memory.

    The chat REPL maintains conversation history, auto-recalls relevant
    past context from the knowledge base and stores key turns as agent
    memories for future recall.

    Slash commands available in the REPL:
        /workspace, /persona, /model, /provider, /recall, /clear,
        /save, /status, /help, /exit
    """
    from ai_workspace.chat import run_chat_repl

    run_chat_repl(
        workspace=workspace,
        agent=agent,
        provider=provider,
        model=model,
        no_recall=no_recall,
    )
