"""CLI commands — `aiw session`."""

import typer
from rich.panel import Panel
from rich.table import Table

from ai_workspace.cli._app import app, console

# Session command — persistent agent conversations

session_app = typer.Typer(help="Persistent agent sessions (like pi's sessions)")
app.add_typer(session_app, name="session")


@session_app.command("start")
def session_start(
    cwd: str = typer.Option(".", "--dir", "-d", help="Working directory"),
    model: str = typer.Option("qwen3:14b", "--model", "-m", help="Model for the session"),
    label: str = typer.Option(None, "--label", "-l", help="Label for this session"),
):
    """Start a new persistent agent session."""
    from ai_workspace.agents.session import PersistentAgentSession

    session = PersistentAgentSession(cwd=cwd, model=model)
    session.store.update_session(session.session_id, label=label)

    console.print(Panel(
        f"[bold]Session Started[/]\n"
        f"ID: [cyan]{session.session_id}[/]\n"
        f"Dir: {session.cwd}\n"
        f"Model: {session.model}\n"
        f"Label: {label or '—'}",
        title=" New Session"
    ))
    console.print("\n[dim]Use 'aiw session chat {session.session_id}' to continue, or Ctrl+D to exit[/]\n")

    # Interactive loop
    import asyncio

    async def interactive():
        await session.start()
        while True:
            try:
                msg = Prompt.ask("[bold][/]")
                if not msg.strip():
                    continue
                if msg.lower() in ("exit", "quit", "q", "/q"):
                    break
                if msg.startswith("/model "):
                    new_model = msg[7:].strip()
                    session.switch_model(new_model)
                    console.print(f"[cyan]Switched to {new_model}[/]")
                    continue
                if msg == "/stats":
                    stats = session.get_stats()
                    console.print(json.dumps(stats, indent=2, default=str))
                    continue
                if msg == "/history":
                    history = session.get_history(limit=10)
                    for h in history:
                        role_icon = "" if h["role"] == "user" else ""
                        console.print(f"  {role_icon} {h['content'][:100]}")
                    continue
                if msg == "/export":
                    path = session.export()
                    console.print(f"[green]Exported to {path}[/]")
                    continue

                console.print()
                with console.status("[cyan]Thinking...", spinner="dots"):
                    response = await session.send(msg)
                console.print(Panel(str(response), title=" Response"))
                console.print()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]Ending session...[/]")
                break
        session.close()

    asyncio.run(interactive())


@session_app.command("chat")
def session_chat(
    session_id: str = typer.Argument(..., help="Session ID to resume"),
):
    """Resume an existing agent session."""
    from ai_workspace.agents.session import PersistentAgentSession

    try:
        session = PersistentAgentSession(session_id=session_id)
    except Exception as e:
        console.print(f"[red]Failed to load session: {e}[/]")
        raise typer.Exit(1)

    console.print(Panel(
        f"[bold]Session Resumed[/]\nID: [cyan]{session.session_id}[/]\nModel: {session.model}",
        title=" Resume"
    ))
    console.print()

    import asyncio

    async def interactive():
        await session.start()

        # Show recent history
        history = session.get_history(limit=5)
        if history:
            console.print("[dim]Recent history:[/]")
            for h in history:
                role_icon = "" if h["role"] == "user" else ""
                console.print(f"  {role_icon} {h['content'][:120]}")
            console.print()

        while True:
            try:
                msg = Prompt.ask("[bold][/]")
                if not msg.strip():
                    continue
                if msg.lower() in ("exit", "quit", "q", "/q"):
                    break
                if msg.startswith("/model "):
                    session.switch_model(msg[7:].strip())
                    continue
                if msg == "/stats":
                    console.print(json.dumps(session.get_stats(), indent=2, default=str))
                    continue
                if msg == "/export":
                    path = session.export()
                    console.print(f"[green]Exported to {path}[/]")
                    continue

                console.print()
                with console.status("[cyan]Thinking...", spinner="dots"):
                    response = await session.send(msg)
                console.print(Panel(str(response), title=" Response"))
                console.print()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]Session saved. Use 'aiw session chat' to resume.[/]")
                break
        session.close()

    asyncio.run(interactive())


@session_app.command("list")
def session_list(
    limit: int = typer.Option(20, "--limit", "-n", help="Max sessions to show"),
):
    """List recent agent sessions."""
    from ai_workspace.core.sessions import SessionStore

    store = SessionStore()
    store.initialize()
    sessions = store.list_sessions(limit=limit)
    store.close()

    if not sessions:
        console.print("[dim]No sessions yet. Start one with 'aiw session start'[/]")
        return

    table = Table(title="Agent Sessions")
    table.add_column("ID", style="cyan")
    table.add_column("Label")
    table.add_column("CWD")
    table.add_column("Model")
    table.add_column("Entries")
    table.add_column("Updated", style="dim")

    for s in sessions:
        table.add_row(
            s["id"][:12] + "…",
            s.get("label", "—") or "—",
            s.get("cwd", ".")[:30],
            s.get("model", "—")[:20],
            str(s.get("entry_count", 0)),
            s.get("updated_at", "")[:19] if s.get("updated_at") else "—",
        )

    console.print(table)


@session_app.command("export")
def session_export(
    session_id: str = typer.Argument(..., help="Session ID to export"),
    output: str = typer.Option(None, "--output", "-o", help="Output JSONL file path"),
):
    """Export a session to pi-compatible JSONL format."""
    from ai_workspace.core.sessions import SessionStore

    store = SessionStore()
    store.initialize()
    path = store.export_jsonl(session_id, Path(output) if output else None)
    store.close()
    console.print(f"[green] Exported to {path}[/]")


@session_app.command("import")
def session_import(
    path: str = typer.Argument(..., help="JSONL file to import"),
):
    """Import a session from pi's JSONL format."""
    from ai_workspace.core.sessions import SessionStore

    store = SessionStore()
    store.initialize()
    session_id = store.import_jsonl(Path(path))
    store.close()
    console.print(f"[green] Imported as session {session_id}[/]")
