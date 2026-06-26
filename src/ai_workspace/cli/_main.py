"""AI Workspace CLI — `aiw` command."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import typer
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from ai_workspace.providers import chat_sync
from ai_workspace.knowledge import KnowledgeStore
from ai_workspace.core.db import get_store

from ai_workspace.cli._app import app, console

# Extracted CLI modules (typer groups registered in each)
from ai_workspace.cli._memory import *  # noqa: F401, F403 — aiw memory
from ai_workspace.cli._source import *  # noqa: F401, F403 — aiw source
from ai_workspace.cli._session import *  # noqa: F401, F403 — aiw session
from ai_workspace.cli._tools import *  # noqa: F401, F403 — aiw tool
from ai_workspace.cli._schedule import *  # noqa: F401, F403 — aiw schedule
from ai_workspace.cli._skill import *  # noqa: F401, F403 — aiw skill
from ai_workspace.cli._obsidian import *  # noqa: F401, F403 — aiw obsidian
from ai_workspace.cli._cache import *  # noqa: F401, F403 — aiw cache
from ai_workspace.cli._wf import *  # noqa: F401, F403 — aiw wf
from ai_workspace.cli._research import *  # noqa: F401, F403 — aiw research
from ai_workspace.cli._projects import *  # noqa: F401, F403 — aiw project

# Search command

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
    from ai_workspace.search import DeepSearchEngine
    from ai_workspace.core.cost import CostService

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
            console.print(f"\n    [bold yellow]Human review requested[/]")
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

def _run_agent_direct(task: str, model: str, cwd: str = ".", provider: str = "ollama") -> None:
    """Fallback: run agent directly without orchestrator."""
    from ai_workspace.agents.swarm import SwarmConfig, create_agent
    from crewai import Task, Crew

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
    from ai_workspace.agents.swarm import SwarmConfig, create_agent
    from crewai import Task, Crew

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
        console.print(f"  [dim]1. List directory structure[/]")
        console.print(f"  [dim]2. Read relevant files[/]")
        console.print(f"  [dim]3. Plan implementation[/]")
        console.print(f"  [dim]4. Edit/write files[/]")
        console.print(f"  [dim]5. Run tests/linters[/]")
        console.print(f"  [dim]6. Git commit with conventional message[/]")
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

    console.print(Panel(f"[bold cyan]Improvement Cycle[/]", title=f" {days}d / {max_traces} traces"))

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
from ai_workspace.cli._session import *  # noqa: F401, F403



# Memory commands (extracted to cli._memory)
from ai_workspace.cli._memory import *  # noqa: F401, F403



@app.command()
def ask(
    message: str = typer.Argument(..., help="Question or prompt"),
    provider: str = typer.Option("ollama", "--provider", "-p", help="LLM provider"),
    model: str | None = typer.Option(None, "--model", "-m", help="Model name"),
    system: str | None = typer.Option(None, "--system", "-s", help="System prompt"),
    no_stream: bool = typer.Option(False, "--no-stream", help="Disable streaming output"),
):
    """Quick chat with any configured model."""
    from ai_workspace.providers import ProviderRegistry, chat_sync
    from ai_workspace.core.cost import CostService
    
    registry = ProviderRegistry()
    cost = CostService()
    cost.initialize()

    if model is None:
        model = registry.get_model(provider)

    console.print(f"[dim]Provider: {provider} | Model: {model}[/]")

    # Check semantic cache first
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": message})

    # Build cache key from the actual prompt
    cache_prompt = message
    if system:
        cache_prompt = f"[SYS]{system}[/SYS] {message}"

    cached = cost.cache.get(cache_prompt, "chat")
    if cached:
        console.print(f"[dim] Cache hit (similarity: {cached['similarity']:.0%})[/]")
        console.print()
        console.print(Panel(Markdown(cached["response_text"]), title=" Response (cached)"))
        cost.budget.record_success(
            provider=provider, model=model or "unknown",
            task_type="chat", cache_hit=True,
        )
        return

    # Budget check before calling LLM
    if provider in ("deepseek", "openrouter"):
        est_cost = 0.00014 * (len(message) // 4 + 500) / 1000  # ~0.0001 per short chat
        allowed, reason = cost.budget.can_call(est_cost, provider)
        if not allowed:
            console.print(f"[red] Budget blocked: {reason}[/]")
            console.print(f"[dim]Daily: ${cost.budget.today_spent():.4f}/${cost.budget.DAILY_BUDGET:.2f}[/]")
            raise typer.Exit(1)

    console.print()

    if no_stream or provider != "ollama":
        # Non-streaming path
        with console.status(f"[cyan]Thinking ({model})...", spinner="dots"):
            try:
                response = chat_sync(messages, provider=provider, model=model)
            except Exception as e:
                console.print(f"[red] Error: {e}[/]")
                cost.budget.record_failure(
                    provider=provider, model=model or "unknown",
                    task_type="chat", error=str(e)[:200],
                )
                raise typer.Exit(1)
        console.print(Panel(Markdown(response), title=" Response"))
        # Store in cache for future use
        cost.cache.set(cache_prompt, response, "chat", model or "unknown",
                       tokens_used=len(message)//4 + len(response)//4,
                       cost=0.0 if provider == "ollama" else 0.0001)
        # Log cost
        cost.budget.record_success(
            provider=provider, model=model or "unknown",
            task_type="chat",
            input_tokens=len(message)//4,
            output_tokens=len(response)//4,
            cost=0.0 if provider == "ollama" else 0.0001,
            cache_hit=False,
        )
    else:
        # Streaming path for Ollama (shows tokens as they arrive)
        token_buffer = []
        
        def print_token(token: str):
            token_buffer.append(token)
            # Print in real-time but try not to break mid-word
            console.print(token, end="")
        
        console.print("[bold cyan] Response[/]:")
        
        try:
            response = chat_sync(messages, provider=provider, model=model, stream=True, on_token=print_token)
        except Exception as e:
            console.print(f"\n[red] Error: {e}[/]")
            cost.budget.record_failure(
                provider=provider, model=model or "unknown",
                task_type="chat", error=str(e)[:200],
            )
            raise typer.Exit(1)
        
        console.print()  # Final newline after stream ends
        console.print(Panel("", title=" Response complete", border_style="dim"))
        # Store in cache
        cost.cache.set(cache_prompt, response, "chat", model or "unknown",
                       tokens_used=len(message)//4 + len(response)//4,
                       cost=0.0)  # Ollama = free
        # Log cost for streaming
        cost.budget.record_success(
            provider=provider, model=model or "unknown",
            task_type="chat",
            input_tokens=len(message)//4,
            output_tokens=len(response)//4,
            cost=0.0, cache_hit=False,
        )


# Models command

@app.command()
def models(
    provider: str = typer.Option("ollama", "--provider", "-p", help="Provider to list"),
):
    """List available models for a provider."""
    registry = ProviderRegistry()
    models_list = registry.list_models(provider)

    table = Table(title=f" Models - {provider}")
    table.add_column("Model", style="cyan")
    table.add_column("Size", style="dim")
    table.add_column("Family")
    table.add_column("Quantization", style="dim")

    for m in models_list:
        size_gb = m.get("size", 0) / 1e9 if m.get("size") else 0
        table.add_row(
            m["name"],
            f"{size_gb:.1f} GB" if size_gb else "?",
            m.get("family", m.get("parameter_size", "")),
            m.get("quantization", ""),
        )

    console.print(table)


# Tool commands (extracted to cli._tools)
from ai_workspace.cli._tools import *  # noqa: F401, F403



# Task commands (extracted to cli._tasks)
from ai_workspace.cli._tasks import *  # noqa: F401, F403
from ai_workspace.cli._kb import *  # noqa: F401, F403



# Worker command (Huey consumer)

@app.command()
def worker():
    """Start the task worker (Huey consumer) to process tasks and periodic schedules."""
    from ai_workspace.tasks import start_worker, init_telemetry

    console.print("[bold cyan]Starting AI Workspace task worker...[/]")
    console.print("[dim]Handles periodic tasks + enqueued jobs. Press Ctrl+C to stop.[/]")
    console.print()

    start_worker()


# Schedule commands (extracted to cli._schedule)
from ai_workspace.cli._schedule import *  # noqa: F401, F403



# Telemetry command

@app.command()
def telemetry():
    """Show telemetry snapshot and recent activity metrics."""
    try:
        from ai_workspace.knowledge import KnowledgeStore
        store = get_store()
        store.initialize()

        c = store.conn.cursor()

        c.execute("SELECT COUNT(*) FROM research_entries WHERE created_at > NOW() - INTERVAL '24 hours'")
        r24 = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM research_entries")
        r_total = c.fetchone()[0]

        c.execute("SELECT ROUND(AVG(confidence)::numeric, 2) FROM research_entries WHERE confidence > 0")
        avg_conf = c.fetchone()[0] or 0

        c.execute("SELECT COUNT(*), COUNT(*) FILTER (WHERE status='completed'), COUNT(*) FILTER (WHERE status='pending') FROM tasks")
        tasks_total, tasks_done, tasks_pending = c.fetchone()

        c.execute("SELECT COUNT(*) FROM agent_memory")
        mem_total = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM knowledge_entries")
        kb_total = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM agent_memory WHERE created_at > NOW() - INTERVAL '24 hours'")
        mem_24 = c.fetchone()[0]

        c.close()
        store.close()

        table = Table(title=" Telemetry Snapshot")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", justify="right")

        table.add_row("Research (24h / total)", f"{r24} / {r_total}")
        table.add_row("Avg research confidence", f"{avg_conf:.1%}")
        table.add_row("Tasks (done / pending / total)", f"{tasks_done} / {tasks_pending} / {tasks_total}")
        table.add_row("Agent memories (total)", str(mem_total))
        table.add_row("Agent memories (24h)", str(mem_24))
        table.add_row("Knowledge entries", str(kb_total))

        console.print(table)

    except Exception as e:
        console.print(f"[red] Could not fetch telemetry: {e}[/]")
        console.print("[dim]Run 'aiw init' first if DB is not initialized.[/]")


# Budget command

@app.command()
def budget():
    """Show budget status: daily/monthly spend, cache savings, circuit states."""
    from ai_workspace.core.cost import CostService

    cost = CostService()
    cost.initialize()

    # Cache stats
    cache = cost.cache.stats()

    # Budget summary
    summary = cost.budget.budget_summary()

    # Build display
    table = Table(title=" Budget Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    # Daily
    daily_icon = "" if summary["today_pct"] < 50 else ("" if summary["today_pct"] < 80 else "")
    table.add_row(
        f"{daily_icon} Today",
        f"${summary['today_spent']:.4f} / ${summary['today_budget']:.2f} ({summary['today_pct']}%)"
    )

    # Monthly
    month_icon = "" if summary["month_pct"] < 50 else ("" if summary["month_pct"] < 80 else "")
    table.add_row(
        f"{month_icon} This month",
        f"${summary['month_spent']:.4f} / ${summary['month_budget']:.2f} ({summary['month_pct']}%)"
    )

    # Cache
    table.add_row(" Cache entries", str(cache["total_entries"]))
    table.add_row(" Cache hits", str(cache["total_hits"]))
    table.add_row(" Tokens saved", f"{cache['tokens_saved']:,}")
    table.add_row(" Cost saved", f"${cache['cost_saved']:.4f}")

    # Circuit breakers
    table.add_section()
    table.add_row(" Circuits", "")
    for prov, state in summary["circuits"].items():
        icon = {"closed": "", "half_open": "", "open": ""}.get(state, "")
        table.add_row(f"  {icon} {prov}", state)

    console.print(table)

    # Per-call limit info
    console.print(
        f"[dim]Limits: ${cost.budget.PER_CALL_LIMIT:.2f}/call, "
        f"${cost.budget.DAILY_BUDGET:.2f}/day, "
        f"${cost.budget.MONTHLY_BUDGET:.2f}/month[/]"
    )


# Version & Health check commands

@app.command()
def version():
    """Show AI Workspace version and dependency info."""
    from ai_workspace import __version__
    from importlib.metadata import version as get_version

    console.print(f"[bold cyan]aiw[/] [dim]v{__version__}[/]")
    console.print()

    # Show key dependency versions
    import sys
    console.print(f"  [dim]Python:[/] {sys.version.split()[0]}")

    for pkg_name in ("crewai", "textual", "pgvector", "psycopg2", "pydantic"):
        try:
            v = get_version(pkg_name)
            console.print(f"  [dim]{pkg_name}:[/] {v}")
        except Exception:
            pass

    console.print()
    console.print("[dim]Run 'aiw health' for full system status.[/]")


@app.command()
def health():
    """Show real-time system health: providers, cache, budget, sources."""
    import asyncio as _asyncio
    
    console.print(Panel.fit(" AI Workspace Health Check", style="bold cyan"))
    console.print()
    
    #  Provider status 
    provider_table = Table(title=" Providers", show_header=True)
    provider_table.add_column("Provider", style="cyan")
    provider_table.add_column("Status")
    provider_table.add_column("Model")
    provider_table.add_column("Cost", justify="right")
    
    try:
        router = _asyncio.run(_check_router_health())
    except Exception as e:
        console.print(f"[red]Router check failed: {e}[/]")
        router = None
    
    if router:
        for model in router.list_available():
            icon = "" if model["available"] else ""
            cost_str = f"${model['cost_per_1k']:.6f}/1k" if model["cost_per_1k"] > 0 else "FREE"
            provider_table.add_row(
                f"{icon} {model['provider']}",
                "online" if model["available"] else "offline",
                model["name"],
                cost_str,
            )
    else:
        provider_table.add_row(" No router data", "—", "—", "—")
    
    console.print(provider_table)
    console.print()
    
    #  Cache status 
    cache_table = Table(title=" Semantic Cache")
    cache_table.add_column("Metric", style="cyan")
    cache_table.add_column("Value", justify="right")
    
    try:
        from ai_workspace.core.cost import CostService
        cost = CostService()
        cost.initialize()
        stats = cost.cache.stats()
        cache_table.add_row("Entries", str(stats.get("total_entries", 0)))
        cache_table.add_row("Total hits", str(stats.get("total_hits", 0)))
        cache_table.add_row("Tokens saved", f"{stats.get('tokens_saved', 0):,}")
        cache_table.add_row("Cost saved", f"${stats.get('cost_saved', 0.0):.4f}")
        cache_table.add_row("Avg similarity", f"{stats.get('avg_similarity', 0):.2f}")
    except Exception as e:
        cache_table.add_row("Error", str(e)[:50])
    
    console.print(cache_table)
    console.print()
    
    #  Budget status 
    budget_table = Table(title=" Budget")
    budget_table.add_column("Scope", style="cyan")
    budget_table.add_column("Spent", justify="right")
    budget_table.add_column("Limit", justify="right")
    budget_table.add_column("Status")
    
    try:
        from ai_workspace.core.cost import BudgetEnforcer
        budget = BudgetEnforcer()
        today = budget.today_spent()
        month = budget.month_spent()
        
        today_pct = (today / budget.DAILY_BUDGET * 100) if budget.DAILY_BUDGET else 0
        month_pct = (month / budget.MONTHLY_BUDGET * 100) if budget.MONTHLY_BUDGET else 0
        
        today_icon = "" if today_pct < 50 else ("" if today_pct < 80 else "")
        month_icon = "" if month_pct < 50 else ("" if month_pct < 80 else "")
        
        budget_table.add_row(
            f"{today_icon} Daily",
            f"${today:.4f}",
            f"${budget.DAILY_BUDGET:.2f}",
            f"{today_pct:.0f}%"
        )
        budget_table.add_row(
            f"{month_icon} Monthly",
            f"${month:.4f}",
            f"${budget.MONTHLY_BUDGET:.2f}",
            f"{month_pct:.0f}%"
        )
    except Exception as e:
        budget_table.add_row("Error", str(e)[:50], "—", "—")
    
    console.print(budget_table)
    console.print()
    
    #  Source reputation 
    source_table = Table(title=" Source Reputation")
    source_table.add_column("Metric", style="cyan")
    source_table.add_column("Value", justify="right")
    
    try:
        from ai_workspace.sources import SourceReputationService
        svc = SourceReputationService()
        s = svc.stats()
        source_table.add_row("Domains tracked", str(s.get("total_domains", 0)))
        source_table.add_row("CRED-1 coverage", str(s.get("cred1_domains", 0)))
        source_table.add_row("Sources used", str(s.get("total_sources", 0)))
        source_table.add_row("Avg score", f"{s.get('avg_score', 0):.2f}")
        source_table.add_row("Cross-ref samples", str(s.get("cross_ref_samples", 0)))
    except Exception as e:
        source_table.add_row("Error", str(e)[:50])
    
    console.print(source_table)
    
    console.print()
    console.print("[dim]Run 'aiw budget' for detailed budget, 'aiw source stats' for source details.[/]")


async def _check_router_health():
    """Check provider availability and return router with status."""
    from ai_workspace.agents.router import SmartRouter
    router = SmartRouter()
    await router.check_availability()
    return router


# Skill commands (extracted to cli._skill)
from ai_workspace.cli._skill import *  # noqa: F401, F403



# Obsidian commands (extracted to cli._obsidian)
from ai_workspace.cli._obsidian import *  # noqa: F401, F403



# Init command

@app.command()
def init(
    db_url: str | None = typer.Option(None, "--db", help="Database URL (default: postgresql:///ai_workspace)"),
):
    """Initialize the AI Workspace database and directories."""
    data_dir = Path.home() / ".ai-workspace"
    data_dir.mkdir(exist_ok=True)

    # Initialize PostgreSQL database
    store = get_store(db_url=db_url)
    try:
        store.initialize()
        console.print("[green] PostgreSQL database initialized[/]")

        # Also initialize cost tables (semantic cache + cost log)
        from ai_workspace.core.cost import CostService
        cost = CostService(db_url=db_url or None)
        cost.initialize()
        console.print("[green] Semantic cache tables initialized[/]")

        # Initialize source reputation tables
        from ai_workspace.core.sources import SourceReputationService
        src = SourceReputationService(db_url=db_url or None)
        src.initialize()
        console.print("[green] Source reputation tables initialized[/]")

        # Initialize project tables
        from ai_workspace.core.projects import ProjectManager
        pm = ProjectManager(db_url=db_url or None)
        pm.initialize()
        console.print("[green] Project tables initialized[/]")
    except Exception as e:
        console.print(f"[red] Database error: {e}[/]")
        console.print("[dim]Make sure PostgreSQL is running and the database exists:[/]")
        console.print("  createdb ai_workspace")
        console.print("  aiw init")
        return
    finally:
        store.close()

    # Create data directories
    (data_dir / "research").mkdir(exist_ok=True)
    (data_dir / "tasks").mkdir(exist_ok=True)
    (data_dir / "exports").mkdir(exist_ok=True)

    console.print("[green] Directories created[/]")
    console.print(f"[dim]Data directory: {data_dir}[/]")
    console.print()

    console.print("[bold]Next steps:[/]")
    console.print("  [cyan]aiw models[/]                     # List available models")
    console.print("  [cyan]aiw search 'rust async vs go'[/]  # Run deep research")
    console.print("  [cyan]aiw ask 'explain nix flakes'[/]   # Quick chat")
    console.print("  [cyan]aiw task add 'daily review' --schedule '0 9 * * *'[/]  # Recurring task")
    console.print("  [cyan]aiw worker[/]                     # Start task worker for schedules")
    console.print("  [cyan]aiw telemetry[/]                  # View metrics")
    console.print()
    console.print("[dim bold]Tip: Run 'aiw worker' in a tmux/screen session to keep schedules alive.[/]")


# Cache commands (extracted to cli._cache)
from ai_workspace.cli._cache import *  # noqa: F401, F403



# Main entry point


# Workflow commands (extracted to cli._wf)
from ai_workspace.cli._wf import *  # noqa: F401, F403



# Sync command (multi-PC)

@app.command()
def sync(
    direction: str = typer.Argument("status", help="push, pull, both, vault, status"),
):
    """Multi-PC knowledge base sync (thinkbook ↔ homelab via Tailscale)."""
    from ai_workspace.knowledge import SyncManager

    manager = SyncManager()

    if direction == "status":
        primary_ok = manager.is_primary_available()
        console.print(f"Primary DB (homelab): {'[green] connected[/]' if primary_ok else '[red] unreachable[/]'}")
        manager._load_queue()
        console.print(f"Offline queue: {len(manager._offline_queue)} pending operations")
        vault_ok = manager.vault_path.exists()
        console.print(f"Obsidian vault: {'[green] exists[/]' if vault_ok else '[dim]not cloned[/]'} ({manager.vault_path})")
        return

    if direction == "vault":
        with console.status("[cyan]Syncing vault (git)...[/]", spinner="dots"):
            result = asyncio.run(manager.sync_vault())
        if result.get("cloned"):
            console.print("[green] Vault cloned from GitHub[/]")
        else:
            console.print(f"Committed: {result.get('committed', 0)} | Pulled: {result.get('pulled', False)} | Pushed: {result.get('pushed', False)}")
        if result.get("error"):
            console.print(f"[yellow] {result['error']}[/]")
        return

    if direction not in ("push", "pull", "both"):
        console.print(f"[red]Invalid: {direction}. Use: push, pull, both, vault, status[/]")
        raise typer.Exit(1)

    if not manager.is_primary_available():
        console.print("[red] Homelab PostgreSQL not reachable[/]")
        console.print("[dim]Make sure Tailscale is connected and homelab is running.[/]")
        raise typer.Exit(1)

    with console.status(f"[cyan]Syncing knowledge ({direction})...[/]", spinner="dots"):
        result = asyncio.run(manager.sync_knowledge(direction))

    console.print(f"[green] Sync complete[/]")
    console.print(f"  Pushed: {result.get('pushed', 0)} entries")
    console.print(f"  Pulled: {result.get('pulled', 0)} entries")
    console.print(f"  Offline queue flushed: {result.get('offline_queue_flushed', 0)} ops")


# Research view commands (extracted to cli._research)
from ai_workspace.cli._research import *  # noqa: F401, F403



# Workflow tail command — follow progress in real-time

@wf_app.command(name="tail")
def wf_tail(
    run_id: int = typer.Argument(..., help="Run ID to follow"),
    interval: float = typer.Option(2.0, "--interval", "-i", help="Polling interval in seconds"),
    timeout: float = typer.Option(300.0, "--timeout", "-t", help="Max time to wait"),
):
    """Follow a workflow run's progress in real-time (polls DB).

    Shows step output as it completes. Like 'tail -f' for workflows.
    Press Ctrl+C to stop.
    """
    import time
    from ai_workspace.knowledge import KnowledgeStore

    store = get_store(db_url=_get_db_url())
    store.initialize()

    # Get workflow name
    c = store.conn.cursor()
    c.execute("SELECT workflow_name, status FROM workflow_runs WHERE run_id = %s", (run_id,))
    row = c.fetchone()
    c.close()

    if not row:
        store.close()
        console.print(f"[red]Run #{run_id} not found[/]")
        return

    wf_name, status = row
    console.print(f"[bold cyan]Following workflow #{run_id} ({wf_name})...[/]")
    console.print(f"[dim]Status: {status} | Polling every {interval}s | Press Ctrl+C to stop[/]\n")

    seen_ids = set()
    start = time.time()

    try:
        while time.time() - start < timeout:
            c = store.conn.cursor()
            c.execute(
                """SELECT id, step_name, status, attempt, duration_ms, left(output::text, 500) as output,
                          left(error::text, 200) as error, created_at
                   FROM workflow_step_logs
                   WHERE run_id = %s
                   ORDER BY id""",
                (run_id,),
            )
            logs = c.fetchall()
            c.close()

            for log in logs:
                log_id = log[0]
                if log_id in seen_ids:
                    continue
                seen_ids.add(log_id)

                step_name, status, attempt, dur, output, error, ts = log[1:8]

                if status == "running":
                    console.print(f"  [yellow]⟳[/] {step_name} (attempt {attempt + 1})...")
                elif status == "done":
                    icon = ""
                    dur_str = f" {dur:.0f}ms" if dur else ""
                    console.print(f"  {icon} [green]{step_name}[/]{dur_str}")
                    if output and len(output) > 10:
                        # Show a preview of the output
                        preview = output[:300].replace("\\n", "\n    ")
                        console.print(f"    [dim]{preview}...[/]")
                elif status == "failed":
                    console.print(f"   [red]{step_name}[/] failed: {error}")

            # Check if run finished
            c = store.conn.cursor()
            c.execute(
                "SELECT status, duration_ms, error FROM workflow_runs WHERE run_id = %s",
                (run_id,),
            )
            run_row = c.fetchone()
            c.close()

            if run_row and run_row[0] in ("done", "failed"):
                final_status = run_row[0]
                final_dur = run_row[1] or 0
                final_error = run_row[2]

                console.print()
                if final_status == "done":
                    console.print(Panel(
                        f"[green] Workflow completed in {final_dur:.0f}ms[/]",
                        border_style="green",
                    ))
                else:
                    console.print(Panel(
                        f"[red] Workflow failed: {final_error}[/]",
                        border_style="red",
                    ))
                    console.print(f"  [dim]Retry: aiw wf retry {run_id}[/]")

                console.print(f"[dim]View report: aiw research view <id>[/]")
                break

            time.sleep(interval)

    except KeyboardInterrupt:
        console.print("\n[dim]Stopped[/]")
    finally:
        store.close()


@app.command(name="config")
def config_cmd(
    action: str = typer.Argument("show", help="Action: init, show"),
):
    """Manage AI Workspace configuration (BYOK).

    aiw config init  - Create config file at ~/.config/aiw/config.toml
    aiw config show  - Show current configuration
    """
    from ai_workspace.user_config import AiwConfig, CONFIG_FILE

    if action == "init":
        cfg = AiwConfig()
        cfg.init_config_dir()
        console.print(f"[green]Config created at {CONFIG_FILE}[/]")
        console.print("[dim]Edit this file to add your API keys for DeepSeek, Gemini, etc.[/]")
    elif action == "show":
        cfg = AiwConfig.load()
        console.print(f"Config file: {CONFIG_FILE}")
        console.print(f"Exists: {CONFIG_FILE.exists()}")
        console.print(f"Providers with keys: {list(cfg.providers.keys())}")
        console.print(f"Ollama host: {cfg.ollama_host}")
        # Show masked keys
        for name, pk in cfg.providers.items():
            if pk.api_key:
                masked = pk.api_key[:8] + "..." if len(pk.api_key) > 8 else "***"
                console.print(f"  {name}: {masked}")
            else:
                env_var = {"deepseek": "DEEPSEEK_API_KEY", "gemini": "GEMINI_API_KEY"}.get(name, "")
                env_status = "[dim](from env)[/]" if (env_var and os.getenv(env_var)) else "[yellow](not set)[/]"
                console.print(f"  {name}: {env_status}")
    else:
        console.print(f"[red]Unknown action: {action}. Use 'init' or 'show'.[/]")
        raise typer.Exit(1)


@app.command()
def tui(
    dev: bool = typer.Option(False, "--dev", "-d", help="Enable hot-reload for TUI development (nix-shell only)"),
):
    """Launch the rich terminal dashboard (Textual TUI).

    With --dev: hot-reload on file changes. Only works inside nix-shell (dev environment).
    """
    if dev:
        from pathlib import Path

        app_path = Path(__file__).resolve().parent / "tui" / "v5" / "app.py"

        # Check if we're in a writable source tree (not Nix store)
        if "/nix/store/" in str(app_path):
            console.print("[red] --dev requires running from source tree (nix-shell), not Nix build.[/]")
            console.print("[dim]Run: nix-shell[/]")
            console.print("[dim]Then: source .venv/bin/activate.fish && pip install -e .[/]")
            console.print("[dim]Then: aiw tui --dev[/]")
            raise typer.Exit(1)

        import os
        os.environ["TEXTUAL_DEVTOOLS"] = "1"

        console.print("[bold cyan]AI Workspace TUI — DEV MODE[/]")
        console.print(f"[dim]Source: {app_path}[/]")
        console.print("[dim]Devtools: press Ctrl+P for command palette, F2 for DOM inspector[/]")
        console.print()

    # Launch TUI (both dev and normal modes)
    from ai_workspace.tui import run_tui
    run_tui()


@app.command()
def web():
    """Launch the PWA web app (http://localhost:8000)."""
    import subprocess
    import sys
    from pathlib import Path

    api_dir = Path(__file__).parent.parent.parent.parent / "api"
    if not (api_dir / "main.py").exists():
        console.print("[red]API module not found at api/main.py[/]")
        raise typer.Exit(1)

    console.print("[bold cyan]Starting AI Workspace PWA Web App...[/]")
    console.print("[dim]Open http://localhost:8000 in your browser (Safari recommended for iOS)[/]")
    console.print("[dim]Press Ctrl+C to stop[/]")

    try:
        subprocess.run(
            [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"],
            cwd=api_dir.parent,
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/]")


@app.command()
def dashboard():
    """Launch the Streamlit web dashboard (http://localhost:8501)."""
    from ai_workspace.dashboard import run_dashboard
    console.print("[bold cyan]Starting AI Workspace Dashboard...[/]")
    console.print("[dim]Open http://localhost:8501 in your browser[/]")
    console.print("[dim]Press Ctrl+C to stop[/]")
    run_dashboard()

# Project commands (extracted to cli._projects)
from ai_workspace.cli._projects import *  # noqa: F401, F403



# Source Reputation commands (extracted to cli._source)
from ai_workspace.cli._source import *  # noqa: F401, F403


# Rules commands (extracted to cli._rules)
from ai_workspace.cli._rules import *  # noqa: F401, F403



# ── Trace commands (observability) ─────────────────────────

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

    table = Table(title=" Agent Traces")
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
        console.print(f"\n[bold]Timeline ({len(trace.steps)} steps):[/]")
        for i, step in enumerate(trace.steps):
            icon = {
                "token": "", "tool_call": "", "tool_result": "",
                "error": "", "phase": "", "done": "",
            }.get(step.get("type", ""), "")
            detail = str(step.get("data", ""))[:100]
            console.print(f"  {i:3d} {icon} [{step.get('type', '?')}]{' ' + detail if detail else ''}")

    # Diffs
    if diff and trace.diff_tracker_data:
        tracker = DiffTracker.from_dict(trace.diff_tracker_data)
        summary = tracker.get_summary()
        console.print(f"\n[bold]File Changes: {summary['files_modified']} files[/]")
        for path, count in summary["changes"].items():
            console.print(f"  {path}: {count} changes")


# Eval commands (extracted to cli._eval)
from ai_workspace.cli._eval import *  # noqa: F401, F403



# Chat command (v2 — primary daily-driver interface)


@app.command()
def chat(
    workspace: str = typer.Option("personal", "--workspace", "-w", help="Workspace context (personal, work, etc.)"),
    agent: str = typer.Option("default", "--persona", "-p", help="Persona: default, coder, researcher, planner"),
    provider: str = typer.Option("ollama", "--provider", help="LLM provider: ollama, deepseek, nvidia, openrouter"),
    model: str | None = typer.Option(None, "--model", "-m", help="Model name (uses provider default if not set)"),
    no_recall: bool = typer.Option(False, "--no-recall", help="Disable auto-recall of past context"),
):
    """Start an interactive chat session with persistent memory.

    The chat REPL maintains conversation history, auto-recalls relevant
    past context from the knowledge base, and stores key turns as agent
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


# MCP commands (extracted to cli._mcp)
from ai_workspace.cli._mcp import *  # noqa: F401, F403



# Partners commands (extracted to cli._partner)
from ai_workspace.cli._partner import *  # noqa: F401, F403



# Context FS commands (extracted to cli._context_fs)
from ai_workspace.cli._context_fs import *  # noqa: F401, F403

