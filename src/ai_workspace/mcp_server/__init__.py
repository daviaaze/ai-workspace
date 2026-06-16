"""
MCP Server for AI Workspace.

Expose aiw's knowledge, tasks, and tools to any MCP-compatible client
(Claude Desktop, Cursor, Cline, Continue, etc.).

Run as:
    aiw mcp serve                # stdio transport (for Claude Desktop)
    aiw mcp serve --http PORT    # HTTP transport (for remote clients)

Available tools exposed to clients:
    aiw_knowledge_search(query, limit=10)
    aiw_knowledge_save(content, title, content_type="note", tags=None)
    aiw_task_list(status=None, limit=20)
    aiw_task_create(title, description="", priority=5, tags=None, schedule=None)
    aiw_task_update(task_id, status)
    aiw_memory_recall(agent, query, limit=10)
    aiw_memory_store(agent, content, memory_type="fact", importance=0.5)
    aiw_research(query, depth=2)
    aiw_search_web(query)
    aiw_browse(url, headless=True)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

from ai_workspace.knowledge import KnowledgeStore


# ─── Tool implementations ────────────────────────────


def _get_store() -> KnowledgeStore:
    store = KnowledgeStore()
    try:
        store.initialize()
    except Exception:
        # If DB unavailable, return store anyway — methods will fail gracefully
        pass
    return store


def tool_knowledge_search(query: str, limit: int = 10, content_type: str | None = None) -> list[dict[str, Any]]:
    """Semantic + keyword search over the knowledge base."""
    store = _get_store()
    try:
        results = store.search_knowledge(query, content_type=content_type, limit=limit)
        return results
    except Exception as e:
        return [{"error": f"search failed: {e}"}]
    finally:
        store.close()


def tool_knowledge_save(
    content: str,
    title: str | None = None,
    content_type: str = "note",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Save a new knowledge entry."""
    store = _get_store()
    try:
        kid = store.add_knowledge(content, content_type, title, tags=tags or [])
        return {"id": kid, "status": "saved"}
    except Exception as e:
        return {"error": f"save failed: {e}"}
    finally:
        store.close()


