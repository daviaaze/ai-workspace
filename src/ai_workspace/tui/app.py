"""
AI Workspace TUI v3 — Clean chat-first interface with styled cards.

┌─ Header: aiw  ~/project  qwen3:14b  $0.005  20:50 ───────────────────┐
│                                                                       │
│  ┌─ Cache ────┐ ┌─ Budget ───┐ ┌─ Tasks ────┐ ┌─ Providers ────────┐ │
│  │ 10 entries │ │ $0.005 day │ │ 0/2 active │ │ ollama  deepseek   │ │
│  │ 31 hits    │ │ $0.006 mon │ │            │ │ gemini  openrouter │ │
│  └────────────┘ └────────────┘ └────────────┘ └────────────────────┘ │
│                                                                       │
│  ─── Output ──────────────────────────────────────────────────────── │
│                                                                       │
│  ▸ Type /search, /ask, /code, or just ask a question...               │
│                                                                       │
├───────────────────────────────────────────────────────────────────────┤
│  /search  /ask  /code  /git  /health  /help    Enter  ESC  Ctrl+Q    │
└───────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widgets import (
    Footer,
    Input,
    RichLog,
    Static,
)

log = logging.getLogger("aiw.tui")

# ═══════════════════════════════════════════════════════════════
# Stat Cards
# ═══════════════════════════════════════════════════════════════

class StatCard(Static):
    """A single metric card with border and icon."""

    def __init__(self, icon: str = "", title: str = "", **kwargs):
        super().__init__(**kwargs)
        self._icon = icon
        self._title = title
        self._lines: list[str] = []

    def set_lines(self, *lines: str) -> None:
        self._lines = list(lines)
        self.refresh()

    def render(self) -> RenderableType:
        content = "\n".join(self._lines) if self._lines else "[dim]—[/]"
        return Panel(
            content,
            title=f"{self._icon} {self._title}",
            border_style="#444444",
            padding=(0, 1),
        )


# ═══════════════════════════════════════════════════════════════
# Main App
# ═══════════════════════════════════════════════════════════════

class AIWorkspaceApp(App):
    """AI Workspace — terminal operations center."""

    TITLE = "AI Workspace"
    SUB_TITLE = "v0.1.0"

    CSS = """
    Screen {
        layout: vertical;
        background: #1a1a2e;
    }

    #header-bar {
        height: 1;
        padding: 0 2;
        background: #16213e;
    }

    #header-bar .logo {
        color: #0f3460;
        text-style: bold;
    }
    #header-bar .path {
        color: #58d1eb;
    }
    #header-bar .info {
        color: #888888;
    }

    #cards-grid {
        height: auto;
        padding: 1 1 0 1;
        grid-size: 4;
        grid-columns: 1fr 1fr 1fr 1fr;
        grid-gutter: 1;
        background: #1a1a2e;
    }

    StatCard {
        height: auto;
        border: none;
        background: #1a1a2e;
    }

    #output-area {
        height: 1fr;
        padding: 1;
        background: #1a1a2e;
    }

    #output-log {
        height: 1fr;
        border: solid #333355;
        background: #0f0f23;
    }

    #input-area {
        height: auto;
        padding: 0 1 1 1;
        background: #1a1a2e;
    }

    #main-input {
        width: 1fr;
        background: #0f0f23;
        border: solid #333355;
    }
    #main-input:focus {
        border: solid #0178d4;
    }

    #help-bar {
        height: 1;
        padding: 0 2;
        background: #16213e;
        color: #666688;
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
        self._metrics: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        # Header
        yield Static("", id="header-bar")

        # Stat cards row
        with Grid(id="cards-grid"):
            yield StatCard("📦", "Cache", id="card-cache")
            yield StatCard("💰", "Budget", id="card-budget")
            yield StatCard("📋", "Tasks", id="card-tasks")
            yield StatCard("🔌", "Providers", id="card-providers")

        # Output area
        with VerticalScroll(id="output-area"):
            yield RichLog(id="output-log", highlight=True, markup=True, wrap=True, max_lines=500)

        # Input
        with Horizontal(id="input-area"):
            yield Input(placeholder="Type /search, /ask, /code, or ask a question...", id="main-input")

        # Help bar
        yield Static(
            "[search] research  [ask] chat  [code] coding  [git] git  [health] system  [help] commands",
            id="help-bar",
        )

    def on_mount(self) -> None:
        self._load_data()
        self.set_interval(60, self._load_data)
        self.query_one("#main-input", Input).focus()

        output = self.query_one("#output-log", RichLog)
        output.write("[bold #58d1eb]AI Workspace v0.1.0[/]")
        output.write("[#888888]Ready. Type a command or question.[/]")

    def _load_data(self) -> None:
        """Load system status from DB."""
        try:
            from ai_workspace.tui.data import load_metrics
            self._metrics = load_metrics()
        except Exception:
            self._metrics = {}

        m = self._metrics

        # Header
        import os
        home = os.path.expanduser("~")
        cwd = self._cwd
        if cwd.startswith(home):
            cwd = "~" + cwd[len(home):]
        if len(cwd) > 30:
            cwd = "…" + cwd[-29:]
        now = datetime.now().strftime("%H:%M")
        self.query_one("#header-bar", Static).update(
            f"[bold #0f3460]aiw[/]  [#58d1eb]{cwd}[/]  [#888888]{self._model}  ${m.get('today_cost', 0):.3f}  {now}"
        )

        # Cache card
        self.query_one("#card-cache", StatCard).set_lines(
            f"[bold]{m.get('cache_entries', 0)}[/] entries",
            f"{m.get('cache_hits', 0)} hits",
            f"{m.get('tokens_saved', 0):,} tokens saved",
        )

        # Budget card
        self.query_one("#card-budget", StatCard).set_lines(
            f"[bold #ff9100]${m.get('today_cost', 0):.4f}[/] today",
            f"[#888888]${m.get('month_cost', 0):.4f}[/] month",
            f"limit $1.00 / $10.00",
        )

        # Tasks card
        self.query_one("#card-tasks", StatCard).set_lines(
            f"[bold]{m.get('tasks_active', 0)}[/] active",
            f"{m.get('tasks_total', 0)} total",
            f"{m.get('memories', 0)} memories",
        )

        # Providers card
        try:
            from ai_workspace.agents.router import get_router
            router = get_router()
            avail = router.check_availability_sync()
        except Exception:
            avail = {"ollama": True}

        def icon(ok): return "[#43a047]●[/]" if ok else "[#e53935]○[/]"
        self.query_one("#card-providers", StatCard).set_lines(
            f"{icon(avail.get('ollama', False))} ollama  {icon(avail.get('deepseek', False))} deepseek",
            f"{icon(avail.get('gemini', False))} gemini  {icon(avail.get('openrouter', False))} openrtr",
        )

    # ═══════════════════════════════════════════════════════════
    # Input handling
    # ═══════════════════════════════════════════════════════════

    @on(Input.Submitted, "#main-input")
    async def on_input(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        event.input.value = ""
        output = self.query_one("#output-log", RichLog)
        output.write(f"\n[bold]▸[/] {text}")

        if text.startswith("/"):
            await self._handle_slash(text, output)
        else:
            await self._handle_chat(text, output)

    async def _handle_slash(self, text: str, out: RichLog) -> None:
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        handlers = {
            "/help": lambda: out.write(self._help_text()),
            "/health": lambda: self._cmd_health(out),
            "/search": lambda: self._cmd_search(arg, out),
            "/ask": lambda: self._cmd_ask(arg, out),
            "/code": lambda: self._cmd_code(arg, out),
            "/git": lambda: self._cmd_git(out),
            "/model": lambda: self._cmd_model(arg, out),
            "/clear": lambda: out.clear(),
        }

        if cmd in handlers:
            await handlers[cmd]() if asyncio.iscoroutinefunction(handlers[cmd]) else handlers[cmd]()
        else:
            out.write(f"[#ff9100]Unknown: {cmd}[/] — [dim]/help for commands[/]")

    # ═══════════════════════════════════════════════════════════
    # Commands
    # ═══════════════════════════════════════════════════════════

    def _help_text(self) -> str:
        return """[bold #58d1eb]Commands[/]
[bold]/search <q>[/]  Deep research
[bold]/ask <q>[/]     Chat with LLM
[bold]/code <task>[/]  Coding agent
[bold]/git[/]          Git status
[bold]/health[/]       System health
[bold]/model <name>[/] Switch model
[bold]/clear[/]        Clear output
[bold]/help[/]         This help

[bold #888888]Keys:[/] Ctrl+Q quit | Esc clear"""

    async def _cmd_health(self, out: RichLog) -> None:
        m = self._metrics
        out.write(f"📦 Cache: {m.get('cache_entries',0)}e / {m.get('cache_hits',0)} hits")
        out.write(f"💰 Today: ${m.get('today_cost',0):.4f} | Month: ${m.get('month_cost',0):.4f}")
        out.write(f"🔍 Sources: {m.get('source_domains',0)} domains")
        out.write(f"📋 Tasks: {m.get('tasks_active',0)}/{m.get('tasks_total',0)}")
        out.write(f"🗄️ DB: {'connected' if m.get('db_connected') else 'disconnected'}")

    async def _cmd_search(self, query: str, out: RichLog) -> None:
        if not query:
            out.write("[#ff9100]Usage: /search <query>[/]"); return
        out.write(f"[#58d1eb]🔍 {query}[/]")
        try:
            from ai_workspace.search.deep_search import DeepSearchEngine
            engine = DeepSearchEngine(max_depth=2)
            result = await engine.research(query)
            if result.summary:
                out.write(f"[#43a047]📝 {result.summary[:600]}[/]")
            if result.sources:
                out.write(f"[#888888]{len(result.sources)} sources, confidence {result.confidence:.0%}[/]")
        except Exception as e:
            out.write(f"[#e53935]Search failed: {e}[/]")

    async def _cmd_ask(self, question: str, out: RichLog) -> None:
        if not question:
            out.write("[#ff9100]Usage: /ask <question>[/]"); return
        await self._handle_chat(question, out)

    async def _cmd_code(self, task: str, out: RichLog) -> None:
        if not task:
            out.write("[#ff9100]Usage: /code <task>[/]"); return
        out.write(f"[#58d1eb]💻 {task}[/]")
        out.write("[#ff9100]⚠ Coding agent not yet available here.[/]")
        out.write("[#888888]Use: aiw code <task>[/]")

    async def _cmd_git(self, out: RichLog) -> None:
        import subprocess
        try:
            r = subprocess.run(["git", "status", "--branch", "--short"], capture_output=True,
                             text=True, cwd=self._cwd, timeout=5)
            if r.returncode == 0:
                out.write(r.stdout.strip() or "(clean)")
            else:
                out.write("[#888888]Not a git repository.[/]")
        except Exception:
            out.write("[#888888]Git unavailable.[/]")

    def _cmd_model(self, name: str, out: RichLog) -> None:
        if name:
            self._model = name
        out.write(f"[#43a047]Model: {self._model}[/]")

    async def _handle_chat(self, text: str, out: RichLog) -> None:
        try:
            from ai_workspace.core.cost import CostService
            cost = CostService(); cost.initialize()
            cached = cost.cache.get(text, "chat")
            if cached:
                out.write(f"[#888888]⚡ cache ({cached['similarity']:.0%})[/]")
                out.write(cached["response_text"][:1500])
                return
        except Exception:
            pass

        try:
            from ai_workspace.providers import chat_sync
            response = chat_sync([{"role": "user", "content": text}],
                               provider="ollama", model=self._model)
            out.write(response[:2000])
        except Exception as e:
            out.write(f"[#e53935]{e}[/]")

    def action_clear_input(self) -> None:
        try:
            self.query_one("#main-input", Input).value = ""
        except NoMatches:
            pass


def run_tui():
    import sys
    app = AIWorkspaceApp()
    try:
        app.run()
    except SystemExit:
        pass
    except Exception as e:
        print(f"TUI crashed: {e}", file=sys.stderr)
        import traceback; traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_tui()
