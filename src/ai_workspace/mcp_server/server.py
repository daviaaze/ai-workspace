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

from ai_workspace.mcp_server.agent_tools import (
    handle_aiw_agent_run,
    handle_aiw_agent_status,
    handle_aiw_agent_kill,
)

from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


# Configuration

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


# Server

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
        Tool(
            name="ui_component_pattern",
            description="Look up UI component patterns, code examples, and best practices. Use when designing a new UI component, choosing a component library, or finding the right pattern for a UI problem. Covers React/Tailwind/shadcn, Streamlit, and Textual TUI.",
            inputSchema={
                "type": "object",
                "properties": {
                    "component": {"type": "string", "description": "Component type: 'card', 'table', 'form', 'modal', 'nav', 'dashboard', 'empty-state', 'loading', 'toast', 'dialog', 'sidebar', 'dropdown', or any UI pattern"},
                    "stack": {"type": "string", "description": "Target stack: 'react-shadcn', 'react-tailwind', 'streamlit', 'textual', 'html-css', or 'any' (default)"},
                },
                "required": ["component"],
            },
        ),
        Tool(
            name="ui_accessibility_check",
            description="Check UI code (HTML, TSX, JSX) for common accessibility issues: missing labels, color contrast, focus management, semantic HTML, ARIA. Returns a list of issues with fix suggestions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "UI code snippet to check"},
                    "file_path": {"type": "string", "description": "Path to a file to read and check (alternative to inline code)"},
                },
            },
        ),
        Tool(
            name="ui_design_tokens",
            description="Generate a complete design token set (colors, spacing, typography, shadows, radius) as CSS custom properties, Tailwind config, or TypeScript constants. Use when starting a new UI project or standardizing design tokens.",
            inputSchema={
                "type": "object",
                "properties": {
                    "style": {"type": "string", "description": "Style: 'professional', 'warm', 'vibrant', 'minimal', or 'brand'"},
                    "format": {"type": "string", "description": "Output: 'css-vars', 'tailwind-config', 'typescript', or 'all' (default)"},
                    "brand_color": {"type": "string", "description": "Primary brand color hex (e.g., '#2563eb'). Required for 'brand' style."},
                },
            },
        ),
        # Agent tools (SPEC_AGENT_MCP_TOOL)
        Tool(
            name="aiw_agent_run",
            description="Run an AI Workspace agent to research, code, or perform general tasks. The agent has access to web search, file system, git, and shell tools. Supports streaming (NDJSON) and batch (result + metadata) modes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Task description in natural language"},
                    "agent_type": {"type": "string", "description": "'coding', 'research', or 'general' (default general)"},
                    "model": {"type": "string", "description": "Model name (default 'qwen3:14b')"},
                    "provider": {"type": "string", "description": "Provider name (default 'ollama')"},
                    "stream": {"type": "boolean", "description": "If true, returns NDJSON events (default false)"},
                },
                "required": ["task"],
            },
        ),
        Tool(
            name="aiw_agent_status",
            description="Get status of all running AI Workspace agents.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="aiw_agent_kill",
            description="Kill a running agent by ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent ID to kill"},
                },
                "required": ["agent_id"],
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
        "ui_component_pattern": handle_ui_component_pattern,
        "ui_accessibility_check": handle_ui_accessibility_check,
        "ui_design_tokens": handle_ui_design_tokens,
        # Agent tools (SPEC_AGENT_MCP_TOOL)
        "aiw_agent_run": handle_aiw_agent_run,
        "aiw_agent_status": handle_aiw_agent_status,
        "aiw_agent_kill": handle_aiw_agent_kill,
    }
    
    handler = handlers.get(name)
    if not handler:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    try:
        result = await handler(arguments)
        return [TextContent(type="text", text=str(result))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e}")]


# Tool handlers

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
        prefix = "" if item.is_dir() else ""
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
        return " No linting errors."
    return result.stdout[:2000] or "Linting issues found (check output)."


