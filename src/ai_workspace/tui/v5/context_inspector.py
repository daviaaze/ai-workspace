"""
Context Inspector — TUI overlay showing token usage, file tree, and drift detection.

Presents the agent's context window state: what files it has read, how many
tokens they consume, whether they've changed on disk since being read (drift),
and whether they were added via compaction summary (stale).

Keyboard shortcuts:
  p — pin/unpin a file (keep during compaction)
  x — exclude a file (remove from context)
  a — add a file to context
  t — sort by token count
  s — sort by status
  r — refresh drift detection
  q / Esc — back

Refs: SPEC_CONTEXT_MANAGEMENT.md, peekctx, ContextLens
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label

from ai_workspace.agents.context_manager import (
    BlockType,
    ContextBlock,
    ContextManager,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _drift_check(block: ContextBlock) -> bool:
    """Check if a file block's content has changed on disk since it was read."""
    path = block.file_path
    if not path or not os.path.isfile(path):
        return False
    try:
        current = Path(path).read_text(encoding="utf-8")
        # Compare first 500 chars as a quick heuristic
        # (full hash would be more accurate but slower)
        stored_prefix = (block.content or "")[:500]
        current_prefix = current[:500]
        return stored_prefix != current_prefix
    except Exception:
        return False


def _is_stale(block: ContextBlock) -> bool:
    """A block is stale if it was created by compaction (summary only)."""
    return block.block_type == BlockType.COMPACTION


def _format_file_tree(
    blocks: list[ContextBlock],
    width: int = 60,
) -> str:
    """Build an ASCII file tree from context blocks, grouped by directory.

    Shows: path, token count, status (drifted / stale / ok).
    """
    if not blocks:
        return "  (no files in context)"

    # Group by directory
    file_blocks = [b for b in blocks if b.file_path]
    if not file_blocks:
        # Show non-file blocks (tool results, compaction summaries)
        lines: list[str] = []
        for b in blocks:
            status = _status_marker(b)
            label = b.summary or b.content.replace("\n", " ")[:40]
            lines.append(f"  {status} {label:<{width - 4}}  {b.tokens}t")
        return "\n".join(lines) if lines else "  (no blocks)"

    # Group by dir
    tree: dict[str, list[ContextBlock]] = {}
    for b in file_blocks:
        d = str(Path(b.file_path).parent) if b.file_path else "."
        tree.setdefault(d, []).append(b)

    lines: list[str] = []
    for d, dir_blocks in sorted(tree.items()):
        lines.append(f"  [#7C8DB5]{d}/[/]")
        for b in dir_blocks:
            fname = Path(b.file_path).name if b.file_path else "?"
            status = _status_marker(b)
            lines.append(
                f"    {status} {fname:<{width - 8}}  {b.tokens}t"
            )
    return "\n".join(lines)


def _status_marker(block: ContextBlock) -> str:
    """Return a status marker string for a context block."""
    if block.pinned:
        return "[#5B8DEE]P[/]"
    if block.excluded:
        return "[#E0556A]X[/]"
    if _is_stale(block):
        return "[#D4A853]S[/]"
    if block.file_path and _drift_check(block):
        return "[#E0556A]D[/]"
    return "[#5FA874]*[/]"


def _token_bar(used: int, total: int, width: int = 30) -> str:
    """ASCII bar showing token budget usage.  Rich-compatible markup."""
    if total == 0:
        return "0/0t (0%)"
    pct = min(used / total, 1.0)
    filled = int(pct * width)
    empty = width - filled

    if pct < 0.5:
        color = "#5FA874"  # success
    elif pct < 0.8:
        color = "#D4A853"  # warning
    else:
        color = "#E0556A"  # error

    fill_str = f"[{color}]{'#' * filled}[/]" if filled > 0 else ""
    bar = f"[{fill_str}{' ' * empty}]"
    return f"{bar} {used:,}/{total:,}t ({pct:.0%})"


# ---------------------------------------------------------------------------
# Context Inspector Screen
# ---------------------------------------------------------------------------


