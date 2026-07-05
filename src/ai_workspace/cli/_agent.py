"""CLI commands — `aiw agent`."""

from __future__ import annotations

import typer
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from ai_workspace.cli._app import app, console


def _run_agent_direct(task: str, model: str, cwd: str = ".", provider: str = "ollama") -> None:
    """Fallback: run agent directly without orchestrator."""
    from crewai import Crew, Task

    from ai_workspace.agents.swarm import SwarmConfig, create_agent

    if provider and provider != "ollama":
        full_model = f"{provider}/{model}"
    else:
        full_model = model

    cfg = SwarmConfig(coder_model=full_model, default_model=full_model, provider=provider)
    agent_instance = create_agent(cfg=cfg, model=full_model)
    t = Task(
        description=f"Working directory: {cwd}\n\n{task}",
        expected_output="The result of the requested task.",
        agent=agent_instance,
    )
    crew = Crew(agents=[agent_instance], tasks=[t], verbose=True)
    result = crew.kickoff()
    console.print()
    console.print(Panel(str(result), title=" Result"))


@app.command()
def agent(
    task: str = typer.Argument(None, help="What do you want me to do? (omit for interactive mode)"),
    model: str = typer.Option("qwen3:14b", "--model", "-m", help="Model for the agent"),
    provider: str = typer.Option("ollama", "--provider", "-p", help="LLM provider: ollama, deepseek, gemini"),
    dir: str = typer.Option(".", "--dir", "-d", help="Working directory"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without executing"),
):
    """Unified AI agent — research, code, browse, manage files.

    This is the main entry point. The agent auto-detects what you need
    and uses the right tools. Replaces pi for daily use.

    Examples:
      aiw agent "What is FastAPI?"              → research
      aiw agent "Add type hints to core/cost.py" → coding
      aiw agent "Scrape https://example.com"     → web scraping
      aiw agent "What's in this directory?"      → filesystem
      aiw agent "Show me recent git commits"     → git
      aiw agent                                  → interactive mode
    """
    from crewai import Crew, Task

    from ai_workspace.agents.swarm import SwarmConfig, create_agent

    if task is None:
        # Interactive mode
        console.print("[bold cyan]AI Workspace Agent[/] — type your request (Ctrl+C to exit)")
        console.print(f"[dim]Provider: {provider} | Model: {model} | Dir: {dir}[/]")
        console.print()

        cfg = SwarmConfig(
            coder_model=f"{provider}/{model}" if provider != "ollama" else model,
            default_model=f"{provider}/{model}" if provider != "ollama" else model,
            provider=provider,
        )
        agent_instance = create_agent(cfg=cfg, model=model)

        while True:
            try:
                task = Prompt.ask("[bold][/]")
                if not task.strip():
                    continue
                if task.lower() in ("exit", "quit", "q"):
                    break

                console.print()
                if dry_run:
                    console.print(f"[yellow] Would execute: {task[:100]}[/]")
                    continue

                t = Task(
                    description=task,
                    expected_output="The result of the requested task.",
                    agent=agent_instance,
                )
                crew = Crew(agents=[agent_instance], tasks=[t], verbose=False)
                result = crew.kickoff()
                console.print()
                console.print(Panel(str(result), title=" Result"))
                console.print()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]Goodbye![/]")
                break
        return

    # One-shot mode — uses AgentOrchestrator for unified pipeline
    # (context injection, smart routing, streaming, fallback)
    console.print(Panel(f"[bold cyan]Agent[/]\n{task}", title=" AI Workspace"))
    console.print(f"[dim]Provider: {provider} | Model: {model} | Dir: {dir}[/]")

    if dry_run:
        console.print("[yellow] DRY RUN — no actions will be taken[/]")
        return

    try:
        from ai_workspace.agents.orchestrator import (
            AgentOrchestrator,
            CLIStreamSink,
            OrchestratorConfig,
        )

        sink = CLIStreamSink(verbose=True)
        config = OrchestratorConfig(
            cwd=dir,
            model=model,
            provider=provider,
            agent_type="general",
            use_streaming=True,
            use_router=True,
        )
        orch = AgentOrchestrator(sink=sink, config=config)
        result = asyncio.run(orch.run(task))
        console.print()
        console.print(Panel(str(result), title=" Result"))
    except ImportError as e:
        console.print(f"[yellow] Orchestrator unavailable ({e}), using direct agent[/]")
        _run_agent_direct(task, model, dir, provider)
    except Exception as e:
        console.print(f"[red] Error: {e}[/]")
        raise typer.Exit(1)


