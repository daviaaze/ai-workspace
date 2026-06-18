"""
AI Workspace TUI v3 — Chat-first with slash commands.

Design principles (from tui-design skill):
1. Discoverability — slash commands always visible in help bar
2. Simplicity — one screen, no tabs overload
3. Safety — confirm destructive actions
4. Keyboard-first — everything via keys
5. Reactive — state changes auto-update UI

Architecture:
┌─ Header: workspace, model, cost, time ──────────────────────────┐
│                                                                  │
│  Status: cache, budget, sources, providers                       │
│                                                                  │
│  ▸ Type a slash command or question...                           │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│  /search  /ask  /code  /git  /health  /help    Enter  Ctrl+Q    │
└──────────────────────────────────────────────────────────────────┘

Slash commands:
  /search <query>  — Deep research
  /ask <question>  — Quick chat with LLM
  /code <task>     — Coding agent
  /git             — Git status overlay
  /health          — System health check
  /help            — Show all commands

Any other text is sent as chat to the LLM.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widgets import (
    Footer,
    Input,
    Label,
    RichLog,
    Static,
)

log = logging.getLogger("aiw.tui")

# ═══════════════════════════════════════════════════════════════
# Main App
# ═══════════════════════════════════════════════════════════════

class AIWorkspaceApp(App):
    """AI Workspace — chat-first terminal interface."""

    TITLE = "AI Workspace"
    SUB_TITLE = "v0.1.0"

    CSS = """
    Screen {
        layout: vertical;
    }

    #header {
        height: 1;
        padding: 0 2;
        background: $panel;
        border-bottom: solid $primary-background;
    }

    #header > Label {
        height: 1;
    }

    #status-area {
        height: auto;
        max-height: 12;
        padding: 1 2;
        background: $background;
        border-bottom: solid $primary-background;
        overflow: hidden hidden;
    }

    #output-area {
        height: 1fr;
        background: $background;
        border-bottom: solid $primary-background;
    }

    #output-area RichLog {
        height: 1fr;
        border: none;
        background: $background;
    }

    #input-area {
        height: auto;
        padding: 1 2;
        background: $panel;
        border-bottom: solid $primary-background;
    }

    #input-area Label {
        height: 1;
        padding: 0 0 0 1;
    }

    #main-input {
        width: 1fr;
        background: $surface;
    }

    #help-bar {
        height: 1;
        padding: 0 2;
        background: $boost;
        color: #888888;
    }

    Footer {
        display: none;
    }
    """

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("escape", "clear_input", "Clear"),
    ]

    def __init__(self):
        super().__init__()
        self._cwd = str(Path.cwd())
        self._model = "qwen3:14b"
        self._provider = "ollama"
        self._metrics: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        """Build the chat-first layout."""
        # Header
        yield Static(self._render_header(), id="header")

        # Status area (cache, budget, sources, providers)
        with VerticalScroll(id="status-area"):
            yield Static("Loading...", id="status-content")

        # Output area (responses)
        with Container(id="output-area"):
            yield RichLog(id="output-log", highlight=True, markup=True, wrap=True)

        # Input area
        with Horizontal(id="input-area"):
            yield Label("▸ ", id="input-prompt")
            yield Input(placeholder="Type a slash command or question...", id="main-input")

        # Help bar
        yield Static(
            "[search] research  [ask] chat  [code] coding  [git] git  [health] system  [help] commands",
            id="help-bar",
        )

    def on_mount(self) -> None:
        """Load initial data and set up timers."""
        self._load_status()
        self.set_interval(60, self._load_status)

        # Focus the input
        try:
            self.query_one("#main-input", Input).focus()
        except NoMatches:
            pass

        # Welcome message
        output = self.query_one("#output-log", RichLog)
        output.write("[bold cyan]AI Workspace v0.1.0[/]")
        output.write("[dim]Type a slash command or question to get started.[/]")
        output.write("")

    def _render_header(self) -> Text:
        """Render the top header line."""
        import os
        home = os.path.expanduser("~")
        cwd = self._cwd
        if cwd.startswith(home):
            cwd = "~" + cwd[len(home):]
        if len(cwd) > 35:
            cwd = "…" + cwd[-34:]

        now = datetime.now().strftime("%H:%M")

        return Text.from_markup(
            f"[bold #0178d4]aiw[/]  "
            f"[#58d1eb]{cwd}[/]  "
            f"[dim]{self._model}[/]  "
            f"[dim]{now}[/]"
        )

    def _load_status(self) -> None:
        """Load system status from DB (runs in background)."""
        try:
            from ai_workspace.tui.data import load_metrics

            self._metrics = load_metrics()

            # Detect available providers
            try:
                from ai_workspace.agents.router import get_router
                router = get_router()
                avail = router.check_availability_sync()
            except Exception:
                avail = {"ollama": True}

            provider_icons = {
                "ollama": "🟢" if avail.get("ollama") else "🔴",
                "deepseek": "🟢" if avail.get("deepseek") else "🔴",
                "gemini": "🟢" if avail.get("gemini") else "🔴",
                "openrouter": "🟢" if avail.get("openrouter") else "⚪",
            }

            status = Text.from_markup(
                f"[bold]System Status[/]\n\n"
                f"📦 [bold]Cache:[/] {self._metrics.get('cache_entries', 0)} entries"
                f" | {self._metrics.get('cache_hits', 0)} hits"
                f" | {self._metrics.get('tokens_saved', 0):,} tokens saved\n"
                f"💰 [bold]Budget:[/] ${self._metrics.get('today_cost', 0):.3f} today"
                f" | ${self._metrics.get('month_cost', 0):.3f} month\n"
                f"🔍 [bold]Sources:[/] {self._metrics.get('source_domains', 0)} domains\n"
                f"🔌 [bold]Providers:[/] "
                f"{provider_icons['ollama']} ollama  "
                f"{provider_icons['deepseek']} deepseek  "
                f"{provider_icons['gemini']} gemini  "
                f"{provider_icons['openrouter']} openrouter\n"
                f"📋 [bold]Tasks:[/] {self._metrics.get('tasks_active', 0)} active"
                f" / {self._metrics.get('tasks_total', 0)} total"
            )

            self.query_one("#status-content", Static).update(status)
        except Exception as e:
            log.warning("Status load failed: %s", e)
            self.query_one("#status-content", Static).update(
                f"[dim]System status unavailable: {e}[/]"
            )

    # ═══════════════════════════════════════════════════════════
    # Input handling
    # ═══════════════════════════════════════════════════════════

    @on(Input.Submitted, "#main-input")
    async def on_input(self, event: Input.Submitted) -> None:
        """Handle user input — route to slash command or chat."""
        text = event.value.strip()
        if not text:
            return

        event.input.value = ""
        output = self.query_one("#output-log", RichLog)

        # Echo user input
        output.write(f"\n▸ [bold]{text}[/]")

        # Route to handler
        if text.startswith("/"):
            await self._handle_slash(text, output)
        else:
            await self._handle_chat(text, output)

    async def _handle_slash(self, text: str, output: RichLog) -> None:
        """Handle slash commands."""
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd == "/help":
            output.write(self._help_text())
        elif cmd == "/health":
            await self._cmd_health(output)
        elif cmd == "/search":
            await self._cmd_search(arg, output)
        elif cmd == "/ask":
            await self._cmd_ask(arg, output)
        elif cmd == "/code":
            await self._cmd_code(arg, output)
        elif cmd == "/git":
            await self._cmd_git(output)
        elif cmd == "/model":
            self._model = arg or "qwen3:14b"
            output.write(f"[green]Model switched to: {self._model}[/]")
            self.query_one("#header", Static).update(self._render_header())
        elif cmd == "/files":
            await self._cmd_files(output)
        elif cmd == "/clear":
            output.clear()
        else:
            output.write(f"[yellow]Unknown command: {cmd}[/]")
            output.write("[dim]Type /help to see available commands.[/]")

    async def _handle_chat(self, text: str, output: RichLog) -> None:
        """Send message to LLM and stream response."""
        output.write("[dim]Thinking...[/]")
        try:
            response = await self._call_llm(text)
            output.write(response)
        except Exception as e:
            output.write(f"[red]Error: {e}[/]")

    # ═══════════════════════════════════════════════════════════
    # Slash command implementations
    # ═══════════════════════════════════════════════════════════

    def _help_text(self) -> str:
        return """[bold]Slash Commands[/]

