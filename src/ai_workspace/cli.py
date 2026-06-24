"""AI Workspace CLI — `aiw` command."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from ai_workspace.providers import ProviderRegistry, chat_sync
from ai_workspace.knowledge import KnowledgeStore
from ai_workspace.core.db import get_store

app = typer.Typer(
    name="aiw",
    help="AI Workspace - Deep search, agent swarm, knowledge base",
    no_args_is_help=True,
)
console = Console()

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


# Memory commands — persistent memory inspection

memory_app = typer.Typer(help="Inspect persistent memory (L1/L2/L3)")
app.add_typer(memory_app, name="memory")


@memory_app.command("stats")
def memory_stats_cmd():
    """Show persistent memory statistics and summary."""
    from ai_workspace.agents.memory import PersistentMemory

    mem = PersistentMemory()
    stats = mem.stats()

    console.print(Panel(
        f"[bold]Persistent Memory[/]  —  {stats.memory_dir}\n"
        f"L1: {stats.l1_files} files, {stats.l1_events} events  |  "
        f"L2: {stats.l2_facts} facts across {len(mem.list_l2_surfaces())} surfaces  |  "
        f"L3: {stats.l3_files} files  |  "
        f"Sessions: {stats.total_sessions}  |  "
        f"Storage: {mem._format_bytes(stats.storage_bytes)}",
    ))

    # L2 surfaces
    surfaces = mem.list_l2_surfaces()
    if surfaces:
        table = Table(title="L2 Surfaces")
        table.add_column("Surface", style="cyan")
        table.add_column("Facts")
        table.add_column("File")
        for surface in surfaces:
            facts = mem.read_l2_facts(surface)
            table.add_row(surface, str(len(facts)), f"l2/{surface}.md")
        console.print(table)

    # L3 files
    l3_files = mem.list_l3_files()
    if l3_files:
        l3_table = Table(title="L3 Synthesis Files")
        l3_table.add_column("Name", style="cyan")
        l3_table.add_column("Size")
        for path in l3_files:
            size = len(path.read_text()) if path.exists() else 0
            l3_table.add_row(path.stem, f"{size} bytes")
        console.print(l3_table)

    if not surfaces and not l3_files:
        console.print("\n[yellow]No memory data yet. Run sessions to build memory.[/]")
        console.print("  Try: aiw improve")


@memory_app.command("show")
def memory_show_cmd(
    surface: str = typer.Argument(None, help="Surface name (coding, research, operations, decisions)"),
    l3: str = typer.Option(None, "--l3", "-3", help="L3 file name (profile, recent, scope)"),
):
    """Show memory contents for a surface or L3 synthesis."""
    from ai_workspace.agents.memory import PersistentMemory

    mem = PersistentMemory()

    if l3:
        content = mem.read_l3(l3)
        if content:
            console.print(Markdown(content))
        else:
            console.print(f"[yellow]No L3 file found: {l3}[/]")
        return

    if surface:
        facts = mem.read_l2_facts(surface)
        if facts:
            console.print(f"[bold]L2 Facts — {surface}[/]\n")
            for fact in facts:
                console.print(f"[cyan]## {fact['title']}[/]")
                console.print(fact["body"][:500])
                if fact.get("tags"):
                    console.print(f"[dim]Tags: {', '.join(fact['tags'])}[/]")
                if fact.get("source"):
                    console.print(f"[dim]{fact['source']}[/]")
                console.print()
        else:
            console.print(f"[yellow]No facts for surface: {surface}[/]")
        return

    # Default: show everything
    console.print(mem.summary())


@memory_app.command("l1")
def memory_l1_cmd(
    session_id: str = typer.Option(None, "--session", "-s", help="Filter by session ID"),
    limit: int = typer.Option(20, "--limit", "-l", help="Max events"),
    days: int = typer.Option(1, "--days", "-d", help="Days back"),
):
    """Show recent L1 trace events."""
    from datetime import timedelta
    from ai_workspace.agents.memory import PersistentMemory

    mem = PersistentMemory()

    since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    events = mem.read_l1_events(
        session_id=session_id,
        since=since_date,
        limit=limit,
    )

    if not events:
        console.print(f"[yellow]No L1 events found (since {since_date})[/]")
        return

    table = Table(title=f"L1 Events (last {days}d)")
    table.add_column("Time", style="dim")
    table.add_column("Type")
    table.add_column("Tool")
    table.add_column("Content")

    for event in events:
        ts = event.get("timestamp", "")[11:19] if len(event.get("timestamp", "")) > 19 else event.get("timestamp", "")
        content = event.get("content", "")[:80]
        table.add_row(
            ts,
            event.get("type", ""),
            event.get("tool", ""),
            content,
        )

    console.print(table)
    console.print(f"[dim]Showing {len(events)} events[/]")


@memory_app.command("consolidate")
def memory_consolidate_cmd():
    """Run L3 consolidation from current L2 facts."""
    from ai_workspace.agents.memory import PersistentMemory

    mem = PersistentMemory()
    console.print("[cyan]Running L3 consolidation...[/]")
    result = mem.consolidate_l3()
    for name, content in result.items():
        lines = content.strip().split("\n")
        first_line = lines[0] if lines else "(empty)"
        console.print(f"  [green]✓[/] L3/{name}.md — {first_line}")
    console.print("[green]Consolidation complete.[/]")


# Ask command (quick chat)

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


# Tool commands (web fetch, browser, marketplace search)

tool_app = typer.Typer(help="Web research tools (fetch, browser, marketplace)")
app.add_typer(tool_app, name="tool")


@tool_app.command()
def fetch(
    url: str = typer.Argument(..., help="URL to fetch and extract text from"),
    max_length: int = typer.Option(5000, "--max-length", "-l", help="Max chars to return"),
):
    """Fetch a URL and extract readable text."""
    from ai_workspace.tools import WebFetchTool
    tool = WebFetchTool()
    result = tool._run(url=url, max_length=max_length)
    console.print(Panel(str(result), title=f" {url[:60]}", border_style="blue"))


@tool_app.command()
def browser(
    url: str = typer.Argument(..., help="URL to open in headless browser (for SPA/JS pages)"),
    max_length: int = typer.Option(8000, "--max-length", "-l", help="Max chars to return"),
    wait_selector: str = typer.Option("", "--wait", "-w", help="CSS selector to wait for"),
    wait_time: int = typer.Option(3, "--wait-time", "-t", help="Extra seconds to wait after page loads"),
):
    """Render a JavaScript SPA page in a headless browser."""
    console.print(f"[dim]Opening browser...[/]")
    from ai_workspace.tools import HeadlessBrowserTool
    tool = HeadlessBrowserTool()
    result = tool._run(url=url, max_length=max_length, wait_selector=wait_selector, wait_time=wait_time)
    console.print(Panel(str(result)[:max_length], title=f" {url[:60]}", border_style="blue"))


@tool_app.command(name="scrape")
def scrape(
    url: str = typer.Argument(..., help="URL of the first page to scrape"),
    max_pages: int = typer.Option(20, "--max-pages", "-p", help="Maximum pages to scrape"),
    next_button: str = typer.Option("Próximo", "--next", "-n", help="Text on the next-page button"),
):
    """Scrape a multi-page SPA by clicking 'next page'."""
    console.print(f"[dim]Scraping up to {max_pages} pages...[/]")
    from ai_workspace.tools import PaginatedScraperTool
    tool = PaginatedScraperTool()
    result = tool._run(url=url, max_pages=max_pages, next_button_text=next_button)
    console.print(Panel(str(result)[:10000], title=f" {url[:60]}", border_style="blue"))


@tool_app.command(name="ml")
def mercado_livre(
    query: str = typer.Argument(..., help="Search query for Mercado Livre"),
    max_results: int = typer.Option(10, "--max-results", "-n", help="Max results"),
    max_price: float | None = typer.Option(None, "--max-price", help="Max price filter (BRL)"),
):
    """Search Mercado Livre for product prices."""
    from ai_workspace.tools import MercadoLivreSearchTool
    tool = MercadoLivreSearchTool()
    result = tool._run(query=query, max_results=max_results, max_price=max_price)
    console.print(Panel(str(result), title=f" Mercado Livre: {query}", border_style="green"))


@tool_app.command(name="olx")
def olx(
    query: str = typer.Argument(..., help="Search query for OLX"),
    max_results: int = typer.Option(10, "--max-results", "-n", help="Max results"),
    max_price: float | None = typer.Option(None, "--max-price", help="Max price filter (BRL)"),
):
    """Search OLX for product prices."""
    from ai_workspace.tools import OLXSearchTool
    tool = OLXSearchTool()
    result = tool._run(query=query, max_results=max_results, max_price=max_price)
    console.print(Panel(str(result), title=f" OLX: {query}", border_style="yellow"))


# Task commands

task_app = typer.Typer(help="Manage tasks")
app.add_typer(task_app, name="task")


@task_app.command(name="list")
def task_list(
    status: str | None = typer.Option(None, "--status", "-s", help="Filter by status"),
    tags: list[str] | None = typer.Option(None, "--tag", "-t", help="Filter by tags"),
    limit: int = typer.Option(50, "--limit", "-l"),
):
    """List tasks."""
    store = get_store()
    store.initialize()
    tasks = store.get_tasks(status=status, tags=tags, limit=limit)
    store.close()

    if not tasks:
        console.print("[dim]No tasks found[/]")
        return

    table = Table(title=" Tasks")
    table.add_column("ID", style="dim")
    table.add_column("Status")
    table.add_column("Priority")
    table.add_column("Title")
    table.add_column("Tags")
    table.add_column("Schedule")

    for t in tasks:
        status_style = {
            "pending": "yellow",
            "in_progress": "cyan",
            "completed": "green",
            "blocked": "red",
        }.get(t.get("status", ""), "white")

        table.add_row(
            str(t["id"]),
            f"[{status_style}]{t['status']}[/]",
            "" if t.get("priority", 0) > 7 else "" if t.get("priority", 0) > 3 else "",
            t["title"][:60],
            ", ".join(t.get("tags", []) or [])[:30],
            t.get("schedule") or "-",
        )

    console.print(table)


@task_app.command()
def add(
    title: str = typer.Argument(..., help="Task title"),
    description: str = typer.Option("", "--description", "-d"),
    priority: int = typer.Option(5, "--priority", "-p", min=0, max=10),
    tags: list[str] | None = typer.Option(None, "--tag", "-t"),
    schedule: str | None = typer.Option(None, "--schedule", "-s", help="Cron expression (e.g. '0 9 * * *')"),
):
    """Add a new task (optionally recurring with cron schedule)."""
    from ai_workspace.tasks import huey, run_scheduled_db_task

    store = get_store()
    store.initialize()
    tid = store.add_task(title, description, priority, tags, schedule)

    # If scheduled, enqueue for processing
    if schedule:
        console.print(f"[dim]Scheduled task will be picked up by the worker[/]")

    store.close()
    console.print(f"[green] Task #{tid} created:[/] {title}")


@task_app.command()
def update(
    task_id: int = typer.Argument(..., help="Task ID"),
    status: str = typer.Option(..., "--status", "-s", help="New status"),
):
    """Update task status."""
    store = get_store()
    store.initialize()
    store.update_task_status(task_id, status)
    store.close()
    console.print(f"[green] Task #{task_id} → {status}[/]")


@task_app.command()
def due():
    """List tasks that are due to run."""
    store = get_store()
    store.initialize()
    tasks = store.get_due_tasks()
    store.close()

    if not tasks:
        console.print("[dim]No due tasks[/]")
        return

    table = Table(title=" Due Tasks")
    table.add_column("ID", style="dim")
    table.add_column("Title")
    table.add_column("Schedule")

    for t in tasks:
        table.add_row(str(t["id"]), t["title"], t.get("schedule", "-"))

    console.print(table)


# Memory commands

memory_app = typer.Typer(help="Agent memory operations")
app.add_typer(memory_app, name="memory")


@memory_app.command()
def add(
    content: str = typer.Argument(..., help="What to remember"),
    agent: str = typer.Option("default", "--agent", "-a"),
    memory_type: str = typer.Option("fact", "--type", "-t"),
    importance: float = typer.Option(0.5, "--importance", "-i", min=0.0, max=1.0),
):
    """Remember a fact or learning."""
    store = get_store()
    store.initialize()
    mid = store.remember(agent, content, memory_type, importance)
    store.close()
    console.print(f"[green] Memory #{mid} stored for agent '{agent}'[/]")


@memory_app.command()
def recall(
    query: str = typer.Argument(..., help="Search query"),
    agent: str = typer.Option("default", "--agent", "-a"),
    limit: int = typer.Option(10, "--limit", "-l"),
):
    """Recall agent memories."""
    store = get_store()
    store.initialize()
    memories = store.recall(agent, query, limit=limit)
    store.close()

    if not memories:
        console.print("[dim]No memories found[/]")
        return

    for m in memories:
        console.print(Panel(
            f"{m['content'][:500]}",
            title=f" {m['memory_type']} (importance: {m.get('importance', 0):.0%})",
            subtitle=f"ID: {m['id']} | {m.get('created_at', '')}",
        ))


@memory_app.command(name="list")
def memory_list(
    limit: int = typer.Option(20, "--limit", "-l", help="Max entries to show"),
):
    """List recent memories from markdown files and database."""
    from ai_workspace.knowledge.store import KnowledgeStore

    store = get_store()
    entries: list[dict[str, Any]] = []

    # Try PostgreSQL first
    try:
        store.initialize()
        raw = store.recall("%", "%", limit=limit)
        for r in raw:
            entries.append({
                "source": "db",
                "title": r.get("content", "")[:80],
                "type": r.get("memory_type", "?"),
                "importance": r.get("importance", 0),
                "date": str(r.get("created_at", ""))[:19],
            })
    except Exception:
        pass

    if store._conn:
        store.close()

    # Fallback: read markdown memory files
    mem_files = store.list_memory_files()
    for mf in mem_files:
        content = store.read_memory_markdown(mf["type"])
        if content:
            entries.append({
                "source": mf["path"],
                "title": f"{mf['entries']} entries",
                "type": mf["type"],
                "importance": 0,
                "date": "",
            })

    if not entries:
        console.print("[dim]No memories found (no DB connected, no markdown files)[/]")
        console.print("[dim]Run 'aiw wf run learn --observation \"...\"' to create one[/]")
        return

    table = Table(title=" Memory")
    table.add_column("Source", style="dim")
    table.add_column("Type", style="cyan")
    table.add_column("Content / Stats", style="green")
    table.add_column("Date", style="dim")

    for e in entries[:limit]:
        table.add_row(
            e["source"],
            e["type"],
            e["title"][:100],
            e["date"],
        )

    console.print(table)


@memory_app.command(name="search")
def memory_search(
    query: str = typer.Argument(..., help="Search term"),
    limit: int = typer.Option(10, "--limit", "-l"),
):
    """Search memories across database and markdown files."""
    from ai_workspace.knowledge.store import KnowledgeStore

    store = get_store()
    results: list[dict[str, Any]] = []

    # Try PostgreSQL
    try:
        store.initialize()
        db_results = store.recall("%", query, limit=limit)
        for r in db_results:
            results.append({
                "source": "db",
                "content": r["content"][:300],
                "type": r.get("memory_type", "?"),
                "importance": r.get("importance", 0),
                "date": str(r.get("created_at", ""))[:19],
            })
    except Exception:
        pass

    if store._conn:
        store.close()

    # Search markdown files
    for mem_type in ["convention", "pattern", "learning"]:
        content = store.read_memory_markdown(mem_type)
        if content and query.lower() in content.lower():
            # Extract the matching section
            sections = content.split("\n## ")
            for section in sections:
                if query.lower() in section.lower():
                    first_line = section.strip().split("\n")[0]
                    results.append({
                        "source": f"memory/{mem_type}s.md",
                        "content": first_line[:200],
                        "type": mem_type,
                        "importance": 0,
                        "date": "",
                    })

    if not results:
        console.print(f"[dim]No results for '{query}'[/]")
        return

    console.print(f"[bold] Results for '{query}':[/]\n")
    for r in results[:limit]:
        console.print(Panel(
            r["content"],
            title=f" {r['source']} — {r['type']}",
            subtitle=r["date"] if r["date"] else "",
        ))


# Knowledge Base commands

kb_app = typer.Typer(help="Knowledge base operations")
app.add_typer(kb_app, name="kb")


@kb_app.command()
def seed():
    """Index the aiw codebase into the knowledge graph for agent context."""
    from ai_workspace.knowledge.seed import seed as run_seed
    console.print("[bold cyan]Seeding aiw knowledge graph...[/]\n")
    indexed, skipped = run_seed(verbose=True)
    console.print(f"\n[green] {indexed} files indexed, {skipped} skipped[/]")
    console.print("[dim]Agents can now search the codebase via the MCP search_knowledge tool.[/]")


@kb_app.command(name="index")
def kb_index(
    path: str = typer.Option(".", "--path", "-p", help="Directory to index"),
    glob: str = typer.Option("**/*.{py,md}", "--glob", "-g", help="File pattern"),
):
    """Index workspace files into pgvector for RAG retrieval.

    Chunks Python files by def/class, Markdown by headings, and generic
    files with fixed-size overlapping windows. Embeddings use Ollama's
    nomic-embed-text (768-dim).
    """
    from ai_workspace.knowledge import index_workspace, setup_schema

    console.print(f"[bold cyan]Indexing {path} ({glob})...[/]\n")

    setup_schema()
    count = index_workspace(Path(path), glob=glob)

    console.print(f"\n[green] {count} chunks indexed into pgvector[/]")
    console.print("[dim]Use 'aiw kb rag-search' to query the knowledge base.[/]")


@kb_app.command()
def add(
    content: str = typer.Argument(..., help="Content to add"),
    title: str | None = typer.Option(None, "--title", "-t"),
    content_type: str = typer.Option("note", "--type"),
    tags: list[str] | None = typer.Option(None, "--tag"),
):
    """Add a knowledge entry."""
    store = get_store()
    store.initialize()
    kid = store.add_knowledge(content, content_type, title, tags=tags)
    store.close()
    console.print(f"[green] Knowledge entry #{kid} added[/]")


@kb_app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    content_type: str | None = typer.Option(None, "--type", "-t"),
    limit: int = typer.Option(10, "--limit", "-l"),
):
    """Search knowledge entries (legacy text search)."""
    store = get_store()
    store.initialize()
    entries = store.search_knowledge(query, content_type=content_type, limit=limit)
    store.close()

    if not entries:
        console.print("[dim]No entries found[/]")
        return

    for e in entries:
        console.print(Panel(
            e["content"][:300],
            title=f" {e.get('title', '#' + str(e.get('id', '?')))} [{e.get('content_type', 'note')}]",
            subtitle=f"ID: {e['id']} | {e.get('created_at', '')}",
        ))


@kb_app.command(name="rag-search")
def kb_rag_search(
    query: str = typer.Argument(..., help="Search query"),
    k: int = typer.Option(5, "--top", "-k", help="Number of results"),
    strategy: str = typer.Option("hybrid", "--strategy", "-s", help="Search: hybrid, dense, or sparse"),
):
    """Hybrid RAG search (dense vector + BM25 + RRF merge).

    Uses pgvector for vector similarity and PostgreSQL tsvector
    for keyword search. Results are merged via Reciprocal Rank Fusion.
    """
    from ai_workspace.knowledge import search_knowledge as rag_search

    console.print(f"[bold cyan]RAG Search[/]: {query}")
    console.print(f"[dim]Strategy: {strategy} | Top-k: {k}[/]\n")

    results = rag_search(query, k=k, strategy=strategy)

    if not results:
        console.print("[dim]No results found. Try 'aiw kb index' first.[/]")
        return

    for r in results:
        source = f"{r['source_file']}"
        if r.get("start_line"):
            source += f":L{r['start_line']}"
        console.print(Panel(
            r["content"][:500],
            title=f" {source} [score: {r['score']:.3f}]",
        ))


# Worker command (Huey consumer)

@app.command()
def worker():
    """Start the task worker (Huey consumer) to process tasks and periodic schedules."""
    from ai_workspace.tasks import start_worker, init_telemetry

    console.print("[bold cyan]Starting AI Workspace task worker...[/]")
    console.print("[dim]Handles periodic tasks + enqueued jobs. Press Ctrl+C to stop.[/]")
    console.print()

    start_worker()


# Schedule commands (Huey-based)

schedule_app = typer.Typer(help="Manage recurring tasks (Huey)")
app.add_typer(schedule_app, name="schedule")


@schedule_app.command(name="run")
def schedule_run(
    name: str = typer.Argument(..., help="Periodic task: morning, research, learning, check, telemetry"),
):
    """Run a periodic task immediately for testing."""
    from ai_workspace.tasks import (
        periodic_morning_briefing,
        periodic_daily_research,
        periodic_continuous_learning,
        periodic_check_db_tasks,
        periodic_telemetry_report,
    )

    tasks_map = {
        "morning": periodic_morning_briefing,
        "briefing": periodic_morning_briefing,
        "research": periodic_daily_research,
        "daily": periodic_daily_research,
        "learning": periodic_continuous_learning,
        "continuous": periodic_continuous_learning,
        "check": periodic_check_db_tasks,
        "db-tasks": periodic_check_db_tasks,
        "telemetry": periodic_telemetry_report,
        "report": periodic_telemetry_report,
    }

    if name not in tasks_map:
        valid = ", ".join(sorted(set(tasks_map.keys())))
        console.print(f"[red]Unknown task: {name}[/]\nAvailable: {valid}")
        raise typer.Exit(1)

    console.print(f"[cyan]Running task: {name}...[/]")
    result = tasks_map[name]()
    console.print(json.dumps(result, indent=2, default=str))


@schedule_app.command()
def status():
    """Show schedule status and periodic task configuration."""
    from ai_workspace.tasks import huey

    try:
        pending = huey.pending_count()
        scheduled = huey.scheduled_count()
    except Exception:
        pending = scheduled = "n/a (worker not running)"

    table = Table(title=" Schedule Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Value")

    table.add_row("Pending tasks", str(pending))
    table.add_row("Scheduled tasks", str(scheduled))
    table.add_row("Task DB", str(Path.home() / ".ai-workspace" / "tasks.db"))
    table.add_row("Worker", "Use: aiw worker")

    console.print(table)
    console.print()
    console.print("[bold]Periodic schedules (BRT timezone):[/]")
    console.print("  07:00  [cyan]morning_briefing[/]      - sync Obsidian + daily briefing")
    console.print("  08:00  [cyan]daily_research[/]        - automated topic research")
    console.print("  02:00  [cyan]continuous_learning[/]   - pattern extraction")
    console.print("  09:00  [cyan]telemetry_report[/]      - metrics snapshot")
    console.print("  **:00  [cyan]db_task_checker[/]       - run due DB tasks")


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


# Source reputation commands

source_app = typer.Typer(help="Source reputation: check, endorse, flag domains")
app.add_typer(source_app, name="source")


@source_app.command(name="check")
def source_check(url: str = typer.Argument(..., help="URL or domain to check")):
    """Check credibility score for a URL or domain."""
    from ai_workspace.sources import SourceReputationService

    svc = SourceReputationService()
    svc.initialize()

    result = svc.get_score(url)
    level_icon = {"trust": "", "warn": "", "ignore": ""}.get(result["level"], "")

    console.print(f"[bold]Domain:[/] {result['domain']}")
    console.print(f"[bold]Score:[/] {level_icon} {result['composite_score']:.2f} ({result['level']})")

    if result["cred1_score"] is not None:
        console.print(f"[bold]CRED-1:[/] {result['cred1_score']:.2f}")
    if result["accuracy_rate"] is not None:
        console.print(f"[bold]Accuracy:[/] {result['accuracy_rate']:.1%}")
    if result["cross_ref_score"] is not None:
        console.print(f"[bold]Cross-ref:[/] {result['cross_ref_score']:.2f}")


@source_app.command(name="endorse")
def source_endorse(url: str = typer.Argument(..., help="URL or domain to endorse as reliable")):
    """Mark a source as trustworthy."""
    from ai_workspace.sources import SourceReputationService

    svc = SourceReputationService()
    svc.initialize()
    svc.endorse(url)
    console.print(f"[green] Endorsed {url}[/]")


@source_app.command(name="flag")
def source_flag(url: str = typer.Argument(..., help="URL or domain to flag as unreliable")):
    """Flag a source as unreliable."""
    from ai_workspace.sources import SourceReputationService

    svc = SourceReputationService()
    svc.initialize()
    svc.flag(url)
    console.print(f"[yellow] Flagged {url}[/]")


@source_app.command(name="stats")
def source_stats():
    """Show source reputation statistics."""
    from ai_workspace.sources import SourceReputationService

    svc = SourceReputationService()
    svc.initialize()

    stats = svc.stats()

    table = Table(title=" Source Reputation System")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Domains tracked", str(stats["total_domains"]))
    table.add_row("CRED-1 coverage", str(stats["cred1_coverage"]))
    table.add_row("Sources used in research", str(stats["sources_tracked"]))
    table.add_row("Average score", f"{stats['avg_score']:.3f}")

    console.print(table)


@source_app.command(name="seed")
def source_seed():
    """Seed the database with CRED-1 dataset and reliable domains."""
    from ai_workspace.sources import SourceReputationService

    svc = SourceReputationService()
    svc.initialize()

    with console.status("[cyan]Seeding CRED-1 dataset...", spinner="dots"):
        cred1_count = svc.seed_cred1()
    console.print(f"[green] CRED-1: {cred1_count} domains[/]")

    with console.status("[cyan]Seeding reliable domains...", spinner="dots"):
        reliable_count = svc.seed_reliable()
    console.print(f"[green] Reliable seed: {reliable_count} domains[/]")

    console.print(f"\n[bold]Total: {cred1_count + reliable_count} domains seeded[/]")


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
    from ai_workspace.skills import get_loader
    from ai_workspace.providers import ProviderRegistry

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

    console.print(f"[green] Sync complete[/]")
    console.print(f"  Imported: {result['imported']} notes")
    console.print(f"  Exported: {result['exported']} notes")


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


# Cache commands

cache_app = typer.Typer(help="Manage semantic cache")
app.add_typer(cache_app, name="cache")


@cache_app.command()
def stats():
    """Show semantic cache statistics."""
    from ai_workspace.core.cost import SemanticCache, CostLog

    cache = SemanticCache()
    cost_log = CostLog()

    try:
        s = cache.stats()
        today = cost_log.today_cost()
        month = cost_log.month_cost()

        console.print(Panel(
            f"[bold]Entries:[/] {s['total_entries']}\n"
            f"[bold]Total hits:[/] {s['total_hits']}\n"
            f"[bold]Tokens saved:[/] {s['tokens_saved']:,}\n"
            f"[bold]Cost saved:[/] ${s['cost_saved']:.4f}\n"
            f"[bold]Today's spend:[/] ${today:.4f}\n"
            f"[bold]Month's spend:[/] ${month:.4f}",
            title=" Cache Statistics",
            border_style="cyan",
        ))

        if s['total_entries'] > 0 and s['total_hits'] > 0:
            hit_rate = s['total_hits'] / (s['total_hits'] + s['total_entries']) * 100
            console.print(f"[dim]Estimated hit rate: {hit_rate:.0f}%[/]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/]")


@cache_app.command()
def clear(
    response_type: str | None = typer.Option(None, "--type", "-t", help="Clear only: chat, search, research"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Clear semantic cache entries."""
    from ai_workspace.core.cost import SemanticCache

    if not force:
        label = response_type or "ALL"
        confirm = typer.confirm(f"Clear {label} cache entries?")
        if not confirm:
            console.print("[dim]Cancelled.[/]")
            return

    cache = SemanticCache()
    try:
        deleted = cache.clear(response_type=response_type)
        console.print(f"[green] Cleared {deleted} cache entries[/]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/]")