def tool_task_list(status: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    """List tasks, optionally filtered by status."""
    store = _get_store()
    try:
        return store.get_tasks(status=status, limit=limit)
    except Exception as e:
        return [{"error": f"list failed: {e}"}]
    finally:
        store.close()


def tool_task_create(
    title: str,
    description: str = "",
    priority: int = 5,
    tags: list[str] | None = None,
    schedule: str | None = None,
) -> dict[str, Any]:
    """Create a new task (optionally recurring via cron schedule)."""
    store = _get_store()
    try:
        tid = store.add_task(title, description, priority, tags or [], schedule)
        return {"id": tid, "status": "created"}
    except Exception as e:
        return {"error": f"create failed: {e}"}
    finally:
        store.close()


def tool_task_update(task_id: int, status: str) -> dict[str, Any]:
    """Update a task's status."""
    store = _get_store()
    try:
        store.update_task_status(task_id, status)
        return {"id": task_id, "status": status}
    except Exception as e:
        return {"error": f"update failed: {e}"}
    finally:
        store.close()


def tool_memory_recall(agent: str, query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Recall past agent memories via keyword search."""
    store = _get_store()
    try:
        return store.recall(agent, query, limit=limit)
    except Exception as e:
        return [{"error": f"recall failed: {e}"}]
    finally:
        store.close()


def tool_memory_store(
    agent: str,
    content: str,
    memory_type: str = "fact",
    importance: float = 0.5,
) -> dict[str, Any]:
    """Store a new agent memory."""
    store = _get_store()
    try:
        mid = store.remember(agent, content, memory_type, importance)
        return {"id": mid, "status": "stored"}
    except Exception as e:
        return {"error": f"store failed: {e}"}
    finally:
        store.close()


def tool_research(query: str, depth: int = 2) -> dict[str, Any]:
    """Run deep recursive research (synchronous, may take minutes)."""
    from ai_workspace.search import DeepSearchEngine

    async def _run():
        engine = DeepSearchEngine(max_depth=depth)
        result = await engine.research(query)
        return {
            "query": result.query,
            "summary": result.summary,
            "confidence": float(result.confidence) if result.confidence else 0.0,
            "sub_questions": [
                {"question": sq.question, "answer": sq.answer, "confidence": sq.confidence}
                for sq in result.sub_questions
            ],
            "sources": result.sources,
        }

    return asyncio.run(_run())


def tool_search_web(query: str) -> str:
    """Quick web search using the web_fetch tool."""
    from ai_workspace.tools import WebFetchTool
    # DuckDuckGo HTML search (no API key required)
    url = f"https://duckduckgo.com/html/?q={query}"
    return WebFetchTool()._run(url=url, max_length=3000)


def tool_browse(url: str, headless: bool = True) -> str:
    """Open a URL in a headless browser (for SPAs)."""
    from ai_workspace.tools import HeadlessBrowserTool
    return HeadlessBrowserTool()._run(url=url, headless=headless, max_length=8000)


# ─── MCP tool registry ──────────────────────────────


TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "aiw_knowledge_search": {
        "impl": tool_knowledge_search,
        "schema": {
            "name": "aiw_knowledge_search",
            "description": "Search the AI Workspace knowledge base. Returns matching entries with id, title, content, content_type, and tags.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "description": "Max results (default 10)", "default": 10},
                    "content_type": {"type": "string", "description": "Filter by type (note, research, code, etc.)"},
                },
                "required": ["query"],
            },
        },
    },
    "aiw_knowledge_save": {
        "impl": tool_knowledge_save,
        "schema": {
            "name": "aiw_knowledge_save",
            "description": "Save a new knowledge entry to the AI Workspace knowledge base.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "The content to save"},
                    "title": {"type": "string", "description": "Optional title"},
                    "content_type": {"type": "string", "description": "Type of content", "default": "note"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Optional tags"},
                },
                "required": ["content"],
            },
        },
    },
    "aiw_task_list": {
        "impl": tool_task_list,
        "schema": {
            "name": "aiw_task_list",
            "description": "List tasks. Optionally filter by status (pending, in_progress, completed, blocked).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Filter by status"},
                    "limit": {"type": "integer", "description": "Max results (default 20)", "default": 20},
                },
            },
        },
    },
    "aiw_task_create": {
        "impl": tool_task_create,
        "schema": {
            "name": "aiw_task_create",
            "description": "Create a new task. Optionally schedule it as a cron expression.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title"},
                    "description": {"type": "string", "description": "Task description", "default": ""},
                    "priority": {"type": "integer", "description": "0-10 (default 5)", "default": 5},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "schedule": {"type": "string", "description": "Cron expression (e.g. '0 9 * * *')"},
                },
                "required": ["title"],
            },
        },
    },
    "aiw_task_update": {
        "impl": tool_task_update,
        "schema": {
            "name": "aiw_task_update",
            "description": "Update a task's status.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "Task ID"},
                    "status": {"type": "string", "description": "New status (pending, in_progress, completed, blocked)"},
                },
                "required": ["task_id", "status"],
            },
        },
    },
    "aiw_memory_recall": {
        "impl": tool_memory_recall,
        "schema": {
            "name": "aiw_memory_recall",
            "description": "Recall past agent memories by keyword search.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent": {"type": "string", "description": "Agent name (e.g. 'researcher', 'coder')"},
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["agent", "query"],
            },
        },
    },
    "aiw_memory_store": {
        "impl": tool_memory_store,
        "schema": {
            "name": "aiw_memory_store",
            "description": "Store a new agent memory.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent": {"type": "string", "description": "Agent name"},
                    "content": {"type": "string", "description": "What to remember"},
                    "memory_type": {"type": "string", "default": "fact", "description": "fact, learning, preference, decision"},
                    "importance": {"type": "number", "default": 0.5, "description": "0.0-1.0"},
                },
                "required": ["agent", "content"],
            },
        },
    },
    "aiw_research": {
        "impl": tool_research,
        "schema": {
            "name": "aiw_research",
            "description": "Run deep recursive research on a query. Returns summary, sub-questions, and sources. May take several minutes.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Research query"},
                    "depth": {"type": "integer", "description": "Recursion depth (1-4)", "default": 2},
                },
                "required": ["query"],
            },
        },
    },
    "aiw_search_web": {
        "impl": tool_search_web,
        "schema": {
            "name": "aiw_search_web",
            "description": "Quick web search via DuckDuckGo. Returns HTML-rendered text of the search results page.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        },
    },
    "aiw_browse": {
        "impl": tool_browse,
        "schema": {
            "name": "aiw_browse",
            "description": "Open a URL in a headless browser (Playwright). For SPA/JS-heavy pages.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to open"},
                    "headless": {"type": "boolean", "default": True},
                },
                "required": ["url"],
            },
        },
    },
}


# ─── MCP protocol (stdio) ───────────────────────────


def _make_jsonrpc_response(req_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _make_jsonrpc_error(req_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def handle_mcp_request(req: dict[str, Any]) -> dict[str, Any] | None:
    """Handle one JSON-RPC 2.0 request and return the response, or None if it's a notification."""
    method = req.get("method")
    req_id = req.get("id")
    params = req.get("params") or {}

    if method == "initialize":
        return _make_jsonrpc_response(req_id, {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "aiw", "version": "0.2.0"},
            "capabilities": {"tools": {}},
        })

    if method == "tools/list":
        return _make_jsonrpc_response(req_id, {
            "tools": [t["schema"] for t in TOOL_REGISTRY.values()],
        })

    if method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments") or {}
        if tool_name not in TOOL_REGISTRY:
            return _make_jsonrpc_error(req_id, -32601, f"Unknown tool: {tool_name}")
        try:
            result = TOOL_REGISTRY[tool_name]["impl"](**args)
            # MCP requires content blocks
            return _make_jsonrpc_response(req_id, {
                "content": [{"type": "text", "text": _to_text(result)}],
            })
        except Exception as e:
            return _make_jsonrpc_error(req_id, -32603, f"Tool failed: {e}")

    if method == "ping":
        return _make_jsonrpc_response(req_id, {})

    if method == "notifications/initialized":
        return None  # Notification, no response

    return _make_jsonrpc_error(req_id, -32601, f"Unknown method: {method}")


def _to_text(value: Any) -> str:
    """Convert a tool result to the text format expected by MCP."""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, indent=2, default=str, ensure_ascii=False)
    except Exception:
        return str(value)


def run_stdio_server() -> None:
    """Run the MCP server over stdio. Each line on stdin is one JSON-RPC request."""
    print("[aiw-mcp] starting on stdio", file=sys.stderr)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as e:
            err = _make_jsonrpc_error(None, -32700, f"Parse error: {e}")
            print(json.dumps(err), flush=True)
            continue
        response = handle_mcp_request(req)
        if response is not None:
            print(json.dumps(response), flush=True)


__all__ = [
    "TOOL_REGISTRY",
    "handle_mcp_request",
    "run_stdio_server",
    "tool_knowledge_search",
    "tool_knowledge_save",
    "tool_task_list",
    "tool_task_create",
    "tool_task_update",
    "tool_memory_recall",
    "tool_memory_store",
    "tool_research",
    "tool_search_web",
    "tool_browse",
]
