"""
Context Workbench — TUI widget for context window observability.

Opened with Ctrl+E in the AI Operations Center. Provides:
- Tree view of all context blocks
- Token budget bar with percentage
- Pin/Exclude/Expand actions per block
- Largest blocks list (for trimming suggestions)
- Snapshot save/load
- Content preview for selected block

Layout:
 Context Workbench 
 Budget: [] 45%  12,340/128,000 tokens     
                                                             
 Context Tree                      Block Detail              
    
  Project Context (500t)         Type: User Message        
    src/auth.py (200t)           Tokens: 340               
    src/middleware.py (150t)     Pinned: No                
  "Fix the auth bug" (340t)        
  "I'll look at..." (180t)      Fix the auth middleware   
  read_file(auth.py) (50t)      bug in the login flow.    
  [file content...] (1200t)     The JWT validation is...  
  edit_file(auth.py) (80t)                                
  [Compaction #1] (600t)        [p] Pin  [x] Exclude      
                                   [s] Save Snapshot         
 [p]in [x]clude [v]iew [s]nap     [Enter] Expand/Collapse   


Keybindings:
  ↑/↓        — navigate blocks
  p          — toggle pin
  x          — toggle exclude
  Enter      — expand/collapse children / view details
  v          — view full content in detail panel
  s          — save snapshot
  l          — load snapshot
  t          — auto-trim to budget
  a          — auto-pin important blocks
  Tab        — switch focus (tree ↔ detail)
  q/Esc      — close workbench
"""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Label, Static

from ai_workspace.agents.context_manager import (
    BlockType,
    ContextBlock,
    ContextManager,
)


class BudgetBar(Static):
    """Token budget visualization bar."""
    
    budget_pct: reactive[float] = reactive(0.0)
    total_tokens: reactive[int] = reactive(0)
    max_tokens: reactive[int] = reactive(128_000)
    status: reactive[str] = reactive("")

    def render(self) -> str:
        width = 30
        pct = min(self.budget_pct, 100)
        filled = int((pct / 100) * width)
        empty = width - filled

        if pct < 40:
            bar_char = ""
            color = "green"
        elif pct < 70:
            bar_char = ""
            color = "yellow"
        else:
            bar_char = ""
            color = "red"

        bar = f"[{color}]{bar_char * filled}[/][dim]{'' * empty}[/]"

        return (
            f"Budget: {bar} [{color}]{pct:.0f}%[/]  "
            f"{self.total_tokens:,}/{self.max_tokens:,} tokens  "
            f"[dim]{self.status}[/]"
        )


class ContextBlockWidget(Static):
    """A single context block row in the tree view."""

    DEFAULT_CSS = """
    ContextBlockWidget {
        height: 1;
        padding: 1 2;
    }
    ContextBlockWidget.selected {
        background: $accent 30%;
    }
    ContextBlockWidget.pinned {
        border-left: solid $success;
    }
    ContextBlockWidget.excluded {
        opacity: 50%;
        border-left: solid $error;
    }
    """

    block_id: reactive[str] = reactive("")
    depth: reactive[int] = reactive(0)
    is_selected: reactive[bool] = reactive(False)
    is_pinned: reactive[bool] = reactive(False)
    is_excluded: reactive[bool] = reactive(False)
    is_expanded: reactive[bool] = reactive(True)
    has_children: reactive[bool] = reactive(False)

    def render(self) -> str:
        block = self.app.query_one(ContextWorkbench).context_manager.get_block(
            self.block_id
        ) if self.app else None

        if not block:
            return "[dim]?[/]"

        indent = "  " * self.depth
        expand_icon = "" if (self.has_children and self.is_expanded) else (
            "" if self.has_children else " "
        )
        icon = block.icon
        label = block.display_label

        if self.is_pinned:
            status_marker = " [bold green][/]"
        elif self.is_excluded:
            status_marker = " [dim][/]"
        else:
            status_marker = ""

        if self.is_selected:
            return f"[reverse]{indent}{expand_icon} {icon} {label}{status_marker}[/]"
        return f"{indent}{expand_icon} {icon} {label}{status_marker}"


