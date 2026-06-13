"""
AI Workspace CLI — `aiw` command.

Commands:
  aiw search <query>          Deep recursive research
  aiw ask [--provider] <msg>  Quick chat with any model
  aiw task list|add|run       Manage tasks
  aiw memory add|recall       Agent memory operations
  aiw kb add|search|sync      Knowledge base operations
  aiw schedule run|status     Recurring tasks (Huey)
  aiw worker                  Start task worker (Huey consumer)
  aiw wf run|status|logs|retry|stats  DAG workflow execution
  aiw obsidian sync|pull      Obsidian vault sync
  aiw sync [push|pull|vault]  Multi-PC knowledge sync
  aiw telemetry               View telemetry snapshot
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from ai_workspace.providers import ProviderRegistry, chat_sync
from ai_workspace.knowledge import KnowledgeStore

app = typer.Typer(
    name="aiw",
    help="AI Workspace - Deep search, agent swarm, knowledge base",
    no_args_is_help=True,
)
console = Console()

# ═══════════════════════════════════════════════════════════════
# Search command
# ═══════════════════════════════════════════════════════════════

@app.command()
def search(
    query: str = typer.Argument(..., help="Research query"),
    depth: int = typer.Option(2, "--depth", "-d", help="Recursion depth (1-4)"),
    model: str = typer.Option("deepseek-r1:14b", "--model", "-m", help="Model for reasoning"),
    fast_model: str = typer.Option("qwen3:14b", "--fast-model", help="Model for planning/synthesis"),
    save: bool = typer.Option(True, "--save/--no-save", help="Save results to DB"),
):
    """Run deep recursive research on a query."""
    from ai_workspace.search import DeepSearchEngine

    console.print(Panel(f"[bold cyan]Deep Research[/]\n{query}", title="🔍 Query"))

    engine = DeepSearchEngine(
        model=f"ollama/{fast_model}",
        deep_model=f"ollama/{model}",
        max_depth=depth,
    )

    with console.status("[cyan]Researching...", spinner="dots"):
        result = asyncio.run(engine.research(query))

    # Display results
    console.print()
    
    table = Table(title="📋 Research Coverage", show_header=True)
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
            title="📝 Executive Summary",
            border_style="green",
        ))

    if result.detailed_report:
        console.print()
        console.print(Panel(
            Markdown(result.detailed_report[:2000]),
            title="📄 Detailed Report",
            border_style="blue",
        ))

    if save:
        try:
            store = KnowledgeStore()
            store.initialize()
            report = {
                "summary": result.summary,
                "detailed_report": result.detailed_report,
                "sources": result.sources,
                "confidence": result.confidence,
                "sub_questions": [
                    {"question": sq.question, "answer": sq.answer}
                    for sq in result.sub_questions
                ],
            }
            rid = store.save_research(query, report)
            store.close()
            console.print(f"\n[dim]✓ Saved to DB (research #{rid})[/]")
        except Exception as e:
            console.print(f"\n[dim yellow]⚠ Could not save to DB: {e}[/]")


# ═══════════════════════════════════════════════════════════════
# Ask command (quick chat)
# ═══════════════════════════════════════════════════════════════

@app.command()
def ask(
    message: str = typer.Argument(..., help="Question or prompt"),
    provider: str = typer.Option("ollama", "--provider", "-p", help="LLM provider"),
    model: str | None = typer.Option(None, "--model", "-m", help="Model name"),
    system: str | None = typer.Option(None, "--system", "-s", help="System prompt"),
):
    """Quick chat with any configured model."""
    registry = ProviderRegistry()

    if model is None:
        model = registry.get_model(provider)

    console.print(f"[dim]Provider: {provider} | Model: {model}[/]")
    console.print()

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": message})

    with console.status(f"[cyan]Thinking ({model})...", spinner="dots"):
        response = chat_sync(messages, provider=provider, model=model)

    console.print(Panel(Markdown(response), title="💬 Response"))


# ═══════════════════════════════════════════════════════════════
# Models command
# ═══════════════════════════════════════════════════════════════

@app.command()
def models(
    provider: str = typer.Option("ollama", "--provider", "-p", help="Provider to list"),
):
    """List available models for a provider."""
    registry = ProviderRegistry()
    models_list = registry.list_models(provider)

    table = Table(title=f"🤖 Models — {provider}")
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


# ═══════════════════════════════════════════════════════════════
# Task commands
# ═══════════════════════════════════════════════════════════════

task_app = typer.Typer(help="Manage tasks")
app.add_typer(task_app, name="task")


@task_app.command(name="list")
def task_list(
    status: str | None = typer.Option(None, "--status", "-s", help="Filter by status"),
    tags: list[str] | None = typer.Option(None, "--tag", "-t", help="Filter by tags"),
    limit: int = typer.Option(50, "--limit", "-l"),
):
    """List tasks."""
    store = KnowledgeStore()
    store.initialize()
    tasks = store.get_tasks(status=status, tags=tags, limit=limit)
    store.close()

    if not tasks:
        console.print("[dim]No tasks found[/]")
        return

    table = Table(title="📋 Tasks")
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
            "🔴" if t.get("priority", 0) > 7 else "🟡" if t.get("priority", 0) > 3 else "🟢",
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

    store = KnowledgeStore()
    store.initialize()
    tid = store.add_task(title, description, priority, tags, schedule)
    
    # If scheduled, enqueue for processing
    if schedule:
        console.print(f"[dim]Scheduled task will be picked up by the worker[/]")
    
    store.close()
    console.print(f"[green]✓ Task #{tid} created:[/] {title}")


@task_app.command()
def update(
    task_id: int = typer.Argument(..., help="Task ID"),
    status: str = typer.Option(..., "--status", "-s", help="New status"),
):
    """Update task status."""
    store = KnowledgeStore()
    store.initialize()
    store.update_task_status(task_id, status)
    store.close()
    console.print(f"[green]✓ Task #{task_id} → {status}[/]")


@task_app.command()
def due():
    """List tasks that are due to run."""
    store = KnowledgeStore()
    store.initialize()
    tasks = store.get_due_tasks()
    store.close()

    if not tasks:
        console.print("[dim]No due tasks[/]")
        return

    table = Table(title="⏰ Due Tasks")
    table.add_column("ID", style="dim")
    table.add_column("Title")
    table.add_column("Schedule")

    for t in tasks:
        table.add_row(str(t["id"]), t["title"], t.get("schedule", "-"))

    console.print(table)


# ═══════════════════════════════════════════════════════════════
# Memory commands
# ═══════════════════════════════════════════════════════════════

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
    store = KnowledgeStore()
    store.initialize()
    mid = store.remember(agent, content, memory_type, importance)
    store.close()
    console.print(f"[green]✓ Memory #{mid} stored for agent '{agent}'[/]")


@memory_app.command()
def recall(
    query: str = typer.Argument(..., help="Search query"),
    agent: str = typer.Option("default", "--agent", "-a"),
    limit: int = typer.Option(10, "--limit", "-l"),
):
    """Recall agent memories."""
    store = KnowledgeStore()
    store.initialize()
    memories = store.recall(agent, query, limit=limit)
    store.close()

    if not memories:
        console.print("[dim]No memories found[/]")
        return

    for m in memories:
        console.print(Panel(
            f"{m['content'][:500]}",
            title=f"🧠 {m['memory_type']} (importance: {m.get('importance', 0):.0%})",
            subtitle=f"ID: {m['id']} | {m.get('created_at', '')}",
        ))


# ═══════════════════════════════════════════════════════════════
# Knowledge Base commands
# ═══════════════════════════════════════════════════════════════

kb_app = typer.Typer(help="Knowledge base operations")
app.add_typer(kb_app, name="kb")


@kb_app.command()
def add(
    content: str = typer.Argument(..., help="Content to add"),
    title: str | None = typer.Option(None, "--title", "-t"),
    content_type: str = typer.Option("note", "--type"),
    tags: list[str] | None = typer.Option(None, "--tag"),
):
    """Add a knowledge entry."""
    store = KnowledgeStore()
    store.initialize()
    kid = store.add_knowledge(content, content_type, title, tags=tags)
    store.close()
    console.print(f"[green]✓ Knowledge entry #{kid} added[/]")


@kb_app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    content_type: str | None = typer.Option(None, "--type", "-t"),
    limit: int = typer.Option(10, "--limit", "-l"),
):
    """Search knowledge entries."""
    store = KnowledgeStore()
    store.initialize()
    entries = store.search_knowledge(query, content_type=content_type, limit=limit)
    store.close()

    if not entries:
        console.print("[dim]No entries found[/]")
        return

    for e in entries:
        console.print(Panel(
            e["content"][:300],
            title=f"📄 {e.get('title', f'#{e[\"id\"]}')} [{e.get('content_type', 'note')}]",
            subtitle=f"ID: {e['id']} | {e.get('created_at', '')}",
        ))


# ═══════════════════════════════════════════════════════════════
# Worker command (Huey consumer)
# ═══════════════════════════════════════════════════════════════

@app.command()
def worker():
    """Start the task worker (Huey consumer) to process tasks and periodic schedules."""
    from ai_workspace.tasks import start_worker, init_telemetry

    console.print("[bold cyan]Starting AI Workspace task worker...[/]")
    console.print("[dim]Handles periodic tasks + enqueued jobs. Press Ctrl+C to stop.[/]")
    console.print()
    
    start_worker()


# ═══════════════════════════════════════════════════════════════
# Schedule commands (Huey-based)
# ═══════════════════════════════════════════════════════════════

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

    table = Table(title="📅 Schedule Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Value")

    table.add_row("Pending tasks", str(pending))
    table.add_row("Scheduled tasks", str(scheduled))
    table.add_row("Task DB", str(Path.home() / ".ai-workspace" / "tasks.db"))
    table.add_row("Worker", "Use: aiw worker")

    console.print(table)
    console.print()
    console.print("[bold]Periodic schedules (BRT timezone):[/]")
    console.print("  07:00  [cyan]morning_briefing[/]      — sync Obsidian + daily briefing")
    console.print("  08:00  [cyan]daily_research[/]        — automated topic research")
    console.print("  02:00  [cyan]continuous_learning[/]   — pattern extraction")
    console.print("  09:00  [cyan]telemetry_report[/]      — metrics snapshot")
    console.print("  **:00  [cyan]db_task_checker[/]       — run due DB tasks")


# ═══════════════════════════════════════════════════════════════
# Telemetry command
# ═══════════════════════════════════════════════════════════════

@app.command()
def telemetry():
    """Show telemetry snapshot and recent activity metrics."""
    try:
        from ai_workspace.knowledge import KnowledgeStore
        store = KnowledgeStore()
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

        table = Table(title="📊 Telemetry Snapshot")
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
        console.print(f"[red]✗ Could not fetch telemetry: {e}[/]")
        console.print("[dim]Run 'aiw init' first if DB is not initialized.[/]")


# ═══════════════════════════════════════════════════════════════
# Obsidian commands
# ═══════════════════════════════════════════════════════════════

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

    console.print(f"[green]✓ Sync complete[/]")
    console.print(f"  Imported: {result['imported']} notes")
    console.print(f"  Exported: {result['exported']} notes")


# ═══════════════════════════════════════════════════════════════
# Init command
# ═══════════════════════════════════════════════════════════════

@app.command()
def init(
    db_url: str | None = typer.Option(None, "--db", help="Database URL (default: postgresql:///ai_workspace)"),
):
    """Initialize the AI Workspace database and directories."""
    data_dir = Path.home() / ".ai-workspace"
    data_dir.mkdir(exist_ok=True)

    # Initialize PostgreSQL database
    store = KnowledgeStore(db_url=db_url)
    try:
        store.initialize()
        console.print("[green]✓ PostgreSQL database initialized[/]")
    except Exception as e:
        console.print(f"[red]✗ Database error: {e}[/]")
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

    console.print("[green]✓ Directories created[/]")
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


# ═══════════════════════════════════════════════════════════════
# Main entry point
# ═══════════════════════════════════════════════════════════════


# ════════════════════════════════════════════════════════════
# Workflow commands
# ════════════════════════════════════════════════════════════

wf_app = typer.Typer(help="DAG-based workflow execution")
app.add_typer(wf_app, name="wf")


@wf_app.command(name="list")
def wf_list():
    """List available workflows."""
    from ai_workspace.workflow import WorkflowRegistry
    
    table = Table(title="🔄 Available Workflows")
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    
    descriptions = {
        "deep_research": "Plan → parallel research → synthesize → store",
        "daily_briefing": "Collect activity → generate briefing → store",
        "continuous_learning": "Extract history → find patterns → remember",
    }
    
    for name in WorkflowRegistry.list():
        table.add_row(name, descriptions.get(name, ""))
    
    console.print(table)


@wf_app.command(name="run")
def wf_run(
    name: str = typer.Argument(..., help="Workflow name"),
    query: str | None = typer.Option(None, "--query", "-q", help="Query for research workflows"),
    depth: int = typer.Option(2, "--depth", "-d", help="Research depth"),
    input_json: str | None = typer.Option(None, "--input", "-i", help="JSON input for workflow"),
):
    """Run a workflow."""
    from ai_workspace.workflow import WorkflowRegistry
    
    wf_cls = WorkflowRegistry.get(name)
    if not wf_cls:
        valid = ", ".join(WorkflowRegistry.list())
        console.print(f"[red]Unknown workflow: {name}[/]
Available: {valid}")
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
    
    console.print(f"[bold cyan]Running workflow: {name}[/]")
    console.print(f"Inputs: {json.dumps(inputs, indent=2)}")
    console.print()
    
    with console.status(f"[cyan]Executing workflow...", spinner="dots"):
        result = wf.run_sync(**inputs)
    
    console.print()
    
    if result.status.value == "done":
        console.print(Panel(
            f"[green]✓ Completed in {result.duration_ms:.0f}ms[/]",
            title=f"Workflow: {name}",
            border_style="green",
        ))
    else:
        console.print(Panel(
            f"[red]✗ Failed: {result.error}[/]

Duration: {result.duration_ms:.0f}ms",
            title=f"Workflow: {name}",
            border_style="red",
        ))
    
    # Show steps
    table = Table(title="📋 Steps")
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
    if name:
        from ai_workspace.workflow import WorkflowRegistry
        wf_cls = WorkflowRegistry.get(name)
        if not wf_cls:
            console.print(f"[red]Unknown workflow: {name}[/]")
            raise typer.Exit(1)
        
        runs = wf_cls.get_runs(limit=limit)
        title = f"📊 Runs — {name}"
    else:
        # Show all workflows' recent runs
        from ai_workspace.workflow import WorkflowRegistry
        runs = []
        for wf_name in WorkflowRegistry.list():
            wf_cls = WorkflowRegistry.get(wf_name)
            if wf_cls:
                runs.extend(wf_cls.get_runs(limit=5))
        runs.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        title = f"📊 Recent Runs (all workflows)"
    
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
        store = KnowledgeStore()
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
    
    logs = wf_cls.get_run_logs(run_id)
    
    if not logs:
        console.print(f"[dim]No logs found for run {run_id}[/]")
        return
    
    console.print(f"[bold]Logs for Run #{run_id} ({workflow_name})[/]
")
    
    table = Table(title="📜 Execution Logs")
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
                title=f"📤 Output: {log.get('step_name', '?')}",
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
        store = KnowledgeStore()
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


@wf_app.command(name="stats")
def wf_stats(
    name: str = typer.Argument(..., help="Workflow name"),
):
    """Show statistics for a workflow."""
    from ai_workspace.workflow import WorkflowRegistry
    
    wf_cls = WorkflowRegistry.get(name)
    if not wf_cls:
        valid = ", ".join(WorkflowRegistry.list())
        console.print(f"[red]Unknown workflow: {name}[/]
Available: {valid}")
        raise typer.Exit(1)
    
    stats = wf_cls.get_run_stats()
    
    table = Table(title=f"📈 Stats — {name}")
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


# ════════════════════════════════════════════════════════════
# Sync command (multi-PC)
# ════════════════════════════════════════════════════════════

@app.command()
def sync(
    direction: str = typer.Argument("status", help="push, pull, both, vault, status"),
):
    """Multi-PC knowledge base sync (thinkbook ↔ homelab via Tailscale)."""
    from ai_workspace.knowledge import SyncManager
    
    manager = SyncManager()
    
    if direction == "status":
        primary_ok = manager.is_primary_available()
        console.print(f"Primary DB (homelab): {'[green]✓ connected[/]' if primary_ok else '[red]✗ unreachable[/]'}")
        manager._load_queue()
        console.print(f"Offline queue: {len(manager._offline_queue)} pending operations")
        vault_ok = manager.vault_path.exists()
        console.print(f"Obsidian vault: {'[green]✓ exists[/]' if vault_ok else '[dim]not cloned[/]'} ({manager.vault_path})")
        return
    
    if direction == "vault":
        with console.status("[cyan]Syncing vault (git)...[/]", spinner="dots"):
            result = asyncio.run(manager.sync_vault())
        if result.get("cloned"):
            console.print("[green]✓ Vault cloned from GitHub[/]")
        else:
            console.print(f"Committed: {result.get('committed', 0)} | Pulled: {result.get('pulled', False)} | Pushed: {result.get('pushed', False)}")
        if result.get("error"):
            console.print(f"[yellow]⚠ {result['error']}[/]")
        return
    
    if direction not in ("push", "pull", "both"):
        console.print(f"[red]Invalid: {direction}. Use: push, pull, both, vault, status[/]")
        raise typer.Exit(1)
    
    if not manager.is_primary_available():
        console.print("[red]✗ Homelab PostgreSQL not reachable[/]")
        console.print("[dim]Make sure Tailscale is connected and homelab is running.[/]")
        raise typer.Exit(1)
    
    with console.status(f"[cyan]Syncing knowledge ({direction})...[/]", spinner="dots"):
        result = asyncio.run(manager.sync_knowledge(direction))
    
    console.print(f"[green]✓ Sync complete[/]")
    console.print(f"  Pushed: {result.get('pushed', 0)} entries")
    console.print(f"  Pulled: {result.get('pulled', 0)} entries")
    console.print(f"  Offline queue flushed: {result.get('offline_queue_flushed', 0)} ops")


if __name__ == "__main__":
    app()
