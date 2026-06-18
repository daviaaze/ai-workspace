"""
AI Workspace TUI v4 — Cyberpunk Agent Grid
Multi-panel terminal interface with neon theme, agent management,
knowledge navigation, and LLM chat.

╭─[ AI WORKSPACE ]──[ ~/project ]──[ qwen3:14b ]──[ $0.005 ]──╮
│  ╭─ Agents ───────────╮ ╭─ Context/KB ────────╮             │
│  │ 🟢 coding-agent    │ │ 📄 auth-pattern     │             │
│  │ 🟡 research-agent  │ │ 📄 MCP tools        │             │
│  ╰────────────────────╯ ╰─────────────────────╯             │
│  ╭─ Canvas/Diagram ───╮ ╭─ Chat ─────────────╮             │
│  │   ASCII diagrams   │ │ ▸ /search query     │             │
│  │                    │ │ 🤖 Response...      │             │
│  ╰────────────────────╯ ╰─────────────────────╯             │
├─────────────────────────────────────────────────────────────┤
│ 1.Agents 2.KB 3.Canvas 4.Chat 5.Tasks 6.Help  TAB  ^Q     │
╰─────────────────────────────────────────────────────────────╯
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Container, Grid, Horizontal, Vertical, VerticalScroll
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
# Cyberpunk Theme
# ═══════════════════════════════════════════════════════════════

CYBERPUNK_THEME = {
    "name": "cyberpunk",
    "dark": True,
    "primary": "#00f3ff",       # neon cyan
    "secondary": "#ff00ff",     # neon magenta
    "accent": "#00ff88",        # neon green
    "error": "#ff3355",         # hot red
    "warning": "#ffaa00",       # amber
    "success": "#00ff88",       # neon green
    "background": "#0a0a0f",    # deep void
    "surface": "#0d0d1a",      # dark blue-black
    "panel": "#111122",         # panel bg
    "boost": "#1a1a33",        # elevated
    "text": "#c0c0d0",         # silver text
    "text-muted": "#666688",
}


class NeonBorder:
    """ASCII art borders in cyberpunk style."""

    TOP_LEFT = "╭"
    TOP_RIGHT = "╮"
    BOTTOM_LEFT = "╰"
    BOTTOM_RIGHT = "╯"
    HORIZ = "─"
    VERT = "│"
    ACTIVE_HORIZ = "━"
    ACTIVE_VERT = "┃"

    @staticmethod
    def panel(title: str, content: str, active: bool = False, width: int = 40) -> str:
        h = NeonBorder.ACTIVE_HORIZ if active else NeonBorder.HORIZ
        v = NeonBorder.ACTIVE_VERT if active else NeonBorder.VERT
        tl = NeonBorder.TOP_LEFT
        tr = NeonBorder.TOP_RIGHT
        bl = NeonBorder.BOTTOM_LEFT
        br = NeonBorder.BOTTOM_RIGHT

        top = f"{tl}[{title}]{h * (width - len(title) - 2)}{tr}"
        lines = [top]
        for line in content.split("\n")[:12]:
            lines.append(f"{v} {line:<{width-2}} {v}")
        lines.append(f"{bl}{h * width}{br}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# Panel Widgets
# ═══════════════════════════════════════════════════════════════

class PanelBase(Vertical, can_focus=True):
    """Base class for focusable panels with neon border."""

    active: reactive[bool] = reactive(False)

    DEFAULT_CSS = """
    PanelBase {
        height: 1fr;
        border: solid #222244;
        background: #0d0d1a;
    }
    PanelBase:focus {
        border: solid #00f3ff;
    }
    PanelBase.-active {
        border: solid #00ff88;
    }
    """

    def on_focus(self) -> None:
        self.active = True
        self.add_class("-active")

    def on_blur(self) -> None:
        self.active = False
        self.remove_class("-active")


class AgentsPanel(PanelBase):
    """Shows running agents with MCPs, skills, and tasks."""

    def compose(self) -> ComposeResult:
        yield Static("No agents spawned yet.\nPress [S] to spawn.", id="agents-content")

    def update_agents(self, agents: list[dict]) -> None:
        lines = []
        if not agents:
            lines = ["[#666688]No agents spawned.[/]",
                     "[#666688]Use 'aiw agent <task>' from CLI[/]",
                     "[#666688]or type /spawn <type> <task>[/]"]
        else:
            for a in agents:
                status_icon = {"running": "[#00ff88]●[/]", "paused": "[#ffaa00]●[/]",
                               "error": "[#ff3355]●[/]", "idle": "[#666688]○[/]"}.get(
                    a.get("status", "idle"), "○")
                name = a.get("name", "agent")[:20]
                task = a.get("task", "")[:25]
                progress = a.get("progress", 0)
                bar = "█" * (progress // 10) + "░" * (10 - progress // 10)
                skills = ", ".join(a.get("skills", [])[:3]) or "none"
                mcps = ", ".join(a.get("mcps", [])[:3]) or "none"

                lines.append(f"{status_icon} [#00f3ff]{name}[/]")
                lines.append(f"   MCPs: [#888888]{mcps}[/]")
                lines.append(f"   Skills: [#888888]{skills}[/]")
                lines.append(f"   Task: {task} [{bar}] {progress}%")
                lines.append("")

        self.query_one("#agents-content", Static).update("\n".join(lines) if lines else "[#666688]No agents.[/]")


class KBPanel(PanelBase):
    """Knowledge base browser — memories, research, patterns."""

    def compose(self) -> ComposeResult:
        yield Static("[#666688]Loading knowledge base...[/]", id="kb-content")

    def load_kb(self) -> None:
        try:
            from ai_workspace.tui.data import load_metrics
            m = load_metrics()
            entries = []

            # Load from memory files
            import os as _os
            ws = Path(_os.environ.get("AIW_WORKSPACE",
                        Path.home() / "Projects" / "pessoal" / "ai-workspace"))
            learning = ws / "memory" / "learning-log.md"
            if learning.exists():
                content = learning.read_text()
                sections = [s.strip() for s in content.split("\n## ") if s.strip()]
                for s in sections[1:8]:
                    title = s.split("\n")[0][:50]
                    entries.append(f"[#ff00ff]💭[/] {title}")

            lines = [
                f"[#00f3ff]📦[/] Cache: {m.get('cache_entries',0)}e / {m.get('cache_hits',0)} hits",
                f"[#00f3ff]🔍[/] Sources: {m.get('source_domains',0)} domains",
                f"[#00f3ff]🧠[/] Memories: {m.get('memories',0)} total",
                "",
            ]
            if entries:
                lines.append("[#00ff88]Recent:[/]")
                lines.extend(entries[:6])

            self.query_one("#kb-content", Static).update("\n".join(lines))
        except Exception as e:
            self.query_one("#kb-content", Static).update(f"[#ff3355]KB load failed: {e}[/]")


class CanvasPanel(PanelBase):
    """Simple ASCII canvas for diagrams and system overview."""

    def compose(self) -> ComposeResult:
        yield Static(self._render_default(), id="canvas-content")

    def _render_default(self) -> str:
        return """[#00f3ff]System Architecture[/]

  ┌──────────┐     ┌──────────┐
  │ [#ff00ff]Ollama[/]  │────▶│ [#00ff88]Router[/]   │
  └──────────┘     └────┬─────┘
                        │
       ┌────────────────┼────────────────┐
       ▼                ▼                ▼
  ┌─────────┐    ┌──────────┐    ┌──────────┐
  │[#ffaa00]DeepSeek[/]│    │[#ff00ff]Gemini[/]   │    │[#00f3ff]OpenRtr[/]  │
  └─────────┘    └──────────┘    └──────────┘

  [#666688]All providers online[/]"""

    def update_diagram(self, text: str) -> None:
        self.query_one("#canvas-content", Static).update(text)


class ChatPanel(PanelBase):
    """Chat interface with LLM."""

    def compose(self) -> ComposeResult:
        yield RichLog(id="chat-log", highlight=True, markup=True, wrap=True, max_lines=200)
        yield Input(placeholder="Type /search, /ask, or ask anything...", id="chat-input")

    def on_mount(self) -> None:
        self.query_one("#chat-log", RichLog).write("[#00f3ff]AI Workspace v0.2.0[/]")
        self.query_one("#chat-log", RichLog).write("[#666688]Ready. Type a command or question.[/]")

    @on(Input.Submitted, "#chat-input")
    async def on_chat_input(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        event.input.value = ""
        log = self.query_one("#chat-log", RichLog)
        log.write(f"\n[#00f3ff]▸[/] {text}")

        if text.startswith("/"):
            await self._handle_command(text, log)
        else:
            await self._chat(text, log)

    async def _handle_command(self, text: str, log: RichLog) -> None:
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd == "/help":
            log.write("""[#00ff88]Commands[/]
[#00f3ff]/search <q>[/]   Deep research
[#00f3ff]/ask <q>[/]      Chat with LLM
[#00f3ff]/code <t>[/]     Coding agent (CLI)
[#00f3ff]/git[/]          Git status
[#00f3ff]/health[/]       System health  
[#00f3ff]/spawn <t>[/]    Spawn agent type
[#00f3ff]/clear[/]        Clear chat
[#00f3ff]/help[/]         This help
[#666688]Keys:[/] 1-4 panels  TAB cycle  ^Q quit""")
        elif cmd == "/health":
            try:
                from ai_workspace.tui.data import load_metrics
                m = load_metrics()
                log.write(f"[#00ff88]📦[/] Cache: {m['cache_entries']}e / {m['cache_hits']} hits / {m['tokens_saved']:,}t saved")
                log.write(f"[#00ff88]💰[/] Budget: ${m['today_cost']:.4f} today / ${m['month_cost']:.4f} month")
                log.write(f"[#00ff88]🔍[/] Sources: {m['source_domains']} domains")
                log.write(f"[#00ff88]🗄️[/] DB: {'connected' if m.get('db_connected') else 'offline'}")
            except Exception as e:
                log.write(f"[#ff3355]{e}[/]")
        elif cmd == "/search":
            if not arg:
                log.write("[#ffaa00]Usage: /search <query>[/]"); return
            log.write(f"[#00f3ff]🔍 Researching: {arg}[/]")
            try:
                from ai_workspace.search.deep_search import DeepSearchEngine
                engine = DeepSearchEngine(max_depth=2)
                result = await engine.research(arg)
                if result.summary:
                    log.write(f"[#00ff88]📝 {result.summary[:500]}[/]")
                log.write(f"[#666688]{len(result.sources)} sources, {result.confidence:.0%} confidence[/]")
            except Exception as e:
                log.write(f"[#ff3355]Search failed: {e}[/]")
        elif cmd == "/git":
            try:
                r = subprocess.run(["git", "status", "--branch", "--short"],
                                 capture_output=True, text=True, timeout=5)
                log.write(r.stdout.strip() or "[#666688](clean)[/]")
            except Exception:
                log.write("[#666688]Git unavailable[/]")
        elif cmd == "/clear":
            log.clear()
        else:
            log.write(f"[#ffaa00]Unknown: {cmd}[/] — /help for commands")

    async def _chat(self, text: str, log: RichLog) -> None:
        try:
            from ai_workspace.core.cost import CostService
            cost = CostService(); cost.initialize()
            cached = cost.cache.get(text, "chat")
            if cached:
                log.write(f"[#666688]⚡ cache ({cached['similarity']:.0%})[/]")
                log.write(cached["response_text"][:1500])
                return
        except Exception:
            pass

        try:
            from ai_workspace.providers import chat_sync
            response = chat_sync([{"role": "user", "content": text}],
                               provider="ollama", model="qwen3:14b")
            log.write(response[:2000])
        except Exception as e:
            log.write(f"[#ff3355]{e}[/]")


# ═══════════════════════════════════════════════════════════════
# Main App
# ═══════════════════════════════════════════════════════════════

class AIWorkspaceApp(App):
    """Cyberpunk Agent Grid — multi-panel AI workspace."""

    TITLE = "AI Workspace"
    SUB_TITLE = "v0.2.0"

    CSS = """
    Screen {
        layout: vertical;
        background: #0a0a0f;
    }

    #header {
        height: 1;
        padding: 0 2;
        background: #0d0d1a;
        border-bottom: solid #00f3ff;
    }

    #main-grid {
        height: 1fr;
        padding: 1;
        grid-size: 2;
        grid-columns: 1fr 1fr;
        grid-rows: 1fr 1fr;
        grid-gutter: 1 2;
        background: #0a0a0f;
    }

    #status-bar {
        height: 1;
        padding: 0 2;
        background: #0d0d1a;
        border-top: solid #00f3ff;
        color: #666688;
    }

    /* Panel borders */
    PanelBase {
        border: solid #222244;
    }
    PanelBase:focus {
        border: solid #00f3ff;
    }
    PanelBase.-active {
        border: solid #00ff88;
    }

    /* Chat panel inner elements */
    ChatPanel RichLog {
        height: 1fr;
        border: none;
        background: #0d0d1a;
    }
    ChatPanel Input {
        height: 3;
        background: #111122;
        border: solid #222244;
    }
    ChatPanel Input:focus {
        border: solid #00f3ff;
    }

    Footer {
        display: none;
    }
    """

    BINDINGS = [
        ("1", "focus_panel('agents')", "Agents"),
        ("2", "focus_panel('kb')", "KB"),
        ("3", "focus_panel('canvas')", "Canvas"),
        ("4", "focus_panel('chat')", "Chat"),
        ("tab", "cycle_focus", "Next"),
        ("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self._cwd = str(Path.cwd())
        self._panels = ["agents", "kb", "canvas", "chat"]
        self._focus_idx = 3  # Start on chat

    def compose(self) -> ComposeResult:
        # Header
        yield Static(self._make_header(), id="header")

        # 2x2 Grid
        with Grid(id="main-grid"):
            yield AgentsPanel(id="agents-panel")
            yield KBPanel(id="kb-panel")
            yield CanvasPanel(id="canvas-panel")
            yield ChatPanel(id="chat-panel")

        # Status bar
        yield Static(
            "[1]Agents  [2]KB  [3]Canvas  [4]Chat   TAB=next  ^Q=quit",
            id="status-bar",
        )

    def on_mount(self) -> None:
        self.set_interval(60, self._refresh)
        self._refresh()

        # Focus chat panel
        self._focus_idx = 3
        try:
            self.query_one("#chat-panel", ChatPanel).focus()
        except NoMatches:
            pass

    def _make_header(self) -> str:
        home = os.path.expanduser("~")
        cwd = self._cwd
        if cwd.startswith(home):
            cwd = "~" + cwd[len(home):]
        now = datetime.now().strftime("%H:%M")
        return f"[bold #00f3ff]AI WORKSPACE[/]  [#666688]{cwd[:35]}[/]  [#ff00ff]qwen3:14b[/]  {now}"

    def _refresh(self) -> None:
        """Refresh all panels."""
        try:
            self.query_one("#kb-panel", KBPanel).load_kb()
        except Exception:
            pass

        try:
            self.query_one("#header", Static).update(self._make_header())
        except Exception:
            pass

    def action_focus_panel(self, name: str) -> None:
        """Focus a specific panel by name."""
        id_map = {"agents": "#agents-panel", "kb": "#kb-panel",
                  "canvas": "#canvas-panel", "chat": "#chat-panel"}
        panel_id = id_map.get(name)
        if panel_id:
            try:
                widget = self.query_one(panel_id)
                widget.focus()
            except NoMatches:
                pass

    def action_cycle_focus(self) -> None:
        """Cycle focus through panels."""
        self._focus_idx = (self._focus_idx + 1) % 4
        panel_ids = ["#agents-panel", "#kb-panel", "#canvas-panel", "#chat-panel"]
        try:
            self.query_one(panel_ids[self._focus_idx]).focus()
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
