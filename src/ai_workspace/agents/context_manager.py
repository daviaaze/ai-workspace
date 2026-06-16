"""
ContextManager — agent context window observability and management.

Provides:
- Context block tracking (id, type, content, tokens, pinned status)
- Token budget visualization (how much of the context window is used)
- Pin/exclude/delete operations on context blocks
- Session context tree traversal
- Formatting for agent injection
- Save/load context snapshots to knowledge base

Design:
  The agent's context window is its most valuable and constrained resource.
  Managing it well = better agent performance + lower costs.

  ContextManager gives the user (and software) control over what goes into
  the context window, with a Obsidian-graph-like mental model:
  - Each message, tool call, file, and context block is a "node"
  - Nodes are connected by parent/child and reference edges
  - The user can pin critical nodes, exclude noise, and save insights

Usage:
    mgr = ContextManager(context_window_tokens=128_000)
    mgr.add_block("conversation", "User asked about auth middleware", tokens=30)
    mgr.add_block("file_read", "# auth.py\n...", file_path="src/auth.py", tokens=200)
    mgr.pin_block(block_id)  # Always include
    mgr.exclude_block(block_id)  # Never include
    formatted = mgr.format_for_injection(max_tokens=100_000)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any


class BlockType(Enum):
    """Types of context blocks that can appear in an agent's context window."""
    USER_MESSAGE = auto()        # 📝 User message
    ASSISTANT_RESPONSE = auto()  # 🤖 Agent response
    TOOL_CALL = auto()           # 🔧 Tool invocation (write_file, shell, etc.)
    TOOL_RESULT = auto()         # 📋 Tool output
    FILE_READ = auto()           # 📄 File content read by agent
    FILE_EDIT = auto()           # ✏️ File edited by agent
    PROJECT_CONTEXT = auto()     # 📁 Auto-injected project info (git, tree)
    SESSION_CONTEXT = auto()     # 🧠 Session history summary
    COMPACTION = auto()          # 📦 Auto-generated compaction summary
    PINNED_KB = auto()           # 📌 User-pinned knowledge base entry
    SYSTEM_PROMPT = auto()       # ⚙️ System instructions
    CUSTOM = auto()              # 📎 User-defined context block


BLOCK_ICONS: dict[BlockType, str] = {
    BlockType.USER_MESSAGE: "📝",
    BlockType.ASSISTANT_RESPONSE: "🤖",
    BlockType.TOOL_CALL: "🔧",
    BlockType.TOOL_RESULT: "📋",
    BlockType.FILE_READ: "📄",
    BlockType.FILE_EDIT: "✏️",
    BlockType.PROJECT_CONTEXT: "📁",
    BlockType.SESSION_CONTEXT: "🧠",
    BlockType.COMPACTION: "📦",
    BlockType.PINNED_KB: "📌",
    BlockType.SYSTEM_PROMPT: "⚙️",
    BlockType.CUSTOM: "📎",
}


