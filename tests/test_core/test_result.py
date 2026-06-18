"""Tests for src/ai_workspace/core/result.py — Result pattern and AiWError."""

from __future__ import annotations

import json

import pytest

from ai_workspace.core.result import (
    AiWError,
    ErrorCode,
    Failure,
    Result,
    Success,
)


# ═══════════════════════════════════════════════════════════
# Success / Failure basics
# ═══════════════════════════════════════════════════════════


def test_success_is_success():
    s = Success(42)
    assert s.is_success() is True
    assert s.is_failure() is False


def test_failure_is_failure():
    err = AiWError(code=ErrorCode.INTERNAL_ERROR, message="boom")
    f = Failure(err)
    assert f.is_success() is False
    assert f.is_failure() is True


def test_success_unwrap():
    s = Success("hello")
    assert s.unwrap() == "hello"


def test_failure_unwrap_raises():
    err = AiWError(code=ErrorCode.NOT_FOUND, message="gone")
    f = Failure(err)
    with pytest.raises(ValueError, match="gone"):
        f.unwrap()


def test_success_unwrap_or():
    s = Success("hello")
    assert s.unwrap_or("default") == "hello"


def test_failure_unwrap_or():
    err = AiWError(code=ErrorCode.NOT_FOUND, message="gone")
    f = Failure(err)
    assert f.unwrap_or("default") == "default"


# ═══════════════════════════════════════════════════════════
# Frozen dataclasses
# ═══════════════════════════════════════════════════════════


def test_success_is_frozen():
    s = Success(1)
    with pytest.raises(Exception):
        s.value = 2  # type: ignore[misc]


def test_failure_is_frozen():
    f = Failure(AiWError(code="E1", message="x"))
    with pytest.raises(Exception):
        f.error = AiWError(code="E2", message="y")  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════
# Pattern matching (Python 3.10+)
# ═══════════════════════════════════════════════════════════


def test_pattern_matching_success():
    result: Result[int, AiWError] = Success(42)

    match result:
        case Success(value):
            assert value == 42
        case Failure(_):
            pytest.fail("Should be Success")


def test_pattern_matching_failure():
    err = AiWError(code=ErrorCode.NOT_FOUND, message="missing")
    result: Result[int, AiWError] = Failure(err)

    match result:
        case Success(_):
            pytest.fail("Should be Failure")
        case Failure(error):
            assert error.code == ErrorCode.NOT_FOUND
            assert error.message == "missing"


def test_pattern_matching_guards():
    """Guards work with Success/Failure."""
    result: Result[int, AiWError] = Success(100)

    match result:
        case Success(v) if v > 50:
            assert True  # matches
        case Success(v):
            pytest.fail("Guard should have matched")
        case Failure(_):
            pytest.fail("Should be Success")


# ═══════════════════════════════════════════════════════════
# AiWError
# ═══════════════════════════════════════════════════════════


def test_aiw_error_defaults():
    e = AiWError(code=ErrorCode.PROVIDER_OFFLINE, message="offline")
    assert e.detail == ""
    assert e.recoverable is True
    assert e.suggestion == ""
    assert e.component == ""


def test_aiw_error_full():
    e = AiWError(
        code=ErrorCode.PROVIDER_OFFLINE,
        message="Ollama is not running",
        detail="Connection refused on port 11434",
        recoverable=True,
        suggestion="Try: systemctl start ollama",
        component="providers",
    )
    assert e.detail == "Connection refused on port 11434"
    assert e.suggestion == "Try: systemctl start ollama"
    assert e.component == "providers"


def test_aiw_error_to_dict():
    e = AiWError(
        code=ErrorCode.BUDGET_EXCEEDED,
        message="Daily budget exceeded",
        recoverable=False,
        suggestion="Increase limit or wait until tomorrow",
    )
    d = e.to_dict()
    assert d["code"] == ErrorCode.BUDGET_EXCEEDED
    assert d["message"] == "Daily budget exceeded"
    assert d["recoverable"] is False
    assert d["suggestion"] == "Increase limit or wait until tomorrow"


def test_aiw_error_to_dict_minimal():
    e = AiWError(code=ErrorCode.UNKNOWN, message="???")
    d = e.to_dict()
    assert "detail" not in d
    assert "suggestion" not in d
    assert "component" not in d


def test_aiw_error_json_serializable():
    """AiWError.to_dict() must be JSON-serializable."""
    e = AiWError(
        code=ErrorCode.MODEL_ERROR,
        message="Model failed",
        detail="timeout",
        recoverable=False,
    )
    d = e.to_dict()
    json_str = json.dumps(d)
    assert "MODEL_ERROR" in json_str
    assert "timeout" in json_str


def test_aiw_error_str_contains_code():
    e = AiWError(code=ErrorCode.TOOL_FAILED, message="bash failed")
    s = str(e)
    assert ErrorCode.TOOL_FAILED in s
    assert "bash failed" in s


def test_aiw_error_str_with_suggestion():
    e = AiWError(
        code=ErrorCode.MODEL_NOT_FOUND,
        message="Model not found",
        suggestion="Try: ollama pull qwen3:14b",
    )
    s = str(e)
    assert "ollama pull" in s


# ═══════════════════════════════════════════════════════════
# ErrorCode catalogue
# ═══════════════════════════════════════════════════════════


def test_error_code_constants_exist():
    """Verify key error codes from the spec exist."""
    assert ErrorCode.PROVIDER_OFFLINE
    assert ErrorCode.PROVIDER_TIMEOUT
    assert ErrorCode.BUDGET_EXCEEDED
    assert ErrorCode.MODEL_NOT_FOUND
    assert ErrorCode.TOOL_FAILED
    assert ErrorCode.SEARCH_FAILED
    assert ErrorCode.AGENT_LOOP_LIMIT
    assert ErrorCode.AGENT_TOKEN_BUDGET
    assert ErrorCode.AGENT_USER_ABORT
    assert ErrorCode.STREAMING_FAILED
    assert ErrorCode.ROUTER_FAILED
    assert ErrorCode.ROUTER_NOT_AVAILABLE
    assert ErrorCode.CONFIG_INVALID
    assert ErrorCode.DB_CONNECTION_FAILED
    assert ErrorCode.NOT_FOUND
    assert ErrorCode.VALIDATION_ERROR


# ═══════════════════════════════════════════════════════════
# Type narrowing with Result
# ═══════════════════════════════════════════════════════════


def test_result_type_narrowing():
    """Demonstrate that match narrows the type correctly."""

    def handle(r: Result[int, AiWError]) -> str:
        match r:
            case Success(v):
                # Type checker knows v is int
                return f"got {v}"
            case Failure(e):
                # Type checker knows e is AiWError
                return f"error: {e.code}"

    assert handle(Success(1)) == "got 1"
    assert handle(Failure(AiWError(code="E1", message="x"))) == "error: E1"


def test_result_isinstance():
    """isinstance checks work (dataclass protocol)."""
    s = Success(1)
    assert isinstance(s, Success)
    f = Failure(AiWError(code="E", message="m"))
    assert isinstance(f, Failure)