# Main entry point


# Workflow commands

def _get_db_url() -> str:
    """Get the database URL from environment or default."""
    import os
    return os.environ.get("AIW_DB_URL", "postgresql:///ai_workspace")


wf_app = typer.Typer(help="DAG-based workflow execution")
app.add_typer(wf_app, name="wf")


@wf_app.command(name="list")
def wf_list():
    """List available workflows."""
    from ai_workspace.workflow import WorkflowRegistry

    table = Table(title=" Available Workflows")
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    
    # Auto-detect descriptions from workflow classes
    descriptions = {}
    for name in WorkflowRegistry.list():
        wf_cls = WorkflowRegistry.get(name)
        if wf_cls and wf_cls.__doc__:
            # First line of docstring after the title
            lines = wf_cls.__doc__.strip().split("\n")
            # Skip blank lines after the title
            for line in lines:
                stripped = line.strip()
                if stripped:
                    # Grab the first meaningful description line
                    descriptions[name] = stripped[:80]
                    break
    
    for name in WorkflowRegistry.list():
        table.add_row(name, descriptions.get(name, ""))

    console.print(table)


@wf_app.command(name="run")
def wf_run(
    name: str = typer.Argument(..., help="Workflow name"),
    query: str | None = typer.Option(None, "--query", "-q", help="Query for research workflows"),
    depth: int = typer.Option(2, "--depth", "-d", help="Research depth"),
    input_json: str | None = typer.Option(None, "--input", "-i", help="JSON input for workflow"),
    background: bool = typer.Option(False, "--background", "-b", help="Submit to worker queue and return immediately"),
):
    """Run a workflow.

    By default, runs synchronously (blocking). Use --background to submit
    to the Huey worker daemon — the workflow survives SSH disconnects.
    Check status later with: aiw wf status
    """
    from ai_workspace.workflow import WorkflowRegistry

    wf_cls = WorkflowRegistry.get(name)
    if not wf_cls:
        valid = ", ".join(WorkflowRegistry.list())
        console.print(f"[red]Unknown workflow: {name}[/]\nAvailable: {valid}")
        raise typer.Exit(1)

    wf = wf_cls()

    inputs = {}
    if input_json:
        try:
            inputs = json.loads(input_json)
        except json.JSONDecodeError as e:
            console.print(f"[red]Invalid JSON input: {e}[/]")
            raise typer.Exit(1)
    elif query:
        inputs = {"query": query, "depth": depth}
    else:
        console.print("[yellow]Provide --query or --input[/]")
        raise typer.Exit(1)

    if background:
        # Submit to Huey worker and return immediately
        from ai_workspace.tasks import run_workflow_task

        console.print(f"[bold cyan]Submitting workflow to background worker: {name}[/]")
        console.print(f"Inputs: {json.dumps(inputs, indent=2)}")
        console.print()

        with console.status("[cyan]Enqueuing...", spinner="dots"):
            result = run_workflow_task(workflow_name=name, inputs=inputs)

        if isinstance(result, dict) and "run_id" in result:
            console.print(f"[green] Submitted (run #{result['run_id']})[/]")
            console.print(f"  [dim]Check status: aiw wf status[/]")
            console.print(f"  [dim]View logs:    aiw wf logs {result['run_id']}[/]")
            console.print(f"  [dim]Retry if fails: aiw wf retry {result['run_id']}[/]")
        else:
            console.print(f"[green] Submitted (task queued)[/]")
            console.print(f"  [dim]Result: {result}[/]")
        return

    console.print(f"[bold cyan]Running workflow: {name}[/]")
    console.print(f"Inputs: {json.dumps(inputs, indent=2)}")
    console.print()

    with console.status(f"[cyan]Executing workflow...", spinner="dots"):
        result = wf.run_sync(**inputs)

    console.print()

    if result.status.value == "done":
        console.print(Panel(
            f"[green] Completed in {result.duration_ms:.0f}ms[/]",
            title=f"Workflow: {name}",
            border_style="green",
        ))
    else:
        console.print(Panel(
            f"[red] Failed: {result.error}[/]\n\nDuration: {result.duration_ms:.0f}ms",
            title=f"Workflow: {name}",
            border_style="red",
        ))

    # Show steps
    table = Table(title=" Steps")
    table.add_column("Step", style="cyan")
    table.add_column("Status")
    table.add_column("Duration")
    table.add_column("Retries")

    for step_name, step in result.steps.items():
        status_style = {
            "done": "green", "failed": "red", "skipped": "dim",
            "running": "yellow", "pending": "dim",
        }.get(step.status.value, "white")
        table.add_row(
            step_name,
            f"[{status_style}]{step.status.value}[/]",
            f"{step.duration_ms:.0f}ms" if step.duration_ms else "-",
            str(step.retry_count),
        )

    console.print(table)
    console.print()
    console.print(f"[dim]Run ID: {result.run_id} | View logs: aiw wf logs {result.run_id}[/]")