# UI Design tools

UI_PATTERNS = {
    "card": {
        "react-shadcn": "Use shadcn/ui <Card>, <CardHeader>, <CardContent>, <CardFooter>. Loading: <Skeleton>. Error: Alert inside card. Empty: centered message with icon.",
        "streamlit": "st.container(border=True) for cards. st.metric() for stat cards. st.columns() for card grid.",
        "textual": "Vertical container with border. CSS: 'border: solid $primary; padding: 1;'. Rich renderables for content.",
        "html-css": "div with rounded-lg border bg-white shadow-sm. Flex column layout. Skeleton animation for loading.",
    },
    "table": {
        "react-shadcn": "@tanstack/react-table + shadcn/ui DataTable. Sorting, filtering, pagination, row selection. Server-side or client-side.",
        "streamlit": "st.dataframe() interactive. st.data_editor() for editable. Column config for formatting.",
        "textual": "DataTable widget. Sorting on click. Cursor navigation. Custom cell renderers.",
        "html-css": "table with thead/tbody. sticky header. Alternating row colors. Responsive: card layout on mobile.",
    },
    "form": {
        "react-shadcn": "react-hook-form + zod. shadcn/ui Form, Input, Select, Checkbox, Textarea. Inline validation on blur + submit.",
        "streamlit": "st.form() for grouped inputs. st.form_submit_button(). Session state for multi-step.",
        "textual": "Input, Select, Checkbox, RadioButton widgets. Screen modal for form dialogs.",
        "html-css": "form element with fieldset/legend. Labels above inputs. Required asterisks. Error messages in red below fields.",
    },
    "modal": {
        "react-shadcn": "shadcn/ui Dialog (modal), Sheet (slide-out), AlertDialog (confirmation). Focus trap, ESC close, backdrop click.",
        "streamlit": "st.dialog() (1.38+). For older: st.expander or session state toggle.",
        "textual": "Screen with modal layer. Dimmed background overlay. Return focus on close.",
        "html-css": "div with fixed inset-0 z-50, backdrop blur. role='dialog' aria-modal='true'. Focus trap with JS.",
    },
    "nav": {
        "react-shadcn": "Sidebar: fixed left w-64, Sheet on mobile. Active state: accent bg. Collapsible groups.",
        "streamlit": "st.sidebar for nav, st.page_link() for multi-page. Radio/select for simple nav.",
        "textual": "Left panel with Vertical layout. TabbedContent for tab navigation.",
        "html-css": "nav element. Desktop: horizontal or vertical. Mobile: hamburger menu with slide-out. aria-current='page'.",
    },
    "dashboard": {
        "react-shadcn": "Grid: grid-cols-1 md:grid-cols-2 lg:grid-cols-4. Stat cards + recharts + DataTable. Filter bar.",
        "streamlit": "layout='wide'. st.columns() for grid. st.metric() for KPIs. st.plotly_chart().",
        "textual": "Grid container. StatCard widgets. Live updates with set_interval().",
        "html-css": "CSS Grid. card components. Responsive breakpoints. Loading skeletons not spinners.",
    },
    "empty-state": {
        "react-shadcn": "Centered flex-col with icon (lucide-react), title, description, CTA button. Use for: no data, no results, error recovery.",
        "streamlit": "st.info() or st.warning() with message and button. Centered container with icon.",
        "textual": "Centered static text. Rich markup for icon. Button for action.",
        "html-css": "flex flex-col items-center justify-center py-12. SVG icon, h3 title, p description, button.",
    },
    "loading": {
        "react-shadcn": "<Skeleton> for content areas (shape-based, pulse animation). <Spinner> for buttons. Progress bar for determinate.",
        "streamlit": "st.spinner() for full page. st.progress() for determinate. st.status() for async operations.",
        "textual": "LoadingIndicator widget. Rich progress bar. set_interval() for polling.",
        "html-css": "Skeleton: div with animate-pulse bg-gray-200 rounded. Spinner: SVG circle with animation. aria-busy='true'.",
    },
}


