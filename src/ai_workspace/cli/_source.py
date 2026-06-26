"""CLI commands for source reputation — `aiw source`."""

from __future__ import annotations

import typer
from rich.panel import Panel

from ai_workspace.cli._app import app, console
from rich.panel import Panel

source_app = typer.Typer(
    help="Manage source reputation (CRED-1 + tracking)",
)
app.add_typer(source_app, name="source")


@source_app.command(name="stats")
def source_stats_cmd():
    """Show source reputation system statistics."""
    from ai_workspace.core.sources import SourceReputationService

    src = SourceReputationService()
    try:
        s = src.stats()
        console.print(Panel(
            f"[bold]Total domains tracked:[/] {s['total_domains']}\n"
            f"[bold]CRED-1 coverage:[/] {s['cred1_coverage']} / {s['total_domains']} "
            f"({s['cred1_coverage']/max(s['total_domains'],1)*100:.1f}%)\n"
            f"[bold]Sources used (tracking):[/] {s['sources_tracked']}\n"
            f"[bold]Average score:[/] {s['avg_score']:.2f}",
            title=" Source Reputation",
            border_style="cyan",
        ))
    except Exception as e:
        console.print(f"[red]Error: {e}[/]")


@source_app.command()
def seed(
    dataset_path: str | None = typer.Option(None, "--dataset", "-d", help="Path to CRED-1 JSON file"),
):
    """Seed the source reputation database with CRED-1 dataset."""
    import os as _os
    from ai_workspace.core.sources import SourceReputationService

    src = SourceReputationService()
    src.initialize()

    if dataset_path is None:
        default_path = _os.path.expanduser("~/.ai-workspace/cred1_current.json")
        if _os.path.exists(default_path):
            dataset_path = default_path
        else:
            console.print("[yellow]No dataset found. Download it first:[/]")
            console.print("  curl -sL https://raw.githubusercontent.com/aloth/cred-1/main/data/cred1_current.json -o ~/.ai-workspace/cred1_current.json")
            return

    console.print(f"[dim]Loading CRED-1 from {dataset_path}...[/]")
    count = src.seed_cred1(dataset_path)
    console.print(f"[green] Seeded {count} domains from CRED-1[/]")

    reliable = src.seed_reliable()
    console.print(f"[green] Added {reliable} reliable domains manually[/]")
    console.print()
    src_stats = src.stats()
    console.print(f"[bold]Total:[/] {src_stats['total_domains']} domains | [bold]Avg score:[/] {src_stats['avg_score']:.2f}")


@source_app.command()
def check(
    url: str = typer.Argument(..., help="URL or domain to check"),
):
    """Check credibility score for a domain."""
    from ai_workspace.core.sources import SourceReputationService

    src = SourceReputationService()
    result = src.get_score(url)

    level_color = {"trust": "green", "warn": "yellow", "ignore": "red"}
    level_icon = {"trust": "", "warn": "", "ignore": ""}

    console.print(Panel(
        f"[bold]Domain:[/] {result['domain']}\n"
        f"[bold]Score:[/] [{level_color[result['level']]}]{result['composite_score']:.2f}[/] "
        f"{level_icon[result['level']]} {result['level']}\n"
        f"[bold]CRED-1 score:[/] {result.get('cred1_score', 'N/A')}\n"
        f"[bold]Accuracy rate:[/] {result.get('accuracy_rate', 'N/A')}",
        title=" Source Check",
    ))


@source_app.command(name="endorse")
def source_endorse(url: str = typer.Argument(..., help="URL or domain to endorse as reliable")):
    """Mark a source as trustworthy."""
    from ai_workspace.core.sources import SourceReputationService

    svc = SourceReputationService()
    svc.initialize()
    svc.endorse(url)
    console.print(f"[green] Endorsed {url}[/]")


@source_app.command(name="flag")
def source_flag(url: str = typer.Argument(..., help="URL or domain to flag as unreliable")):
    """Flag a source as unreliable."""
    from ai_workspace.core.sources import SourceReputationService

    svc = SourceReputationService()
    svc.initialize()
    svc.flag(url)
    console.print(f"[yellow] Flagged {url}[/]")