@wf_app.command(name="status")
def wf_status(
    name: str | None = typer.Option(None, "--name", "-n", help="Workflow name"),
    limit: int = typer.Option(20, "--limit", "-l"),
):
    """View workflow runs and their status."""
    db_url = _get_db_url()

    if name:
        from ai_workspace.workflow import WorkflowRegistry
        wf_cls = WorkflowRegistry.get(name)
        if not wf_cls:
            console.print(f"[red]Unknown workflow: {name}[/]")
            raise typer.Exit(1)

        runs = wf_cls.get_runs(limit=limit, db_url=db_url)
        title = f" Runs - {name}"
    else:
        # Show all workflows' recent runs
        from ai_workspace.workflow import WorkflowRegistry
        runs = []
        for wf_name in WorkflowRegistry.list():
            wf_cls = WorkflowRegistry.get(wf_name)
            if wf_cls:
                runs.extend(wf_cls.get_runs(limit=5, db_url=db_url))
        runs.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        title = f" Recent Runs (all workflows)"

    if not runs:
        console.print("[dim]No runs found[/]")
        return

    table = Table(title=title)
    table.add_column("Run ID", style="dim")
    table.add_column("Workflow")
    table.add_column("Status")
    table.add_column("Duration")
    table.add_column("When")

    for r in runs[:limit]:
        status_style = {
            "done": "green", "failed": "red", "running": "yellow", "pending": "dim",
        }.get(r.get("status", ""), "white")

        created = r.get("created_at", "")
        if isinstance(created, datetime):
            created = created.strftime("%m-%d %H:%M")
        elif isinstance(created, str) and "T" in created:
            created = created[:16].replace("T", " ")

        table.add_row(
            str(r["run_id"]),
            r.get("workflow_name", "?"),
            f"[{status_style}]{r.get('status', '?')}[/]",
            f"{r.get('duration_ms', 0):.0f}ms",
            str(created),
        )

    console.print(table)


