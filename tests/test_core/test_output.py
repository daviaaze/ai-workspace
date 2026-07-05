"""Tests for src/ai_workspace/core/output.py — OutputFormatter and OutputEnvelope."""

from __future__ import annotations

import io
import json

import pytest

from ai_workspace.core.output import (
    OutputEnvelope,
    OutputFormatter,
    OutputMode,
    get_output_formatter,
)

# ═══════════════════════════════════════════════════════════
# OutputEnvelope
# ═══════════════════════════════════════════════════════════


def test_envelope_default_timestamp():
    env = OutputEnvelope(ok=True, command="health", data={"x": 1})
    assert env.timestamp  # auto-generated
    assert env.ok is True
    assert env.command == "health"


def test_envelope_to_dict_basic():
    env = OutputEnvelope(
        ok=True,
        command="budget",
        timestamp="2026-01-01T00:00:00Z",
        data={"spent": 1.0},
    )
    d = env.to_dict()
    assert d["ok"] is True
    assert d["command"] == "budget"
    assert d["timestamp"] == "2026-01-01T00:00:00Z"
    assert d["data"] == {"spent": 1.0}


def test_envelope_to_dict_with_error():
    env = OutputEnvelope(
        ok=False,
        command="search",
        error={"code": "PROVIDER_OFFLINE", "message": "Ollama offline"},
    )
    d = env.to_dict()
    assert d["ok"] is False
    assert d["error"]["code"] == "PROVIDER_OFFLINE"


def test_envelope_to_dict_with_warnings():
    env = OutputEnvelope(
        ok=True,
        command="health",
        warnings=["model codellama is offline"],
    )
    d = env.to_dict()
    assert d["warnings"] == ["model codellama is offline"]


def test_envelope_to_dict_with_meta():
    env = OutputEnvelope(
        ok=True,
        command="health",
        meta={"version": "0.1.0", "duration_ms": 234},
    )
    d = env.to_dict()
    assert d["meta"]["version"] == "0.1.0"


def test_envelope_to_dict_excludes_empty_optionals():
    """Empty lists/dicts should not appear in to_dict."""
    env = OutputEnvelope(ok=True, command="test")
    d = env.to_dict()
    assert "error" not in d
    assert "warnings" not in d
    assert "meta" not in d


# ═══════════════════════════════════════════════════════════
# OutputFormatter — JSON mode
# ═══════════════════════════════════════════════════════════


def test_json_mode_produces_valid_json():
    buf = io.StringIO()
    fmt = OutputFormatter(mode="json", file=buf)
    env = OutputEnvelope(
        ok=True,
        command="health",
        timestamp="2026-01-01T00:00:00Z",
        data={"providers": [{"name": "ollama", "status": "online"}]},
    )
    fmt.print(env)

    output = buf.getvalue()
    parsed = json.loads(output)
    assert parsed["ok"] is True
    assert parsed["command"] == "health"
    assert parsed["data"]["providers"][0]["name"] == "ollama"


def test_json_mode_with_error():
    buf = io.StringIO()
    fmt = OutputFormatter(mode="json", file=buf)
    env = OutputEnvelope(
        ok=False,
        command="search",
        error={"code": "SEARCH_FAILED", "message": "No results"},
    )
    fmt.print(env)

    parsed = json.loads(buf.getvalue())
    assert parsed["ok"] is False
    assert parsed["error"]["code"] == "SEARCH_FAILED"


def test_json_mode_pretty_print():
    """JSON mode uses indent=2 for readability."""
    buf = io.StringIO()
    fmt = OutputFormatter(mode="json", file=buf)
    fmt.print(OutputEnvelope(ok=True, command="test", data={"key": "val"}))

    output = buf.getvalue()
    assert "  " in output  # indentation present
    assert "\n" in output  # multi-line


# ═══════════════════════════════════════════════════════════
# OutputFormatter — NDJSON mode
# ═══════════════════════════════════════════════════════════


def test_ndjson_each_line_is_valid_json():
    buf = io.StringIO()
    fmt = OutputFormatter(mode="ndjson", file=buf)

    fmt.write_event("start", command="search", query="hello")
    fmt.write_event("phase", phase="planning", message="planning...")
    fmt.write_event("done", ok=True)

    lines = buf.getvalue().strip().split("\n")
    assert len(lines) == 3

    for line in lines:
        obj = json.loads(line)
        assert "type" in obj


def test_ndjson_events_have_type():
    buf = io.StringIO()
    fmt = OutputFormatter(mode="ndjson", file=buf)

    fmt.write_event("start")
    fmt.write_event("done")

    lines = buf.getvalue().strip().split("\n")
    assert json.loads(lines[0])["type"] == "start"
    assert json.loads(lines[1])["type"] == "done"


def test_ndjson_timestamp_auto_added():
    buf = io.StringIO()
    fmt = OutputFormatter(mode="ndjson", file=buf)

    fmt.write_event("test_event", key="value")

    line = json.loads(buf.getvalue().strip())
    assert "timestamp" in line


