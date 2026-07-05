"""
Command registry — self-registering slash commands with categories, aliases, and TUI/CLI parity.

Inspired by OpenSRE's command_registry/ pattern (modular, categorized, extensible).
Each command registers itself via the @command decorator or CommandRegistry.register().

Two use cases:
  - TUI: CommandPalette reads registry for autocomplete + descriptions
  - CLI: same registry used for slash-command dispatch in REPL mode
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

# ── Types ──────────────────────────────────────────────────────────

CommandHandler = Callable[..., Any]
"""Signature: handler(registry, *args) or handler(*args) depending on context."""


@dataclass
class Command:
    """A single slash command in the registry.

    Attributes:
        name: The command name including leading slash, e.g. "/help"
        description: One-line description shown in autocomplete
        category: Grouping for the help panel
        aliases: Alternative names (e.g. "/?" for "/help")
        handler: Optional callable. Receives (registry, *args) in TUI mode.
        usage: Usage hint, e.g. "/model <model-name>"
        hidden: If True, not shown in autocomplete but still dispatchable
    """
    name: str
    description: str
    category: str = "general"
    aliases: list[str] = field(default_factory=list)
    handler: CommandHandler | None = None
    usage: str = ""
    hidden: bool = False


# ── Registry ───────────────────────────────────────────────────────


class CommandRegistry:
    """Slash command registry — self-registering, categorized, extensible.

    Usage::

        from ai_workspace.tui.command_registry import registry, command

        @command(name="/status", description="Show system status", category="system")
        def status_cmd(args: str | None = None):
            ...

        # Manual registration:
        from ai_workspace.tui.command_registry import Command, registry
        registry.register(Command(name="/ping", description="..."))
    """

    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}
        self._categories: dict[str, list[str]] = {}

    # ── Registration ────────────────────────────────────────────

    def register(self, cmd: Command) -> None:
        """Register a command and its aliases."""
        self._commands[cmd.name] = cmd
        for alias in cmd.aliases:
            self._commands[alias] = cmd

        if cmd.category not in self._categories:
            self._categories[cmd.category] = []
        if cmd.name not in self._categories[cmd.category]:
            self._categories[cmd.category].append(cmd.name)

    def unregister(self, name: str) -> None:
        """Remove a command and its aliases."""
        cmd = self._commands.get(name)
        if cmd is None:
            return
        # Remove from category
        if cmd.category in self._categories and cmd.name in self._categories[cmd.category]:
            self._categories[cmd.category].remove(cmd.name)
        # Remove primary name and aliases
        self._commands.pop(cmd.name, None)
        for alias in cmd.aliases:
            self._commands.pop(alias, None)

    # ── Lookup ──────────────────────────────────────────────────

    def get(self, name: str) -> Command | None:
        """Look up a command by name (with or without leading /)."""
        key = name if name.startswith("/") else f"/{name}"
        return self._commands.get(key)

    def filter(self, prefix: str) -> list[Command]:
        """Return commands whose name starts with *prefix* (for autocomplete)."""
        if not prefix.startswith("/"):
            return []
        return sorted(
            [cmd for name, cmd in self._commands.items()
             if name.startswith(prefix) and not cmd.hidden and name == cmd.name],
            key=lambda c: c.name,
        )

    def all(self) -> list[Command]:
        """Return all non-hidden primary commands, sorted by name."""
        seen: set[str] = set()
        result: list[Command] = []
        for name, cmd in self._commands.items():
            if cmd.hidden:
                continue
            if name != cmd.name:
                continue  # skip aliases
            if cmd.name in seen:
                continue
            seen.add(cmd.name)
            result.append(cmd)
        result.sort(key=lambda c: c.name)
        return result

    def by_category(self) -> dict[str, list[Command]]:
        """Return commands grouped by category."""
        result: dict[str, list[Command]] = {}
        for cmd in self.all():
            result.setdefault(cmd.category, []).append(cmd)
        return result

    def categories(self) -> list[str]:
        """Return sorted list of category names."""
        return sorted(self._categories.keys())

    def dispatch(self, raw: str) -> str | None:
        """Parse and dispatch a raw slash-command string.

        Returns an error message string if the command is not found,
        or None on successful dispatch (or if no handler is registered).

        Handles: "/command arg1 arg2" → handler("arg1 arg2")
        """
        parts = raw.strip().split(maxsplit=1)
        cmd_name = parts[0]
        args = parts[1] if len(parts) > 1 else ""

        cmd = self.get(cmd_name)
        if cmd is None:
            return f"Unknown command: {cmd_name}. Try /help."

        if cmd.handler is not None:
            cmd.handler(self, args)
        return None

    def size(self) -> int:
        """Return number of registered primary commands (excludes aliases)."""
        return len(self.all())


# ── Module-level singleton ─────────────────────────────────────────

registry: CommandRegistry = CommandRegistry()
"""Global command registry. Import and use ``registry.register()`` or ``@command``."""


# ── Decorator ──────────────────────────────────────────────────────


def command(
    name: str,
    description: str,
    *,
    category: str = "general",
    aliases: list[str] | None = None,
    usage: str = "",
    hidden: bool = False,
) -> Callable[[CommandHandler], CommandHandler]:
    """Decorator to register a slash command.

    Usage::

        @command(name="/hello", description="Say hello", category="fun")
        def hello_cmd(registry, args):
            print(f"Hello, {args or 'world'}!")
    """
    def decorator(handler: CommandHandler) -> CommandHandler:
        cmd = Command(
            name=name,
            description=description,
            category=category,
            aliases=aliases or [],
            handler=handler,
            usage=usage,
            hidden=hidden,
        )
        registry.register(cmd)
        return handler
    return decorator


# ── Default commands (always registered on import) ─────────────────

@command(
    name="/help",
    description="Show command reference and key bindings",
    category="navigation",
    aliases=["/?"],
)
def help_cmd(_registry: CommandRegistry, _args: str | None = None) -> None:
    """Display all available commands grouped by category."""
    from rich.console import Console
    from rich.table import Table
    console = Console()

    table = Table(title=" aiw Slash Commands", show_header=True)
    table.add_column("Command", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")
    table.add_column("Category", style="dim")

    for cmd in _registry.all():
        table.add_row(cmd.name, cmd.description, cmd.category)

    console.print(table)


@command(
    name="/model",
    description="Switch LLM model (e.g. /model qwen3:14b)",
    category="session",
    usage="/model <model-name>",
)
def model_cmd(_registry: CommandRegistry, args: str | None = None) -> None:
    """Switch the active LLM model for the current session."""
    from rich.console import Console
    console = Console()
    if not args:
        console.print("[yellow]Usage: /model <model-name> (e.g. /model qwen3:14b)[/]")
        return
    # Delegate to session context manager
    try:
        from ai_workspace.core.sessions import SessionManager
        mgr = SessionManager()
        mgr.set_active_model(args.strip())
        console.print(f"[green]Active model switched to: {args.strip()}[/]")
    except Exception as exc:
        console.print(f"[red]Failed to switch model: {exc}[/]")


@command(
    name="/research",
    description="Run deep research on a query",
    category="research",
    usage="/research <your query>",
)
def research_cmd(_registry: CommandRegistry, args: str | None = None) -> None:
    """Trigger a deep research run from the TUI."""
    from rich.console import Console
    console = Console()
    if not args:
        console.print("[yellow]Usage: /research <your research query>[/]")
        return
    console.print(f"[cyan] Researching:[/] {args}")
    # TODO: dispatch to research engine asynchronously
    console.print("[dim]Research dispatch — implement async execution[/]")


@command(
    name="/tasks",
    description="List all tasks with status",
    category="navigation",
)
def tasks_cmd(_registry: CommandRegistry, _args: str | None = None) -> None:
    """Display current tasks and their statuses."""
    from rich.console import Console
    from rich.table import Table
    console = Console()

    try:
        from ai_workspace.tasks import TaskManager
        mgr = TaskManager()
        tasks = mgr.list_tasks()
        table = Table(title=" Tasks", show_header=True)
        table.add_column("ID", style="dim")
        table.add_column("Name")
        table.add_column("Status")
        table.add_column("Priority")
        for t in tasks:
            table.add_row(str(t.id), t.name, t.status, t.priority)
        console.print(table)
    except Exception as exc:
        console.print(f"[yellow]Could not load tasks: {exc}[/]")
        console.print("[dim]Tasks may require a running database connection.[/]")


@command(
    name="/clear",
    description="Clear agent output area",
    category="navigation",
)
def clear_cmd(_registry: CommandRegistry, _args: str | None = None) -> None:
    """Clear the terminal screen."""
    import os
    import sys
    os.system("cls" if sys.platform == "win32" else "clear")


@command(
    name="/cost",
    description="Show token usage, cache stats, and budget",
    category="system",
)
def cost_cmd(_registry: CommandRegistry, _args: str | None = None) -> None:
    """Display LLM cost tracking, cache hit rates, and budget info."""
    from rich.console import Console
    from rich.table import Table
    console = Console()

    try:
        from ai_workspace.core.cost import CostService
        cost = CostService()
        cost.initialize()

        stats = cost.get_stats() if hasattr(cost, 'get_stats') else {}
        cache_stats = cost.cache.stats() if hasattr(cost, 'cache') else {}

        table = Table(title=" Cost & Usage", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value")

        total_cost = stats.get("total_cost", 0)
        total_tokens = stats.get("total_tokens", 0)
        table.add_row("Total Cost", f"${total_cost:.4f}")
        table.add_row("Total Tokens", f"{total_tokens:,}")

        if cache_stats:
            table.add_row("Cache Hits", str(cache_stats.get("hits", 0)))
            table.add_row("Cache Misses", str(cache_stats.get("misses", 0)))
            table.add_row("Cache Hit Rate", f"{cache_stats.get('hit_rate', 0):.1%}")

        console.print(table)

    except ImportError:
        console.print("[yellow]Cost tracking requires database connection.[/]")
    except Exception as exc:
        console.print(f"[dim]Cost stats unavailable: {exc}[/]")


@command(
    name="/quit",
    description="Exit the TUI",
    category="system",
    aliases=["/exit"],
)
def quit_cmd(_registry: CommandRegistry, _args: str | None = None) -> None:
    """Exit the application."""
    import sys
    sys.exit(0)


# ── New commands (from OpenSRE inspiration) ────────────────────────

@command(
    name="/sessions",
    description="List and manage active agent sessions",
    category="session",
)
def sessions_cmd(_registry: CommandRegistry, _args: str | None = None) -> None:
    """Show all active agent sessions with status."""
    from rich.console import Console
    from rich.table import Table
    console = Console()

    try:
        from ai_workspace.core.sessions import SessionManager
        mgr = SessionManager()
        sessions = mgr.list_sessions() if hasattr(mgr, 'list_sessions') else []

        table = Table(title=" Active Sessions", show_header=True)
        table.add_column("ID", style="dim")
        table.add_column("Agent")
        table.add_column("Model")
        table.add_column("Status")
        table.add_column("Duration")

        for s in sessions:
            table.add_row(
                str(s.get("id", "")),
                s.get("agent_name", ""),
                s.get("model", ""),
                s.get("status", ""),
                s.get("duration", ""),
            )

        if not sessions:
            console.print("[dim]No active sessions.[/]")
        else:
            console.print(table)

    except Exception as exc:
        console.print(f"[yellow]Session list unavailable: {exc}[/]")


@command(
    name="/resume",
    description="Restore a previous agent session",
    category="session",
    usage="/resume <session-id>",
)
def resume_cmd(_registry: CommandRegistry, args: str | None = None) -> None:
    """Resume a previous session by ID."""
    from rich.console import Console
    console = Console()

    if not args:
        console.print("[yellow]Usage: /resume <session-id>[/]")
        console.print("[dim]Use /sessions to list available sessions.[/]")
        return

    try:
        from ai_workspace.core.sessions import SessionManager
        mgr = SessionManager()
        mgr.restore_session(args.strip())
        console.print(f"[green]Session {args.strip()} restored.[/]")
    except Exception as exc:
        console.print(f"[red]Failed to restore session: {exc}[/]")


@command(
    name="/agents",
    description="Monitor local agent fleet (Claude Code, Codex, etc.)",
    category="system",
)
def agents_cmd(_registry: CommandRegistry, _args: str | None = None) -> None:
    """Scan for and display local coding agents running on this machine."""
    import shutil

    from rich.console import Console
    from rich.table import Table
    console = Console()

    agents_found: list[dict[str, str]] = []

    # Detect common coding agents on PATH
    agents_to_check = [
        ("Claude Code", "claude"),
        ("Codex CLI", "codex"),
        ("Cursor", "cursor"),
        ("OpenCode", "opencode"),
        ("Windsurf", "windsurf"),
        ("Qwen CLI", "qwen"),
    ]

    for name, cmd in agents_to_check:
        path = shutil.which(cmd)
        if path:
            agents_found.append({"name": name, "command": cmd, "path": path})

    if not agents_found:
        console.print("[dim]No supported coding agents detected on PATH.[/]")
        return

    table = Table(title=" Local Agent Fleet", show_header=True)
    table.add_column("Agent", style="cyan")
    table.add_column("Command", style="green")
    table.add_column("Path")

    for a in agents_found:
        table.add_row(a["name"], a["command"], a["path"])

    console.print(table)
    console.print()
    console.print("[dim]Tip: Use [/]/integrations verify[dim] to check connectivity.[/][/]")


@command(
    name="/integrations",
    description="List and verify connected integrations",
    category="system",
    usage="/integrations [list|verify]",
)
def integrations_cmd(_registry: CommandRegistry, args: str | None = None) -> None:
    """List or verify configured integrations (tools, providers, MCP servers).

    Uses IntegrationCatalog for auto-discovery across all integration types.
    Inspired by OpenSRE's integration catalog pattern.
    """
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    from ai_workspace.tools.integration_catalog import create_catalog
    console = Console()

    sub = (args or "list").strip().lower()

    if sub == "verify":
        console.print("[cyan]Verifying integrations...[/]")
        catalog = create_catalog()
        results = catalog.verify_all()
        table = Table(title=" Integration Status", show_header=True)
        table.add_column("Integration", style="cyan")
        table.add_column("Status")
        for name, status in results.items():
            table.add_row(name, status)
        if not results:
            console.print("[yellow]No configured integrations to verify.[/]")
        else:
            console.print(table)
        return

    # Default: list all integrations via catalog
    catalog = create_catalog()
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
    console.print("[dim]Use [/]/integrations verify[dim] to check connectivity.[/][/]")


@command(
    name="/effort",
    description="Set reasoning effort level (low|medium|high|max)",
    category="session",
    usage="/effort <low|medium|high|max>",
)
def effort_cmd(_registry: CommandRegistry, args: str | None = None) -> None:
    """Set the reasoning effort level for supported providers."""
    from rich.console import Console
    console = Console()

    valid_levels = {"low", "medium", "high", "max"}
    level = (args or "").strip().lower()

    if not level or level not in valid_levels:
        console.print(f"[yellow]Usage: /effort <{'|'.join(valid_levels)}>[/]")
        return

    try:
        from ai_workspace.core.sessions import SessionManager
        mgr = SessionManager()
        mgr.set_reasoning_effort(level)
        console.print(f"[green]Reasoning effort set to: {level}[/]")
    except Exception as exc:
        console.print(f"[red]Failed to set effort level: {exc}[/]")


@command(
    name="/status",
    description="Show system status (backend, model, database)",
    category="system",
)
def status_cmd(_registry: CommandRegistry, _args: str | None = None) -> None:
    """Display overall system health and active configuration."""
    import os

    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    console = Console()

    table = Table(show_header=False)
    table.add_column("Component", style="cyan")
    table.add_column("Status")

    # Backend status
    os.getenv("AIW_DB_URL", "postgresql:///ai_workspace")
    try:
        from ai_workspace.core.db import get_store
        store = get_store()
        store.initialize()
        table.add_row("Database", "[green]Connected[/]")
        store.close()
    except Exception:
        table.add_row("Database", "[yellow]Unavailable[/]")

    # Provider status
    try:
        from ai_workspace.providers import ProviderRegistry
        providers = ProviderRegistry()
        active = [n for n, c in providers.providers.items() if c.api_key]
        table.add_row("LLM Providers", f"{len(active)} active ({', '.join(active[:3])})")
    except Exception:
        table.add_row("LLM Providers", "[yellow]Unknown[/]")

    # Active model
    try:
        from ai_workspace.core.sessions import SessionManager
        mgr = SessionManager()
        model = mgr.get_active_model() if hasattr(mgr, 'get_active_model') else "unknown"
        table.add_row("Active Model", model)
    except Exception:
        table.add_row("Active Model", "[dim]unknown[/]")

    console.print(Panel(table, title=" System Status"))