class DetailPanel(Static):
    """Right panel showing details of the selected context block."""

    block: ContextBlock | None = None

    def render(self) -> str:
        if not self.block:
            return "[dim]Select a block to view details[/]"

        b = self.block
        lines = [
            f"[bold]Type:[/] {b.block_type.name.replace('_', ' ').title()}",
            f"[bold]Tokens:[/] {b.tokens:,}",
            f"[bold]Pinned:[/] {'[green]Yes [/]' if b.pinned else 'No'}",
            f"[bold]Excluded:[/] {'[red]Yes [/]' if b.excluded else 'No'}",
            f"[bold]Importance:[/] {b.importance:.0%}",
            "",
        ]

        if b.file_path:
            lines.append(f"[bold]File:[/] [cyan]{b.file_path}[/]")
        if b.tool_name:
            lines.append(f"[bold]Tool:[/] [yellow]{b.tool_name}[/]")
        if b.summary:
            lines.append(f"[bold]Summary:[/] {b.summary}")

        lines.append("")
        lines.append("[dim] Content [/]")
        # Show first 15 lines of content
        content_lines = b.content.split("\n")[:15]
        for cl in content_lines:
            lines.append(f"[dim]{cl[:120]}[/]")
        if len(b.content.split("\n")) > 15:
            lines.append("[dim]... (more lines)[/]")

        lines.append("")
        lines.append(
            "[bold][[p]][/] Pin  "
            "[bold][[x]][/] Exclude  "
            "[bold][[s]][/] Save Snapshot  "
            "[bold][[v]][/] Full Content"
        )

        return "\n".join(lines)


class SnapshotList(Static):
    """List of saved context snapshots."""

    snapshots: list[dict] = []

    def render(self) -> str:
        if not self.snapshots:
            return "[dim]No snapshots saved yet.[/]"

        lines = ["[bold]Saved Snapshots:[/]", ""]
        for i, s in enumerate(self.snapshots):
            lines.append(
                f"[{i+1}] [cyan]{s['label'][:40]}[/] "
                f"({s['blocks']} blocks)"
            )
        lines.append("")
        lines.append("[dim]Press number to load, [d] to delete[/]")
        return "\n".join(lines)