class ContextInspector(ModalScreen[None]):
    """Overlay showing agent context window state.

    Use: push_screen(ContextInspector(context_manager))
    """

    CSS = """
    ContextInspector {
        align: center middle;
        background: $background 90%;
    }

    ContextInspector #inspector-box {
        width: 90%;
        height: 90%;
        background: $surface;
        border: solid $primary 40%;
        padding: 1 2;
    }

    ContextInspector #token-bar {
        height: 1;
        margin-bottom: 1;
    }

    ContextInspector #file-tree {
        height: 1fr;
        overflow-y: auto;
    }

    ContextInspector #tool-stats {
        height: auto;
        margin-top: 1;
        border-top: solid $primary 15%;
        padding-top: 1;
    }

    ContextInspector #help-bar {
        height: 1;
        margin-top: 1;
        border-top: solid $primary 15%;
        padding-top: 1;
        color: $text 40%;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "dismiss", "Back"),
        Binding("q", "dismiss", "Back"),
        Binding("r", "refresh", "Refresh"),
        Binding("p", "toggle_pin", "Pin"),
        Binding("x", "toggle_exclude", "Exclude"),
        Binding("t", "sort_by_tokens", "ByTokens"),
        Binding("s", "sort_by_status", "ByStatus"),
    ]

    def __init__(
        self,
        context_manager: ContextManager | None = None,
        name: str = "Context Inspector",
        id: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id)
        self.ctx = context_manager or ContextManager()
        self._sort = "order"  # order, tokens, status

    def compose(self) -> ComposeResult:
        with Vertical(id="inspector-box"):
            yield Label("", id="token-bar")
            yield Label("", id="file-tree")
            yield Label("", id="tool-stats")
            yield Label("", id="help-bar")

    def on_mount(self) -> None:
        self._render_all()

    def _render_all(self) -> None:
        """Render all sections of the inspector."""
        # Token bar
        used = self.ctx.total_tokens
        total = self.ctx.context_window_tokens
        bar = _token_bar(used, total)
        compact_pct = 0.80
        total - used
        compact_at = int(total * compact_pct)

        if used >= compact_at:
            note = " [$error]Compaction triggered[/]"
        else:
            note = f" Compaction at {compact_pct:.0%} - {max(0, compact_at - used):,}t free"

        self.query_one("#token-bar", Label).update(
            f"[bold #5B8DEE]Token Usage[/]  {bar}{note}"
        )

        # File tree
        blocks = self._sorted_blocks()
        tree = _format_file_tree(blocks, width=50)

        header = "[bold #5B8DEE]Files in Context[/]\n"
        header += "  [#7C8DB5]P=pinned X=excluded S=stale D=drifted *=ok[/]\n"
        self.query_one("#file-tree", Label).update(
            header + tree
        )

        # Tool stats
        tool_blocks = [b for b in blocks if b.tool_name]
        if tool_blocks:
            tool_counts: dict[str, int] = {}
            tool_tokens: dict[str, int] = {}
            for b in tool_blocks:
                name = b.tool_name or "?"
                tool_counts[name] = tool_counts.get(name, 0) + 1
                tool_tokens[name] = tool_tokens.get(name, 0) + b.tokens

            lines = ["[bold #5B8DEE]Tools Used[/]"]
            for name in sorted(tool_counts, key=lambda n: tool_tokens[n], reverse=True):
                calls = tool_counts[name]
                tokens = tool_tokens[name]
                pct = (tokens / max(1, used)) * 100
                lines.append(
                    f"  [#7C8DB5]{name:<20}[/] "
                    f"{calls:>3} calls  {tokens:>6}t  {pct:>5.1f}%"
                )
            self.query_one("#tool-stats", Label).update("\n".join(lines))
        else:
            self.query_one("#tool-stats", Label).update("")

        # Help bar
        self.query_one("#help-bar", Label).update(
            "[#7C8DB5][p]in [x]exclude [t]okens [s]tatus [r]efresh [q] back[/]"
        )

    def _sorted_blocks(self) -> list[ContextBlock]:
        """Get blocks sorted according to current sort mode."""
        blocks = self.ctx.get_active_blocks()
        if self._sort == "tokens":
            blocks.sort(key=lambda b: b.tokens, reverse=True)
        elif self._sort == "status":
            # Show problems first: drift, stale, large
            def status_priority(b: ContextBlock) -> int:
                if b.excluded:
                    return 4
                if _drift_check(b):
                    return 0
                if _is_stale(b):
                    return 1
                if b.tokens > 5000:
                    return 2
                return 3

            blocks.sort(key=status_priority)
        return blocks

    def action_refresh(self) -> None:
        self._render_all()

    def action_toggle_pin(self) -> None:
        """Toggle pin on the largest non-pinned block (simple demo UX)."""
        blocks = [b for b in self.ctx.get_active_blocks() if not b.pinned and not b.excluded]
        if not blocks:
            return
        largest = max(blocks, key=lambda b: b.tokens)
        self.ctx.pin_block(largest.block_id)
        self._render_all()

    def action_toggle_exclude(self) -> None:
        """Toggle exclude on the largest non-excluded, non-pinned block."""
        blocks = [b for b in self.ctx.get_active_blocks() if not b.pinned and not b.excluded]
        if not blocks:
            return
        largest = max(blocks, key=lambda b: b.tokens)
        self.ctx.exclude_block(largest.block_id)
        self._render_all()

    def action_sort_by_tokens(self) -> None:
        self._sort = "tokens"
        self._render_all()

    def action_sort_by_status(self) -> None:
        self._sort = "status"
        self._render_all()

    def action_dismiss(self) -> None:
        self.dismiss()
