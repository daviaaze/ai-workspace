"""CLI commands — `aiw obsidian`."""

import typer

from ai_workspace.cli._app import app, console

# Obsidian commands

obsidian_app = typer.Typer(help="Obsidian vault operations")
app.add_typer(obsidian_app, name="obsidian")


@obsidian_app.command()
def sync(
    vault_path: str | None = typer.Option(None, "--vault", "-v", help="Vault path"),
    direction: str = typer.Option("both", "--direction", "-d", help="import, export, both"),
):
    """Sync AI Workspace ↔ Obsidian vault."""
    from ai_workspace.tasks import sync_obsidian_task

    result = sync_obsidian_task(vault_path=vault_path, direction=direction)

    console.print("[green] Sync complete[/]")
    console.print(f"  Imported: {result['imported']} notes")
    console.print(f"  Exported: {result['exported']} notes")