class ContextWorkbench(Static):
    """Full context workbench — Obsidian-style context graph and management.

    Opened with Ctrl+E. Shows context blocks as a tree with token budget,
    pin/exclude controls, and snapshot management.
    """

    can_focus = True

    DEFAULT_CSS = """
    ContextWorkbench {
        display: none;
        layer: overlay;
        background: $surface;
        border: thick $accent;
        padding: 0 1;
        width: 90%;
        height: 85%;
        dock: top;
        offset-x: 5%;
        offset-y: 3;
        overflow: hidden;
    }
    ContextWorkbench.visible {
        display: block;
    }

    ContextWorkbench > Vertical {
        height: 1fr;
    }

    #wb-budget {
        height: 2;
        padding: 1 2;
        background: $boost;
    }

    #wb-main {
        height: 1fr;
    }

    #wb-tree-container {
        width: 50%;
        height: 1fr;
        border: solid $primary 20%;
        overflow-y: auto;
    }

    #wb-detail-container {
        width: 50%;
        height: 1fr;
        border: solid $primary 20%;
        padding: 1 2;
    }

    #wb-snapshots {
        height: auto;
        max-height: 12;
        border-top: solid $primary 20%;
        padding: 1 2;
    }

    #wb-help {
        height: 1;
        padding: 0 2;
        text-style: dim;
        background: $boost;
    }
    """

    class Closed(Message):
        """Posted when the workbench is dismissed."""

    def __init__(
        self,
        context_manager: ContextManager | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.context_manager = context_manager or ContextManager()
        self._selected_idx: int = 0
        self._focus_panel: str = "tree"  # "tree" or "detail"
        self._viewing_snapshots: bool = False

    def compose(self) -> ComposeResult:
        with Vertical():
            yield BudgetBar(id="wb-budget")
            with Horizontal(id="wb-main"):
                yield VerticalScroll(id="wb-tree-container")
                yield DetailPanel(id="wb-detail", classes="hidden")
            yield SnapshotList(id="wb-snapshots", classes="hidden")
            yield Label(
                "[bold]↑↓[/] nav  [bold]p[/] pin  [bold]x[/] exclude  "
                "[bold]Enter[/] detail  [bold]v[/] full content  "
                "[bold]s[/] snapshot  [bold]t[/] auto-trim  "
                "[bold]a[/] auto-pin  [bold]Tab[/] switch panel  "
                "[bold]q/Esc[/] close",
                id="wb-help",
            )

    def show(self) -> None:
        """Open the workbench."""
        self.set_class(True, "visible")
        self._refresh_all()
        self.focus()

    def hide(self) -> None:
        """Close the workbench."""
        self.set_class(False, "visible")
        self.post_message(self.Closed())

    def _refresh_all(self) -> None:
        """Refresh all panels."""
        self._refresh_budget()
        self._refresh_tree()
        self._refresh_detail()

    def _refresh_budget(self) -> None:
        """Update budget bar."""
        try:
            bar = self.query_one(BudgetBar)
            cm = self.context_manager
            bar.budget_pct = cm.budget_used_pct
            bar.total_tokens = cm.total_tokens
            bar.max_tokens = cm.context_window_tokens
            bar.status = cm.budget_status
            bar.refresh()
        except NoMatches:
            pass

    def _refresh_tree(self) -> None:
        """Rebuild the context tree."""
        try:
            container = self.query_one("#wb-tree-container", VerticalScroll)
        except NoMatches:
            return

        # Remove old block widgets
        for child in list(container.children):
            if isinstance(child, ContextBlockWidget):
                child.remove()

        blocks = self.context_manager.get_active_blocks()

        if not blocks:
            container.mount(Label(
                "[dim]No context blocks yet. "
                "Blocks appear as the agent works.[/]",
                id="wb-empty",
            ))
            return

        # Remove empty message if present
        try:
            container.query_one("#wb-empty").remove()
        except NoMatches:
            pass

        # Track which blocks to show (tree expansion)
        visible_ids = self._get_visible_block_ids(blocks)

        for i, block in enumerate(blocks):
            if block.block_id not in visible_ids:
                continue

            depth = self._get_depth(block.block_id)
            has_children = len(block.children_ids) > 0

            widget = ContextBlockWidget()
            widget.block_id = block.block_id
            widget.depth = depth
            widget.is_selected = (i == self._selected_idx)
            widget.is_pinned = block.pinned
            widget.is_excluded = block.excluded
            widget.has_children = has_children
            widget.is_expanded = True  # Could be stored per-block

            container.mount(widget)

        # Scroll to selected
        if 0 <= self._selected_idx < len(blocks):
            try:
                widgets = [
                    w for w in container.children
                    if isinstance(w, ContextBlockWidget)
                ]
                if widgets and self._selected_idx < len(widgets):
                    # Mount a scroll anchor could be added here
                    pass
            except Exception:
                pass

    def _get_visible_block_ids(self, blocks: list[ContextBlock]) -> set[str]:
        """Get block IDs that should be visible (tree expansion logic)."""
        # For MVP: show all blocks
        return {b.block_id for b in blocks}

    def _get_depth(self, block_id: str) -> int:
        """Calculate tree depth for a block."""
        depth = 0
        current_id = block_id
        while True:
            block = self.context_manager.get_block(current_id)
            if not block or not block.parent_id:
                break
            depth += 1
            current_id = block.parent_id
            if depth > 20:  # Safety limit
                break
        return depth

    def _refresh_detail(self) -> None:
        """Update the detail panel for the selected block."""
        try:
            detail = self.query_one(DetailPanel)
        except NoMatches:
            return

        blocks = self.context_manager.get_active_blocks()
        if 0 <= self._selected_idx < len(blocks):
            detail.block = blocks[self._selected_idx]
            detail.set_class(False, "hidden")
        else:
            detail.block = None
            detail.set_class(True, "hidden")

        detail.refresh()


    def key_up(self) -> None:
        """Move selection up."""
        blocks = self.context_manager.get_active_blocks()
        if blocks:
            self._selected_idx = max(0, self._selected_idx - 1)
            self._refresh_tree()
            self._refresh_detail()

    def key_down(self) -> None:
        """Move selection down."""
        blocks = self.context_manager.get_active_blocks()
        if blocks:
            self._selected_idx = min(
                len(blocks) - 1, self._selected_idx + 1
            )
            self._refresh_tree()
            self._refresh_detail()

    def key_p(self) -> None:
        """Toggle pin on selected block."""
        blocks = self.context_manager.get_active_blocks()
        if 0 <= self._selected_idx < len(blocks):
            bid = blocks[self._selected_idx].block_id
            result = self.context_manager.toggle_pin(bid)
            self._refresh_all()

    def key_x(self) -> None:
        """Toggle exclude on selected block."""
        blocks = self.context_manager.get_active_blocks()
        if 0 <= self._selected_idx < len(blocks):
            bid = blocks[self._selected_idx].block_id
            result = self.context_manager.toggle_exclude(bid)
            self._refresh_all()

    def key_enter(self) -> None:
        """Toggle detail panel or expand/collapse."""
        if self._focus_panel == "tree":
            self._focus_panel = "detail"
        else:
            self._focus_panel = "tree"
        self._refresh_detail()

    def key_v(self) -> None:
        """View full content of selected block."""
        blocks = self.context_manager.get_active_blocks()
        if 0 <= self._selected_idx < len(blocks):
            block = blocks[self._selected_idx]
            # Show full content in detail panel
            try:
                detail = self.query_one(DetailPanel)
                detail.block = block
                detail.set_class(False, "hidden")
                detail.refresh()
            except NoMatches:
                pass

    def key_s(self) -> None:
        """Save context snapshot."""
        label = f"Snapshot {len(self.context_manager._snapshots) + 1}"
        self.context_manager.save_snapshot(label)
        self._refresh_snapshots()

    def key_l(self) -> None:
        """Toggle snapshot list view."""
        self._viewing_snapshots = not self._viewing_snapshots
        try:
            snap_panel = self.query_one(SnapshotList)
            snap_panel.set_class(not self._viewing_snapshots, "hidden")
        except NoMatches:
            pass
        if self._viewing_snapshots:
            self._refresh_snapshots()

    def key_t(self) -> None:
        """Auto-trim context to fit budget."""
        trimmed = self.context_manager.auto_trim()
        self._refresh_all()

    def key_a(self) -> None:
        """Auto-pin important blocks."""
        pinned = self.context_manager.auto_pin_important()
        self._refresh_all()

    def key_tab(self) -> None:
        """Switch focus between tree and detail."""
        self._focus_panel = "detail" if self._focus_panel == "tree" else "tree"

    def key_escape(self) -> None:
        """Close workbench."""
        self.hide()

    def key_q(self) -> None:
        """Close workbench."""
        self.hide()

    def _refresh_snapshots(self) -> None:
        """Update snapshot list."""
        try:
            snap_panel = self.query_one(SnapshotList)
            snap_panel.snapshots = self.context_manager.list_snapshots()
            snap_panel.refresh()
        except NoMatches:
            pass


    def key_1(self) -> None:
        self._load_snapshot_by_index(0)

    def key_2(self) -> None:
        self._load_snapshot_by_index(1)

    def key_3(self) -> None:
        self._load_snapshot_by_index(2)

    def key_4(self) -> None:
        self._load_snapshot_by_index(3)

    def key_5(self) -> None:
        self._load_snapshot_by_index(4)

    def key_d(self) -> None:
        """Delete selected snapshot (when viewing snapshots)."""
        if self._viewing_snapshots:
            snapshots = self.context_manager.list_snapshots()
            if 0 <= self._selected_idx < len(snapshots):
                sid = snapshots[self._selected_idx]["id"]
                self.context_manager.delete_snapshot(sid)
                self._refresh_snapshots()

    def _load_snapshot_by_index(self, idx: int) -> None:
        """Load a snapshot by its list index."""
        snapshots = self.context_manager.list_snapshots()
        if idx < len(snapshots):
            sid = snapshots[idx]["id"]
            self.context_manager.load_snapshot(sid)
            self._refresh_all()
