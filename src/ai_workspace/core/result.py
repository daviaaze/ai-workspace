"""
Structured error handling with the Result pattern.

Railway-Oriented Programming in Python: Success[T] | Failure[E].
Replaces silent ``except: pass`` blocks with explicit, traceable errors.

Refs:
- dry-python/returns: https://returns.readthedocs.io/
- SPEC_ERROR_HANDLING.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E", bound="AiWError")


# ═══════════════════════════════════════════════════════════
# Result types
# ═══════════════════════════════════════════════════════════


@dataclass(frozen=True)
class Success(Generic[T]):
    """A successful outcome carrying a value."""

    value: T

    def is_success(self) -> bool:
        return True

    def is_failure(self) -> bool:
        return False

    def unwrap(self) -> T:
        """Return the inner value."""
        return self.value

    def unwrap_or(self, _default: T) -> T:
        """Return the inner value (default ignored for Success)."""
        return self.value

    def __repr__(self) -> str:
        return f"Success({self.value!r})"


@dataclass(frozen=True)
class Failure(Generic[E]):
    """A failed outcome carrying an error."""

    error: E

    def is_success(self) -> bool:
        return False

    def is_failure(self) -> bool:
        return True

    def unwrap(self) -> T:
        """Raise the error (no value to return)."""
        raise ValueError(f"Attempted to unwrap a Failure: {self.error}")

    def unwrap_or(self, default: T) -> T:
        """Return the default value instead of the error."""
        return default

    def __repr__(self) -> str:
        return f"Failure({self.error!r})"


# Python 3.12+ type alias syntax (PEP 695)
type Result[T, E] = Success[T] | Failure[E]


# ═══════════════════════════════════════════════════════════
# Error catalogue
# ═══════════════════════════════════════════════════════════


class ErrorCode:
    """Canonical error codes for the entire system.

    Every AiWError carries one of these codes so consumers (agents,
    CLIs, MCP) can react programmatically without parsing messages.
    """

    # Provider-level
    PROVIDER_OFFLINE = "PROVIDER_OFFLINE"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    PROVIDER_AUTH = "PROVIDER_AUTH"

    # Model-level
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    MODEL_OVERLOADED = "MODEL_OVERLOADED"
    MODEL_ERROR = "MODEL_ERROR"

    # Budget
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    BUDGET_WARNING = "BUDGET_WARNING"

    # Tools
    TOOL_FAILED = "TOOL_FAILED"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    TOOL_PERMISSION_DENIED = "TOOL_PERMISSION_DENIED"
    TOOL_INVALID_ARGS = "TOOL_INVALID_ARGS"

    # Search / RAG
    SEARCH_FAILED = "SEARCH_FAILED"
    RAG_INDEX_FAILED = "RAG_INDEX_FAILED"
    RAG_RETRIEVAL_FAILED = "RAG_RETRIEVAL_FAILED"

    # Agent Loop
    AGENT_LOOP_LIMIT = "AGENT_LOOP_LIMIT"
    AGENT_LOOP_TIMEOUT = "AGENT_LOOP_TIMEOUT"
    AGENT_TOKEN_BUDGET = "AGENT_TOKEN_BUDGET"
    AGENT_USER_ABORT = "AGENT_USER_ABORT"

    # Streaming / I/O
    STREAMING_FAILED = "STREAMING_FAILED"

    # Routing
    ROUTER_FAILED = "ROUTER_FAILED"
    ROUTER_NOT_AVAILABLE = "ROUTER_NOT_AVAILABLE"

    # Config
    CONFIG_INVALID = "CONFIG_INVALID"
    CONFIG_MISSING = "CONFIG_MISSING"

    # Data / persistence
    DB_CONNECTION_FAILED = "DB_CONNECTION_FAILED"
    DB_QUERY_FAILED = "DB_QUERY_FAILED"
    NOT_FOUND = "NOT_FOUND"

    # General
    INTERNAL_ERROR = "INTERNAL_ERROR"
    UNKNOWN = "UNKNOWN"
    VALIDATION_ERROR = "VALIDATION_ERROR"


# ═══════════════════════════════════════════════════════════
# AiWError — structured error payload
# ═══════════════════════════════════════════════════════════


@dataclass
class AiWError:
    """A structured, machine-readable error.

    Compatible with JSON/NDJSON output modes and MCP error reporting.
    Every field is designed so an external agent can decide whether to
    retry, fall back, or escalate without parsing human prose.
    """

    code: str
    """Machine-readable error code (see ErrorCode)."""

    message: str
    """Human-readable description of what went wrong."""

    detail: str = ""
    """Technical detail (traceback snippet, API response body, etc.)."""

    recoverable: bool = True
    """Can the caller retry this operation and expect a different result?"""

    suggestion: str = ""
    """Actionable hint for the user (e.g. 'Try: ollama pull qwen3:14b')."""

    component: str = ""
    """Which subsystem produced this error (e.g. 'providers', 'search')."""

    def to_dict(self) -> dict:
        """Serialize to a dict for JSON/NDJSON envelopes."""
        d = {
            "code": self.code,
            "message": self.message,
            "recoverable": self.recoverable,
        }
        if self.detail:
            d["detail"] = self.detail
        if self.suggestion:
            d["suggestion"] = self.suggestion
        if self.component:
            d["component"] = self.component
        return d

    def __str__(self) -> str:
        parts = [f"[{self.code}] {self.message}"]
        if self.suggestion:
            parts.append(f"💡 {self.suggestion}")
        if self.detail:
            parts.append(f"   detail: {self.detail}")
        return "\n".join(parts)

    def __repr__(self) -> str:
        return (
            f"AiWError(code={self.code!r}, message={self.message!r}, "
            f"recoverable={self.recoverable})"
        )
