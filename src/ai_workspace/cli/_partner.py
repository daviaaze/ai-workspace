"""CLI commands — `aiw partner`."""

from __future__ import annotations

import typer
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from ai_workspace.cli._app import app, console

# Partners command


partners_app = typer.Typer(help="Manage agent partners (DeepTutor-inspired SOUL.md system)")
app.add_typer(partners_app, name="partners")


@partners_app.command(name="list")
def partners_list():
    """List all registered partners."""
    from ai_workspace.agents.partner import Partner

    partners = Partner.list_all()
    if not partners:
        console.print("[yellow]No partners registered. Create one with: aiw partners create <name>[/]")
        return

    table = Table(title=" Partners")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    table.add_column("Tools")
    table.add_column("Soul")

    for p in partners:
        emoji = f"{p.emoji} " if p.emoji else ""
        desc = p.description[:60] if p.description else "—"
        tool_info = f"{len(p.tool_policy.allowed or [])} allowed" if p.tool_policy.allowed else "all"
        soul_preview = p.soul_preview[:50]
        table.add_row(p.partner_id, f"{emoji}{p.name}", desc, tool_info, soul_preview)

    console.print(table)


@partners_app.command(name="create")
def partners_create(
    name: str = typer.Argument(..., help="Partner name"),
    description: str = typer.Option("", "--desc", help="One-line description"),
    soul: str = typer.Option("", "--soul", help="SOUL.md content (identity / rules / expertise)"),
    soul_file: str = typer.Option("", "--soul-file", help="Read SOUL.md from a file"),
    emoji: str = typer.Option("", "--emoji", help="Emoji avatar (e.g. 🧠, 🤖)"),
    color: str = typer.Option("", "--color", help="UI accent color (e.g. #FF6B6B)"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing partner"),
):
    """Create a new agent partner with a SOUL.md identity."""
    from ai_workspace.agents.partner import Partner

    # Resolve soul content
    actual_soul = soul
    if soul_file:
        try:
            actual_soul = Path(soul_file).read_text(encoding="utf-8")
        except OSError as exc:
            console.print(f"[red]Failed to read soul file: {exc}[/]")
            raise typer.Exit(1)

    try:
        p = Partner.create(
            name=name,
            description=description,
            soul=actual_soul,
            emoji=emoji,
            color=color,
            overwrite=overwrite,
        )
        console.print(f"[green]Created partner[/] [bold cyan]{p.name}[/] ([dim]{p.partner_id}[/])")
        console.print(f"  Soul: {p.soul_preview}")
        console.print(f"  Workspace: {p.workspace_dir}")
    except FileExistsError as exc:
        console.print(f"[red]{exc}[/]")
        console.print("[yellow]Use --overwrite to replace the existing partner.[/]")
        raise typer.Exit(1)


@partners_app.command(name="show")
def partners_show(
    partner_id: str = typer.Argument(..., help="Partner ID or name"),
):
    """Show partner details including full SOUL.md."""
    from ai_workspace.agents.partner import Partner

    p = Partner.get(partner_id)
    if not p:
        console.print(f"[red]Partner not found: {partner_id}[/]")
        raise typer.Exit(1)

    console.print(f"[bold cyan]{p.emoji} {p.name}[/]")
    console.print(f"  ID: {p.partner_id}")
    console.print(f"  Description: {p.description or '—'}")
    console.print(f"  Created: {p.created_at[:19]}")
    console.print(f"  Updated: {p.updated_at[:19]}")
    console.print(f"  Workspace: {p.workspace_dir}")

    if p.tool_policy.allowed:
        console.print(f"  Tools allowed: {', '.join(p.tool_policy.allowed)}")
    if p.tool_policy.denied:
        console.print(f"  Tools denied: {', '.join(p.tool_policy.denied)}")

    console.print("")
    console.print("[bold]SOUL.md[/]")
    console.print(Markdown(p.soul if p.soul else "_(empty)_"))


@partners_app.command(name="delete")
def partners_delete(
    partner_id: str = typer.Argument(..., help="Partner ID or name"),
    force: bool = typer.Option(False, "--force", "-f", help="Delete without confirmation"),
):
    """Delete a partner and all its data."""
    from ai_workspace.agents.partner import Partner

    p = Partner.get(partner_id)
    if not p:
        console.print(f"[red]Partner not found: {partner_id}[/]")
        raise typer.Exit(1)

    if not force:
        confirm = Prompt.ask(
            f"[yellow]Delete partner '{p.name}' ({p.partner_id}) and all data?[/]",
            choices=["y", "n"],
            default="n",
        )
        if confirm != "y":
            console.print("[dim]Cancelled.[/]")
            return

    p.delete()
    console.print(f"[red]Deleted partner[/] [bold]{p.name}[/]")


@partners_app.command(name="chat")
def partners_chat(
    partner_id: str = typer.Argument(..., help="Partner ID or name"),
    message: str = typer.Argument(..., help="Message to send"),
):
    """Send a message to a partner (simulated consultation)."""
    from ai_workspace.agents.partner import Partner

    p = Partner.get(partner_id)
    if not p:
        console.print(f"[red]Partner not found: {partner_id}[/]")
        raise typer.Exit(1)

    response = p.consult(message)
    console.print(f"[bold]{p.emoji} {p.name}[/]")
    console.print(response)


@partners_app.command(name="soul")
def partners_soul(
    partner_id: str = typer.Argument(..., help="Partner ID or name"),
    soul: str = typer.Argument(..., help="New SOUL.md content (or use --file)"),
    file: str = typer.Option("", "--file", "-f", help="Read SOUL.md from a file"),
):
    """Update a partner's SOUL.md."""
    from ai_workspace.agents.partner import Partner

    p = Partner.get(partner_id)
    if not p:
        console.print(f"[red]Partner not found: {partner_id}[/]")
        raise typer.Exit(1)

    actual_soul = soul
    if file:
        try:
            actual_soul = Path(file).read_text(encoding="utf-8")
        except OSError as exc:
            console.print(f"[red]Failed to read file: {exc}[/]")
            raise typer.Exit(1)

    p.soul = actual_soul
    p.save()
    console.print(f"[green]Updated SOUL.md for {p.name}[/]")
    console.print(Markdown(p.soul[:500]))
