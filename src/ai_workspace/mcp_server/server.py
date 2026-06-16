"""
AI Workspace MCP Server — lets AI agents (Claude, Codex, Gemini) work on aiw itself.

Connect with (Claude Code):
  claude mcp add aiw-dev -- python -m ai_workspace.mcp_server

Or use the .mcp.json already in the project root.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


# ═══════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ALLOWED_PATHS = [
    WORKSPACE_ROOT / "src",
    WORKSPACE_ROOT / "docs",
    WORKSPACE_ROOT / "tests",
    WORKSPACE_ROOT / "pyproject.toml",
    WORKSPACE_ROOT / "Makefile",
    WORKSPACE_ROOT / "README.md",
]
ALLOWED_SHELL_COMMANDS = [
    "cd", "ls", "cat", "grep", "find", "wc", "head", "tail",
    "git", "python", "pytest", "ruff", "nix", "make",
    "go", "npm",
]


def _safe_path(path_str: str) -> Path:
    p = (WORKSPACE_ROOT / path_str).resolve()
    if not str(p).startswith(str(WORKSPACE_ROOT.resolve())):
        raise ValueError(f"Path traversal blocked: {path_str}")
    return p


def _is_shell_allowed(cmd: str) -> bool:
    base = cmd.strip().split()[0] if cmd.strip().split() else ""
    if base.startswith("./") or base.startswith(str(WORKSPACE_ROOT)):
        return True
    return base in ALLOWED_SHELL_COMMANDS


# ═══════════════════════════════════════════════════════════════
# Server
# ═══════════════════════════════════════════════════════════════

server = Server("aiw-dev")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="read_file",
            description="Read a file from the aiw workspace. Returns content with line numbers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path from workspace root"},
                    "start_line": {"type": "integer", "description": "First line (1-indexed, 0=from start)"},
                    "end_line": {"type": "integer", "description": "Last line (-1=to end)"},
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="write_file",
            description="Write content to a file in the aiw workspace. Creates parent directories.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path from workspace root"},
                    "content": {"type": "string", "description": "Full file content to write"},
                },
                "required": ["path", "content"],
            },
        ),
        Tool(
            name="run_shell",
            description="Run a shell command in the aiw workspace directory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"},
                    "timeout": {"type": "integer", "description": "Max execution time in seconds (default 30)"},
                },
                "required": ["command"],
            },
        ),
        Tool(
            name="list_tasks",
            description="List tasks from the aiw knowledge store.",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Filter: pending, in_progress, completed, all"},
                },
            },
        ),
        Tool(
            name="create_task",
            description="Create a new task in the aiw knowledge store.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Short task title"},
                    "description": {"type": "string", "description": "Detailed description"},
                    "priority": {"type": "integer", "description": "Priority 0-10 (default 5)"},
                },
                "required": ["title"],
            },
        ),
        Tool(
            name="update_task_status",
            description="Update a task's status.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "Task ID number"},
                    "status": {"type": "string", "description": "New status: pending, in_progress, completed, blocked"},
                },
                "required": ["task_id", "status"],
            },
        ),
        Tool(
            name="search_knowledge",
            description="Search the aiw knowledge base for relevant context (architecture, code, docs, past research).",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "description": "Max results (default 5)"},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_workspace_info",
            description="Get information about the aiw development workspace (paths, config, stats).",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="list_directory",
            description="List files and directories at a path within the workspace.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path (empty = root)"},
                },
            },
        ),
        Tool(
            name="run_tests",
            description="Run aiw tests using pytest.",
            inputSchema={
                "type": "object",
                "properties": {
                    "test_path": {"type": "string", "description": "Specific test file or directory (empty = all tests)"},
                },
            },
        ),
        Tool(
            name="lint_check",
            description="Run ruff linter on the specified path.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File or directory to lint (empty = entire src)"},
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Route tool calls to handlers."""
    handlers = {
        "read_file": handle_read_file,
        "write_file": handle_write_file,
        "run_shell": handle_run_shell,
        "list_tasks": handle_list_tasks,
        "create_task": handle_create_task,
        "update_task_status": handle_update_task_status,
        "search_knowledge": handle_search_knowledge,
        "get_workspace_info": handle_get_workspace_info,
        "list_directory": handle_list_directory,
        "run_tests": handle_run_tests,
        "lint_check": handle_lint_check,
    }
    
    handler = handlers.get(name)
    if not handler:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    try:
        result = await handler(arguments)
        return [TextContent(type="text", text=str(result))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e}")]