# Code command (autonomous coding agent)

@app.command()
def code(
    task: str = typer.Argument(..., help="Coding task description"),
    model: str = typer.Option("qwen3:14b", "--model", "-m", help="Model for coding (qwen3:14b fits 12GB VRAM)"),
    provider: str = typer.Option("ollama", "--provider", "-p", help="LLM provider: ollama, deepseek"),
    dir: str = typer.Option(".", "--dir", "-d", help="Working directory"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without executing"),
):
    """Run an autonomous coding agent with filesystem/git/shell access."""
    from ai_workspace.agents.swarm import SwarmConfig, coding_crew

    console.print(Panel(f"[bold cyan]Coding Agent[/]\n{task}", title=" Code"))
    console.print(f"[dim]Provider: {provider} | Model: {model} | Dir: {dir}[/]")

    if dry_run:
        console.print("[yellow] DRY RUN — would explore {dir} and implement:[/]")
        console.print("  [dim]1. List directory structure[/]")
        console.print("  [dim]2. Read relevant files[/]")
        console.print("  [dim]3. Plan implementation[/]")
        console.print("  [dim]4. Edit/write files[/]")
        console.print("  [dim]5. Run tests/linters[/]")
        console.print("  [dim]6. Git commit with conventional message[/]")
        console.print()
        console.print("[green]Dry run complete. Run without --dry-run to execute.[/]")
        return

    full_model = f"{provider}/{model}" if provider != "ollama" else model
    cfg = SwarmConfig(coder_model=full_model, provider=provider)
    crew = coding_crew(task_description=task, cfg=cfg, working_dir=dir)

    console.print("[dim]Agent is exploring the codebase and implementing changes...[/]")
    console.print()

    try:
        result = crew.kickoff()
        console.print()
        console.print(Panel(str(result), title=" Coding Complete"))
    except Exception as e:
        console.print(f"[red] Error: {e}[/]")
        raise typer.Exit(1)


# Improve command — self-improvement cycle (HALO-inspired)

@app.command()
def improve(
    days: int = typer.Option(7, "--days", "-d", help="Days of traces to analyze"),
    max_traces: int = typer.Option(100, "--max-traces", "-n", help="Max traces to include"),
    llm: bool = typer.Option(False, "--llm", "-l", help="Use LLM for deeper analysis"),
    prompt: str = typer.Option(
        "Diagnose errors and suggest improvements for this agent harness.",
        "--prompt", "-p",
        help="Custom analysis prompt (used with --llm)",
    ),
    report: bool = typer.Option(False, "--report", "-r", help="Print full report"),
):
    """Run the agent self-improvement cycle.

    Collects recent agent execution traces, analyzes them for failure
    patterns and optimization opportunities, and writes findings to
    workspace memory files.

    Inspired by HALO's collect → analyze → improve → redeploy pattern.
    """
    import asyncio

    from ai_workspace.agents.improvement import ImprovementCycle, print_report

    console.print(Panel("[bold cyan]Improvement Cycle[/]", title=f" {days}d / {max_traces} traces"))

    cycle = ImprovementCycle()

    if llm:
        console.print("[dim]Using LLM analysis (deep mode)...[/]")
        report_obj = asyncio.run(cycle.run(
            days=days,
            max_traces=max_traces,
            use_llm=True,
            llm_prompt=prompt,
        ))
    else:
        console.print("[dim]Using heuristic analysis (fast mode)...[/]")
        report_obj = cycle.run_sync(days=days, max_traces=max_traces)

    console.print()
    print_report(report_obj)

    modified = len(report_obj.patterns) + len(report_obj.recommendations)
    if modified:
        console.print(f"\n[green] {modified} findings written to workspace memory[/]")
        console.print("[dim]  See: memory/learning-log.md, memory/conventions.md, memory/project-patterns.md[/]")
    else:
        console.print("\n[yellow]No findings to write. Run more agent tasks first.[/]")


# Integrations command — catalog and verification

@app.command()
def integrations(
    verify: bool = typer.Option(False, "--verify", "-v", help="Verify connectivity of all integrations"),
    name: str = typer.Option(None, "--name", "-n", help="Specific integration to verify"),
):
    """List and verify all integrations (providers, tools, MCP, databases).

    Scans the environment for all available integrations and shows their
    status. Use --verify to check connectivity.
    """
    from ai_workspace.tools.integration_catalog import create_catalog

    catalog = create_catalog()

    if verify:
        if name:
            console.print(f"[cyan]Verifying integration: {name}[/]")
            console.print(catalog.verify(name))
        else:
            console.print("[cyan]Verifying all integrations...[/]")
            results = catalog.verify_all()
            table = Table(title=" Integration Status")
            table.add_column("Integration", style="cyan")
            table.add_column("Status")
            for integration_name, status in results.items():
                table.add_row(integration_name, status)
            if not results:
                console.print("[yellow]No configured integrations to verify.[/]")
            else:
                console.print(table)
        return

    # Default: list catalog
    summary = catalog.summary()
    console.print(Panel(
        f"[bold]Integration Catalog[/]  —  "
        f"{summary['total']} total  |  "
        f"{summary['categories']} categories",
    ))

    for cat_name, integrations in catalog.by_category().items():
        table = Table(title=cat_name, show_header=True)
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="dim")
        table.add_column("Status")
        table.add_column("Description")

        for integration in integrations:
            status_style = {
                "available": "[green]Available[/]",
                "configured": "[green]Configured[/]",
                "unconfigured": "[yellow]No key[/]",
                "error": "[red]Error[/]",
            }.get(integration.status, f"[dim]{integration.status}[/]")
            table.add_row(
                integration.name,
                integration.type,
                status_style,
                integration.description[:80],
            )
        console.print(table)

    console.print()
    console.print("[dim]Use --verify to check connectivity.[/]")


