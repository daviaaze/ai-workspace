"""Core types for the agent loop — events, state, params, terminal reasons."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ai_workspace.agents.patterns import LoopPattern


class TerminalReason(Enum):
    """Why the loop stopped."""

    COMPLETED = "completed"
    MAX_TURNS = "max_turns"
    TOKEN_BUDGET = "token_budget"
    USER_ABORT = "user_abort"
    TOOL_ERROR = "tool_error"
    MODEL_ERROR = "model_error"
    NO_TOOLS = "no_tools"
    TIMEOUT = "timeout"


@dataclass
class LoopEvent:
    """A single event emitted during the loop.

    The ``type`` determines the shape of ``data``:

    +---------------+-------------------------------------+
    | type          | data keys                           |
    +===============+=====================================+
    | ``token``     | ``text``                            |
    +---------------+-------------------------------------+
    | ``thinking``  | ``thought``                         |
    +---------------+-------------------------------------+
    | ``tool_call`` | ``tool``, ``args``                  |
    +---------------+-------------------------------------+
    | ``tool_result``| ``tool``, ``result``, ``error``    |
    +---------------+-------------------------------------+
    | ``error``     | ``code``, ``message``, ...          |
    +---------------+-------------------------------------+
    | ``phase``     | ``phase``, ``message``              |
    +---------------+-------------------------------------+
    | ``done``      | ``reason``, ``turns``, ``tokens``   |
    +---------------+-------------------------------------+
    """

    type: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class LoopState:
    """Mutable state carried between iterations."""

    messages: list[dict[str, Any]] = field(default_factory=list)
    turn_count: int = 0
    token_count: int = 0
    tool_errors: int = 0
    recovery_attempts: int = 0
    aborted: bool = False
    final_response: str = ""

    # Context compaction (Phase 2)
    compactor: Any | None = None
    """ContextCompactor instance set by agent_loop after construction."""

    # Memory Tree (Phase 5+)
    memory_tree: Any | None = None
    """MemoryTree instance for hierarchical state tracking."""

    # Tiered context loader (OpenViking-inspired L0/L1/L2)
    tiered_ctx: Any | None = None
    """TieredContextLoader for progressive context loading."""

    # All events for L1 trace writing
    _all_events: list = field(default_factory=list)

    def add_message(self, role: str, content: str | None, **extra: Any) -> None:
        msg: dict[str, Any] = {"role": role}
        if content is not None:
            msg["content"] = content
        msg.update(extra)
        self.messages.append(msg)

    def add_tool_result(self, tool_call_id: str, content: str) -> None:
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
        })


@dataclass
class LoopParams:
    """All parameters for a single agent loop invocation."""

    task: str
    pattern: LoopPattern = LoopPattern.DIRECT

    # --- Model config ---
    model: str = "qwen3:14b"
    provider: str = "ollama"
    temperature: float = 0.7

    # --- System prompt ---
    system_prompt: str = ""

    # --- Tools ---
    tools: list[dict[str, Any]] = field(default_factory=list)
    tool_handlers: dict[str, Callable[..., Any]] = field(default_factory=dict)

    # --- Parallel tool execution ---
    parallel_tools: bool = True

    # --- Limits ---
    max_turns: int = 20
    max_tokens: int = 100_000
    timeout: float = 300.0

    # --- Streaming ---
    stream: bool = True

    # --- Callbacks ---
    on_step: Callable[[LoopEvent], None] | None = None

    # --- History ---
    messages: list[dict[str, Any]] = field(default_factory=list)

    # --- Deps injection (testability) ---
    deps: dict[str, Any] = field(default_factory=dict)
