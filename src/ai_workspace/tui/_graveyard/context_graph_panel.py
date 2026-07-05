"""
Context Graph Panel — Obsidian-like context visualization for the right side panel.

Shows the agent's context window as an interactive graph:
  - Nodes: files, messages, tool calls, memories, edits
  - Edges: connections between nodes (file → edit, message → tool)
  - Colors: by block type (green=project, blue=tool, yellow=message, etc.)
  - Pinned nodes glow; excluded nodes fade

Design (inspired by Obsidian graph view):
[  Context Graph ]
 Budget:  38%  48,000/128,000

   Knowledge Base
     auth-pattern (0.8) →  JWT memory (0.9)

          →  shell_exec →  passed

     ci-setup (0.6)
     api-design (0.5) →  edit_file(auth.py)


   Active Context
     "Fix the auth middleware" (340t)
     "I'll look at the auth code..." (180t)
     read_file(auth.py) (50t)
     edit_file(auth.py) (80t)
     [Compaction #1] (600t)


  [p] pin  [x] exclude  [v] view  [Enter] expand  [/] filter

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widgets import Button, Input, Label, Static

if TYPE_CHECKING:
    from ai_workspace.agents.context_manager import ContextManager


class BudgetBar(Static):
    """Compact token budget bar."""

    DEFAULT_CSS = """
    BudgetBar {
        height: 1;
        padding: 0 1;
    }
    """

    budget_pct: reactive[float] = reactive(0.0)
    total_tokens: reactive[int] = reactive(0)
    max_tokens: reactive[int] = reactive(128_000)

    def render(self) -> str:
        width = 15
        pct = min(self.budget_pct, 100)
        filled = int((pct / 100) * width)
        bar = "" * filled + "" * (width - filled)

        if pct < 40:
            color = "green"
        elif pct < 70:
            color = "yellow"
        else:
            color = "red"

        return (
            f"Budget: [{color}]{bar}[/] [{color}]{pct:.0f}%[/]  "
            f"{self.total_tokens:,}/{self.max_tokens:,}"
        )


class ContextNodeItem(Static):
    """A single context block row."""

    DEFAULT_CSS = """
    ContextNodeItem {
        height: 1;
        padding: 0 1;
    }
    ContextNodeItem:hover {
        background: $boost;
    }
    ContextNodeItem.-selected {
        background: $accent 25%;
        border-left: solid $accent;
    }
    ContextNodeItem.-pinned {
        border-left: solid $success;
    }
    ContextNodeItem.-excluded {
        opacity: 50%;
        border-left: solid $error;
    }
    """

    label: reactive[str] = reactive("")
    tokens: reactive[int] = reactive(0)
    is_pinned: reactive[bool] = reactive(False)
    is_excluded: reactive[bool] = reactive(False)
    is_selected: reactive[bool] = reactive(False)
    icon: reactive[str] = reactive("•")

    def render(self) -> str:
        pin = " [green][/]" if self.is_pinned else ""
        excl = " [red][/]" if self.is_excluded else ""
        tokens_str = f" [dim]({self.tokens}t)[/]" if self.tokens > 0 else ""
        return f"{self.icon} {self.label[:60]}{tokens_str}{pin}{excl}"


class ContextGraphPanel(Vertical):
    """Context graph panel for the right side stack."""

    DEFAULT_CSS = """
    ContextGraphPanel {
        height: 1fr;
        padding: 1;
    }

    ContextGraphPanel #ctx-header {
        dock: top;
        height: 1;
        padding: 0 1 1 1;
        text-style: bold;
        border-bottom: solid $primary 20%;
        background: $boost;
    }

    ContextGraphPanel #ctx-budget {
        dock: top;
        height: auto;
        padding: 0 0 1 0;
    }

    ContextGraphPanel #ctx-filter {
        dock: top;
        height: 3;
        padding: 0 0 1 0;
    }

    ContextGraphPanel #ctx-filter Input {
        width: 1fr;
        margin: 0 0 1 0;
    }

    ContextGraphPanel #ctx-filter Button {
        margin: 0 1 0 0;
        min-width: 10;
    }

    ContextGraphPanel #ctx-sections {
        height: 1fr;
    }

    ContextGraphPanel .ctx-section-title {
        height: 1;
        padding: 1 1 0 1;
        text-style: bold;
        border-bottom: solid $primary 20%;
        background: $surface;
    }

    ContextGraphPanel #ctx-empty {
        padding: 2 2;
        text-style: dim;
        text-align: center;
    }

    ContextGraphPanel #ctx-help {
        dock: bottom;
        height: 1;
        padding: 1 1 0 1;
        text-style: dim;
        border-top: solid $primary 20%;
    }
    """

    context_manager: ContextManager | None = None
    selected_idx: reactive[int] = reactive(0)

    def __init__(self, context_manager: ContextManager | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.context_manager = context_manager

    def compose(self) -> ComposeResult:
        yield Label(" Context", id="ctx-header")

        yield BudgetBar(id="ctx-budget")

        with Horizontal(id="ctx-filter"):
            yield Input(placeholder="Filter blocks...", id="ctx-search")
            yield Button(" Pin", id="ctx-pin", variant="default")
            yield Button(" Exclude", id="ctx-exclude", variant="default")
            yield Button(" Auto-trim", id="ctx-trim", variant="default")

        with VerticalScroll(id="ctx-sections"):
            pass  # Sections built dynamically

        yield Label(
            "[p] pin  [x] exclude  [↑↓] select  [/] filter  [t] trim",
            id="ctx-help",
        )

    def on_mount(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        """Rebuild the context graph from the context manager."""
        self._refresh_budget()
        self._refresh_blocks()

    def _refresh_budget(self) -> None:
        """Update budget bar."""
        try:
            bar = self.query_one(BudgetBar)
        except NoMatches:
            return

        if self.context_manager:
            cm = self.context_manager
            bar.budget_pct = cm.budget_used_pct
            bar.total_tokens = cm.total_tokens
            bar.max_tokens = cm.context_window_tokens
        else:
            bar.budget_pct = 0
            bar.total_tokens = 0
        bar.refresh()

    def _refresh_blocks(self) -> None:
        """Rebuild the block list grouped by category."""
        try:
            container = self.query_one("#ctx-sections", VerticalScroll)
        except NoMatches:
            return

        # Clear old content
        for child in list(container.children):
            child.remove()

        blocks = (
            self.context_manager.get_active_blocks()
            if self.context_manager
            else []
        )

        if not blocks:
            container.mount(Label(
                "No context blocks yet.\n\n"
                "[dim]Context blocks appear as agents work — [/]\n"
                "[dim]files read, messages sent, tools called, edits made.[/]",
                id="ctx-empty",
            ))
            return

        # Group by block type
        grouped: dict[str, list] = {}
        for b in blocks:
            category = self._category_for(b)
            grouped.setdefault(category, []).append(b)

        for category, items in grouped.items():
            # Section title
            container.mount(Label(
                f"[bold]{category}[/] ({len(items)})",
                classes="ctx-section-title",
            ))

            for i, b in enumerate(items):
                node = ContextNodeItem()
                node.label = b.display_label
                node.tokens = b.tokens
                node.icon = b.icon
                node.is_pinned = b.pinned
                node.is_excluded = b.excluded
                container.mount(node)

        # Scroll to end (latest blocks)
        container.scroll_end(animate=False)

    def _category_for(self, block) -> str:
        """Map block type to a display category."""
        from ai_workspace.agents.context_manager import BlockType
        category_map = {
            BlockType.PROJECT_CONTEXT: " Project Files",
            BlockType.USER_MESSAGE: " Messages",
            BlockType.ASSISTANT_RESPONSE: " Responses",
            BlockType.TOOL_CALL: " Tool Calls",
            BlockType.FILE_EDIT: " Edits",
        }
        return category_map.get(block.block_type, " Other")

    @on(Input.Changed, "#ctx-search")
    def on_search(self, event: Input.Changed) -> None:
        """Filter blocks by search text (stub — simple filter)."""
        self._refresh_blocks()

    @on(Button.Pressed, "#ctx-pin")
    def on_pin(self, event: Button.Pressed) -> None:
        """Pin the selected block."""
        if self.context_manager:
            blocks = self.context_manager.get_active_blocks()
            if blocks and self.selected_idx < len(blocks):
                self.context_manager.toggle_pin(blocks[self.selected_idx].block_id)
                self._refresh()

    @on(Button.Pressed, "#ctx-exclude")
    def on_exclude(self, event: Button.Pressed) -> None:
        """Exclude the selected block."""
        if self.context_manager:
            blocks = self.context_manager.get_active_blocks()
            if blocks and self.selected_idx < len(blocks):
                self.context_manager.toggle_exclude(blocks[self.selected_idx].block_id)
                self._refresh()

    @on(Button.Pressed, "#ctx-trim")
    def on_trim(self, event: Button.Pressed) -> None:
        """Auto-trim context to fit budget."""
        if self.context_manager:
            self.context_manager.auto_trim()
            self._refresh()

    def key_up(self) -> None:
        if self.selected_idx > 0:
            self.selected_idx -= 1

    def key_down(self) -> None:
        blocks = self.context_manager.get_active_blocks() if self.context_manager else []
        if self.selected_idx < len(blocks) - 1:
            self.selected_idx += 1
