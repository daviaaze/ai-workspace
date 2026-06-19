"""
TUI Agent Tools — OpenAI function-calling format for agent_loop.

Each tool has a definition dict (schema) and a handler callable.
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger("aiw.tui.tools")


def build_tools(cwd: str) -> tuple[list[dict], dict[str, callable]]:
    """Build the full toolset for the TUI agent loop."""

    base = Path(cwd).resolve()

    def _safe_path(path: str) -> Path:
        target = Path(path)
        if not target.is_absolute():
            target = base / target
        target = target.resolve()
        try:
            target.relative_to(base)
        except ValueError:
            raise PermissionError(f"Path outside workspace: {path}")
        return target

    # ── Tool Definitions ────────────────────────────────

    tool_defs = [
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files and subdirectories in a directory",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Directory path (relative or absolute)"}
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read the contents of a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the file"},
                        "limit": {"type": "integer", "description": "Max lines to read (default 200)"},
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Create or overwrite a file with given content",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the file"},
                        "content": {"type": "string", "description": "Content to write"},
                    },
                    "required": ["path", "content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_files",
                "description": "Search file contents using grep (pattern matching)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "Text or regex pattern to search for"},
                        "path": {"type": "string", "description": "Directory to search in (default: project root)"},
                    },
                    "required": ["pattern"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "run_command",
                "description": "Execute a shell command. Use for git, tests, builds, etc.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Shell command to execute"}
                    },
                    "required": ["command"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "git_status",
                "description": "Show working tree status (changed files, branch, etc.)",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "git_log",
                "description": "Show recent commit history",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "Max commits (default 10)"}
                    },
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "git_diff",
                "description": "Show unstaged changes in working tree",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web for information on a topic",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "max_results": {"type": "integer", "description": "Max results (default 5)"},
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "web_fetch",
                "description": "Fetch and read content from a URL",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to fetch"},
                        "max_length": {"type": "integer", "description": "Max characters to return (default 3000)"},
                    },
                    "required": ["url"],
                },
            },
        },
    ]

    # ── Tool Handlers ──────────────────────────────────

    def list_files(path: str) -> str:
        try:
            target = _safe_path(path)
        except PermissionError as e:
            return f"Error: {e}"
        if not target.exists():
            return "Error: Path does not exist"
        if not target.is_dir():
            target = target.parent
        entries = []
        for p in sorted(target.iterdir()):
            suffix = "/" if p.is_dir() else ""
            size = ""
            if p.is_file():
                try:
                    s = p.stat().st_size
                    if s < 1024:
                        size = f" ({s}B)"
                    elif s < 1024 * 1024:
                        size = f" ({s // 1024}KB)"
                    else:
                        size = f" ({s // (1024 * 1024)}MB)"
                except OSError:
                    pass
            entries.append(f"  {p.name}{suffix}{size}")
        return "\n".join(entries[:80]) if entries else "(empty)"

    def read_file(path: str, limit: int = 200) -> str:
        try:
            target = _safe_path(path)
        except PermissionError as e:
            return f"Error: {e}"
        if not target.is_file():
            return "Error: Not a file"
        try:
            lines = target.read_text(encoding="utf-8").splitlines()
            if len(lines) > limit:
                return "\n".join(lines[:limit]) + f"\n... ({len(lines) - limit} more lines)"
            return "\n".join(lines)
        except UnicodeDecodeError:
            return "Error: Binary file, cannot read as text"
        except Exception as e:
            return f"Error: {e}"

    def write_file(path: str, content: str) -> str:
        try:
            target = _safe_path(path)
        except PermissionError as e:
            return f"Error: {e}"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return f"Wrote {len(content)} bytes to {target}"
        except Exception as e:
            return f"Error: {e}"

    def search_files(pattern: str, path: str = ".") -> str:
        try:
            search_dir = _safe_path(path)
        except PermissionError as e:
            return f"Error: {e}"
        try:
            r = subprocess.run(
                ["grep", "-rn", "--include=*.py", "--include=*.md", "--include=*.toml",
                 "--include=*.yaml", "--include=*.json", "--include=*.nix",
                 "-I", pattern, str(search_dir)],
                capture_output=True, text=True, timeout=10, cwd=cwd,
            )
            if r.returncode == 1:  # no matches
                return f"No matches for '{pattern}'"
            output = r.stdout.strip()[:4000]
            if r.stdout.count("\n") > 30:
                output = "\n".join(output.split("\n")[:30]) + "\n... (truncated)"
            return output or "(no matches)"
        except subprocess.TimeoutExpired:
            return "Error: search timed out"
        except FileNotFoundError:
            return "Error: grep not available"
        except Exception as e:
            return f"Error: {e}"

    def run_command(command: str) -> str:
        try:
            r = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                cwd=cwd, timeout=30,
            )
            output = r.stdout.strip() or r.stderr.strip() or "(no output)"
            if r.returncode != 0:
                output += f"\n(exit code: {r.returncode})"
            return output[:3000]
        except subprocess.TimeoutExpired:
            return "Error: command timed out (30s)"
        except Exception as e:
            return f"Error: {e}"

    def git_status() -> str:
        try:
            r = subprocess.run(
                ["git", "status", "--short", "--branch"],
                capture_output=True, text=True, cwd=cwd, timeout=5,
            )
            return r.stdout.strip()[:2000] or "(clean)"
        except subprocess.TimeoutExpired:
            return "Error: git timed out"
        except FileNotFoundError:
            return "Error: git not installed"
        except Exception as e:
            return f"Error: {e}"

    def git_log(limit: int = 10) -> str:
        try:
            r = subprocess.run(
                ["git", "log", "--oneline", f"-{limit}"],
                capture_output=True, text=True, cwd=cwd, timeout=5,
            )
            return r.stdout.strip()[:2000] or "(no commits)"
        except subprocess.TimeoutExpired:
            return "Error: git timed out"
        except FileNotFoundError:
            return "Error: git not installed"
        except Exception as e:
            return f"Error: {e}"

    def git_diff() -> str:
        try:
            r = subprocess.run(
                ["git", "diff"],
                capture_output=True, text=True, cwd=cwd, timeout=10,
            )
            output = r.stdout.strip()[:3000] or "(no changes)"
            return output
        except subprocess.TimeoutExpired:
            return "Error: git timed out"
        except FileNotFoundError:
            return "Error: git not installed"
        except Exception as e:
            return f"Error: {e}"

    def web_search(query: str, max_results: int = 5) -> str:
        try:
            from ai_workspace.search.deep_search import DeepSearchEngine
            engine = DeepSearchEngine(max_depth=1)
            result = engine.research_sync(query)
            if result and result.answer:
                return f"Answer: {result.answer[:2000]}\nConfidence: {result.confidence:.0%}"
            return f"No results for '{query}'"
        except ImportError:
            return "Web search not available (DeepSearchEngine not found)"
        except Exception as e:
            logger.warning("web_search failed: %s", e)
            return f"Web search error: {e}"

    def web_fetch(url: str, max_length: int = 3000) -> str:
        try:
            import httpx
            with httpx.Client(timeout=httpx.Timeout(10), follow_redirects=True) as client:
                r = client.get(url)
                r.raise_for_status()
                text = r.text[:max_length]
                return text
        except ImportError:
            return "Error: httpx not available"
        except Exception as e:
            return f"Error fetching URL: {e}"

    handlers = {
        "list_files": list_files,
        "read_file": read_file,
        "write_file": write_file,
        "search_files": search_files,
        "run_command": run_command,
        "git_status": git_status,
        "git_log": git_log,
        "git_diff": git_diff,
        "web_search": web_search,
        "web_fetch": web_fetch,
    }

    return tool_defs, handlers
