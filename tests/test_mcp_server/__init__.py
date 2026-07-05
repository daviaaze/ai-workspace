"""
Tests for the MCP server.

Verifies JSON-RPC 2.0 protocol compliance and tool dispatch.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

# ─── Tool registry ──────────────────────────────────


def test_tool_registry_has_expected_tools():
    from ai_workspace.mcp_server import TOOL_REGISTRY
    expected = {
        "aiw_knowledge_search",
        "aiw_knowledge_save",
        "aiw_task_list",
        "aiw_task_create",
        "aiw_task_update",
        "aiw_memory_recall",
        "aiw_memory_store",
        "aiw_research",
        "aiw_search_web",
        "aiw_browse",
    }
    assert expected.issubset(set(TOOL_REGISTRY.keys()))


def test_tool_schemas_have_required_fields():
    from ai_workspace.mcp_server import TOOL_REGISTRY
    for name, spec in TOOL_REGISTRY.items():
        schema = spec["schema"]
        assert schema["name"] == name
        assert "description" in schema
        assert "inputSchema" in schema
        assert schema["inputSchema"]["type"] == "object"
        assert "properties" in schema["inputSchema"]


# ─── JSON-RPC protocol ──────────────────────────────


def test_initialize_returns_server_info():
    from ai_workspace.mcp_server import handle_mcp_request
    resp = handle_mcp_request({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {},
    })
    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == 1
    assert "serverInfo" in resp["result"]
    assert resp["result"]["serverInfo"]["name"] == "aiw"


def test_tools_list_returns_all_schemas():
    from ai_workspace.mcp_server import TOOL_REGISTRY, handle_mcp_request
    resp = handle_mcp_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tools = resp["result"]["tools"]
    assert len(tools) == len(TOOL_REGISTRY)
    names = {t["name"] for t in tools}
    assert "aiw_knowledge_search" in names


def test_tools_call_dispatches_to_impl():
    from ai_workspace.mcp_server import handle_mcp_request
    with patch("ai_workspace.mcp_server.tool_knowledge_search", return_value=[{"id": 1, "title": "hit"}]):
        resp = handle_mcp_request({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "aiw_knowledge_search", "arguments": {"query": "test"}},
        })
    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == 3
    content = resp["result"]["content"]
    assert content[0]["type"] == "text"
    assert "hit" in content[0]["text"]


def test_tools_call_unknown_tool_returns_error():
    from ai_workspace.mcp_server import handle_mcp_request
    resp = handle_mcp_request({
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {"name": "aiw_does_not_exist", "arguments": {}},
    })
    assert "error" in resp
    assert resp["error"]["code"] == -32601


def test_tools_call_handles_exception():
    from ai_workspace.mcp_server import handle_mcp_request
    with patch("ai_workspace.mcp_server.tool_knowledge_search", side_effect=RuntimeError("boom")):
        resp = handle_mcp_request({
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "aiw_knowledge_search", "arguments": {"query": "x"}},
        })
    assert "error" in resp
    assert "boom" in resp["error"]["message"]


def test_ping_returns_empty_result():
    from ai_workspace.mcp_server import handle_mcp_request
    resp = handle_mcp_request({"jsonrpc": "2.0", "id": 6, "method": "ping"})
    assert resp["result"] == {}


def test_unknown_method_returns_error():
    from ai_workspace.mcp_server import handle_mcp_request
    resp = handle_mcp_request({"jsonrpc": "2.0", "id": 7, "method": "nonexistent"})
    assert "error" in resp
    assert resp["error"]["code"] == -32601


def test_initialized_notification_returns_none():
    """notifications/initialized is a notification, no response expected."""
    from ai_workspace.mcp_server import handle_mcp_request
    resp = handle_mcp_request({"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert resp is None


# ─── _to_text helper ────────────────────────────────


def test_to_text_string():
    from ai_workspace.mcp_server import _to_text
    assert _to_text("hello") == "hello"


def test_to_text_dict():
    from ai_workspace.mcp_server import _to_text
    out = _to_text({"a": 1, "b": [1, 2, 3]})
    assert '"a": 1' in out
    assert '"b"' in out


def test_to_text_list():
    from ai_workspace.mcp_server import _to_text
    out = _to_text([{"id": 1}, {"id": 2}])
    assert '"id": 1' in out
    assert '"id": 2' in out


# ─── Tool impl behavior (with mocked DB) ───────────


def test_tool_knowledge_search_uses_knowledge_store():
    from ai_workspace.mcp_server import tool_knowledge_search

    mock_store = MagicMock()
    mock_store.search_knowledge.return_value = [{"id": 1, "title": "x"}]
    with patch("ai_workspace.mcp_server._get_store", return_value=mock_store):
        result = tool_knowledge_search(query="test", limit=5)
    assert result == [{"id": 1, "title": "x"}]
    mock_store.search_knowledge.assert_called_once_with("test", content_type=None, limit=5)


def test_tool_knowledge_search_handles_db_error():
    from ai_workspace.mcp_server import tool_knowledge_search

    mock_store = MagicMock()
    mock_store.search_knowledge.side_effect = RuntimeError("DB down")
    with patch("ai_workspace.mcp_server._get_store", return_value=mock_store):
        result = tool_knowledge_search(query="x")
    assert "error" in result[0]


def test_tool_task_create_invokes_store():
    from ai_workspace.mcp_server import tool_task_create

    mock_store = MagicMock()
    mock_store.add_task.return_value = 42
    with patch("ai_workspace.mcp_server._get_store", return_value=mock_store):
        result = tool_task_create(title="Test task", priority=8, tags=["urgent"])
    assert result == {"id": 42, "status": "created"}
    mock_store.add_task.assert_called_once_with("Test task", "", 8, ["urgent"], None)


def test_tool_memory_store_invokes_store():
    from ai_workspace.mcp_server import tool_memory_store

    mock_store = MagicMock()
    mock_store.remember.return_value = 7
    with patch("ai_workspace.mcp_server._get_store", return_value=mock_store):
        result = tool_memory_store(agent="coder", content="learned X", importance=0.9)
    assert result == {"id": 7, "status": "stored"}
    mock_store.remember.assert_called_once_with("coder", "learned X", "fact", 0.9)


def test_tool_task_update_invokes_store():
    from ai_workspace.mcp_server import tool_task_update

    mock_store = MagicMock()
    with patch("ai_workspace.mcp_server._get_store", return_value=mock_store):
        result = tool_task_update(task_id=5, status="completed")
    assert result == {"id": 5, "status": "completed"}
    mock_store.update_task_status.assert_called_once_with(5, "completed")


# ─── Stdio loop (smoke test with mocked stdin/stdout) ──


def test_run_stdio_server_processes_lines():
    from ai_workspace.mcp_server import run_stdio_server

    requests = [
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
        json.dumps({"jsonrpc": "2.0", "id": 2, "method": "ping"}),
    ]
    stdin_text = "\n".join(requests) + "\n"

    responses: list[str] = []

    class FakeStdin:
        def __init__(self, text):
            self._lines = iter(text.splitlines(keepends=True))

        def __iter__(self):
            return self._lines

    with patch("ai_workspace.mcp_server.sys.stdin", FakeStdin(stdin_text)):
        with patch("builtins.print", side_effect=lambda s, **kw: responses.append(s)):
            run_stdio_server()

    parsed = [json.loads(r) for r in responses]
    assert parsed[0]["id"] == 1
    assert "serverInfo" in parsed[0]["result"]
    assert parsed[1]["id"] == 2
    assert parsed[1]["result"] == {}
