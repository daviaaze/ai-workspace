"""CLI commands — `aiw rules`."""

from __future__ import annotations

import typer
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from ai_workspace.cli._app import app, console

# Rules command

rules_app = typer.Typer(help="Manage behavioral rules for agents")
app.add_typer(rules_app, name="rules")


@rules_app.command(name="list")
def rules_list():
    """List all active rules and their tags."""
    from ai_workspace.rules import get_rules_loader

    loader = get_rules_loader()
    rules = loader.all

    if not rules:
        console.print("[dim]No rules loaded.[/]")
        return

    table = Table(title=" Behavioral Rules")
    table.add_column("Rule", style="cyan")
    table.add_column("Tags")
    table.add_column("Always Apply")
    table.add_column("Lines")

    for rule in rules:
        tag_str = ", ".join(sorted(rule.tags))
        always = "[green][/]" if rule.always_apply else "[dim]—[/]"
        lines = str(rule.content.count("\n") + 1)
        table.add_row(rule.name, tag_str, always, lines)

    console.print(table)


@rules_app.command(name="show")
def rules_show(
    name: str = typer.Argument(..., help="Rule name to show"),
):
    """Show the full content of a rule."""
    from ai_workspace.rules import get_rules_loader

    loader = get_rules_loader()
    rule = loader.get(name)

    if not rule:
        known = ", ".join(r.name for r in loader.all)
        console.print(f"[red]Unknown rule: {name}[/]\nAvailable: {known}")
        raise typer.Exit(1)

    tags = ", ".join(sorted(rule.tags)) if rule.tags else "none"
    always = "yes" if rule.always_apply else "no"

    console.print(Panel(
        rule.content,
        title=f" Rule: {rule.name}",
        subtitle=f"Tags: {tags}  |  Always apply: {always}",
    ))
