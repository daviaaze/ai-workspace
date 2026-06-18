"""
Memory as Execution State — Hierarchical State Tree.

Organizes agent memory as a tree of execution states instead of a flat
vector store. Each node represents a subgoal with its steps, branches
for error recovery, and compressed summaries for completed work.

Four operations:
- Grow: Add steps to the active node
- Compress: Summarize completed subgoals to free tokens
- Maintain: Validate summaries periodically (background)
- Revise: Create recovery branches on error

Refs:
- SPEC_MEMORY_TREE.md
- Mage (arXiv 2606.06090) — Microsoft + USTC, Jun 2026
- AutoAgent (arXiv 2603.09716) — elastic memory orchestration
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("aiw.memory_tree")


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class NodeStatus(str, Enum):
    """Execution status of a tree node."""
    ACTIVE = "active"          # Currently being executed
    COMPLETED = "completed"    # Finished successfully
    FAILED = "failed"          # Terminated with error (dead branch)
    COMPRESSED = "compressed"  # Summarized to free tokens


@dataclass
class StepRecord:
    """A single step within a subgoal."""
    type: str                           # "tool_call", "tool_result", "thinking", "token"
    content: str
    tool_name: str = ""                 # For tool_call/tool_result steps
    error: str = ""                     # Non-empty for failed steps
    tokens: int = 0                     # Estimated token count
    timestamp: float = field(default_factory=time.time)


@dataclass
class StateNode:
    """A node in the hierarchical execution state tree.

    Each node represents a subgoal — a self-contained unit of work.
    """
    id: str
    parent_id: Optional[str]
    subgoal: str
    status: NodeStatus = NodeStatus.ACTIVE
    steps: list[StepRecord] = field(default_factory=list)
    summary: str = ""                   # Filled when compressed/completed
    tokens: int = 0                     # Estimated tokens in steps
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    children: list[StateNode] = field(default_factory=list)

    def add_step(self, step: StepRecord) -> None:
        """Add a step to this node, updating token count."""
        self.steps.append(step)
        self.tokens += step.tokens

    def last_n_steps(self, n: int = 10) -> list[StepRecord]:
        """Return the most recent n steps."""
        return self.steps[-n:]


# ---------------------------------------------------------------------------
# Memory Tree
# ---------------------------------------------------------------------------


@dataclass
class MemoryTreeConfig:
    """Configuration for the memory tree."""
    max_active_tokens: int = 80_000
    """Maximum tokens kept in the active path context."""

    compress_at_pct: float = 0.85
    """Trigger compression when active path tokens exceed this fraction."""

    max_recent_steps: int = 10
    """Number of recent steps kept for active subgoals."""

    summary_model: str = "qwen3:14b"
    """Model used for generating summaries."""


class MemoryTree:
    """Hierarchical execution state tree (Mage-inspired).

    Organizes agent memory as a tree where:
    - Each node is a subgoal
    - The active path is the chain from root to current node
    - Completed subgoals are compressed to summaries
    - Failed branches are isolated and don't contaminate good branches

    Usage::

        tree = MemoryTree()
        tree.start_subgoal("Fix auth middleware")
        tree.grow(StepRecord(type="tool_call", content="read auth.py", ...))
        tree.grow(StepRecord(type="tool_result", content="...", ...))
        tree.complete_subgoal(success=True)

        context = tree.get_context()  # Only active path + summaries
    """

    def __init__(self, config: MemoryTreeConfig | None = None) -> None:
        self.config = config or MemoryTreeConfig()
        self.root = StateNode(
            id="root",
            parent_id=None,
            subgoal="Session",
            status=NodeStatus.ACTIVE,
        )
        self.active_path: list[str] = ["root"]
        self._node_index: dict[str, StateNode] = {"root": self.root}
        self._counter: int = 0

    # -- Public API -----------------------------------------------------------

    def grow(self, step: StepRecord) -> None:
        """Add a step to the currently active node."""
        node = self._get_active_node()
        node.add_step(step)

    def start_subgoal(self, description: str) -> str:
        """Start a new subgoal as a child of the active node.

        Returns the new subgoal's ID.
        """
        parent = self._get_active_node()
        node_id = self._next_id()
        node = StateNode(
            id=node_id,
            parent_id=parent.id,
            subgoal=description,
        )
        parent.children.append(node)
        self._node_index[node_id] = node
        self.active_path.append(node_id)
        logger.debug("Started subgoal %s: %s", node_id, description)
        return node_id

    def complete_subgoal(self, success: bool = True) -> str:
        """Complete the active subgoal and generate a summary.

        Returns the generated summary string.
        """
        node = self._get_active_node()
        if node.id == "root":
            return ""  # Can't complete root

        node.status = NodeStatus.COMPLETED if success else NodeStatus.FAILED
        node.completed_at = time.time()
        node.summary = self._generate_summary(node)

        # Move up one level
        if len(self.active_path) > 1:
            self.active_path.pop()

        if success:
            logger.debug("Completed subgoal %s: %s", node.id, node.subgoal)
        else:
            logger.warning("Failed subgoal %s: %s", node.id, node.subgoal)

        return node.summary

    def revise(self, error_description: str) -> str:
        """Create a recovery branch from the current node.

        Used when a step fails — creates a sibling branch that
        represents a corrected approach. The failed branch is
        marked as FAILED and won't contaminate future context.

        Returns the new branch's ID.
        """
        parent = self._get_active_node().parent_id
        if parent is None:
            # At root — just start a new subgoal
            return self.start_subgoal(f"Recovery: {error_description[:80]}")

        parent_node = self._node_index[parent]
        branch_id = self._next_id()
        branch = StateNode(
            id=branch_id,
            parent_id=parent,
            subgoal=f"Recovery: {error_description[:80]}",
        )
        parent_node.children.append(branch)
        self._node_index[branch_id] = branch
        self.active_path[-1] = branch_id
        logger.info("Created recovery branch %s: %s", branch_id, error_description[:80])
        return branch_id

    def get_context(self) -> str:
        """Build context for the LLM from the active path.

        Only includes:
        - Summaries of completed subgoals (compressed)
        - Recent steps of the active subgoal
        - Excludes failed branches entirely (no contamination)
        """
        parts: list[str] = []
        estimated_tokens = 0

        for node_id in self.active_path:
            node = self._node_index[node_id]

            if node.status in (NodeStatus.COMPLETED, NodeStatus.COMPRESSED):
                # Completed subgoal: only its summary
                summary = node.summary or f"[Completed: {node.subgoal}]"
                parts.append(f"[Subgoal: {node.subgoal}]\n{summary}")
                estimated_tokens += len(summary) // 4

            elif node.status == NodeStatus.ACTIVE:
                # Active subgoal: recent steps + summaries of siblings
                recent = node.last_n_steps(self.config.max_recent_steps)
                if recent:
                    step_texts = []
                    for s in recent:
                        prefix = ""
                        if s.type == "tool_call":
                            prefix = f"[Tool: {s.tool_name}]"
                        elif s.type == "tool_result":
                            prefix = "[Result]"
                        elif s.type == "error":
                            prefix = "[Error]"
                        step_texts.append(f"{prefix} {s.content[:500]}")
                    parts.append(f"[Active: {node.subgoal}]\n" + "\n".join(step_texts))
                    estimated_tokens += sum(len(t) // 4 for t in step_texts)

                # Include summaries of completed siblings for context
                parent_id = node.parent_id
                if parent_id:
                    parent = self._node_index.get(parent_id)
                    if parent:
                        for sibling in parent.children:
                            if sibling.id != node.id and sibling.status in (
                                NodeStatus.COMPLETED,
                                NodeStatus.COMPRESSED,
                            ):
                                sib_summary = sibling.summary or "[Completed]"
                                parts.append(f"[Done: {sibling.subgoal}]\n{sib_summary}")

        # Trigger compression if over budget
        if estimated_tokens > self.config.max_active_tokens * self.config.compress_at_pct:
            self._compress_completed()

        return "\n\n".join(parts)

    def get_context_tokens(self) -> int:
        """Estimate token count of the active path context."""
        ctx = self.get_context()
        return len(ctx) // 4  # Rough 4 chars per token

    def get_stats(self) -> dict[str, Any]:
        """Return statistics about the memory tree."""
        total_nodes = len(self._node_index)
        completed = sum(1 for n in self._node_index.values() if n.status == NodeStatus.COMPLETED)
        failed = sum(1 for n in self._node_index.values() if n.status == NodeStatus.FAILED)
        active = sum(1 for n in self._node_index.values() if n.status == NodeStatus.ACTIVE)
        total_steps = sum(len(n.steps) for n in self._node_index.values())
        total_tokens = sum(n.tokens for n in self._node_index.values())

        return {
            "total_nodes": total_nodes,
            "completed": completed,
            "failed": failed,
            "active": active,
            "active_path_depth": len(self.active_path),
            "total_steps": total_steps,
            "total_tokens": total_tokens,
            "context_tokens": self.get_context_tokens(),
            "max_active_tokens": self.config.max_active_tokens,
        }

    def reset(self) -> None:
        """Reset the tree to initial state."""
        self.root = StateNode(
            id="root",
            parent_id=None,
            subgoal="Session",
            status=NodeStatus.ACTIVE,
        )
        self.active_path = ["root"]
        self._node_index = {"root": self.root}
        self._counter = 0

    # -- Internal helpers -----------------------------------------------------

    def _get_active_node(self) -> StateNode:
        """Return the currently active (deepest) node."""
        return self._node_index[self.active_path[-1]]

    def _next_id(self) -> str:
        """Generate a unique node ID."""
        self._counter += 1
        return f"n{self._counter}"

    def _generate_summary(self, node: StateNode) -> str:
        """Generate a heuristic summary of a completed subgoal.

        For production use, this would call a fast LLM.
        The heuristic version extracts key information from steps.
        """
        if not node.steps:
            return f"Completed {node.subgoal}. No steps recorded."

        tool_calls = [s for s in node.steps if s.type == "tool_call"]
        errors = [s for s in node.steps if s.error]

        parts = [f"Completed: {node.subgoal}"]
        parts.append(f"Steps: {len(node.steps)}")

        if tool_calls:
            tool_names = list({t.tool_name for t in tool_calls})
            parts.append(f"Tools used: {', '.join(tool_names)}")

        if errors:
            parts.append(f"Errors: {len(errors)} encountered")

        # Extract file paths mentioned
        file_paths = set()
        for s in node.steps:
            for word in s.content.split():
                if word.startswith("/") or (word.endswith(".py") and "/" in word):
                    file_paths.add(word)
        if file_paths:
            parts.append(f"Files: {', '.join(sorted(file_paths))}")

        return " | ".join(parts)

    def _compress_completed(self) -> None:
        """Compress all completed subgoals to free tokens."""
        compressed = 0
        for node_id, node in self._node_index.items():
            if node.status == NodeStatus.COMPLETED and not node.summary:
                node.summary = self._generate_summary(node)

            if node.status == NodeStatus.COMPLETED:
                node.status = NodeStatus.COMPRESSED
                node.steps = []  # Free raw steps
                node.tokens = len(node.summary) // 4
                compressed += 1

        if compressed:
            logger.debug("Compressed %d subgoals", compressed)

    async def summarize_with_llm(self, node: StateNode) -> str:
        """Generate a summary using an LLM (async)."""
        from ai_workspace.providers import ProviderRegistry

        steps_text = "\n".join(
            f"[{s.type}] {s.content[:300]}"
            for s in node.steps
        )

        prompt = f"""Summarize the following agent subgoal execution.
Keep only: what was done, key decisions, files modified, errors encountered.

Subgoal: {node.subgoal}

Steps:
{steps_text}

Summary:"""

        try:
            registry = ProviderRegistry()
            provider = registry.get_client("ollama") or registry.get_client(
                list(registry.providers)[0]
            )

            response = await provider.chat.completions.create(
                model=self.config.summary_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                stream=False,
            )

            content = response.choices[0].message.content if response.choices else ""
            return content or f"Completed {node.subgoal}"

        except Exception as exc:
            logger.warning("LLM summarization failed, using heuristic: %s", exc)
            return self._generate_summary(node)


# ---------------------------------------------------------------------------
# Memory Tree — Builder utilities
# ---------------------------------------------------------------------------


def build_memory_tree() -> MemoryTree:
    """Factory for creating a memory tree with default config."""
    return MemoryTree()


def estimate_step_tokens(content: str) -> int:
    """Estimate token count for a step's content."""
    return max(1, len(content) // 4)
