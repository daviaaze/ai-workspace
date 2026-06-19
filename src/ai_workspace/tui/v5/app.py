"""
TUI v5 — Clean terminal interface for AI Workspace.
No external CSS. Uses built-in Header. Works.

Layout:
  Header (built-in)     — title, clock, bindings
  Conversation (custom)  — agent steps and chat
  Input + Autocomplete (bottom)  — commands and tasks
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.theme import Theme
from textual.widgets import (
    Header,
    Input,
    ListItem,
    ListView,
    Static,
)

from ai_workspace.agents.loop import LoopParams, agent_loop, suggest_pattern
from ai_workspace.tui.v5.conversation import Conversation, ToolCall
from ai_workspace.tui.v5.input_bar import SLASH_COMMANDS
from ai_workspace.tui.v5.tools import build_tools

logger = logging.getLogger("aiw.tui.v5")

# ── Theme ──────────────────────────────────────────────────

THEME = Theme(
    name="workstation",
    primary="#5B8DEE",
    secondary="#7C8DB5",
    accent="#5B8DEE",
    warning="#D4A853",
    error="#E0556A",
    success="#5FA874",
    background="#0F1117",
    surface="#161822",
    panel="#1D1F2B",
    dark=True,
)


# ── Model Selector Overlay ─────────────────────────────────


class ModelSelect(ModalScreen[str | None]):
    """Select an Ollama model from the list."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
        Binding("enter", "select", "Select"),
    ]

    CSS = """
    ModelSelect {
        align: center middle;
        background: $background 85%;
    }
    #model-box {
        width: 50;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: solid $primary 40%;
        padding: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="model-box"):
            yield Static("Select Model", id="model-title")
            yield ListView(id="model-list")

    def on_mount(self) -> None:
        self._load_models()

    @work(exclusive=True)
    async def _load_models(self) -> None:
        try:
            proc = await asyncio.create_subprocess_exec(
                "ollama", "list",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()

            lines = stdout.decode(errors="replace").strip().split("\n")
            model_list = self.query_one("#model-list", ListView)
            model_list.clear()

            # First line is header "NAME   ID   SIZE   MODIFIED", skip it
            for line in lines[1:]:
                if line.strip():
                    name = line.split()[0] if line.split() else line
                    model_list.append(ListItem(Static(name)))

            # Add a custom option
            model_list.append(ListItem(Static("Custom model...")))

            if model_list.children:
                model_list.index = 0

        except Exception:
            model_list = self.query_one("#model-list", ListView)
            model_list.clear()
            for m in ["qwen3:14b", "qwen3:7b", "deepseek-r1:7b"]:
                model_list.append(ListItem(Static(m)))

    def action_select(self) -> None:
        lv = self.query_one("#model-list", ListView)
        if lv.visible and lv.highlighted_child is not None:
            item = lv.highlighted_child
            if isinstance(item, ListItem) and item.children:
                label = item.children[0]
                if isinstance(label, Static):
                    name = str(label.renderable)
                    if name == "Custom model...":
                        self.dismiss(None)
                    else:
                        self.dismiss(name)

    def action_dismiss(self) -> None:
        self.dismiss(None)


# ── Autocomplete Popup ────────────────────────────────────


class Autocomplete(Vertical):
    """Shows matching slash commands below the input."""

    DEFAULT_CSS = """
    Autocomplete {
        height: auto;
        max-height: 6;
        padding: 0 1;
        margin: 0 1;
        background: $surface;
        border: solid $primary 20%;
        display: none;
    }
    Autocomplete.-visible {
        display: block;
    }
    Autocomplete ListView {
        height: auto;
        max-height: 5;
        background: $surface;
    }
    Autocomplete > ListView > ListItem {
        padding: 0 1;
        height: 1;
    }
    Autocomplete > ListView > ListItem.--highlight {
        background: $primary 20%;
        color: $text;
    }
    """

    def compose(self) -> ComposeResult:
        yield ListView(id="ac-list")

    def filter(self, prefix: str) -> None:
        lv = self.query_one("#ac-list", ListView)
        lv.clear()

        matches = [
            (cmd, desc)
            for cmd, desc in SLASH_COMMANDS.items()
            if cmd.lower().startswith(prefix.lower())
        ]

        if not matches:
            self.set_class(False, "-visible")
            return

        self.set_class(True, "-visible")
        for cmd, desc in matches:
            lv.append(ListItem(Static(f"{cmd:<24} {desc[:30]}")))

        if lv.children:
            lv.index = 0
            self.styles.height = min(len(matches) + 1, 6)

    def selected_command(self) -> str | None:
        lv = self.query_one("#ac-list", ListView)
        if not lv.visible or not lv.children:
            return None
        idx = lv.index or 0
        if 0 <= idx < len(lv.children):
            item = lv.children[idx]
            if isinstance(item, ListItem) and item.children:
                label = item.children[0]
                if isinstance(label, Static):
                    return str(label.renderable).split()[0]
        return None

    def move_up(self) -> None:
        lv = self.query_one("#ac-list", ListView)
        if lv.index is not None and lv.index > 0:
            lv.index = lv.index - 1

    def move_down(self) -> None:
        lv = self.query_one("#ac-list", ListView)
        if lv.index is not None and lv.index < len(lv.children) - 1:
            lv.index = lv.index + 1


# ── App ────────────────────────────────────────────────────


class AIWorkspaceApp(App[None], inherit_bindings=False):
    """Works if you can see the header."""

    TITLE = "AI Workspace"
    SUB_TITLE = ""

    CSS = """
    Screen { background: $background; }
    Header {
        dock: top; height: 3;
        background: $surface;
        color: $text;
        text-style: bold;
        content-align: left middle;
        padding: 0 2;
    }
    Header > HeaderIcon { display: none; }
    #conv { height: 1fr; background: $background; }
    #status-bar {
        dock: bottom; height: 1;
        background: $surface;
        color: $text;
        padding: 0 2;
        display: none;
    }
    #status-bar.-visible { display: block; }
    #task-input {
        dock: bottom; height: 3;
        margin: 0 1 1 1;
        background: $surface;
        border: solid $primary 20%;
        padding: 0 1;
    }
    #task-input:focus { border: solid $primary 50%; }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", priority=True),
        Binding("ctrl+m", "select_model", "Model"),
        Binding("ctrl+l", "clear", "Clear"),
        Binding("ctrl+g", "git", "Git"),
        Binding("f4", "context", "Context"),
        Binding("escape", "focus_input", "Focus", show=False),
        Binding("tab", "autocomplete", "", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.cwd = str(Path.cwd())
        self._model: str = "qwen3:14b"
        self._agent_task: asyncio.Task | None = None
        self._agent_running: bool = False

        from ai_workspace.agents.context_manager import ContextManager
        self.context_manager = ContextManager()

    # ── Compose ──

    def compose(self) -> ComposeResult:
        yield Header()
        yield Conversation(id="conv")
        yield Static(id="status-bar")
        yield Autocomplete(id="autocomplete")
        yield Input(
            placeholder="Type a task or /command...",
            id="task-input",
        )

    def on_mount(self) -> None:
        self.register_theme(THEME)
        self.theme = "workstation"
        self._update_title()
        self._load_git_branch()
        self.query_one("#task-input", Input).focus()

    # ── Title & Git ──

    def _update_title(self) -> None:
        path = self.cwd
        home = str(Path.home())
        if path.startswith(home):
            path = "~" + path[len(home):]
        if len(path) > 30:
            path = "..." + path[-27:]
        self.sub_title = f"{path}  [{self._model}]"

    def _load_git_branch(self) -> None:
        try:
            r = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, cwd=self.cwd, timeout=2,
            )
            if r.returncode == 0 and (branch := r.stdout.strip()):
                self.sub_title = f"{self.cwd} ({branch})  [{self._model}]"
        except Exception:
            pass

    # ── Autocomplete ──

    @on(Input.Changed, "#task-input")
    def on_input_changed(self, event: Input.Changed) -> None:
        value = event.value
        try:
            ac = self.query_one("#autocomplete", Autocomplete)
        except Exception:
            return
        if value.startswith("/"):
            ac.filter(value)
        else:
            ac.set_class(False, "-visible")

    def action_autocomplete(self) -> None:
        """Tab: accept highlighted autocomplete command."""
        try:
            ac = self.query_one("#autocomplete", Autocomplete)
        except Exception:
            return
        cmd = ac.selected_command()
        if cmd:
            inp = self.query_one("#task-input", Input)
            inp.value = cmd + " "
            inp.cursor_position = len(inp.value)
            ac.set_class(False, "-visible")

    def on_key(self, event) -> None:
        """Handle arrow keys for autocomplete navigation."""
        try:
            ac = self.query_one("#autocomplete", Autocomplete)
        except Exception:
            return
        if not ac.has_class("-visible"):
            return
        if event.key == "up":
            ac.move_up()
            event.prevent_default()
        elif event.key == "down":
            ac.move_down()
            event.prevent_default()
        elif event.key == "escape":
            ac.set_class(False, "-visible")
            event.prevent_default()

    # ── Input Submit ──

    @on(Input.Submitted, "#task-input")
    async def on_input_submit(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        event.input.value = ""

        # Hide autocomplete
        try:
            self.query_one("#autocomplete", Autocomplete).set_class(False, "-visible")
        except Exception:
            pass

        if text.startswith("/"):
            await self._handle_slash(text)
        else:
            self._spawn_agent(text)

    # ── Slash Commands ──

    async def _handle_slash(self, text: str) -> None:
        cmd, _, args = text.partition(" ")

        if cmd == "/help":
            self._show_help()
        elif cmd == "/quit":
            self.exit()
        elif cmd == "/clear":
            self.query_one("#conv", Conversation).clear()
        elif cmd == "/model":
            self.push_screen(ModelSelect(), callback=self._on_model_selected)
        elif cmd == "/cost":
            self._show_cost()
        elif cmd == "/git":
            self._show_git()
        elif cmd == "/ctx":
            await self._handle_ctx(args)
        else:
            self._toast(f"Unknown: {cmd} (try /help)", "error")

    async def _on_model_selected(self, name: str | None) -> None:
        if name:
            self._model = name
            self._update_title()
            self._toast(f"Model: {name}", "info")

    # ── Keybinding Actions ──

    def action_select_model(self) -> None:
        self.push_screen(ModelSelect(), callback=self._on_model_selected)

    def action_quit(self) -> None:
        if self._agent_running and self._agent_task:
            self._agent_task.cancel()
            self._agent_running = False
        self.exit()

    def action_clear(self) -> None:
        self.query_one("#conv", Conversation).clear()

    def action_git(self) -> None:
        self._show_git()

    def action_context(self) -> None:
        from ai_workspace.tui.v5.context_inspector import ContextInspector
        self.push_screen(ContextInspector(context_manager=self.context_manager))

    def action_focus_input(self) -> None:
        self.query_one("#task-input", Input).focus()

    # ── Agent Integration ──

    def _spawn_agent(self, task: str) -> None:
        """Start agent loop (non-blocking)."""
        conv = self.query_one("#conv", Conversation)
        conv.add_user(task)
        self._show_status(f"[$warning]●[/] Agent running — {self._model}", visible=True)
        self._agent_running = True
        self._agent_task = asyncio.create_task(self._run_agent(task))

    async def _run_agent(self, task: str) -> None:
        conv = self.query_one("#conv", Conversation)
        tool_defs, tool_handlers = build_tools(self.cwd)
        pattern = suggest_pattern(task, tool_defs)

        params = LoopParams(
            task=task, pattern=pattern, model=self._model,
            tools=tool_defs, tool_handlers=tool_handlers, max_turns=20,
            stream=True, on_step=None,
        )

        step = 0

        try:
            async for event in agent_loop(params):
                etype, data = event.type, event.data

                if etype == "token":
                    if conv._current_response is None:
                        conv.start_response()
                    conv.append_token(data.get("text", ""))

                elif etype == "thinking" or (etype == "phase" and data.get("phase") == "thinking"):
                    step += 1  # count step, tool_call will show it

                elif etype == "tool_call":
                    tool = data.get("tool", "?")
                    args = str(data.get("args", ""))[:100]
                    if step > 0:
                        conv.add_thought("", step)
                    conv.add_tool_call(tool, args)

                elif etype == "tool_result":
                    result = str(data.get("result", ""))[:500]
                    # Find last ToolCall and set result
                    for child in reversed(conv.children):
                        if isinstance(child, ToolCall):
                            conv.add_tool_result(child, result)
                            break

                elif etype == "done":
                    conv.finish_response()
                    reason = data.get("reason", "completed")
                    turns = data.get("turns", 0)
                    if reason == "completed":
                        msg = "✓ Done" if turns == 0 else f"✓ Done in {turns} turns"
                        self._show_status(f"[#5FA874]{msg}[/]", visible=True)
                    else:
                        self._show_status(f"[#E0556A]✗ Stopped: {reason}[/]", visible=True)
                    self.set_timer(5, lambda: self._show_status("", visible=False))

                elif etype == "error":
                    conv.add_error(data.get("message", "Error"))
                    self.set_timer(5, lambda: self._show_status("", visible=False))

                else:
                    # Unknown event type — log for debugging
                    logger.debug("Unknown agent event: %s data=%s", etype, str(data)[:100])

        except asyncio.CancelledError:
            self._show_status("[#D4A853]✗ Cancelled[/]", visible=True)
            self.set_timer(3, lambda: self._show_status("", visible=False))
        except Exception as e:
            self._show_status(f"[#E0556A]✗ {e}[/]", visible=True)
            self.set_timer(5, lambda: self._show_status("", visible=False))
            logger.exception("Agent loop failed")
        finally:
            self._agent_running = False

    # ── Overlays (inline) ──

    def _show_help(self) -> None:
        conv = self.query_one("#conv", Conversation)
        conv.add_system("\n[bold #5B8DEE]Commands:[/]")
        for cmd, desc in SLASH_COMMANDS.items():
            conv.add_system(f"  [#7C8DB5]{cmd:<24}[/] {desc}")
        conv.add_system(
            "\n[bold #5B8DEE]Keys:[/]"
            "\n  Ctrl+M Select Model   Ctrl+Q Quit   Ctrl+L Clear"
            "\n  F4 Context   Ctrl+G Git   Tab Autocomplete"
        )

    def _show_cost(self) -> None:
        try:
            from ai_workspace.core.cost import CostService
            cs = CostService()
            cs.initialize()
            budget = cs.budget.budget_summary()
            today = budget.get("today_spent", 0)
            total = budget.get("total_spent", 0)
            self._toast(f"Today ${today:.4f} | Total ${total:.4f}", "info")
        except Exception as e:
            self._toast(f"Cost: {e}", "warning")

    def _show_git(self) -> None:
        conv = self.query_one("#conv", Conversation)
        try:
            r = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True, text=True, cwd=self.cwd, timeout=3,
            )
            if r.stdout.strip():
                conv.add_system("\n[bold #5B8DEE]Git:[/]")
                for line in r.stdout.strip().split("\n")[:15]:
                    conv.add_system(f"  [#A0A5B8]{line}[/]")
            else:
                conv.add_system("\n[#5FA874]Git: clean[/]")
        except Exception as e:
            conv.add_system(f"\n[#E0556A]Git: {e}[/]")

    async def _handle_ctx(self, args: str) -> None:
        parts = args.strip().split(maxsplit=1)
        sub = parts[0] if parts else "show"

        if sub in ("show", ""):
            self.action_context()
        elif sub == "stats":
            stats = self.context_manager.stats()
            self._toast(
                f"Context: {stats['total_blocks']} blocks "
                f"({stats['total_tokens']:,}t, {stats['budget_used_pct']}%)",
                "info",
            )
        elif sub == "add" and len(parts) > 1:
            from ai_workspace.agents.context_manager import BlockType
            path = Path(parts[1]).expanduser()
            if path.exists() and path.is_file():
                content = path.read_text(encoding="utf-8")
                self.context_manager.add_block(
                    block_type=BlockType.FILE_READ, content=content,
                    summary=f"File: {path.name}", file_path=str(path), importance=0.7,
                )
                self._toast(f"Added: {path.name}", "info")
            else:
                self._toast(f"Not found: {parts[1]}", "warning")
        elif sub == "list":
            blocks = self.context_manager.get_active_blocks()
            names = [Path(b.file_path).name for b in blocks if b.file_path]
            self._toast(f"{len(names)} files in context", "info")
        else:
            self._toast("Usage: /ctx [show|stats|add|remove|list]", "warning")

    # ── Helpers ──

    def _show_status(self, text: str, *, visible: bool = True) -> None:
        try:
            bar = self.query_one("#status-bar", Static)
            bar.update(text)
            bar.set_class(visible and bool(text), "-visible")
        except Exception:
            pass

    def _toast(self, message: str, severity: str = "info") -> None:
        colors = {"info": "#A0A5B8", "warning": "#D4A853", "error": "#E0556A"}
        color = colors.get(severity, "#A0A5B8")
        try:
            self.query_one("#conv", Conversation).write(f"[{color}]-- {message} --[/]")
        except Exception:
            pass


# ── Entry ──

def run_tui():
    AIWorkspaceApp().run()


if __name__ == "__main__":
    run_tui()