async def handle_ui_component_pattern(args: dict) -> str:
    component = args.get("component", "").lower()
    stack = args.get("stack", "any").lower()

    patterns = UI_PATTERNS.get(component)
    if not patterns:
        available = ", ".join(sorted(UI_PATTERNS.keys()))
        return f"Component '{component}' not found. Available patterns: {available}\n\nTip: Try one of these or search the knowledge base with 'ui component {component}'."

    result = [f"## {component.title()} Component Pattern\n"]

    if stack in patterns:
        result.append(f"### {stack}\n{patterns[stack]}")
    else:
        result.append(f"Available stacks for '{component}':\n")
        for s, desc in patterns.items():
            result.append(f"- **{s}**: {desc}")
        result.append(f"\nTip: Specify 'stack' parameter for a specific implementation.")

    return "\n".join(result)


async def handle_ui_accessibility_check(args: dict) -> str:
    code = args.get("code", "")
    file_path = args.get("file_path", "")

    if file_path and not code:
        p = _safe_path(file_path)
        if p.exists():
            code = p.read_text()
        else:
            return f"Error: file not found: {file_path}"

    if not code:
        return "Provide either 'code' (inline snippet) or 'file_path' (file to read)."

    issues = []

    # Check 1: Semantic HTML
    if '<div onclick' in code or '<div onKeyDown' in code:
        issues.append(" DIV used as button — use <button> element instead")
    if '<div role="button"' in code and 'tabindex' not in code:
        issues.append(" DIV button missing tabindex — add tabindex='0'")

    # Check 2: Form labels
    has_input = any(t in code for t in ["<input", "<select", "<textarea"])
    has_label = any(t in code for t in ["<label", "aria-label", "aria-labelledby"])
    if has_input and not has_label:
        issues.append(" Form input missing label — add <label> or aria-label")

    # Check 3: Alt text
    if "<img " in code and "alt=" not in code:
        issues.append(" Image missing alt attribute — add descriptive alt text or alt='' for decorative")

    # Check 4: Focus
    if "outline-none" in code and "ring" not in code and "focus" not in code:
        issues.append(" outline-none without replacement focus style — add focus-visible:ring-2")
    if "outline: none" in code and "focus" not in code:
        issues.append(" outline:none without replacement focus style")

    # Check 5: Color-only indicators
    if ("text-red" in code or "text-green" in code) and "icon" not in code.lower():
        issues.append(" Possible color-only indicator — add icon or text label alongside color")

    # Check 6: Touch targets
    for small in ["w-6 h-6", "w-8 h-8", "size-8", "w-5 h-5"]:
        if small in code:
            issues.append(f" Small touch target ({small}) — ensure ≥ 44×44px on mobile. Add padding.")
            break

    # Check 7: Reduced motion
    if "animate-" in code and "prefers-reduced-motion" not in code:
        issues.append(" Animation without reduced-motion check — wrap in @media (prefers-reduced-motion: no-preference)")

    # Check 8: lang attribute
    if (code.strip().startswith("<!DOCTYPE") or code.strip().startswith("<html")) and "lang=" not in code:
        issues.append(" Missing lang attribute on <html> — add lang='en'")

    # Check 9: role on interactive elements
    if "<button" in code and 'type="button"' not in code and 'type="submit"' not in code and 'type="reset"' not in code:
        issues.append(" Button missing type attribute — add type='button' (prevents accidental form submission)")

    if not issues:
        return (" No common accessibility issues detected.\n\n"
                "Manual review still recommended:\n"
                "- Tab through component with keyboard\n"
                "- Test with screen reader (VoiceOver/NVDA)\n"
                "- Verify color contrast with axe DevTools")

    return "## Accessibility Issues Found\n\n" + "\n".join(issues) + (
        "\n\n---\nReference: .agents/skills/ui-design/references/accessibility.md"
    )


