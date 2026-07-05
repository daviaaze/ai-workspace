"""
AI Workspace Web API — FastAPI backend with SSE streaming.

This wraps the existing ai_workspace Python core (deep search, agent
orchestrator, sandboxed tools) as a REST + SSE API suitable for a
mobile-first PWA frontend.

Run:
    python -m api.main
    # or
    uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

# --- Ensure ai-workspace core is importable ---
_api_dir = Path(__file__).parent.resolve()
_workspace_root = _api_dir.parent
sys.path.insert(0, str(_workspace_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aiw.api")

app = FastAPI(title="AI Workspace API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# Lazy imports of core modules
# ──────────────────────────────────────────────

def _get_engine():
    from ai_workspace.search.deep_search import DeepSearchEngine
    return DeepSearchEngine(
        provider=os.environ.get("AIW_PROVIDER", "ollama"),
        model=os.environ.get("AIW_MODEL", "ollama/qwen3:14b"),
    )

def _get_orchestrator():
    from ai_workspace.agents.orchestrator import AgentOrchestrator
    return AgentOrchestrator()

# ──────────────────────────────────────────────
# SSE helpers
# ──────────────────────────────────────────────

def sse_event(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"

# ──────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    provider: str | None = None
    model: str | None = None

class SearchRequest(BaseModel):
    query: str
    depth: int = Field(default=2, ge=1, le=4)
    max_sub_questions: int = Field(default=5, ge=1, le=10)

class AgentRunRequest(BaseModel):
    task: str
    mode: str = Field(default="auto", pattern="^(auto|research|code|browse)$")
    session_id: str | None = None

class AgentPermissionRequest(BaseModel):
    request_id: str
    verdict: str = Field(pattern="^(allow|deny|always)$")

class HealthResponse(BaseModel):
    status: str
    version: str
    providers: dict[str, bool] = {}

# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────

@app.get("/")
async def index():
    """Serve the PWA frontend."""
    index_path = _workspace_root / "web" / "dist" / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    # Fallback: tell the user to build the frontend
    return {
        "message": "AI Workspace API running. Build the frontend with: cd web && npm run build",
        "docs": "/docs",
    }

@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check with provider status."""
    providers = {}
    try:
        from ai_workspace.providers import ProviderRegistry
        registry = ProviderRegistry()
        for name, prov in registry.providers.items():
            providers[name] = prov.is_available() if hasattr(prov, "is_available") else True
    except Exception:
        pass
    return HealthResponse(
        status="ok",
        version="0.1.0",
        providers=providers,
    )

# ── Chat (SSE streaming) ──