[bold cyan]/search <query>[/]  Deep research on a topic
[bold cyan]/ask <question>[/]  Quick chat with LLM
[bold cyan]/code <task>[/]     Run autonomous coding agent
[bold cyan]/git[/]             Show git status
[bold cyan]/health[/]          System health check
[bold cyan]/model <name>[/]    Switch LLM model
[bold cyan]/files[/]           List files in workspace
[bold cyan]/clear[/]           Clear output
[bold cyan]/help[/]            Show this help

[bold]Keybindings[/]
Ctrl+Q             Quit
Esc                Clear input"""

    async def _cmd_health(self, output: RichLog) -> None:
        """Show system health."""
        from ai_workspace.tui.data import load_metrics
        m = load_metrics()

        output.write(f"[bold]🩺 System Health[/]")
        output.write(f"  📦 Cache: {m['cache_entries']} entries, {m['cache_hits']} hits")
        output.write(f"  💰 Today: ${m['today_cost']:.4f} / $1.00")
        output.write(f"  💰 Month: ${m['month_cost']:.4f} / $10.00")
        output.write(f"  🔍 Sources: {m['source_domains']} domains tracked")
        output.write(f"  📋 Tasks: {m['tasks_active']} active / {m['tasks_total']} total")
        output.write(f"  🗄️ DB: {'connected' if m.get('db_connected') else 'disconnected'}")

    async def _cmd_search(self, query: str, output: RichLog) -> None:
        """Run deep research."""
        if not query:
            output.write("[yellow]Usage: /search <query>[/]")
            return

        output.write(f"[cyan]🔍 Researching: {query}[/]")
        output.write("[dim]This may take a minute...[/]")

        try:
            from ai_workspace.search.deep_search import DeepSearchEngine
            engine = DeepSearchEngine(max_depth=2)
            result = await engine.research(query)

            if result.summary:
                output.write(f"[green]📝 Summary:[/] {result.summary[:500]}")
            if result.sources:
                output.write(f"[dim]Sources: {len(result.sources)} total[/]")
                for s in result.sources[:5]:
                    output.write(f"  • {s[:80]}")
            output.write(f"[dim]Confidence: {result.confidence:.0%}[/]")
        except Exception as e:
            output.write(f"[red]Search failed: {e}[/]")

    async def _cmd_ask(self, question: str, output: RichLog) -> None:
        """Quick chat with LLM."""
        if not question:
            output.write("[yellow]Usage: /ask <question>[/]")
            return

        await self._handle_chat(question, output)

    async def _cmd_code(self, task: str, output: RichLog) -> None:
        """Run coding agent."""
        if not task:
            output.write("[yellow]Usage: /code <task description>[/]")
            return

        output.write(f"[cyan]💻 Coding: {task}[/]")
        output.write("[dim]Running autonomous coding agent...[/]")
        output.write("[yellow]⚠ Coding agent not yet available in TUI mode.[/]")
        output.write("[dim]Use 'aiw code <task>' from the terminal instead.[/]")

    async def _cmd_git(self, output: RichLog) -> None:
        """Show git status."""
        import subprocess
        try:
            result = subprocess.run(
                ["git", "status", "--branch", "--short"],
                capture_output=True, text=True,
                cwd=self._cwd, timeout=5,
            )
            if result.returncode == 0:
                out = result.stdout.strip() or "(clean)"
                output.write(f"[bold] Git Status[/]\n{out[:1000]}")
            else:
                output.write("[dim]Not a git repository.[/]")
        except Exception as e:
            output.write(f"[dim]Git unavailable: {e}[/]")

    async def _cmd_files(self, output: RichLog) -> None:
        """List files in workspace."""
        import os
        try:
            items = sorted(os.listdir(self._cwd))[:30]
            for item in items:
                path = os.path.join(self._cwd, item)
                icon = "📁" if os.path.isdir(path) else "📄"
                output.write(f"  {icon} {item}")
            if len(items) == 30:
                output.write(f"  [dim]... and more[/]")
        except Exception as e:
            output.write(f"[dim]Cannot list files: {e}[/]")

    async def _call_llm(self, text: str) -> str:
        """Call the LLM and return response."""
        from ai_workspace.providers import ProviderRegistry, chat_sync

        # Check semantic cache first
        try:
            from ai_workspace.core.cost import CostService
            cost = CostService()
            cost.initialize()
            cached = cost.cache.get(text, "chat")
            if cached:
                return (
                    f"[dim]⚡ Cache hit (similarity: {cached['similarity']:.0%})[/]\n"
                    f"{cached['response_text'][:1000]}"
                )
        except Exception:
            pass

        # Call LLM
        messages = [{"role": "user", "content": text}]
        try:
            response = chat_sync(
                messages,
                provider=self._provider,
                model=self._model,
            )
            return response[:2000]
        except Exception as e:
            return f"[red]LLM call failed: {e}[/]"

    def action_clear_input(self) -> None:
        """Clear the input field."""
        try:
            self.query_one("#main-input", Input).value = ""
        except NoMatches:
            pass


def run_tui():
    """Entry point for `aiw tui` command."""
    import sys
    app = AIWorkspaceApp()
    try:
        app.run()
    except SystemExit:
        pass
    except Exception as e:
        print(f"TUI crashed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_tui()
