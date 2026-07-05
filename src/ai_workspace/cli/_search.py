"""CLI commands — `aiw search`."""

from __future__ import annotations

import typer
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from ai_workspace.cli._app import app, console


@app.command()
def search(
    query: str = typer.Argument(..., help="Research query"),
    depth: int = typer.Option(2, "--depth", "-d", help="Recursion depth (1-4)"),
    model: str = typer.Option("deepseek-r1:14b", "--model", "-m", help="Model for reasoning"),
    fast_model: str = typer.Option("qwen3:14b", "--fast-model", help="Model for planning/synthesis"),
    provider: str = typer.Option("ollama", "--provider", "-p", help="LLM provider: ollama, deepseek"),
    save: bool = typer.Option(True, "--save/--no-save", help="Save results to DB"),
    review: bool = typer.Option(False, "--review", "-r", help="Human-in-the-loop: pause for approval before returning"),
):
    """Run deep recursive research on a query."""
    from ai_workspace.core.cost import CostService
    from ai_workspace.search import DeepSearchEngine

    console.print(Panel(f"[bold cyan]Deep Research[/]\n{query}", title=" Query"))
    model_display = "deepseek-reasoner" if provider == "deepseek" else model
    fast_display = "deepseek-chat" if provider == "deepseek" else fast_model
    console.print(f"[dim]Provider: {provider} | Deep: {model_display} | Fast: {fast_display}[/]")

    # Initialize cost service (cache + log)
    cost = CostService()
    cost.initialize()
    console.print(f"[dim]Cache entries: {cost.cache.stats()['total_entries']}[/]")

    engine = DeepSearchEngine(
        model=f"ollama/{fast_model}" if provider == "ollama" else fast_model,
        deep_model=f"ollama/{model}" if provider == "ollama" else model,
        max_depth=depth,
        provider=provider,
        cost_service=cost,
    )

    # Live progress instead of silent spinner
    def on_progress(update: dict):
        phase = update["phase"]
        detail = update["detail"]
        status = update.get("status", "running")
        icon = {"planning": "", "supervising": "", "researching": "", "filtering": "", "synthesizing": "", "reviewing": ""}.get(phase, "•")
        if status == "done":
            console.print(f"  {icon} [green][/] {detail}")
        elif status == "info":
            console.print(f"    [dim]{detail}[/]")
        elif phase == "researching":
            current = update.get("current", 0)
            total = update.get("total", 0)
            bar = "" * current + "" * (total - current) if total else ""
            console.print(f"  {icon} {bar} [cyan]{detail}[/]")
        elif status == "awaiting_approval":
            # Human-in-the-loop: show report and ask for approval
            console.print("\n    [bold yellow]Human review requested[/]")
            report_info = update.get("report", {})
            console.print(f"  Summary: {report_info.get('summary', 'N/A')[:200]}")
            console.print(f"  Confidence: {report_info.get('confidence', 0):.0%}")
            console.print(f"  Sources: {len(report_info.get('sources', []))} total")
            console.print(f"\n  [dim]Preview: {report_info.get('preview', '')[:300]}[/]")
            console.print()
            response = typer.prompt(
                "  Approve report? [y=approve / n=reject / r=revise]",
                default="y",
            )
            if response.lower().startswith("y"):
                console.print("  [green] Approved[/]")
            elif response.lower().startswith("r"):
                console.print("  [yellow] Revision requested — re-synthesizing...[/]")
            else:
                console.print("  [red] Rejected[/]")
        else:
            console.print(f"  {icon} [yellow]⟳[/] {detail}")

    console.print()
    result = asyncio.run(engine.research(query, progress=on_progress, human_review=review))
    console.print()

    # Display results
    console.print()

    table = Table(title=" Research Coverage", show_header=True)
    table.add_column("#", style="dim")
    table.add_column("Question")
    table.add_column("Confidence")
    for i, sq in enumerate(result.sub_questions, 1):
        table.add_row(
            str(i),
            sq.question[:100] + ("..." if len(sq.question) > 100 else ""),
            f"{sq.confidence:.0%}",
        )
    console.print(table)

    if result.summary:
        console.print(Panel(
            Markdown(result.summary),
            title=" Executive Summary",
            border_style="green",
        ))

    if result.detailed_report:
        console.print()
        console.print(Panel(
            Markdown(result.detailed_report[:2000]),
            title=" Detailed Report",
            border_style="blue",
        ))

    if save:
        try:
            store = get_store()
            store.initialize()
            report = {
                "summary": result.summary,
                "detailed_report": result.detailed_report,
                "sources": result.sources,
                "confidence": float(result.confidence) if isinstance(result.confidence, (int, float)) else 0.0,
                "sub_questions": [
                    {"question": sq.question, "answer": sq.answer}
                    for sq in result.sub_questions
                ],
            }
            rid = store.save_research(query, report)
            store.close()
            console.print(f"\n[dim] Saved to DB (research #{rid})[/]")
        except Exception as e:
            console.print(f"\n[dim yellow] Could not save to DB: {e}[/]")


# Research command (v2 — graph-based multi-agent)

@app.command(name="deep-research")
def deep_research_cmd(
    query: str = typer.Argument(..., help="Research question"),
    depth: int = typer.Option(2, "--depth", "-d", help="Max recursion depth (1-4)"),
    parallel: int = typer.Option(3, "--parallel", "-j", help="Max concurrent research tasks"),
    max_tasks: int = typer.Option(3, "--max-tasks", "-n", help="Max sub-questions to research"),
    model: str = typer.Option("qwen3:14b", "--model", "-m", help="LLM model"),
    provider: str = typer.Option("ollama", "--provider", "-p", help="LLM provider"),
):
    """Deep research v2 — graph-based multi-agent research.

    Planner decomposes the query into a task DAG. Multiple agents
    execute in parallel. Results are verified and synthesized.
    """
    import asyncio

    from ai_workspace.search import deep_research as run_research

    console.print(Panel(f"[bold cyan]Research[/]\n{query}", title=" Query"))
    console.print(f"[dim]Model: {model} | Depth: {depth} | Parallel: {parallel}[/]")
    console.print()

    def on_progress(phase: str, detail: str):
        icon = {
            "planning": "", "executing": "", "verifying": "",
            "reflecting": "", "synthesizing": "",
        }.get(phase, "")
        if phase == "synthesizing":
            console.print(f"  {icon} [green]{detail}[/]")
        elif phase == "executing":
            console.print(f"  {icon} [dim]{detail}[/]")
        else:
            console.print(f"  {icon} [cyan]{detail}[/]")

    report = asyncio.run(run_research(
        query,
        model=model,
        provider=provider,
        max_parallel=parallel,
        max_depth=depth,
        max_tasks=max_tasks,
        progress=on_progress,
    ))

    console.print()

    # Summary
    if report.summary:
        console.print(Panel(report.summary, title=" Summary", border_style="green"))

    # Sections
    for section in report.sections[:5]:
        console.print(Panel(
            section["content"][:1000],
            title=f" {section.get('title', 'Section')}",
        ))

    # Meta
    console.print(f"[dim]Confidence: {report.confidence:.0%} | "
                  f"Sources: {len(report.sources)} | "
                  f"Duration: {report.duration_ms}ms[/]")


# Agent command — unified AI agent (pi replacement)