@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Chat with the LLM — streams tokens via SSE."""

    async def _stream() -> AsyncGenerator[str, None]:
        yield sse_event("start", {"session_id": req.session_id or str(uuid.uuid4())})
        try:
            from ai_workspace.providers import ProviderRegistry
            registry = ProviderRegistry()
            provider_name = req.provider or os.environ.get("AIW_PROVIDER", "ollama")
            model = req.model or os.environ.get("AIW_MODEL", "qwen3:14b")

            if provider_name == "ollama":
                import httpx
                async with httpx.AsyncClient(timeout=120) as client:
                    async with client.stream(
                        "POST",
                        "http://localhost:11434/api/chat",
                        json={
                            "model": model.replace("ollama/", ""),
                            "messages": [{"role": "user", "content": req.message}],
                            "stream": True,
                        },
                    ) as response:
                        async for line in response.aiter_lines():
                            if line.strip():
                                try:
                                    chunk = json.loads(line)
                                    if "message" in chunk and "content" in chunk["message"]:
                                        content = chunk["message"]["content"]
                                        if content:
                                            yield sse_event("token", {"token": content})
                                    if chunk.get("done"):
                                        yield sse_event(
                                            "done",
                                            {
                                                "total_duration": chunk.get("total_duration", 0),
                                                "eval_count": chunk.get("eval_count", 0),
                                            },
                                        )
                                except json.JSONDecodeError:
                                    pass
            else:
                # DeepSeek / Gemini / OpenRouter via registry
                provider = registry.get(provider_name)
                if not provider:
                    yield sse_event("error", {"error": f"Provider '{provider_name}' not configured"})
                    return
                messages = [{"role": "user", "content": req.message}]
                full_text = ""
                async for chunk in provider.stream_chat(messages, model=model):
                    if chunk:
                        full_text += chunk
                        yield sse_event("token", {"token": chunk})
                yield sse_event("done", {"full_text": full_text})

        except Exception as e:
            logger.exception("Chat error")
            yield sse_event("error", {"error": str(e)})

    return StreamingResponse(_stream(), media_type="text/event-stream")

# ── Deep Research (SSE streaming) ──

@app.post("/api/search")
async def search(req: SearchRequest):
    """Run deep recursive research — streams progress via SSE."""

    async def _stream() -> AsyncGenerator[str, None]:
        engine = _get_engine()
        engine.max_depth = req.depth
        engine.max_sub_questions = req.max_sub_questions

        async def on_progress(progress: dict):
            yield sse_event("progress", progress)

        yield sse_event("start", {"query": req.query})

        try:
            result = await engine.research(
                req.query,
                progress=lambda p: None,  # progress handled via callback below
            )

            # Stream the structured result
            yield sse_event("result", {
                "summary": result.summary,
                "confidence": result.confidence,
                "sources": result.sources,
                "detailed_report": result.detailed_report,
                "sub_questions": [
                    {
                        "question": sq.question,
                        "answer": sq.answer,
                        "confidence": sq.confidence,
                        "sources": sq.sources,
                    }
                    for sq in result.sub_questions
                ],
                "original_query": result.original_query,
            })
            yield sse_event("done", {})

        except Exception as e:
            logger.exception("Search error")
            yield sse_event("error", {"error": str(e)})

    return StreamingResponse(_stream(), media_type="text/event-stream")

# ── Agent Run (SSE streaming) ──

@app.post("/api/agent")
async def run_agent(req: AgentRunRequest):
    """Run an agent task — streams progress via SSE."""

    async def _stream() -> AsyncGenerator[str, None]:
        # SSEStreamSink bridges the orchestrator's StreamSink protocol → SSE events
        class SSEStreamSink:
            async def emit_token(self, token: str) -> None:
                yield sse_event("token", {"token": token})
            async def emit_thinking(self, thought: str) -> None:
                yield sse_event("thinking", {"thought": thought[:500]})
            async def emit_tool_call(self, tool_name: str, args: dict) -> None:
                yield sse_event("tool_call", {"tool": tool_name, "args": args})
            async def emit_tool_result(self, tool_name: str, result: str) -> None:
                yield sse_event("tool_result", {"tool": tool_name, "result": result[:1000]})
            async def emit_status(self, status: str, metadata: dict | None = None) -> None:
                yield sse_event("status", {"status": status, "metadata": metadata or {}})
            async def emit_error(self, error: str, recoverable: bool = False) -> None:
                yield sse_event("error", {"error": error, "recoverable": recoverable})
            async def emit_context_update(self, blocks, budget_pct):
                pass  # too verbose for streaming
            async def request_permission(self, request):
                # Auto-deny for now; web UI will handle this via WebSocket
                from ai_workspace.tui.permissions import PermissionVerdict
                return PermissionVerdict.DENY

        sink = SSEStreamSink()
        yield sse_event("start", {"task": req.task, "mode": req.mode})

        try:
            orchestrator = _get_orchestrator()
            result = await orchestrator.run(
                task=req.task,
                mode=req.mode,
                sink=sink,
                session_id=req.session_id,
            )
            yield sse_event("done", {"result": str(result)[:5000]})
        except Exception as e:
            logger.exception("Agent error")
            yield sse_event("error", {"error": str(e)})

    return StreamingResponse(_stream(), media_type="text/event-stream")

# ── Agent Permissions (WebSocket) ──

@app.websocket("/ws/permissions")
async def permission_websocket(websocket: WebSocket):
    """WebSocket for real-time permission requests/responses."""
    await websocket.accept()
    pending: dict[str, asyncio.Future] = {}
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "request":
                req_id = data["request_id"]
                future = asyncio.get_event_loop().create_future()
                pending[req_id] = future
                # Send to client
                await websocket.send_json({
                    "type": "permission_request",
                    "request_id": req_id,
                    "agent_name": data.get("agent_name", "agent"),
                    "tool_name": data.get("tool_name", ""),
                    "description": data.get("description", ""),
                    "preview": data.get("preview", ""),
                })
                # Wait for user decision
                try:
                    verdict = await asyncio.wait_for(future, timeout=120)
                    await websocket.send_json({
                        "type": "permission_result",
                        "request_id": req_id,
                        "verdict": verdict,
                    })
                except TimeoutError:
                    await websocket.send_json({
                        "type": "permission_result",
                        "request_id": req_id,
                        "verdict": "deny",
                        "reason": "timeout",
                    })

            elif action == "respond":
                req_id = data["request_id"]
                verdict = data["verdict"]  # "allow", "deny", "always"
                if req_id in pending:
                    pending[req_id].set_result(verdict)
                    del pending[req_id]

    except WebSocketDisconnect:
        # Cancel all pending requests
        for future in pending.values():
            if not future.done():
                future.set_result("deny")
        pending.clear()

# ── Static files (served PWA) ──

@app.get("/{path:path}")
async def serve_static(path: str):
    """Serve PWA static files from web/dist."""
    dist_dir = _workspace_root / "web" / "dist"
    file_path = dist_dir / path
    if file_path.exists() and file_path.is_file():
        return FileResponse(str(file_path))
    # SPA fallback
    index_path = dist_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"error": "not found", "path": path}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
