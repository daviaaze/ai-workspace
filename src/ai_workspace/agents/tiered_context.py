"""
Tiered Context Loading — Token-Economy Context Construction.

OpenViking-inspired L0/L1/L2 tiered context loading with directory-based
retrieval and retrieval trajectory visualization.

Architecture:
- L0: Always-injected (system prompt, active task, pinned context)
- L1: On-demand (KB entries, recent tool results, session context)
- L2: Expanded (full documents, trace details, raw file contents)

Usage::

    loader = TieredContextLoader()
    loader.set_task("Refactor auth middleware")

    # Build context progressively
    ctx = loader.get_context(tier="L0")         # Light, always available
    ctx = loader.get_context(tier="L1")         # Add KB entries, recent tools
    ctx = loader.get_context(tier="L2")         # Full expanded context

    # Track retrieval trajectory
    trajectory = loader.trajectory
    for step in trajectory:
        print(f"{step.tier} | {step.source} | {step.query} | score={step.score}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from ai_workspace.agents.context_manager import (
    BlockType,
    ContextBlock,
    ContextManager,
)

logger = logging.getLogger("aiw.tiered_context")


# ═══════════════════════════════════════════════════════════
# Enums & Data Types
# ═══════════════════════════════════════════════════════════


class ContextTier(str, Enum):
    """Loading tier for context blocks.

    - ``L0``: Always injected. System prompt, active task, pinned context.
    - ``L1``: On-demand. KB entries, tool results, session context.
    - ``L2``: Expanded. Full documents, trace details, raw file contents.
    """

    L0 = "L0"
    L1 = "L1"
    L2 = "L2"


@dataclass
class RetrievalStep:
    """A single step in the retrieval trajectory.

    Records how a piece of context was found — the engine, query,
    source path, and relevance score. Makes context sourcing auditable.
    """

    tier: ContextTier  # L0, L1, or L2
    source: str  # File path, doc name, or KB reference
    query: str  # The search query or trigger
    score: float = 0.0  # Relevance score if applicable
    engine: str = ""  # Which engine found it (if any)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    content_preview: str = ""  # First 100 chars of what was loaded
    tokens: int = 0  # Token count for this step


@dataclass
class TieredContextConfig:
    """Configuration for tiered context loading.

    Attributes:
        l0_max_tokens: Max tokens always injected (default: 8K).
        l1_max_tokens: Max tokens for on-demand loading (default: 32K).
        l2_max_tokens: Max tokens for expanded loading (default: 128K).
        l1_max_sources: Max sources to include in L1 (default: 10).
        l2_max_sources: Max sources to include in L2 (default: 5).
        context_dir: Directory-based context root (for dir-based retrieval).
        enable_trajectory: Track retrieval steps (default: True).
    """

    l0_max_tokens: int = 8_000
    l1_max_tokens: int = 32_000
    l2_max_tokens: int = 128_000
    l1_max_sources: int = 10
    l2_max_sources: int = 5
    context_dir: str | None = None
    enable_trajectory: bool = True


# ═══════════════════════════════════════════════════════════
# TieredContextLoader
# ═══════════════════════════════════════════════════════════


class TieredContextLoader:
    """Build context progressively across tiers.

    The loader wraps a ``ContextManager`` for block tracking and adds
    tier-aware loading logic. Each tier adds more context on top of
    the previous one, respecting token budgets per tier.

    Args:
        config: Tier configuration. See ``TieredContextConfig``.
        context_manager: Optional existing ``ContextManager`` instance.
            Creates a new one if not provided.
    """

    def __init__(
        self,
        config: TieredContextConfig | None = None,
        context_manager: ContextManager | None = None,
    ):
        self.config = config or TieredContextConfig()
        self._cm = context_manager or ContextManager(
            context_window_tokens=self.config.l2_max_tokens,
        )
        self._trajectory: list[RetrievalStep] = []
        self._task: str = ""
        self._system_prompt: str = ""
        self._context_dir: Path | None = None

        if self.config.context_dir:
            self._context_dir = Path(self.config.context_dir).expanduser()

    # ── Properties ─────────────────────────────────────────────────────────

    @property
    def trajectory(self) -> list[RetrievalStep]:
        """Retrieval trajectory — how each context piece was found.

        Empty if ``enable_trajectory`` is False.
        """
        return list(self._trajectory)

    @property
    def context_manager(self) -> ContextManager:
        """The underlying context manager."""
        return self._cm

    @property
    def task(self) -> str:
        """Current active task."""
        return self._task

    # ── Configuration ───────────────────────────────────────────────────────

    def set_task(self, task: str) -> None:
        """Set the current active task (injected as L0 context)."""
        self._task = task

    def set_system_prompt(self, prompt: str) -> None:
        """Set the system prompt (injected as L0 context)."""
        self._system_prompt = prompt

    def set_context_dir(self, path: str | Path) -> None:
        """Set the directory-based context root.

        Directory-based contexts are organized by topic directories
        instead of flat vector search. Each subdirectory represents
        a context surface (e.g. ``architecture/``, ``database/``,
        ``api/``).
        """
        self._context_dir = Path(path).expanduser()
        if not self._context_dir.is_dir():
            logger.warning(
                "Context directory does not exist: %s", self._context_dir,
            )

    # ── Context Construction ────────────────────────────────────────────────

    def get_context(
        self,
        tier: str | ContextTier = "L1",
        extra_context: str = "",
    ) -> str:
        """Build context up to the specified tier.

        Each tier includes all context from lower tiers plus its own.

        Args:
            tier: Target tier (``\"L0\"``, ``\"L1\"``, or ``\"L2\"``).
            extra_context: Additional context to include at L0.

        Returns:
            Formatted context string ready for LLM injection.
        """
        tier = ContextTier(tier.upper() if isinstance(tier, str) else tier)

        parts: list[str] = []

        # L0: Always injected
        parts.extend(self._build_l0(extra_context))

        if tier == ContextTier.L0:
            result = self._join(parts)
            self._record_trajectory("L0", len(result))
            return result

        # L1: On-demand
        l1_context = self._build_l1()
        if l1_context:
            parts.append("")
            parts.append("=== ON-DEMAND CONTEXT (L1) ===")
            parts.extend(l1_context)

        if tier == ContextTier.L1:
            result = self._join(parts)
            self._record_trajectory("L1", len(result))
            return result

        # L2: Expanded
        l2_context = self._build_l2()
        if l2_context:
            parts.append("")
            parts.append("=== EXPANDED CONTEXT (L2) ===")
            parts.extend(l2_context)

        result = self._join(parts)
        self._record_trajectory("L2", len(result))
        return result

    def get_context_blocks(
        self,
        tier: str | ContextTier = "L1",
    ) -> list[ContextBlock]:
        """Get context blocks up to the specified tier.

        Returns blocks rather than a formatted string, for direct
        injection into the ``ContextManager``.
        """
        tier = ContextTier(tier.upper() if isinstance(tier, str) else tier)

        blocks: list[ContextBlock] = []

        # L0 pinned blocks from context manager
        for block in self._cm.get_active_blocks():
            if block.pinned:
                blocks.append(block)

        if tier == ContextTier.L0:
            return blocks

        # L1: non-pinned blocks sorted by recency
        for block in self._cm.get_active_blocks():
            if not block.pinned and not block.excluded:
                blocks.append(block)
                if len(blocks) >= self.config.l1_max_sources:
                    break

        if tier == ContextTier.L1:
            return blocks

        # L2: all blocks including expanded
        for block in self._cm.get_active_blocks():
            if block not in blocks:
                blocks.append(block)

        return blocks

    # ── L0 Builders ─────────────────────────────────────────────────────────

    def _build_l0(self, extra_context: str = "") -> list[str]:
        """Build L0 context: system prompt + active task + pinned context.

        This is always injected in every call.
        """
        parts: list[str] = []
        parts.append("=== SYSTEM CONTEXT (L0) ===")

        if self._system_prompt:
            parts.append(f"<system>{self._system_prompt}</system>")

        if self._task:
            parts.append(f"<task>{self._task}</task>")

        if extra_context:
            parts.append(f"<extra>{extra_context}</extra>")

        # Pinned context blocks from the context manager
        pinned = self._cm.get_active_blocks()
        pinned = [b for b in pinned if b.pinned]
        if pinned:
            parts.append("")
            parts.append("--- Pinned Context ---")
            for block in pinned[:5]:  # Limit to top 5 pinned
                label = block.summary or block.content[:80]
                parts.append(f"  [{block.block_type.name}] {label}")

        return parts

    # ── L1 Builders ─────────────────────────────────────────────────────────

    def _build_l1(self) -> list[str]:
        """Build L1 context: knowledge base entries + recent tool results.

        Loaded on-demand. Pulls from the context manager's active
        (non-pinned, non-excluded) blocks plus directory-based KB.
        """
        parts: list[str] = []

        # Active blocks from context manager
        active = [
            b for b in self._cm.get_active_blocks()
            if not b.pinned and not b.excluded
        ]
        if active:
            parts.append("--- Recent Context Blocks ---")
            for block in active[:self.config.l1_max_sources]:
                summary = block.summary or block.content[:80]
                parts.append(
                    f"  [{block.block_type.name}] {summary[:120]}"
                    f"  ({block.tokens}t, imp={block.importance:.1f})"
                )

        # Directory-based KB retrieval
        dir_context = self._retrieve_directory(self._task, max_items=5)
        if dir_context:
            parts.append("--- Knowledge Base (L1) ---")
            parts.extend(dir_context)

        return parts

    # ── L2 Builders ─────────────────────────────────────────────────────────

    def _build_l2(self) -> list[str]:
        """Build L2 context: expanded documents and full content.

        The full expanded view — retrieves full file contents,
        detailed session traces, and verbose KB entries.
        """
        parts: list[str] = []

        # Full directory context
        dir_context = self._retrieve_directory(
            self._task,
            max_items=self.config.l2_max_sources,
            expanded=True,
        )
        if dir_context:
            parts.append("--- Full Documents (L2) ---")
            parts.extend(dir_context)

        # Full active block content
        active = self._cm.get_active_blocks()
        for block in active[:3]:  # Top 3 most important
            if block.content and len(block.content) > 200:
                parts.append("")
                parts.append(f"--- Expanded: {block.summary[:60] or block.block_type.name} ---")
                parts.append(block.content[:2000])

        return parts

    # ── Directory-Based Retrieval ───────────────────────────────────────────

    def _retrieve_directory(
        self,
        query: str,
        max_items: int = 5,
        expanded: bool = False,
    ) -> list[str]:
        """Retrieve context from the directory-based knowledge store.

        ``context_dir`` is organized as::

            context_dir/
            ├── architecture/
            │   ├── overview.md
            │   └── decisions.md
            ├── database/
            │   └── schema.md
            └── api/
                ├── endpoints.md
                └── auth.md

        Retrieval strategy:
        1. Match query tokens to directory names (surface-level)
        2. Scan matching directories for relevant files
        3. Return content up to the tier's budget

        Args:
            query: Search query (typically the task description).
            max_items: Maximum files to include.
            expanded: If True, include full file content.
                If False, include truncated previews.

        Returns:
            List of markdown-formatted context strings.
        """
        if not self._context_dir or not self._context_dir.is_dir():
            return []

        query_lower = query.lower() if query else ""
        query_tokens = set(query_lower.split()) if query_lower else set()

        scored_files: list[tuple[float, Path]] = []

        # Walk the context directory
        for path in self._context_dir.rglob("*"):
            if not path.is_file() or path.suffix not in (".md", ".txt", ".py"):
                continue

            rel = path.relative_to(self._context_dir)
            score = self._score_path(rel, query_tokens)

            if score > 0:
                scored_files.append((score, path))

        # Sort by score descending
        scored_files.sort(key=lambda x: x[0], reverse=True)
        top = scored_files[:max_items]

        parts: list[str] = []
        for score, path in top:
            rel = path.relative_to(self._context_dir)
            try:
                content = path.read_text()
            except OSError:
                continue

            # Record trajectory
            self._add_trajectory_step(
                tier="L2" if expanded else "L1",
                source=str(rel),
                query=query or "(browse)",
                score=score,
                engine="directory",
                preview=content[:100],
            )

            if expanded:
                parts.append(f"### {rel}")
                parts.append(f"*Source: {path} (score={score:.2f})*")
                parts.append(content)
            else:
                content.split("\n")[0] if content else "(empty)"
                preview = content[:300].replace("\n", " ")
                parts.append(f"- **{rel}** — {preview[:100]}...")

        return parts

    # ── Trajectory ──────────────────────────────────────────────────────────

    def clear_trajectory(self) -> None:
        """Clear the retrieval trajectory."""
        self._trajectory.clear()

    def trajectory_summary(self) -> str:
        """Return a human-readable trajectory summary.

        Shows how each piece of context was found, making the
        retrieval process auditable (OpenViking's key insight).
        """
        if not self._trajectory:
            return "No retrieval steps recorded."

        lines = ["## Retrieval Trajectory\n"]
        for i, step in enumerate(self._trajectory, 1):
            source = step.source[:60]
            query = step.query[:40]
            lines.append(
                f"{i}. [{step.tier}] "
                f"{source} "
                f"← \"{query}\" "
                f"({step.engine}) "
                f"[score={step.score:.2f}]"
            )

        return "\n".join(lines)

    # ── Convenience ─────────────────────────────────────────────────────────

    def add_to_context(
        self,
        block_type: BlockType,
        content: str,
        summary: str = "",
        importance: float = 0.5,
        tier: str | ContextTier = "L1",
        **kwargs: Any,
    ) -> str:
        """Add a block to the context manager with tier annotation.

        Args:
            block_type: Type of context block.
            content: Block content.
            summary: One-line summary.
            importance: Importance score (0.0-1.0).
            tier: Which tier this belongs to.
            **kwargs: Additional args for add_block.

        Returns:
            Block ID.
        """
        block_id = self._cm.add_block(
            block_type=block_type,
            content=content,
            summary=summary,
            importance=importance,
            **kwargs,
        )

        self._add_trajectory_step(
            tier=str(tier),
            source=summary or block_type.name,
            query="",
            score=importance,
            engine="manual",
            preview=content[:100],
        )

        return block_id

    def add_l0_block(
        self,
        block_type: BlockType,
        content: str,
        summary: str = "",
    ) -> str:
        """Add a block that will be always injected (L0)."""
        block_id = self.add_to_context(
            block_type=block_type,
            content=content,
            summary=summary,
            importance=1.0,
            tier="L0",
        )
        # Pin the block so it's always included in context
        self._cm.pin_block(block_id)
        return block_id

    def stats(self) -> dict[str, Any]:
        """Get tier statistics."""
        return {
            "config": {
                "l0_max_tokens": self.config.l0_max_tokens,
                "l1_max_tokens": self.config.l1_max_tokens,
                "l2_max_tokens": self.config.l2_max_tokens,
            },
            "context_manager": self._cm.stats(),
            "trajectory_steps": len(self._trajectory),
            "task_set": bool(self._task),
            "context_dir": str(self._context_dir) if self._context_dir else None,
        }

    # ── Private Helpers ─────────────────────────────────────────────────────

    def _score_path(self, rel: Path, query_tokens: set[str]) -> float:
        """Score a relative path against query tokens.

        Matches directory/file names against query tokens.
        Returns 0-1 score.
        """
        if not query_tokens:
            return 0.5  # No query — still include in browse mode

        path_str = str(rel).lower()
        # Tokenize the path: split by /, -, ., _
        path_tokens = set(
            path_str.replace("/", " ").replace("-", " ").replace(".", " ").replace("_", " ").split()
        )

        if not path_tokens:
            return 0.0

        overlap = len(query_tokens & path_tokens)
        if overlap > 0:
            return overlap / len(query_tokens)

        # Substring match
        for token in query_tokens:
            if token in path_str:
                return 0.3

        return 0.0

    def _add_trajectory_step(
        self,
        tier: str | ContextTier,
        source: str,
        query: str,
        score: float,
        engine: str,
        preview: str,
        tokens: int = 0,
    ) -> None:
        """Add a step to the retrieval trajectory (if enabled)."""
        if not self.config.enable_trajectory:
            return

        if isinstance(tier, str):
            tier = ContextTier(tier)

        self._trajectory.append(RetrievalStep(
            tier=tier,
            source=source,
            query=query,
            score=score,
            engine=engine,
            content_preview=preview[:100],
            tokens=tokens,
        ))

    def _record_trajectory(self, tier: str | ContextTier, chars: int) -> None:
        """Record a summary step when get_context is called."""
        self._add_trajectory_step(
            tier=tier,
            source=f"get_context({tier})",
            query="",
            score=0.0,
            engine="loader",
            preview=f"Built context: ~{chars} chars",
        )

    @staticmethod
    def _join(parts: list[str]) -> str:
        """Join context parts with newlines."""
        return "\n".join(parts)
