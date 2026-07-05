"""CLI commands — `aiw skill`."""

import typer
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from ai_workspace.cli._app import app, console

# Skill commands

skill_app = typer.Typer(help="Run pi-compatible skills as agent workflows")
app.add_typer(skill_app, name="skill")


@skill_app.command(name="list")
def skill_list():
    """List available skills from pi-setup/skills/ and ~/.agents/skills/"""
    from ai_workspace.skills import get_loader

    loader = get_loader()
    skills = loader.list_skills()

    if not skills:
        console.print("[dim]No skills found. Add SKILL.md files to pi-setup/skills/ or ~/.agents/skills/[/]")
        return

    table = Table(title="  Available Skills")
    table.add_column("Name", style="cyan")
    table.add_column("Source", style="dim")
    table.add_column("Steps", justify="right")
    table.add_column("Description")

    for s in skills:
        table.add_row(s["name"], s["source"], str(s["steps"]), s["description"][:80])

    console.print(table)


@skill_app.command(name="run")
def skill_run(
    name: str = typer.Argument(..., help="Skill name (e.g., debug, feature-dev, commit)"),
    task: str = typer.Argument(..., help="Task description"),
    provider: str = typer.Option("ollama", "--provider", "-p", help="LLM provider"),
    model: str | None = typer.Option(None, "--model", "-m", help="Model name"),
):
    """Run a skill with a task.

    Examples:
        aiw skill run debug "tests failing in test_store.py"
        aiw skill run feature-dev "add user authentication"
        aiw skill run commit
    """
    from ai_workspace.providers import ProviderRegistry
    from ai_workspace.skills import get_loader

    registry = ProviderRegistry()
    if model is None:
        model = registry.get_model(provider)

    loader = get_loader()

    try:
        skill = loader.get(name)
        if not skill:
            available = [s["name"] for s in loader.list_skills()]
            console.print(f"[red] Skill '{name}' not found.[/]")
            console.print(f"[dim]Available: {', '.join(available)}[/]")
            raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red] {e}[/]")
        raise typer.Exit(1)

    console.print(f"[bold]  Skill: {name}[/]")
    console.print(f"[dim]{skill.description}[/]")
    console.print(f"[dim]Provider: {provider} | Model: {model}[/]")

    if skill.workflow_steps:
        console.print("\n[bold]Workflow:[/]")
        for i, step in enumerate(skill.workflow_steps, 1):
            console.print(f"  [dim]{i}.[/] {step[:100]}")

    console.print()

    with console.status(f"[cyan]Running {name}...", spinner="dots"):
        try:
            result = loader.run(
                name, task,
                provider=provider, model=model,
            )
        except Exception as e:
            console.print(f"[red] Skill failed: {e}[/]")
            raise typer.Exit(1)

    console.print(Panel(Markdown(str(result)[:8000]), title=f"  {name}: result"))