@wf_app.command(name="logs")
def wf_logs(
    run_id: int = typer.Argument(..., help="Run ID to inspect"),
    workflow_name: str | None = typer.Option(None, "--workflow", "-w", help="Workflow name (required for lookup)"),
):
    """View detailed execution logs for a workflow run."""
    # First, find the workflow name from the runs table
    if not workflow_name:
        from ai_workspace.knowledge import KnowledgeStore
        store = get_store(db_url=_get_db_url())
        store.initialize()
        c = store.conn.cursor()
        c.execute("SELECT workflow_name FROM workflow_runs WHERE run_id = %s", (run_id,))
        row = c.fetchone()
        store.close()
        if row:
            workflow_name = row[0]
        else:
            console.print(f"[red]Run {run_id} not found[/]")
            raise typer.Exit(1)

    from ai_workspace.workflow import WorkflowRegistry
    wf_cls = WorkflowRegistry.get(workflow_name)
    if not wf_cls:
        console.print(f"[red]Unknown workflow: {workflow_name}[/]")
        raise typer.Exit(1)

    logs = wf_cls.get_run_logs(run_id, db_url=_get_db_url())

    if not logs:
        console.print(f"[dim]No logs found for run {run_id}[/]")
        return

    console.print(f"[bold]Logs for Run #{run_id} ({workflow_name})[/]\n")

    table = Table(title=" Execution Logs")
    table.add_column("Step", style="cyan")
    table.add_column("Attempt")
    table.add_column("Status")
    table.add_column("Duration")
    table.add_column("Error")

    for log in logs:
        status_style = {
            "done": "green", "failed": "red", "running": "yellow",
        }.get(log.get("status", ""), "white")
        error = log.get("error") or ""
        table.add_row(
            log.get("step_name", "?"),
            str(log.get("attempt", 0)),
            f"[{status_style}]{log.get('status', '?')}[/]",
            f"{log.get('duration_ms', 0):.0f}ms",
            error[:80],
        )

    console.print(table)

    # Show output for completed steps
    for log in logs:
        if log.get("status") == "done" and log.get("output"):
            output = log["output"]
            if isinstance(output, str):
                try:
                    output = json.loads(output)
                except json.JSONDecodeError:
                    pass
            console.print(Panel(
                json.dumps(output, indent=2, default=str)[:1000],
                title=f" Output: {log.get('step_name', '?')}",
                border_style="blue",
            ))