async def handle_ui_design_tokens(args: dict) -> str:
    style = args.get("style", "professional")
    fmt = args.get("format", "all")
    brand_color = args.get("brand_color", "#2563eb")

    palettes = {
        "professional": {"secondary": "#475569", "accent": "#8b5cf6", "bg": "#f8fafc", "surface": "#ffffff", "text": "#0f172a"},
        "warm": {"secondary": "#78716c", "accent": "#f59e0b", "bg": "#fafaf9", "surface": "#ffffff", "text": "#292524"},
        "vibrant": {"secondary": "#059669", "accent": "#db2777", "bg": "#faf5ff", "surface": "#ffffff", "text": "#1e1b4b"},
        "minimal": {"secondary": "#52525b", "accent": "#18181b", "bg": "#ffffff", "surface": "#fafafa", "text": "#09090b"},
    }
    p = palettes.get(style, palettes["professional"])

    result = [f"## Design Tokens — {style} style\n"]

    if fmt in ("css-vars", "all"):
        result.append("### CSS Custom Properties\n```css")
        result.append(":root {")
        result.append(f"  --color-primary: {brand_color};")
        result.append(f"  --color-secondary: {p['secondary']};")
        result.append(f"  --color-accent: {p['accent']};")
        result.append(f"  --color-background: {p['bg']};")
        result.append(f"  --color-surface: {p['surface']};")
        result.append(f"  --color-text: {p['text']};")
        result.append("  --color-text-muted: #64748b;")
        result.append("  --color-border: #e2e8f0;")
        result.append("  --color-success: #16a34a;")
        result.append("  --color-warning: #f59e0b;")
        result.append("  --color-error: #dc2626;")
        result.append("  --space-xs: 4px; --space-sm: 8px; --space-md: 16px; --space-lg: 24px; --space-xl: 32px;")
        result.append("  --radius-sm: 4px; --radius-md: 6px; --radius-lg: 8px;")
        result.append("  --font-sans: 'Inter', system-ui, sans-serif;")
        result.append("  --font-mono: 'JetBrains Mono', monospace;")
        result.append("  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);")
        result.append("  --shadow-md: 0 4px 6px rgba(0,0,0,0.07);")
        result.append("  --shadow-lg: 0 10px 15px rgba(0,0,0,0.1);")
        result.append("  --transition-fast: 100ms ease-in-out;")
        result.append("  --transition-normal: 150ms ease-in-out;")
        result.append("}")
        result.append("```\n")

    if fmt in ("tailwind-config", "all"):
        result.append("### Tailwind Config\n```js")
        result.append("module.exports = {")
        result.append("  theme: {")
        result.append("    extend: {")
        result.append(f"      colors: {{ brand: {{ DEFAULT: '{brand_color}', hover: 'color-mix(in srgb, {brand_color} 90%, black)', light: 'color-mix(in srgb, {brand_color} 10%, white)' }} }},")
        result.append("    },")
        result.append("  },")
        result.append("};")
        result.append("```\n")

    if fmt in ("typescript", "all"):
        result.append("### TypeScript Constants\n```typescript")
        result.append("export const tokens = {")
        result.append(f"  colors: {{ primary: '{brand_color}', secondary: '{p['secondary']}', accent: '{p['accent']}', background: '{p['bg']}', surface: '{p['surface']}', text: '{p['text']}', muted: '#64748b', border: '#e2e8f0', success: '#16a34a', warning: '#f59e0b', error: '#dc2626' }} as const,")
        result.append("  spacing: { xs: 4, sm: 8, md: 16, lg: 24, xl: 32, '2xl': 48 } as const,")
        result.append("  radius: { sm: 4, md: 6, lg: 8, xl: 12 } as const,")
        result.append("};")
        result.append("```")

    return "\n".join(result)


# Entry points


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