# Finance command — specialized financial analysis

@app.command()
def finance(
    task: str = typer.Argument(..., help="Financial analysis task"),
    model: str = typer.Option("llama-open-finance:8b", "--model", "-m",
                              help="Finance model (llama-open-finance:8b fits 12GB VRAM)"),
    provider: str = typer.Option("ollama", "--provider", "-p",
                                 help="LLM provider: ollama, deepseek"),
    dir: str = typer.Option(".", "--dir", "-d", help="Working directory"),
    dry_run: bool = typer.Option(False, "--dry-run",
                                 help="Show what would be done without executing"),
):
    """Run a finance-specialized agent for financial analysis.

    Uses llama-open-finance:8b for:
    - Company financial report analysis (DRE, balance sheet, cash flow)
    - Market news classification and sentiment
    - Regulatory compliance Q&A
    - Financial data extraction from documents
    - Investment thesis analysis

    Examples:
      aiw finance "Summarize this quarterly earnings report"
      aiw finance "Classify these market news by sentiment"
      aiw finance "What are the key risk factors in this balance sheet?"
      aiw finance --dir ./reports "Extract financial metrics from these PDFs"
    """
    from ai_workspace.agents.orchestrator import (
        AgentOrchestrator,
        CLIStreamSink,
        OrchestratorConfig,
    )

    console.print(Panel(
        f"[bold cyan]Finance Agent[/]\n{task}", title=" Finance"
    ))
    console.print(
        f"[dim]Provider: {provider} | Model: {model} | Dir: {dir}[/]"
    )

    if dry_run:
        console.print(
            "[yellow] DRY RUN — finance analysis without execution[/]"
        )
        console.print(f"  [dim]Task: {task[:120]}...[/]")
        console.print()
        console.print(
            "[green]Run without --dry-run to execute.[/]"
        )
        return

    try:
        sink = CLIStreamSink(verbose=True)
        config = OrchestratorConfig(
            cwd=dir,
            model=model,
            provider=provider,
            agent_type="finance",
            use_streaming=True,
            use_router=True,
        )
        orch = AgentOrchestrator(sink=sink, config=config)
        result = asyncio.run(orch.run(task))
        console.print()
        console.print(Panel(str(result), title=" Finance Analysis Complete"))
    except Exception as e:
        console.print(f"[red] Error: {e}[/]")
        raise typer.Exit(1)


# Session commands (extracted to cli._session)
