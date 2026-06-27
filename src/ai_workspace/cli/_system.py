"""CLI commands — `aiw system`."""

from __future__ import annotations

import typer
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

from ai_workspace.cli._app import app, console
from ai_workspace.providers import chat_sync
from ai_workspace.core.db import get_store
from ai_workspace.knowledge import KnowledgeStore

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


@app.command()
def worker():
    """Start the task worker (Huey consumer) to process tasks and periodic schedules."""
    from ai_workspace.tasks import start_worker, init_telemetry

    console.print("[bold cyan]Starting AI Workspace task worker...[/]")
    console.print("[dim]Handles periodic tasks + enqueued jobs. Press Ctrl+C to stop.[/]")
    console.print()

    start_worker()


# Schedule commands (extracted to cli._schedule)


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