@wf_app.command(name="retry")
def wf_retry(
    run_id: int = typer.Argument(..., help="Run ID to retry"),
    workflow_name: str | None = typer.Option(None, "--workflow", "-w", help="Workflow name"),
):
    """Retry a failed workflow run from the last completed step."""
    if not workflow_name:
        from ai_workspace.knowledge import KnowledgeStore
        store = get_store(db_url=_get_db_url())
        store.initialize()
        c = store.conn.cursor()
        c.execute("SELECT workflow_name FROM workflow_runs WHERE run_id = %s", (run_id,))
        row = c.fetchone()
        store.close()
        if row:
            workflow_name = row[0]
        else:
            console.print(f"[red]Run {run_id} not found[/]")
            raise typer.Exit(1)

    from ai_workspace.workflow import WorkflowRegistry
    wf_cls = WorkflowRegistry.get(workflow_name)
    if not wf_cls:
        console.print(f"[red]Unknown workflow: {workflow_name}[/]")
        raise typer.Exit(1)

    console.print(f"[cyan]Retrying run #{run_id} ({workflow_name})...[/]")


@wf_app.command(name="result")
def wf_result(
    task_id: str = typer.Argument(..., help="Task ID from --background submission"),
):
    """Get the result of a background workflow task."""
    from huey.api import Result as HueyResult
    from ai_workspace.tasks import huey

    try:
        result = HueyResult(huey, task_id)
        if result() is not None:
            data = result()
            if isinstance(data, dict):
                console.print(Panel(
                    json.dumps(data, indent=2, default=str),
                    title=f" Task Result: {task_id}",
                ))
            else:
                console.print(str(data))
        else:
            console.print("[yellow]Task not yet completed or not found[/]")
            console.print(f"[dim]Check worker status: systemctl --user status aiw-worker[/]")
    except Exception as e:
        console.print(f"[red]Could not retrieve result: {e}[/]")