# ═══════════════════════════════════════════════════════════════
# Tool handlers
# ═══════════════════════════════════════════════════════════════

async def handle_read_file(args: dict) -> str:
    path = args.get("path", "")
    start_line = args.get("start_line", 0)
    end_line = args.get("end_line", -1)

    p = _safe_path(path)
    if not p.exists():
        return f"Error: file not found: {path}"
    
    try:
        allowed = any(str(p).startswith(str(a)) for a in ALLOWED_PATHS)
    except Exception:
        allowed = False
    if not allowed:
        return f"Error: path not in allowed directories: {path}"

    content = p.read_text()
    lines = content.split("\n")

    if start_line > 0:
        lines = lines[start_line - 1:]
    if end_line > 0:
        lines = lines[:end_line - max(start_line - 1, 0)]

    numbered = []
    base = max(start_line, 1)
    for i, line in enumerate(lines):
        numbered.append(f"{base + i:4d} | {line}")

    result = "\n".join(numbered)
    if len(result) > 8000:
        result = result[:8000] + f"\n... (truncated, {len(lines)} lines total)"
    return result


async def handle_write_file(args: dict) -> str:
    path = args.get("path", "")
    content = args.get("content", "")

    p = _safe_path(path)
    try:
        allowed = any(str(p).startswith(str(a)) for a in ALLOWED_PATHS)
    except Exception:
        allowed = False
    if not allowed:
        return f"Error: path not in allowed directories: {path}"

    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"Written {len(content)} bytes to {path}"


