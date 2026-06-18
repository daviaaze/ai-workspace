"""
Context Compaction — Progressive Compression Pipeline (L1 -> L2 -> L3).

Reduces token usage in long-running agent sessions by applying three
levels of compaction, from cheapest to most expensive:

- L1: Tool Result Cap — truncates tool outputs > 10KB, saves full to disk
- L2: Time-based Cleanup — clears tool results older than 10 minutes
- L3: Summarization — when tokens > 80% of budget, summarizes via cheap model

Refs:
- SPEC_CONTEXT_COMPACTION.md
- Claude Code compact.ts (5-level pipeline)
- pi contextTransform
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("aiw.compaction")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class CompactionConfig:
    """Configuration for the progressive compaction pipeline."""

    max_tokens: int = 128_000
    """Maximum context window size in tokens."""

    compact_at_pct: float = 0.80
    """Trigger L3 summarization when token usage exceeds this fraction."""

    # -- L1: Tool Result Cap --
    tool_result_max_chars: int = 10_000
    """Maximum characters for a single tool result before truncation."""

    tool_result_preview_chars: int = 2_000
    """Characters kept as preview after truncation."""

    # -- L2: Time-based Cleanup --
    tool_result_ttl_seconds: int = 600
    """Age (seconds) after which tool results are replaced by placeholder."""

    max_recent_results: int = 20
    """Keep at most N most recent tool results; older ones are cleared."""

    # -- L3: Summarization --
    summary_model: str = "qwen3:14b"
    """Model used for summarization (should be fast and cheap)."""

    session_dir: str = "/tmp/.aiw/sessions"
    """Directory for saving truncated tool outputs to disk."""

    # -- Token estimation --
    chars_per_token: float = 3.5
    """Rough estimate: average characters per token."""

    # -- L3 Safety --
    max_summary_input_chars: int = 20_000
    """Maximum characters fed to the summarizer (truncate older messages)."""

    keep_recent_messages: int = 5
    """Number of most recent messages kept after summarization."""


# ---------------------------------------------------------------------------
# Context Compactor
# ---------------------------------------------------------------------------


class ContextCompactor:
    """Progressive context compaction for long agent sessions.

    Applied after each turn in the agent loop to keep token usage
    within budget. Operates directly on the message list.

    Usage::

        compactor = ContextCompactor(config)
        messages = compactor.compact(messages, estimated_tokens)
    """

    def __init__(self, config: CompactionConfig | None = None) -> None:
        self.config = config or CompactionConfig()
        self._tool_timestamps: dict[str, float] = {}
        """Maps tool_call_id -> unix timestamp of when the result was added."""

    # -- Public API --

    def compact(
        self,
        messages: list[dict[str, Any]],
        current_tokens: int,
    ) -> list[dict[str, Any]]:
        """Apply progressive compaction to a message list.

        Parameters
        ----------
        messages:
            Full message history (system, user, assistant, tool).
        current_tokens:
            Estimated token count for the current messages.

        Returns
        -------
        Compacted message list (may be shorter or have truncated contents).
        """
        # L1: Cap large tool results
        messages = self._cap_tool_results(messages)

        # L2: Clear old tool results
        messages = self._clear_old_results(messages)

        # L3: Summarize if near budget limit
        pct = current_tokens / max(1, self.config.max_tokens)
        if pct >= self.config.compact_at_pct:
            messages = self._summarize(messages)

        return messages

    async def compact_async(
        self,
        messages: list[dict[str, Any]],
        current_tokens: int,
    ) -> list[dict[str, Any]]:
        """Async variant of compact() — used when L3 summarization needs an
        LLM call.

        L1 and L2 are synchronous; only L3 may be async.
        """
        messages = self._cap_tool_results(messages)
        messages = self._clear_old_results(messages)

        pct = current_tokens / max(1, self.config.max_tokens)
        if pct >= self.config.compact_at_pct:
            messages = await self._summarize_async(messages)

        return messages

    # -- Token estimation helpers --

    def estimate_tokens(self, text: str) -> int:
        """Rough token count from character count."""
        if not text:
            return 0
        return max(1, int(len(text) / self.config.chars_per_token))

    def estimate_total_tokens(self, messages: list[dict[str, Any]]) -> int:
        """Estimate total tokens across all messages."""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += self.estimate_tokens(content)
            elif isinstance(content, list):
                # Multimodal content
                for part in content:
                    if isinstance(part, dict) and "text" in part:
                        total += self.estimate_tokens(part["text"])
        return total

    # -- L1: Tool Result Cap --------------------------------------------------

    def _cap_tool_results(
        self, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Truncate large tool results, saving full output to disk."""
        result: list[dict[str, Any]] = []
        for msg in messages:
            if msg.get("role") != "tool":
                result.append(msg)
                continue

            content = msg.get("content", "")
            if not isinstance(content, str) or len(content) <= self.config.tool_result_max_chars:
                result.append(msg)
                continue

            tool_id = msg.get("tool_call_id", "unknown")
            truncated = content[:self.config.tool_result_preview_chars]

            # Save full output to disk
            self._save_tool_result(tool_id, content)

            capped_msg = {
                **msg,
                "content": (
                    truncated
                    + f"\n[... truncated: {len(content)} total chars, "
                    + f"{self.estimate_tokens(content)} estimated tokens. "
                    + f"Full output saved to {self.config.session_dir}/{tool_id}.txt]"
                ),
            }
            result.append(capped_msg)

        return result

    # -- L2: Time-based Cleanup -----------------------------------------------

    def _clear_old_results(
        self, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Replace tool results older than TTL with a placeholder.

        Also respects max_recent_results: keeps only the N most recent,
        replacing the rest with placeholders.
        """
        now = time.time()

        # Track timestamps for all tool results
        for i, msg in enumerate(messages):
            if msg.get("role") == "tool":
                tid = msg.get("tool_call_id", "")
                if not tid:
                    tid = f"auto_{i}"
                if tid not in self._tool_timestamps:
                    self._tool_timestamps[tid] = now

        # Determine which tool results to keep (most recent N, within TTL)
        entries = sorted(
            self._tool_timestamps.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        keep_ids: set[str] = set()
        kept = 0
        for tid, ts in entries:
            age = now - ts
            if age > self.config.tool_result_ttl_seconds:
                continue  # Too old
            if kept >= self.config.max_recent_results:
                continue  # Already have N recent ones
            keep_ids.add(tid)
            kept += 1

        result: list[dict[str, Any]] = []
        for msg in messages:
            if msg.get("role") != "tool":
                result.append(msg)
                continue

            tid = msg.get("tool_call_id", "")
            if tid in keep_ids:
                result.append(msg)
            else:
                # Replace with placeholder
                result.append({
                    **msg,
                    "content": "[Old tool result cleared by context compaction]",
                })

        return result

    # -- L3: Summarization ----------------------------------------------------

    def _summarize(
        self, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Synchronous summarization — builds a heuristic summary without
        an LLM call.

        This is a fast fallback when async summarization is not available.
        It preserves system messages, user requests, and recent exchanges
        while collapsing the middle of the conversation.
        """
        system_msgs = [m for m in messages if m.get("role") == "system"]
        user_msgs = [m for m in messages if m.get("role") == "user"]
        recent = messages[-self.config.keep_recent_messages:]

        # Build a structural summary
        lines: list[str] = []
        lines.append("[CONVERSATION SUMMARY — context compacted]")
        lines.append(f"Total messages before compaction: {len(messages)}")
        lines.append("")

        # Summarize user requests
        if user_msgs:
            lines.append("User requests:")
            for m in user_msgs:
                content = str(m.get("content", ""))[:200]
                lines.append(f"  - {content}")
            lines.append("")

        # Summarize tool usage
        tool_msgs = [m for m in messages if m.get("role") == "tool"]
        if tool_msgs:
            lines.append(f"Tool results: {len(tool_msgs)} total")
            lines.append("")

        # Summarize assistant messages
        assistant_msgs = [m for m in messages if m.get("role") == "assistant"]
        if assistant_msgs:
            lines.append(f"Assistant responses: {len(assistant_msgs)} total")
            # Keep last assistant message as context
            last_content = str(assistant_msgs[-1].get("content", ""))[:500]
            if last_content:
                lines.append(f"Last response: {last_content}")
            lines.append("")

        lines.append("[/CONVERSATION SUMMARY]")

        summary = "\n".join(lines)

        return system_msgs + [{
            "role": "system",
            "content": summary,
        }] + recent

    async def _summarize_async(
        self, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Async summarization using a fast LLM call.

        Calls the configured summary model to produce a structured summary
        preserving: user intents, decisions, modified files, errors, and
        pending tasks.
        """
        try:
            summary = await self._call_summarizer(messages)
        except Exception as exc:
            logger.warning("Async summarization failed, falling back to heuristic: %s", exc)
            return self._summarize(messages)

        system_msgs = [m for m in messages if m.get("role") == "system"]
        recent = messages[-self.config.keep_recent_messages:]

        return system_msgs + [{
            "role": "system",
            "content": f"[CONVERSATION SUMMARY]\n{summary}\n[/CONVERSATION SUMMARY]",
        }] + recent

    async def _call_summarizer(
        self, messages: list[dict[str, Any]]
    ) -> str:
        """Call a fast/cheap model to summarize the conversation."""
        from ai_workspace.providers import ProviderRegistry

        # Build the summarization prompt from truncated messages
        conversation_parts: list[str] = []
        for m in messages:
            role = m.get("role", "unknown")
            content = str(m.get("content", ""))[:500]
            if role == "system":
                continue  # System messages are preserved separately
            conversation_parts.append(f"[{role}]: {content}")

        conversation_text = "\n".join(conversation_parts)
        if len(conversation_text) > self.config.max_summary_input_chars:
            conversation_text = conversation_text[:self.config.max_summary_input_chars]

        prompt = f"""Summarize this conversation. Keep ONLY:
1. User's original requests and intents
2. Key technical decisions made
3. Files that were modified (with paths)
4. Errors encountered and how they were resolved
5. Pending tasks not yet completed

Be concise. This summary will replace the original messages to save context space.

Conversation:
{conversation_text}
"""

        registry = ProviderRegistry()
        try:
            provider = registry.get_client("ollama") or registry.get_client(list(registry.providers)[0])
        except (KeyError, IndexError):
            raise RuntimeError("No providers available for summarization")

        response = await provider.chat.completions.create(
            model=self.config.summary_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            stream=False,
        )

        content = response.choices[0].message.content if response.choices else ""
        return content or "[Summary unavailable]"

    # -- Disk persistence for truncated tool results -------------------------

    def _save_tool_result(self, tool_id: str, content: str) -> None:
        """Save full tool output to disk for later inspection."""
        path = Path(self.config.session_dir) / f"{tool_id}.txt"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        except OSError as exc:
            logger.warning("Failed to save tool result %s: %s", tool_id, exc)

    # -- Statistics -----------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Return compaction statistics for monitoring."""
        return {
            "active_tool_results": len(self._tool_timestamps),
            "session_dir": self.config.session_dir,
            "compact_at_pct": self.config.compact_at_pct,
            "max_tokens": self.config.max_tokens,
            "tool_result_max_chars": self.config.tool_result_max_chars,
            "tool_result_ttl_seconds": self.config.tool_result_ttl_seconds,
        }

    def reset(self) -> None:
        """Reset internal state (timestamps, etc.)."""
        self._tool_timestamps.clear()