@wf_app.command(name="stats")
def wf_stats(
    name: str = typer.Argument(..., help="Workflow name"),
):
    """Show statistics for a workflow."""
    from ai_workspace.workflow import WorkflowRegistry

    wf_cls = WorkflowRegistry.get(name)
    if not wf_cls:
        valid = ", ".join(WorkflowRegistry.list())
        console.print(f"[red]Unknown workflow: {name}[/]\nAvailable: {valid}")
        raise typer.Exit(1)

    stats = wf_cls.get_run_stats(db_url=_get_db_url())

    table = Table(title=f" Stats - {name}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Total runs", str(stats.get("total", 0)))
    table.add_row("Completed", f"[green]{stats.get('completed', 0)}[/]")
    table.add_row("Failed", f"[red]{stats.get('failed', 0)}[/]" if stats.get("failed", 0) > 0 else str(stats.get("failed", 0)))
    table.add_row("Running", f"[yellow]{stats.get('running', 0)}[/]" if stats.get("running", 0) > 0 else "0")
    table.add_row("Avg duration", f"{stats.get('avg_duration_ms', 0):.0f}ms")
    table.add_row("Avg success duration", f"{stats.get('avg_success_duration_ms', 0):.0f}ms")
    table.add_row("First run", str(stats.get("first_run", "-"))[:19])
    table.add_row("Last run", str(stats.get("last_run", "-"))[:19])

    console.print(table)


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


# Research view commands

research_app = typer.Typer(help="View completed research results")
app.add_typer(research_app, name="research")


