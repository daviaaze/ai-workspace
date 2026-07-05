"""TUI IPC Server — reads JSON commands from stdin, streams NDJSON events to stdout.

Protocol:
  TUI → stdin:  {"cmd":"chat","task":"...","model":"..."}
                {"cmd":"cancel"}
                {"cmd":"models","provider":"ollama"}
                {"cmd":"sessions","action":"list"}
                {"cmd":"dashboard"}
                {"cmd":"context","action":"list"}
                {"cmd":"git"}
                {"cmd":"kb_search","query":"..."}
                {"cmd":"filebrowser","path":"..."}
                {"cmd":"quit"}

  stdout → TUI: {"type":"token","data":{"text":"..."}}
                {"type":"thinking","data":{"text":"..."}}
                {"type":"tool_call","data":{"name":"...","args":{...},"id":"..."}}
                {"type":"tool_result","data":{"id":"...","result":"...","duration":0.0}}
                {"type":"done","data":{"reason":"...","tokens":0,"cost":0.0}}
                {"type":"error","data":{"message":"..."}}
                {"type":"phase","data":{"phase":"..."}}
                {"type":"status","data":{"running":false,"tokens":0,"cost":0.0,"model":"..."}}
                {"type":"result","data":{...}}   # for non-streaming commands
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger("aiw.tui.server")

# ── Helpers ──────────────────────────────────────────────────────────


def emit(event_type: str, data: dict) -> None:
    """Write one NDJSON event to stdout."""
    line = json.dumps({"type": event_type, "data": data}, default=str)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def emit_result(data: dict) -> None:
    emit("result", data)


def emit_error(message: str) -> None:
    emit("error", {"message": message})


# ── Command Handlers ────────────────────────────────────────────────


async def handle_chat(task: str, model: str, history: list | None = None) -> None:
    """Run agent_loop and stream events to stdout."""
    from ai_workspace.agents.loop import LoopParams, agent_loop, suggest_pattern
    from ai_workspace.tui.v5.tools import build_tools

    tool_defs, tool_handlers = build_tools(str(Path.cwd()))
    pattern = suggest_pattern(task, tool_defs)

    params = LoopParams(
        task=task,
        pattern=pattern,
        model=model,
        tools=tool_defs,
        tool_handlers=tool_handlers,
        max_turns=20,
        stream=True,
        messages=history or [],
    )

    try:
        async for event in agent_loop(params):
            etype = event.type
            data = event.data

            if etype == "token":
                emit("token", {"text": data.get("text", "")})
            elif etype == "thinking":
                emit("thinking", {"text": data.get("text", "")})
            elif etype == "tool_call":
                emit("tool_call", {
                    "name": data.get("name", ""),
                    "args": data.get("arguments", data.get("args", {})),
                    "id": data.get("id", ""),
                })
            elif etype == "tool_result":
                emit("tool_result", {
                    "id": data.get("id", ""),
                    "result": data.get("result", ""),
                    "duration": data.get("duration", 0.0),
                })
            elif etype == "done":
                emit("done", {
                    "reason": data.get("reason", "completed"),
                    "tokens": data.get("tokens", 0),
                    "cost": data.get("cost", 0.0),
                })
            elif etype == "error":
                emit("error", {"message": str(data.get("message", data))})
            elif etype == "phase":
                emit("phase", {"phase": data.get("phase", "")})

    except asyncio.CancelledError:
        emit("done", {"reason": "cancelled", "tokens": 0, "cost": 0.0})
    except Exception as exc:
        emit_error(f"Agent loop failed: {exc}")
        logger.exception("agent_loop failed")


async def handle_models(provider: str = "ollama") -> list[dict]:
    """List available models from a provider."""
    if provider == "ollama":
        try:
            import httpx

            base_url = "http://localhost:11434"
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{base_url}/api/tags", timeout=5)
                resp.raise_for_status()
                data = resp.json()
                models = [
                    {"name": m["name"], "size": m.get("size", 0)}
                    for m in data.get("models", [])
                ]
                return models or [{"name": "qwen3:14b", "size": 0}]
        except Exception as exc:
            logger.warning("Failed to list Ollama models: %s", exc)
            return [{"name": "qwen3:14b", "size": 0}]

    return [{"name": "qwen3:14b", "size": 0}]


async def handle_sessions(action: str) -> list[dict] | None:
    """Manage sessions."""
    from ai_workspace.tui.v5.sessions import list_sessions

    if action == "list":
        return list_sessions()
    elif action == "load":
        # session_id is passed via extra data — we handle it at router level
        return None
    return None


async def handle_dashboard() -> dict:
    """Collect dashboard stats from backend."""
    result: dict = {
        "stats": {},
        "health": {},
        "activity": [],
        "cost": {},
    }

    try:
        from ai_workspace.core.cost import CostService

        cost = CostService()
        result["cost"] = {
            "total": cost.get_total_cost(),
            "session": cost.get_session_cost(),
            "budget": cost.get_budget(),
        }
    except Exception:
        pass

    try:
        from ai_workspace.knowledge import KnowledgeStore

        kb = KnowledgeStore()
        stats = kb.get_stats()
        result["stats"] = {
            "documents": stats.get("documents", 0),
            "chunks": stats.get("chunks", 0),
            "kbs": stats.get("knowledge_bases", 0),
        }
    except Exception:
        pass

    try:
        from ai_workspace.core.db import get_store

        db = get_store()
        db_ok = await db.check_connection()
        result["health"]["db"] = "ok" if db_ok else "error"
    except Exception:
        result["health"]["db"] = "error"

    return result


async def handle_context(action: str) -> list[dict] | dict:
    """Query context manager state."""
    from ai_workspace.agents.context_manager import ContextManager

    cm = ContextManager()

    if action == "list":
        blocks = cm.get_blocks()
        files = []
        for b in blocks:
            files.append({
                "path": b.file_path or "",
                "tokens": b.tokens or 0,
                "status": b.status or "active",
                "lines": len((b.content or "").splitlines()),
            })
        return {"files": files, "total_tokens": cm.total_tokens()}

    return {"files": [], "total_tokens": 0}


async def handle_git() -> dict:
    """Get git status."""
    import subprocess

    result: dict = {"branch": "", "status": [], "log": []}

    try:
        r = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, timeout=2,
        )
        if r.returncode == 0:
            result["branch"] = r.stdout.strip()
    except Exception:
        pass

    try:
        r = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=2,
        )
        if r.returncode == 0:
            for line in r.stdout.strip().splitlines():
                if line:
                    xy = line[:2]
                    path = line[3:]
                    result["status"].append({"flag": xy.strip(), "path": path})
    except Exception:
        pass

    try:
        r = subprocess.run(
            ["git", "log", "--oneline", "-10"],
            capture_output=True, text=True, timeout=2,
        )
        if r.returncode == 0:
            for line in r.stdout.strip().splitlines():
                if line:
                    parts = line.split(" ", 1)
                    result["log"].append({
                        "hash": parts[0],
                        "message": parts[1] if len(parts) > 1 else "",
                    })
    except Exception:
        pass

    return result


async def handle_kb_search(query: str) -> dict:
    """Search knowledge base."""
    try:
        from ai_workspace.knowledge import KnowledgeStore

        kb = KnowledgeStore()
        results = await kb.search(query, limit=5)
        return {
            "results": [
                {
                    "title": r.get("title", ""),
                    "content": r.get("content", "")[:300],
                    "score": r.get("score", 0.0),
                    "source": r.get("source", ""),
                }
                for r in results
            ]
        }
    except Exception as exc:
        return {"results": [], "error": str(exc)}


async def handle_filebrowser(path: str) -> dict:
    """List directory contents."""
    try:
        p = Path(path).resolve()
        if not p.is_dir():
            return {"error": "Not a directory", "entries": []}

        entries = []
        for child in sorted(p.iterdir()):
            try:
                is_dir = child.is_dir()
                stat = child.stat()
                entries.append({
                    "name": child.name,
                    "path": str(child),
                    "is_dir": is_dir,
                    "size": stat.st_size if not is_dir else 0,
                    "modified": stat.st_mtime,
                })
            except OSError:
                continue

        return {"entries": entries, "current": str(p), "parent": str(p.parent)}
    except Exception as exc:
        return {"error": str(exc), "entries": []}


# ── Command Router ──────────────────────────────────────────────────


async def route_command(cmd: dict) -> None:
    """Route a parsed JSON command to the appropriate handler."""
    cmd_type = cmd.get("cmd", "")

    if cmd_type == "chat":
        await handle_chat(
            task=cmd.get("task", ""),
            model=cmd.get("model", "qwen3:14b"),
            history=cmd.get("messages"),
        )

    elif cmd_type == "models":
        models = await handle_models(cmd.get("provider", "ollama"))
        emit_result({"models": models})

    elif cmd_type == "sessions":
        action = cmd.get("action", "list")
        if action == "list":
            sessions = handle_sessions("list")
            emit_result({"sessions": sessions})
        elif action == "load":
            session_id = cmd.get("session_id", "")
            from ai_workspace.tui.v5.sessions import load_session

            msgs = load_session(session_id)
            emit_result({"messages": msgs or []})

    elif cmd_type == "dashboard":
        data = await handle_dashboard()
        emit_result(data)

    elif cmd_type == "context":
        data = await handle_context(cmd.get("action", "list"))
        emit_result(data)

    elif cmd_type == "git":
        data = await handle_git()
        emit_result(data)

    elif cmd_type == "kb_search":
        data = await handle_kb_search(cmd.get("query", ""))
        emit_result(data)

    elif cmd_type == "filebrowser":
        data = await handle_filebrowser(cmd.get("path", "."))
        emit_result(data)

    else:
        emit_error(f"Unknown command: {cmd_type}")


# ── Main Loop ───────────────────────────────────────────────────────


def run_stdio_server() -> None:
    """Main entry: read JSON commands from stdin, stream events to stdout.

    Usage:
        aiw tui-server --stdio

    The TUI frontend spawns this process and communicates over stdio.
    """
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s %(name)s %(message)s",
    )

    # Must use unbuffered I/O for IPC
    sys.stdin.reconfigure(line_buffering=False)
    sys.stdout.reconfigure(line_buffering=False)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    current_task: asyncio.Task | None = None

    try:
        for raw_line in sys.stdin:
            raw_line = raw_line.strip()
            if not raw_line:
                continue

            try:
                cmd = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                emit_error(f"Invalid JSON: {exc}")
                continue

            cmd_type = cmd.get("cmd", "")

            # Handle quit immediately
            if cmd_type == "quit":
                if current_task and not current_task.done():
                    current_task.cancel()
                break

            # Handle cancel: cancel the running agent task
            if cmd_type == "cancel":
                if current_task and not current_task.done():
                    current_task.cancel()
                emit("done", {"reason": "cancelled", "tokens": 0, "cost": 0.0})
                continue

            # Run command (blocking until done for non-chat, or streaming for chat)
            if cmd_type == "chat":
                current_task = loop.create_task(route_command(cmd))
                try:
                    loop.run_until_complete(current_task)
                except asyncio.CancelledError:
                    pass
            else:
                loop.run_until_complete(route_command(cmd))

    except KeyboardInterrupt:
        if current_task and not current_task.done():
            current_task.cancel()
    finally:
        loop.close()


if __name__ == "__main__":
    run_stdio_server()