@dataclass
class ContextBlock:
    """A single block of context in the agent's window."""
    block_id: str
    block_type: BlockType
    content: str
    summary: str = ""               # Short description (1 line)
    tokens: int = 0                 # Estimated token count
    pinned: bool = False            # Always include, even if over budget
    excluded: bool = False          # Never include
    parent_id: str | None = None    # Parent block in conversation tree
    children_ids: list[str] = field(default_factory=list)
    
    # Metadata
    file_path: str | None = None    # If type is FILE_* 
    tool_name: str | None = None    # If type is TOOL_*
    timestamp: float = field(default_factory=time.time)
    importance: float = 0.5         # 0.0 = trivia, 1.0 = critical
    
    def estimate_tokens(self) -> int:
        """Estimate tokens from content (rough: 1 token ≈ 4 chars)."""
        if not self.content:
            return 0
        return max(1, len(self.content) // 4)
    
    def refresh_tokens(self) -> None:
        """Recalculate token estimate."""
        self.tokens = self.estimate_tokens()
    
    @property
    def icon(self) -> str:
        return BLOCK_ICONS.get(self.block_type, "•")
    
    @property
    def display_label(self) -> str:
        """One-line label for tree/graph display."""
        icon = self.icon
        status = ""
        if self.pinned:
            status = " 📌"
        elif self.excluded:
            status = " 🗑️"
        
        if self.summary:
            label = self.summary[:60]
        else:
            label = self.content.replace("\n", " ")[:60]
        
        token_info = f" ({self.tokens}t)"
        return f"{icon} {label}{status}{token_info}"


@dataclass
class ContextSnapshot:
    """A saved snapshot of the context window for later restoration."""
    snapshot_id: str
    label: str
    blocks: list[ContextBlock]
    created_at: float = field(default_factory=time.time)
    session_id: str | None = None


class ContextManager:
    """Manages the agent's context window with observability.
    
    Tracks all context blocks, their token usage, and provides
    operations to pin, exclude, reorder, and save context.
    
    The context window has a token budget (e.g., 128K for qwen3:14b).
    The manager helps stay within budget by:
    - Tracking token usage per block
    - Auto-excluding low-importance blocks when over budget
    - Respecting pinned blocks (always included)
    - Respecting excluded blocks (never included)
    """
    
    def __init__(
        self,
        context_window_tokens: int = 128_000,
        max_context_chars: int = 50_000,
        session_id: str | None = None,
    ):
        self.context_window_tokens = context_window_tokens
        self.max_context_chars = max_context_chars
        self.session_id = session_id
        self._blocks: dict[str, ContextBlock] = {}
        self._block_order: list[str] = []  # Ordered block IDs
        self._pinned_ids: set[str] = set()
        self._excluded_ids: set[str] = set()
        self._snapshots: dict[str, ContextSnapshot] = {}
    
    # ─── Block CRUD ────────────────────────────────────
    
    def add_block(
        self,
        block_type: BlockType,
        content: str,
        summary: str = "",
        parent_id: str | None = None,
        file_path: str | None = None,
        tool_name: str | None = None,
        importance: float = 0.5,
        block_id: str | None = None,
    ) -> str:
        """Add a context block. Returns the block_id."""
        bid = block_id or str(uuid.uuid4())[:12]
        
        block = ContextBlock(
            block_id=bid,
            block_type=block_type,
            content=content,
            summary=summary,
            tokens=0,  # Will be calculated
            parent_id=parent_id,
            file_path=file_path,
            tool_name=tool_name,
            importance=importance,
        )
        block.refresh_tokens()
        
        self._blocks[bid] = block
        self._block_order.append(bid)
        
        # Link to parent
        if parent_id and parent_id in self._blocks:
            parent = self._blocks[parent_id]
            if bid not in parent.children_ids:
                parent.children_ids.append(bid)
        
        return bid
    
    def get_block(self, block_id: str) -> ContextBlock | None:
        return self._blocks.get(block_id)
    
    def remove_block(self, block_id: str) -> bool:
        """Remove a block and its children from the context."""
        if block_id not in self._blocks:
            return False
        
        block = self._blocks[block_id]
        
        # Remove children recursively
        for child_id in list(block.children_ids):
            self.remove_block(child_id)
        
        # Remove from parent's children list
        if block.parent_id and block.parent_id in self._blocks:
            parent = self._blocks[block.parent_id]
            if block_id in parent.children_ids:
                parent.children_ids.remove(block_id)
        
        del self._blocks[block_id]
        if block_id in self._block_order:
            self._block_order.remove(block_id)
        self._pinned_ids.discard(block_id)
        self._excluded_ids.discard(block_id)
        
        return True
    
    def update_block(self, block_id: str, **kwargs) -> ContextBlock | None:
        """Update block fields. Recalculates tokens if content changes."""
        block = self._blocks.get(block_id)
        if not block:
            return None
        
        for key, value in kwargs.items():
            if hasattr(block, key):
                setattr(block, key, value)
        
        if 'content' in kwargs:
            block.refresh_tokens()
        
        return block
    
    # ─── Pin / Exclude ─────────────────────────────────
    
    def pin_block(self, block_id: str) -> bool:
        """Pin a block — always included regardless of budget."""
        block = self._blocks.get(block_id)
        if not block:
            return False
        block.pinned = True
        block.excluded = False
        self._pinned_ids.add(block_id)
        self._excluded_ids.discard(block_id)
        return True
    
    def unpin_block(self, block_id: str) -> bool:
        """Unpin a block."""
        block = self._blocks.get(block_id)
        if not block:
            return False
        block.pinned = False
        self._pinned_ids.discard(block_id)
        return True
    
    def exclude_block(self, block_id: str) -> bool:
        """Exclude a block — never included in context."""
        block = self._blocks.get(block_id)
        if not block:
            return False
        block.excluded = True
        block.pinned = False
        self._excluded_ids.add(block_id)
        self._pinned_ids.discard(block_id)
        return True
    
    def include_block(self, block_id: str) -> bool:
        """Re-include a previously excluded block."""
        block = self._blocks.get(block_id)
        if not block:
            return False
        block.excluded = False
        self._excluded_ids.discard(block_id)
        return True
    
    def toggle_pin(self, block_id: str) -> str:
        """Toggle pin status. Returns 'pinned', 'unpinned', or 'not_found'."""
        block = self._blocks.get(block_id)
        if not block:
            return "not_found"
        if block.pinned:
            self.unpin_block(block_id)
            return "unpinned"
        else:
            self.pin_block(block_id)
            return "pinned"
    
    def toggle_exclude(self, block_id: str) -> str:
        """Toggle exclude status. Returns 'excluded', 'included', or 'not_found'."""
        block = self._blocks.get(block_id)
        if not block:
            return "not_found"
        if block.excluded:
            self.include_block(block_id)
            return "included"
        else:
            self.exclude_block(block_id)
            return "excluded"
    
    # ─── Token Budget ──────────────────────────────────
    
    @property
    def total_tokens(self) -> int:
        """Total tokens of all non-excluded blocks."""
        return sum(
            b.tokens for b in self._blocks.values()
            if not b.excluded
        )
    
    @property
    def pinned_tokens(self) -> int:
        """Tokens consumed by pinned blocks."""
        return sum(
            b.tokens for b in self._blocks.values()
            if b.pinned and not b.excluded
        )
    
    @property
    def budget_used_pct(self) -> float:
        """Percentage of token budget used."""
        if self.context_window_tokens == 0:
            return 0.0
        return (self.total_tokens / self.context_window_tokens) * 100
    
    @property
    def budget_status(self) -> str:
        """Human-readable budget status."""
        pct = self.budget_used_pct
        if pct < 30:
            return "🟢 Plenty of room"
        elif pct < 60:
            return "🟡 Getting full"
        elif pct < 85:
            return "🟠 Near capacity"
        else:
            return "🔴 Critical — over budget"
    
    def get_budget_bar(self, width: int = 20) -> str:
        """ASCII bar showing token budget usage."""
        pct = min(self.budget_used_pct, 100)
        filled = int((pct / 100) * width)
        empty = width - filled
        
        if pct < 50:
            bar_char = "█"
        elif pct < 80:
            bar_char = "▓"
        else:
            bar_char = "▒"
        
        return f"[{bar_char * filled}{'░' * empty}] {self.total_tokens:,}/{self.context_window_tokens:,}t ({pct:.0f}%)"
    
    def get_largest_blocks(self, n: int = 5) -> list[ContextBlock]:
        """Get the N largest blocks by token count (for trimming suggestions)."""
        active = [b for b in self._blocks.values() if not b.excluded and not b.pinned]
        active.sort(key=lambda b: b.tokens, reverse=True)
        return active[:n]
    
    # ─── Formatting ────────────────────────────────────
    
    def get_active_blocks(self) -> list[ContextBlock]:
        """Get blocks that would be included in the context window, in order."""
        return [
            self._blocks[bid]
            for bid in self._block_order
            if bid in self._blocks
            and not self._blocks[bid].excluded
        ]
    
    def format_for_injection(
        self,
        max_tokens: int | None = None,
        include_pinned: bool = True,
    ) -> str:
        """Format the context window for injection into the agent prompt.
        
        Builds a structured context string with sections for each block type.
        Respects pin/exclude status and token budget.
        
        Args:
            max_tokens: Override max tokens (default: context_window_tokens)
            include_pinned: Whether to include pinned blocks
        """
        max_t = max_tokens or self.context_window_tokens
        parts: list[str] = []
        tokens_used = 0
        
        # Format header
        parts.append(
            f"<context_window budget=\"{max_t}\" used=\"{self.total_tokens}\" "
            f"pinned=\"{self.pinned_tokens}\">"
        )
        
        # Group blocks by type for structured output
        type_order = [
            BlockType.PINNED_KB,
            BlockType.PROJECT_CONTEXT,
            BlockType.SESSION_CONTEXT,
            BlockType.COMPACTION,
            BlockType.FILE_READ,
            BlockType.USER_MESSAGE,
            BlockType.TOOL_CALL,
            BlockType.TOOL_RESULT,
            BlockType.ASSISTANT_RESPONSE,
        ]
        
        for block_type in type_order:
            type_blocks = [
                b for b in self.get_active_blocks()
                if b.block_type == block_type
            ]
            if not type_blocks:
                continue
            
            section_name = block_type.name.lower().replace("_", " ")
            parts.append(f"  <{section_name}>")
            
            for block in type_blocks:
                if tokens_used + block.tokens > max_t and not block.pinned:
                    parts.append(
                        f"    <!-- {block.summary[:40]}... "
                        f"[trimmed: budget exceeded] -->"
                    )
                    continue
                
                content = block.content
                # Truncate very long blocks
                if block.tokens > 5000 and block.tokens > (max_t - tokens_used):
                    content = content[:2000] + "\n... [truncated for budget]"
                
                if block.file_path:
                    parts.append(f"    <!-- file: {block.file_path} -->")
                if block.summary and block.summary != content[:60]:
                    parts.append(f"    <!-- {block.summary[:80]} -->")
                
                parts.append(f"    {content}")
                tokens_used += block.tokens
            
            parts.append(f"  </{section_name}>")
        
        parts.append("</context_window>")
        return "\n".join(parts)
    
    # ─── Snapshots ─────────────────────────────────────
    
    def save_snapshot(self, label: str) -> str:
        """Save the current context state as a named snapshot."""
        snapshot_id = str(uuid.uuid4())[:12]
        blocks_copy = [
            ContextBlock(
                block_id=b.block_id,
                block_type=b.block_type,
                content=b.content,
                summary=b.summary,
                tokens=b.tokens,
                pinned=b.pinned,
                excluded=b.excluded,
                parent_id=b.parent_id,
                children_ids=list(b.children_ids),
                file_path=b.file_path,
                tool_name=b.tool_name,
                timestamp=b.timestamp,
                importance=b.importance,
            )
            for b in self._blocks.values()
        ]
        snapshot = ContextSnapshot(
            snapshot_id=snapshot_id,
            label=label,
            blocks=blocks_copy,
            session_id=self.session_id,
        )
        self._snapshots[snapshot_id] = snapshot
        return snapshot_id
    
    def load_snapshot(self, snapshot_id: str) -> bool:
        """Restore context from a saved snapshot."""
        snapshot = self._snapshots.get(snapshot_id)
        if not snapshot:
            return False
        
        self._blocks.clear()
        self._block_order.clear()
        self._pinned_ids.clear()
        self._excluded_ids.clear()
        
        for block in snapshot.blocks:
            self._blocks[block.block_id] = block
            self._block_order.append(block.block_id)
            if block.pinned:
                self._pinned_ids.add(block.block_id)
            if block.excluded:
                self._excluded_ids.add(block.block_id)
        
        return True
    
    def list_snapshots(self) -> list[dict[str, Any]]:
        """List saved snapshots."""
        return [
            {
                "id": s.snapshot_id,
                "label": s.label,
                "blocks": len(s.blocks),
                "created_at": s.created_at,
                "session_id": s.session_id,
            }
            for s in self._snapshots.values()
        ]
    
    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a saved snapshot."""
        if snapshot_id in self._snapshots:
            del self._snapshots[snapshot_id]
            return True
        return False
    
    # ─── Bulk Operations ───────────────────────────────
    
    def auto_trim(self, target_tokens: int | None = None) -> int:
        """Auto-trim context to fit within token budget.
        
        Strategy:
        1. Always keep pinned blocks
        2. Keep most recent blocks (by order)
        3. Exclude low-importance blocks first
        4. Compaction summaries have priority over old messages
        
        Returns number of blocks trimmed.
        """
        target = target_tokens or int(self.context_window_tokens * 0.8)
        trimmed = 0
        
        # Get non-pinned, non-excluded blocks sorted by:
        # (importance ASC, timestamp ASC) — trim lowest first
        trimmable = [
            b for b in self._blocks.values()
            if not b.pinned and not b.excluded
            and b.block_type != BlockType.SYSTEM_PROMPT
        ]
        trimmable.sort(key=lambda b: (b.importance, b.timestamp))
        
        current_tokens = self.total_tokens
        
        for block in trimmable:
            if current_tokens <= target:
                break
            self.exclude_block(block.block_id)
            current_tokens -= block.tokens
            trimmed += 1
        
        return trimmed
    
    def auto_pin_important(self, threshold: float = 0.8) -> int:
        """Auto-pin high-importance blocks."""
        pinned = 0
        for block in self._blocks.values():
            if block.importance >= threshold and not block.pinned:
                self.pin_block(block.block_id)
                pinned += 1
        return pinned
    
    def import_from_session(
        self,
        session_entries: list[Any],  # SessionEntry objects
        include_tool_results: bool = True,
    ) -> int:
        """Import context blocks from session entries."""
        imported = 0
        for entry in session_entries:
            entry_type = getattr(entry, 'entry_type', 'message')
            role = getattr(entry, 'role', '')
            content = getattr(entry, 'content', '') or ''
            
            if entry_type == 'message':
                if role == 'user':
                    btype = BlockType.USER_MESSAGE
                elif role == 'assistant':
                    btype = BlockType.ASSISTANT_RESPONSE
                elif role == 'tool_result':
                    if not include_tool_results:
                        continue
                    btype = BlockType.TOOL_RESULT
                else:
                    btype = BlockType.CUSTOM
            elif entry_type == 'compaction':
                btype = BlockType.COMPACTION
            else:
                btype = BlockType.CUSTOM
            
            parent_id = getattr(entry, 'parent_id', None)
            block_id = getattr(entry, 'id', None)
            
            self.add_block(
                block_type=btype,
                content=content,
                summary=content[:80].replace("\n", " "),
                parent_id=parent_id,
                block_id=block_id,
                importance=0.7 if role == 'user' else 0.5,
            )
            imported += 1
        
        return imported
    
    def clear(self) -> None:
        """Clear all blocks and state."""
        self._blocks.clear()
        self._block_order.clear()
        self._pinned_ids.clear()
        self._excluded_ids.clear()
    
    # ─── Stats ─────────────────────────────────────────
    
    def stats(self) -> dict[str, Any]:
        """Get context manager statistics."""
        blocks_by_type: dict[str, int] = {}
        for b in self._blocks.values():
            tname = b.block_type.name
            blocks_by_type[tname] = blocks_by_type.get(tname, 0) + 1
        
        return {
            "total_blocks": len(self._blocks),
            "active_blocks": len(self.get_active_blocks()),
            "pinned_blocks": len(self._pinned_ids),
            "excluded_blocks": len(self._excluded_ids),
            "total_tokens": self.total_tokens,
            "pinned_tokens": self.pinned_tokens,
            "budget_used_pct": round(self.budget_used_pct, 1),
            "budget_status": self.budget_status,
            "blocks_by_type": blocks_by_type,
            "snapshots": len(self._snapshots),
        }