@research_app.command(name="list")
def research_list(
    limit: int = typer.Option(20, "--limit", "-l", help="Number of results"),
):
    """List completed research entries."""
    from ai_workspace.knowledge import KnowledgeStore
    store = get_store(db_url=_get_db_url())
    store.initialize()
    entries = store.get_research_history(limit=limit)
    store.close()

    if not entries:
        console.print("[dim]No research entries yet[/]")
        return

    table = Table(title=" Research History")
    table.add_column("ID", style="dim")
    table.add_column("Query")
    table.add_column("Confidence", justify="right")
    table.add_column("When")

    for e in entries:
        created = e.get("created_at", "")
        if hasattr(created, "strftime"):
            created = created.strftime("%m-%d %H:%M")
        elif isinstance(created, str) and "T" in created:
            created = created[:16].replace("T", " ")

        table.add_row(
            str(e["id"]),
            e.get("query", "?")[:80],
            f"{e.get('confidence', 0):.0%}",
            str(created),
        )

    console.print(table)
    console.print("[dim]View details: aiw research view <id>[/]")


@research_app.command(name="view")
def research_view(
    research_id: int = typer.Argument(..., help="Research entry ID"),
):
    """View a completed research report."""
    from ai_workspace.knowledge import KnowledgeStore
    store = get_store(db_url=_get_db_url())
    store.initialize()

    c = store.conn.cursor()
    c.execute(
        "SELECT id, query, summary, detailed_report, sources, confidence, sub_questions, created_at "
        "FROM research_entries WHERE id = %s",
        (research_id,),
    )
    row = c.fetchone()
    c.close()
    store.close()

    if not row:
        console.print(f"[red]Research #{research_id} not found[/]")
        return

    cols = ["id", "query", "summary", "detailed_report", "sources", "confidence", "sub_questions", "created_at"]
    entry = dict(zip(cols, row))

    created_str = entry.get("created_at", "")
    if hasattr(created_str, "strftime"):
        created_str = created_str.strftime("%Y-%m-%d %H:%M")
    elif isinstance(created_str, str) and "T" in created_str:
        created_str = created_str[:16].replace("T", " ")

    console.print(Panel(
        f"[bold cyan]{entry['query']}[/]\n\n"
        f"[dim]ID: {entry['id']} | Confidence: {entry.get('confidence', 0):.0%} | "
        f"Created: {created_str}[/]",
        title=" Research",
    ))

    console.print(Panel(
        f"[bold cyan]{entry['query']}[/]\n\n"
        f"[dim]ID: {entry['id']} | Confidence: {entry.get('confidence', 0):.0%} | "
        f"Created: {created_str}[/]",
        title=" Research",
    ))

    if entry.get("summary"):
        console.print()
        console.print(Panel(
            Markdown(entry["summary"]),
            title=" Summary",
            border_style="green",
        ))

    if entry.get("detailed_report"):
        console.print()
        console.print(Panel(
            Markdown(entry["detailed_report"][:5000]),
            title=" Detailed Report",
            border_style="blue",
        ))

    if entry.get("sub_questions"):
        console.print()
        table = Table(title=" Sub-questions")
        table.add_column("#", style="dim")
        table.add_column("Question")
        for i, sq in enumerate(entry["sub_questions"], 1):
            if isinstance(sq, dict):
                q = sq.get("question", str(sq))[:120]
            else:
                q = str(sq)[:120]
            table.add_row(str(i), q)
        console.print(table)


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

# Project commands — multi-agent coding with git worktrees

project_app = typer.Typer(help="Manage coding projects with git worktrees")
app.add_typer(project_app, name="project")


@project_app.command()
def create(
    name: str = typer.Argument(..., help="Project name"),
    description: str = typer.Option("", "--description", "-d", help="Project description"),
    repo: list[str] = typer.Option([], "--repo", "-r", help="Repository: name=path (repeatable)"),
):
    """Create a new coding project with optional git repositories."""
    import os as _os
    from ai_workspace.core.projects import ProjectManager

    pm = ProjectManager()
    pm.initialize()

    repos = []
    for r in repo:
        if "=" in r:
            repo_name, repo_path = r.split("=", 1)
        else:
            repo_name = os.path.basename(r.rstrip("/"))
            repo_path = r
        repos.append({"name": repo_name.strip(), "path": _os.path.abspath(repo_path.strip())})

    project = pm.create_project(name, description, repos)
    console.print(f"[green] Project '{name}' created[/]")
    console.print(f"  Repos: {len(project.repos)}")
    for r in project.repos:
        console.print(f"    • {r.name} → {r.path}")


@project_app.command(name="list")
def project_list():
    """List all coding projects."""
    from datetime import datetime, timezone
    from ai_workspace.core.projects import ProjectManager

    pm = ProjectManager()
    projects = pm.list_projects()

    if not projects:
        console.print("[dim]No projects yet. Create one with: aiw project create <name>[/]")
        return

    for p in projects:
        agent_info = f"{len(p.agents)} active agents" if p.agents else "no active agents"
        console.print(f"[bold]{p.name}[/] — {p.description or 'no description'} — [dim]{agent_info}[/]")
        for r in p.repos:
            console.print(f"   {r.name} → {r.path}")
        for a in p.agents:
            elapsed = ""
            if a.started_at:
                try:
                    st = datetime.fromisoformat(a.started_at.replace("Z", "+00:00"))
                    delta = datetime.now(timezone.utc) - st
                    elapsed = f" ({delta.seconds // 60}m ago)"
                except Exception:
                    pass
            console.print(f"   [cyan]{a.name}[/] [{a.branch}] — {a.task[:60]}…{elapsed}")
        console.print()


@project_app.command()
def spawn(
    project_name: str = typer.Argument(..., help="Project to spawn agent in"),
    repo_name: str = typer.Argument("main", help="Repository within the project"),
    task: str = typer.Option(..., "--task", "-t", help="Coding task for the agent"),
    agent_name: str = typer.Option("", "--name", "-n", help="Agent name (auto-generated if empty)"),
    model: str = typer.Option("qwen3:14b", "--model", "-m", help="LLM model for coding"),
):
    """Spawn a coding agent in an isolated git worktree."""
    from datetime import datetime
    from ai_workspace.core.projects import ProjectManager
    from ai_workspace.agents.swarm import SwarmConfig, coding_crew

    pm = ProjectManager()
    pm.initialize()

    if not agent_name:
        agent_name = f"agent-{datetime.now().strftime('%H%M%S')}"

    # Create worktree
    console.print(f"[dim]Creating worktree for {agent_name}...[/]")
    wt = pm.create_worktree(project_name, agent_name, repo_name, task, model)
    console.print(f"[green] Worktree: {wt.worktree_path}[/]")
    console.print(f"[green] Branch: {wt.branch}[/]")
    console.print()

    # Spawn coding crew in the worktree
    console.print(f"[bold cyan]Spawning coding agent in worktree...[/]")
    cfg = SwarmConfig(coder_model=f"ollama/{model}")
    crew = coding_crew(task_description=task, cfg=cfg, working_dir=wt.worktree_path)

    try:
        result = crew.kickoff()
        summary = str(result)[:500]
        console.print()
        console.print(Panel(summary, title=f" {agent_name} Complete"))

        # Update DB
        c = pm.conn.cursor()
        c.execute(
            "UPDATE project_agents SET status = 'completed', completed_at = NOW(), summary = %s "
            "WHERE project_name = %s AND agent_name = %s",
            (summary, project_name, agent_name),
        )
    except Exception as e:
        console.print(f"[red] Agent failed: {e}[/]")
        c = pm.conn.cursor()
        c.execute(
            "UPDATE project_agents SET status = 'failed', summary = %s "
            "WHERE project_name = %s AND agent_name = %s",
            (str(e)[:500], project_name, agent_name),
        )