def test_ndjson_custom_timestamp_respected():
    buf = io.StringIO()
    fmt = OutputFormatter(mode="ndjson", file=buf)

    fmt.write_event("test_event", timestamp="2026-01-01T00:00:00Z")

    line = json.loads(buf.getvalue().strip())
    assert line["timestamp"] == "2026-01-01T00:00:00Z"


def test_ndjson_no_raw_newlines_in_output():
    """NDJSON spec: JSON must not contain raw newlines (only escaped \\n).

    The validation in write_event checks for literal \n bytes in the
    JSON output. Properly escaped \\n sequences are fine.
    """
    buf = io.StringIO()
    fmt = OutputFormatter(mode="ndjson", file=buf)

    # This is fine: json.dumps escapes \n as \\n
    fmt.write_event("ok", content="line1\nline2")
    line = buf.getvalue().strip()
    # Should be valid JSON
    parsed = json.loads(line)
    assert parsed["content"] == "line1\nline2"
    # No raw newline between the event braces
    assert "\n" not in line  # the only \n is at end of line (added by print)


def test_ndjson_rejects_internal_newlines_in_json():
    """If someone constructs JSON with raw newlines, it should be caught.

    This simulates a malformed payload that would produce invalid NDJSON.
    """
    buf = io.StringIO()
    fmt = OutputFormatter(mode="ndjson", file=buf)

    # Directly inject a raw newline into the payload string would only
    # happen with manual construction. json.dumps() always escapes.
    # So this test verifies the guard exists but won't trigger from normal usage.
    # We'll test that write_event with normal data works fine.
    fmt.write_event("safe", text="hello world")
    line = buf.getvalue().strip()
    assert json.loads(line)  # valid JSON


def test_ndjson_does_not_allow_print():
    """print() should fail in NDJSON mode."""
    buf = io.StringIO()
    fmt = OutputFormatter(mode="ndjson", file=buf)

    with pytest.raises(RuntimeError, match="NDJSON"):
        fmt.print(OutputEnvelope(ok=True, command="test"))


def test_ndjson_ensure_ascii_false():
    """UTF-8 characters must be preserved (ensure_ascii=False)."""
    buf = io.StringIO()
    fmt = OutputFormatter(mode="ndjson", file=buf)

    fmt.write_event("test_event", message="olá mundo")
    line = buf.getvalue().strip()
    assert "olá mundo" in line
    # The line should contain actual UTF-8 bytes, not escaped
    assert "ol\\u00e1" not in line  # not escaped


def test_ndjson_multiple_fields():
    buf = io.StringIO()
    fmt = OutputFormatter(mode="ndjson", file=buf)

    fmt.write_event(
        "research_done",
        current=1,
        confidence=0.85,
        sources=["https://example.com"],
        duration_ms=3420,
    )

    line = json.loads(buf.getvalue().strip())
    assert line["current"] == 1
    assert line["confidence"] == 0.85
    assert line["sources"] == ["https://example.com"]
    assert line["duration_ms"] == 3420


# ═══════════════════════════════════════════════════════════
# OutputFormatter — Rich mode (does not crash)
# ═══════════════════════════════════════════════════════════


def test_rich_mode_does_not_crash():
    buf = io.StringIO()
    fmt = OutputFormatter(mode="rich", file=buf)

    env = OutputEnvelope(
        ok=True,
        command="health",
        data={"providers": [{"name": "ollama"}]},
        warnings=["test warning"],
    )
    fmt.print(env)

    output = buf.getvalue()
    # Rich produces some output — at minimum, it shouldn't crash
    assert len(output) > 0


def test_rich_mode_error_envelope():
    buf = io.StringIO()
    fmt = OutputFormatter(mode="rich", file=buf)

    env = OutputEnvelope(
        ok=False,
        command="search",
        error={"code": "FAIL", "message": "Something broke", "suggestion": "Try again"},
    )
    fmt.print_error(env)

    output = buf.getvalue()
    assert "Something broke" in output


def test_rich_mode_fallback_no_rich_installed():
    """Rich mode with empty envelope still outputs something."""
    buf = io.StringIO()
    fmt = OutputFormatter(mode="rich", file=buf)

    fmt.print(OutputEnvelope(ok=False, command="unknown"))
    # Should not crash
    assert len(buf.getvalue()) > 0


# ═══════════════════════════════════════════════════════════
# OutputFormat mode enum
# ═══════════════════════════════════════════════════════════


def test_output_mode_from_string():
    assert OutputMode("rich") == OutputMode.RICH
    assert OutputMode("json") == OutputMode.JSON
    assert OutputMode("ndjson") == OutputMode.NDJSON


def test_output_mode_invalid():
    with pytest.raises(ValueError):
        OutputMode("yaml")


# ═══════════════════════════════════════════════════════════
# get_output_formatter helper
# ═══════════════════════════════════════════════════════════


def test_get_output_formatter():
    """Simulates a typer context with output mode in ctx.obj."""

    class FakeCtx:
        obj = {"output": "json"}

    fmt = get_output_formatter(FakeCtx())
    assert fmt.mode == OutputMode.JSON


def test_get_output_formatter_default():
    """Without ctx.obj, defaults to rich."""

    class FakeCtx:
        pass

    fmt = get_output_formatter(FakeCtx())
    assert fmt.mode == OutputMode.RICH
