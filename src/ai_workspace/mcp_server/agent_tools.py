"""
MCP Agent Tools — expose AI Workspace agents as MCP-callable tools.

Registered tools:
  aiw_agent_run     — run an agent on a task (batch or streaming via NDJSON)
  aiw_agent_status  — list running agents and their current state
  aiw_agent_kill    — kill a running agent by ID

Refs:
- SPEC_AGENT_MCP_TOOL.md
- fastmcp-agents (archived pattern)
"""

from __future__ import annotations

import asyncio
import json as _json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from ai_workspace.agents.loop import (
    agent_loop,
    LoopParams,
    LoopPattern,
    TerminalReason,
    suggest_pattern,
)

logger = logging.getLogger("aiw.mcp.agent_tools")


# ═══════════════════════════════════════════════════════════
# Agent registry (tracks running agents)
# ═══════════════════════════════════════════════════════════

@dataclass
class AgentRecord:
    """Tracks a running agent."""
    id: str
    task: str
    agent_type: str
    model: str
    provider: str
    status: str  # "starting", "running", "done", "error", "killed"
    started_at: float = field(default_factory=time.monotonic)
    turns: int = 0
    tokens: int = 0
    task_ref: asyncio.Task | None = None
    result: str = ""
    error: str = ""


# In-memory agent registry (shared across MCP calls within the same process)
_agents: dict[str, AgentRecord] = {}
_agent_counter: int = 0


def _next_id() -> str:
    global _agent_counter
    _agent_counter += 1
    return f"agent-{_agent_counter}"


# ═══════════════════════════════════════════════════════════
# Tool: aiw_agent_run
# ═══════════════════════════════════════════════════════════

async def handle_aiw_agent_run(arguments: dict) -> str:
    """Run an AI Workspace agent on a task.

    Args:
        task: Task description in natural language.
        agent_type: 'coding', 'research', or 'general' (default general).
        model: Model name (default 'qwen3:14b').
        provider: Provider name (default 'ollama').
        stream: If true, returns NDJSON events (default false).
    """
    task = arguments.get("task", "")
    agent_type = arguments.get("agent_type", "general")
    model = arguments.get("model", "qwen3:14b")
    provider = arguments.get("provider", "ollama")
    stream = arguments.get("stream", False)

    if not task.strip():
        return "[$error]Error: task is required[/]"

    agent_id = _next_id()
    record = AgentRecord(
        id=agent_id,
        task=task,
        agent_type=agent_type,
        model=model,
        provider=provider,
        status="starting",
    )
    _agents[agent_id] = record

    pattern = suggest_pattern(task)

    params = LoopParams(
        task=task,
        pattern=pattern,
        model=model,
        provider=provider,
        stream=True,
        max_turns=15 if agent_type == "coding" else 10,
    )

    if stream:
        # Streaming mode: collect NDJSON events as they happen
        events: list[str] = []

        async def _stream_task():
            record.status = "running"
            try:
                async for event in agent_loop(params):
                    evt_data: dict[str, Any] = {
                        "type": event.type,
                        "data": event.data,
                    }
                    events.append(_json.dumps(evt_data, ensure_ascii=False))

                    if event.type == "done":
                        record.status = "done"
                        record.turns = event.data.get("turns", 0)
                        record.tokens = event.data.get("tokens", 0)
            except Exception as exc:
                record.status = "error"
                record.error = str(exc)
                events.append(_json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False))

        # Run in background so the caller gets streaming events
        record.task_ref = asyncio.create_task(_stream_task())

        # Wait for completion (collect all events)
        await record.task_ref

        return "\n".join(events)

    else:
        # Batch mode: collect final result + metadata
        record.status = "running"
        final_text: list[str] = []
        meta: dict[str, Any] = {}

        try:
            async for event in agent_loop(params):
                if event.type == "token":
                    final_text.append(event.data.get("text", ""))
                elif event.type == "done":
                    meta = {
                        "agent_id": agent_id,
                        "agent_type": agent_type,
                        "model": model,
                        "turns": event.data.get("turns", 0),
                        "tokens": event.data.get("tokens", 0),
                        "reason": event.data.get("reason", "unknown"),
                        "duration_ms": int((time.monotonic() - record.started_at) * 1000),
                    }
                    record.status = "done"
                    record.turns = meta["turns"]
                    record.tokens = meta["tokens"]
                elif event.type == "error":
                    record.error = event.data.get("message", "Unknown error")

            result_text = "".join(final_text)
            record.result = result_text[:5000]

            # Build response with metadata
            output = {
                "result": result_text,
                "meta": meta,
            }
            return _json.dumps(output, ensure_ascii=False, indent=2)

        except Exception as exc:
            record.status = "error"
            record.error = str(exc)
            return f"Error running agent: {exc}"


# ═══════════════════════════════════════════════════════════
# Tool: aiw_agent_status
# ═══════════════════════════════════════════════════════════

async def handle_aiw_agent_status(arguments: dict) -> str:
    """Get status of all running AI Workspace agents."""
    if not _agents:
        return "No agents running."

    agents_data = []
    for agent_id, record in sorted(_agents.items()):
        agents_data.append({
            "id": record.id,
            "task": record.task[:80],
            "agent_type": record.agent_type,
            "model": record.model,
            "status": record.status,
            "turns": record.turns,
            "tokens": record.tokens,
            "duration_s": round(time.monotonic() - record.started_at, 1),
            "error": record.error[:200] if record.error else None,
        })

    return _json.dumps({"agents": agents_data}, indent=2)


# ═══════════════════════════════════════════════════════════
# Tool: aiw_agent_kill
# ═══════════════════════════════════════════════════════════

async def handle_aiw_agent_kill(arguments: dict) -> str:
    """Kill a running agent by ID."""
    agent_id = arguments.get("agent_id", "")

    if not agent_id:
        return "Error: agent_id is required"

    record = _agents.get(agent_id)
    if record is None:
        return f"Agent '{agent_id}' not found"

    if record.task_ref and not record.task_ref.done():
        record.task_ref.cancel()
        record.status = "killed"
        return f"Agent '{agent_id}' killed"
    else:
        return f"Agent '{agent_id}' is not running (status: {record.status})"