@project_app.command()
def cleanup(
    project_name: str = typer.Argument(..., help="Project name"),
    agent_name: str = typer.Option("", "--agent", "-a", help="Agent to clean up (all completed if empty)"),
):
    """Clean up completed agent worktrees."""
    from psycopg2.extras import RealDictCursor
    from ai_workspace.core.projects import ProjectManager

    pm = ProjectManager()

    if agent_name:
        pm.cleanup_worktree(project_name, agent_name)
        console.print(f"[green] Cleaned up {agent_name}[/]")
    else:
        # Clean all completed agents
        c = pm.conn.cursor(cursor_factory=RealDictCursor)
        c.execute(
            "SELECT agent_name FROM project_agents WHERE project_name = %s AND status = 'completed'",
            (project_name,),
        )
        for row in c.fetchall():
            pm.cleanup_worktree(project_name, row["agent_name"])
            console.print(f"[green] Cleaned up {row['agent_name']}[/]")


# Source Reputation commands

source_app = typer.Typer(help="Manage source reputation (CRED-1 + tracking)")
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


# ── Eval commands ─────────────────────────────────────────

eval_app = typer.Typer(help="Agent evaluation harness")
app.add_typer(eval_app, name="eval")


@eval_app.command(name="run")
def eval_run(
    suite: str = typer.Option("all", "--suite", "-s", help="Suite: all, coding, reasoning, facts"),
    model: str = typer.Option("qwen3:14b", "--model", "-m", help="Model to evaluate"),
    provider: str = typer.Option("ollama", "--provider", "-p", help="Provider"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate eval definitions without LLM calls"),
):
    """Run agent evaluation suites."""
    import asyncio
    from ai_workspace.evals import EvalRunner, ALL_EVAL_SUITES

    console.print("[bold cyan]Eval Harness[/]")
    console.print(f"[dim]Model: {model} | Provider: {provider} | Suite: {suite}[/]")
    console.print()

    suite_names = list(ALL_EVAL_SUITES.keys()) if suite == "all" else [suite]

    if dry_run:
        runner = EvalRunner(model=model, provider=provider)
        all_cases = []
        for name in suite_names:
            all_cases.extend(ALL_EVAL_SUITES.get(name, []))
        import asyncio as _asyncio
        results = _asyncio.run(runner.run_dry(all_cases))
        console.print(f"[dim]Dry run: {len(results)} case definitions validated.[/]")
        return

    from ai_workspace.evals import run_all_evals

    suite_results = _asyncio.run(run_all_evals(
        model=model, provider=provider, suites=suite_names,
    ))

    table = Table(title=" Eval Results")
    table.add_column("Suite", style="cyan")
    table.add_column("Passed", justify="right")
    table.add_column("Rate", justify="right")
    table.add_column("Avg Latency", justify="right")
    table.add_column("Avg Tokens", justify="right")

    total_passed = 0
    total_cases = 0

    for name, sr in suite_results.items():
        icon = "" if sr.pass_rate >= 0.8 else ("" if sr.pass_rate >= 0.5 else "")
        table.add_row(
            f"{icon} {name}",
            f"{sr.passed_count}/{sr.total_cases}",
            f"{sr.pass_rate:.0%}",
            f"{sr.avg_latency_ms:.0f}ms",
            f"{sr.avg_tokens:.0f}",
        )
        total_passed += sr.passed_count
        total_cases += sr.total_cases

    console.print(table)
    console.print()
    overall = total_passed / total_cases if total_cases > 0 else 0
    console.print(f"[bold]Overall: {total_passed}/{total_cases} passed ({overall:.0%})[/]")


@eval_app.command(name="list")
def eval_list():
    """List available eval suites and their cases."""
    from ai_workspace.evals import ALL_EVAL_SUITES

    for name, cases in ALL_EVAL_SUITES.items():
        console.print(f"[bold cyan]{name}[/] ({len(cases)} cases)")
        for case in cases:
            expected = []
            if case.expected_keywords:
                expected.append(f"keys: {', '.join(case.expected_keywords[:3])}")
            if case.forbidden_keywords:
                expected.append(f"forbidden: {', '.join(case.forbidden_keywords[:2])}")
            if case.expected_tools:
                expected.append(f"tools: {', '.join(case.expected_tools)}")
            extra = f" [{'; '.join(expected)}]" if expected else ""
            console.print(f"  [dim]{case.id}[/]: {case.task[:80]}...{extra}")
        console.print()


if __name__ == "__main__":
    app()


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


# MCP server command


mcp_app = typer.Typer(help="MCP server for AI Workspace (expose aiw as tools)")
app.add_typer(mcp_app, name="mcp")


@mcp_app.command(name="serve")
def mcp_serve(
    transport: str = typer.Option("stdio", "--transport", "-t", help="Transport: stdio, http"),
    port: int = typer.Option(8765, "--port", "-p", help="Port for HTTP transport"),
):
    """Run the MCP server, exposing aiw as a tool provider.

    stdio transport is what Claude Desktop / Cursor / Cline / Continue expect.
    HTTP transport is useful for remote clients.

    Example claude_desktop_config.json entry:

        {
          "mcpServers": {
            "aiw": {
              "command": "aiw",
              "args": ["mcp", "serve"]
            }
          }
        }
    """
    from ai_workspace.mcp_server import run_stdio_server, TOOL_REGISTRY

    console.print(f"[bold cyan]AIW MCP Server[/]")
    console.print(f"  Transport: {transport}")
    console.print(f"  Tools exposed: {len(TOOL_REGISTRY)}")
    for name in TOOL_REGISTRY:
        console.print(f"    • {name}")
    console.print()

    if transport == "stdio":
        run_stdio_server()
    elif transport == "http":
        console.print(f"[yellow]HTTP transport not yet implemented; use stdio[/]")
        raise typer.Exit(1)
    else:
        console.print(f"[red]Unknown transport: {transport}[/]")
        raise typer.Exit(1)


@mcp_app.command(name="list")
def mcp_list():
    """List the tools that the MCP server exposes."""
    from ai_workspace.mcp_server import TOOL_REGISTRY

    table = Table(title=" MCP Tools Exposed by aiw")
    table.add_column("Tool", style="cyan")
    table.add_column("Description")

    for name, spec in TOOL_REGISTRY.items():
        desc = spec["schema"].get("description", "")
        table.add_row(name, desc[:120] + ("..." if len(desc) > 120 else ""))

    console.print(table)