async def handle_run_shell(args: dict) -> str:
    command = args.get("command", "")
    timeout = args.get("timeout", 30)

    if not _is_shell_allowed(command):
        return (
            f"Error: command not allowed: '{command.split()[0]}'. "
            f"Allowed: {', '.join(ALLOWED_SHELL_COMMANDS)}"
        )

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(WORKSPACE_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout
        if result.stderr:
            output += "\n[stderr]\n" + result.stderr
        if result.returncode != 0:
            output += f"\n[exit code: {result.returncode}]"
        return output[:5000]
    except subprocess.TimeoutExpired:
        return f"Error: command timed out after {timeout}s"
    except Exception as e:
        return f"Error: {e}"


async def handle_list_tasks(args: dict) -> str:
    status = args.get("status", "pending")
    try:
        from ai_workspace.knowledge import KnowledgeStore
        store = KnowledgeStore()
        store.initialize()
        tasks = store.get_tasks(
            status=None if status == "all" else status,
            limit=20,
        )
        store.close()

        if not tasks:
            return "No tasks found."

        lines = []
        for t in tasks:
            lines.append(
                f"[{t['status']}] #{t['id']} {t['title'][:80]} "
                f"(priority: {t.get('priority', '-')})"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error accessing knowledge store: {e}\n\nTip: Run 'aiw init' first if the database is not set up."


async def handle_create_task(args: dict) -> str:
    title = args.get("title", "")
    description = args.get("description", "")
    priority = args.get("priority", 5)

    try:
        from ai_workspace.knowledge import KnowledgeStore
        store = KnowledgeStore()
        store.initialize()
        tid = store.add_task(title, description, priority)
        store.close()
        return f"Task #{tid} created: {title}"
    except Exception as e:
        return f"Error creating task: {e}\n\nTip: Run 'aiw init' first."


async def handle_update_task_status(args: dict) -> str:
    task_id = args.get("task_id", 0)
    status = args.get("status", "")

    try:
        from ai_workspace.knowledge import KnowledgeStore
        store = KnowledgeStore()
        store.initialize()
        store.update_task_status(task_id, status)
        store.close()
        return f"Task #{task_id} → {status}"
    except Exception as e:
        return f"Error updating task: {e}\n\nTip: Run 'aiw init' first."


async def handle_search_knowledge(args: dict) -> str:
    query = args.get("query", "")
    limit = args.get("limit", 5)

    try:
        from ai_workspace.knowledge import KnowledgeStore
        store = KnowledgeStore()
        store.initialize()
        results = store.search_knowledge(query, limit=limit)
        store.close()

        if not results:
            return "No matching knowledge entries found. Tip: Run 'aiw knowledge seed' to index the codebase."

        lines = []
        for r in results:
            content = r.get('content', '')
            lines.append(
                f"## {r.get('title', 'Untitled')} [{r.get('content_type', '?')}]\n"
                f"{content[:500]}"
                + ("..." if len(content) > 500 else "")
                + f"\n---"
            )
        return "\n\n".join(lines)
    except Exception as e:
        return f"Error searching knowledge: {e}"


async def handle_get_workspace_info(args: dict) -> str:
    info = {
        "workspace_root": str(WORKSPACE_ROOT),
        "python_version": sys.version,
        "source_files": len(list(WORKSPACE_ROOT.glob("src/**/*.py"))),
        "test_files": len(list(WORKSPACE_ROOT.glob("tests/**/*.py"))),
        "doc_files": len(list(WORKSPACE_ROOT.glob("docs/**/*.md"))),
        "allowed_paths": [
            str(p.relative_to(WORKSPACE_ROOT))
            for p in ALLOWED_PATHS
        ],
        "allowed_commands": ALLOWED_SHELL_COMMANDS,
    }
    return json.dumps(info, indent=2)


async def handle_list_directory(args: dict) -> str:
    path = args.get("path", "")

    p = _safe_path(path) if path else WORKSPACE_ROOT
    if not p.exists():
        return f"Error: path not found: {path}"

    items = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name))
    lines = []
    for item in items:
        if item.name.startswith(".") and item.name not in (".gitignore", ".env.example", ".mcp.json"):
            continue
        prefix = "📁" if item.is_dir() else "📄"
        size = ""
        if item.is_file():
            size = f" ({item.stat().st_size:,} bytes)"
        lines.append(f"{prefix} {item.name}{size}")
    return "\n".join(lines[:50])


async def handle_run_tests(args: dict) -> str:
    test_path = args.get("test_path", "")
    venv_python = WORKSPACE_ROOT / ".venv" / "bin" / "python"
    python = str(venv_python) if venv_python.exists() else "python"
    cmd = f"cd {WORKSPACE_ROOT} && {python} -m pytest {test_path or 'tests/'} -x --tb=short -q 2>&1"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
    return result.stdout[-3000:] + (result.stderr[-1000:] if result.stderr else "")


async def handle_lint_check(args: dict) -> str:
    path = args.get("path", "")
    target = path or "src/"
    venv_python = WORKSPACE_ROOT / ".venv" / "bin" / "python"
    python = str(venv_python) if venv_python.exists() else "python"
    cmd = f"cd {WORKSPACE_ROOT} && {python} -m ruff check {target} 2>&1"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    if result.returncode == 0:
        return "✅ No linting errors."
    return result.stdout[:2000] or "Linting issues found (check output)."


# ═══════════════════════════════════════════════════════════════
# Entry points
# ═══════════════════════════════════════════════════════════════


async def run_stdio():
    """Run the MCP server over stdio (for Claude Code, Codex, etc.)."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main():
    """Entry point: aiw-mcp or python -m ai_workspace.mcp_server"""
    asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
