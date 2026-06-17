"""
AgentOrchestrator — unified agent execution across all interfaces.

The problem: CLI, TUI, Dashboard, and MCP Server each have their own
duplicated logic for spawning agents, streaming output, handling permissions,
injecting context, routing models, and managing fallback.

The solution: A single AgentOrchestrator that receives a StreamSink
and works identically whether the sink is a terminal, a TUI widget,
a WebSocket, or an MCP response stream.

Architecture:
  ┌──────────────────────────────────────────────────────────┐
  │                   AgentOrchestrator                       │
  │                                                          │
  │  run(task, agent_type) → full pipeline:                  │
  │    1. ContextBundle.build()                              │
  │    2. SmartRouter.route()                                │
  │    3. ContextManager.add_block()                         │
  │    4. SessionStore.load()                                │
  │    5. AgentWorker.execute()   ← with fallback            │
  │    6. StreamSink.emit_*()     ← token, tool, status      │
  │    7. PermissionGate         ← sink.request_permission() │
  │    8. ContextManager.trim()                              │
  │    9. SessionStore.save()                                │
  │                                                          │
  │  start_loop(task) → continuous agent with message queue  │
  │  send_message(msg, prio) → enqueue for loop agent        │
  └──────────────────────────────────────────────────────────┘
           │
           ├──▶ CLIStreamSink      (Rich terminal)
           ├──▶ TUIStreamSink      (asyncio.Queue → AgentLane)
           ├──▶ DashboardStreamSink(WebSocket → Streamlit)
           └──▶ MCPStreamSink      (JSON-RPC responses)

Usage (TUI):
    sink = TUIStreamSink(queue=asyncio.Queue())
    orch = AgentOrchestrator(sink=sink, session_id="abc123")
    await orch.start_loop("Fix the auth middleware bug")
    await orch.send_message("Also add tests")

Usage (CLI):
    sink = CLIStreamSink()
    orch = AgentOrchestrator(sink=sink)
    result = await orch.run("Research Rust vs Go performance", agent_type="research")

Usage (MCP):
    sink = MCPStreamSink()
    orch = AgentOrchestrator(sink=sink)
    result = await orch.run(tool_input)
"""

from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from ai_workspace.agents.context_manager import (
    BlockType,
    ContextBlock,
    ContextManager,
)
from ai_workspace.agents.message_queue import (
    MessagePriority,
    MessageQueue,
    PendingMessage,
)
from ai_workspace.tui.permissions import (
    PermissionGate,
    PermissionRequest,
    PermissionVerdict,
)

logger = logging.getLogger("aiw.orchestrator")


# ═══════════════════════════════════════════════════════════════
# StreamSink Protocol
# ═══════════════════════════════════════════════════════════════

@runtime_checkable
class StreamSink(Protocol):
    """Protocol for streaming agent output to any interface.
    
    Each interface (CLI, TUI, Dashboard, MCP) implements this protocol
    to receive real-time agent output in its native format.
    """
    
    async def emit_token(self, token: str) -> None:
        """Stream a single token from the LLM response."""
        ...
    
    async def emit_thinking(self, thought: str) -> None:
        """Stream a reasoning/thinking chunk."""
        ...
    
    async def emit_tool_call(self, tool_name: str, args: dict[str, Any]) -> None:
        """Notify that a tool is being called."""
        ...
    
    async def emit_tool_result(self, tool_name: str, result: str) -> None:
        """Stream a tool execution result."""
        ...
    
    async def emit_status(self, status: str, metadata: dict[str, Any] | None = None) -> None:
        """Emit a status update (e.g., 'routing', 'executing', 'completed')."""
        ...
    
    async def emit_error(self, error: str, recoverable: bool = False) -> None:
        """Emit an error notification."""
        ...
    
    async def emit_context_update(
        self,
        blocks: list[ContextBlock],
        budget_pct: float,
    ) -> None:
        """Notify that the context window state has changed."""
        ...
    
    async def request_permission(
        self,
        request: PermissionRequest,
    ) -> PermissionVerdict:
        """Request human approval for a dangerous operation.
        
        Returns the verdict synchronously (blocks until user decides).
        """
        ...


# ═══════════════════════════════════════════════════════════════
# Built-in StreamSink Implementations
# ═══════════════════════════════════════════════════════════════

class CLIStreamSink:
    """StreamSink that prints to terminal using Rich."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._tokens_since_newline = 0
    
    async def emit_token(self, token: str) -> None:
        import sys
        sys.stdout.write(token)
        sys.stdout.flush()
        self._tokens_since_newline += len(token)
        if self._tokens_since_newline > 80 and ' ' in token:
            sys.stdout.write('\n')
            self._tokens_since_newline = 0
    
    async def emit_thinking(self, thought: str) -> None:
        if self.verbose:
            from rich.console import Console
            Console(stderr=True).print(f"  [dim]💭 {thought[:200]}[/]")
    
    async def emit_tool_call(self, tool_name: str, args: dict[str, Any]) -> None:
        from rich.console import Console
        Console(stderr=True).print(f"  🔧 [bold]{tool_name}[/]")
    
    async def emit_tool_result(self, tool_name: str, result: str) -> None:
        from rich.console import Console
        Console(stderr=True).print(f"  📋 [{tool_name}]: {result[:200]}")
    
    async def emit_status(self, status: str, metadata: dict[str, Any] | None = None) -> None:
        from rich.console import Console
        emoji_map = {
            "routing": "🧭",
            "executing": "▶",
            "completed": "✅",
            "idle": "⏳",
            "error": "🔴",
            "compacting": "📦",
        }
        emoji = emoji_map.get(status, "•")
        Console(stderr=True).print(f"  {emoji} {status}")
    
    async def emit_error(self, error: str, recoverable: bool = False) -> None:
        from rich.console import Console
        prefix = "⚠" if recoverable else "🔴"
        Console(stderr=True).print(f"  {prefix} {error}")
    
    async def emit_context_update(
        self,
        blocks: list[ContextBlock],
        budget_pct: float,
    ) -> None:
        if self.verbose:
            from rich.console import Console
            Console(stderr=True).print(
                f"  📊 Context: {len(blocks)} blocks, {budget_pct:.0f}% budget"
            )
    
    async def request_permission(
        self,
        request: PermissionRequest,
    ) -> PermissionVerdict:
        """CLI permission: prompt user in terminal."""
        from rich.console import Console
        from rich.panel import Panel
        
        console = Console()
        body = (
            f"[bold]Agent:[/] {request.agent_name}\n"
            f"[bold]Tool:[/]  {request.tool_name}\n"
            f"[italic]\"{request.description}\"[/]\n\n"
            f"[dim]{request.preview[:500]}[/]"
        )
        console.print(Panel(body, title="🔒 Permission Required", border_style="orange1"))
        console.print("[a] Allow  [A] Always  [d] Deny")
        
        try:
            key = input("> ").strip().lower()
            if key == 'a':
                return PermissionVerdict.ALLOW
            elif key == 'd':
                return PermissionVerdict.DENY
            else:
                return PermissionVerdict.ALLOW_ALWAYS
        except (EOFError, KeyboardInterrupt):
            return PermissionVerdict.DENY


class TUIStreamSink:
    """StreamSink that pushes to an asyncio.Queue for TUI AgentLane."""
    
    def __init__(self, queue: asyncio.Queue):
        self.queue = queue
    
    async def _put(self, text: str) -> None:
        try:
            self.queue.put_nowait(text)
        except asyncio.QueueFull:
            pass
    
    async def emit_token(self, token: str) -> None:
        await self._put(f"  💬 {token[:200]}")
    
    async def emit_thinking(self, thought: str) -> None:
        await self._put(f"  💭 {thought[:200]}")
    
    async def emit_tool_call(self, tool_name: str, args: dict[str, Any]) -> None:
        args_str = ", ".join(f"{k}={str(v)[:50]}" for k, v in list(args.items())[:3])
        await self._put(f"  🔧 {tool_name}({args_str})")
    
    async def emit_tool_result(self, tool_name: str, result: str) -> None:
        await self._put(f"  📋 [{tool_name}]: {result[:300]}")
    
    async def emit_status(self, status: str, metadata: dict[str, Any] | None = None) -> None:
        await self._put(f"  • {status}")
    
    async def emit_error(self, error: str, recoverable: bool = False) -> None:
        prefix = "⚠" if recoverable else "🔴"
        await self._put(f"  {prefix} {error}")
    
    async def emit_context_update(
        self,
        blocks: list[ContextBlock],
        budget_pct: float,
    ) -> None:
        pinned = sum(1 for b in blocks if b.pinned)
        excluded = sum(1 for b in blocks if b.excluded)
        await self._put(
            f"📊 Context: {len(blocks)} blocks ({pinned}📌 {excluded}🚫) "
            f"[{budget_pct:.0f}% budget]"
        )
    
    async def request_permission(
        self,
        request: PermissionRequest,
    ) -> PermissionVerdict:
        """TUI permission: handled externally via PermissionModal.
        
        This method blocks until the TUI's PermissionModal resolves the request.
        The TUI poller (_poll_permissions) handles the UI.
        """
        return request.wait(timeout=120.0)


class MCPStreamSink:
    """StreamSink that formats output for MCP JSON-RPC responses."""
    
    def __init__(self):
        self._tokens: list[str] = []
        self._tool_calls: list[dict] = []
        self._errors: list[str] = []
        self._statuses: list[dict] = []
    
    def get_result(self) -> dict[str, Any]:
        """Get the accumulated result as an MCP tool result."""
        return {
            "content": [
                {"type": "text", "text": "".join(self._tokens)},
            ],
            "tool_calls": self._tool_calls,
            "errors": self._errors,
            "statuses": self._statuses,
        }
    
    async def emit_token(self, token: str) -> None:
        self._tokens.append(token)
    
    async def emit_thinking(self, thought: str) -> None:
        pass  # MCP doesn't stream thinking by default
    
    async def emit_tool_call(self, tool_name: str, args: dict[str, Any]) -> None:
        self._tool_calls.append({"tool": tool_name, "args": args})
    
    async def emit_tool_result(self, tool_name: str, result: str) -> None:
        pass
    
    async def emit_status(self, status: str, metadata: dict[str, Any] | None = None) -> None:
        self._statuses.append({"status": status, "metadata": metadata or {}})
    
    async def emit_error(self, error: str, recoverable: bool = False) -> None:
        self._errors.append(error)
    
    async def emit_context_update(
        self,
        blocks: list[ContextBlock],
        budget_pct: float,
    ) -> None:
        pass
    
    async def request_permission(
        self,
        request: PermissionRequest,
    ) -> PermissionVerdict:
        """MCP permission: auto-approve (MCP tools are pre-authorized)."""
        return PermissionVerdict.ALLOW


# ═══════════════════════════════════════════════════════════════
# Agent Orchestrator
# ═══════════════════════════════════════════════════════════════

@dataclass
class OrchestratorConfig:
    """Configuration for the AgentOrchestrator."""
    cwd: str = "."
    model: str = "qwen3:14b"
    provider: str = "ollama"
    agent_type: str = "general"  # coding, research, general
    session_id: str | None = None
    project: str | None = None
    
    # Feature flags
    use_context: bool = True       # Inject project context
    use_router: bool = True        # SmartRouter model selection
    use_permission_gate: bool = True  # Human approval for dangerous ops
    use_streaming: bool = True     # Token-level streaming
    use_fallback: bool = True      # Auto-retry with fallback models
    
    # Budget
    context_window_tokens: int = 128_000
    max_context_chars: int = 50_000
    max_fallback_attempts: int = 3


class OrchestratorStatus(Enum):
    IDLE = auto()
    RUNNING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    ERROR = auto()
    KILLED = auto()


class AgentOrchestrator:
    """Unified agent execution pipeline for all interfaces.
    
    This replaces the duplicated logic in:
    - tui/worker.py (AgentWorker._run_crew_sync, _execute_with_fallback)
    - agents/session.py (PersistentAgentSession.send)
    - cli.py (agent/code/ask commands)
    - mcp_server/server.py (tool execution)
    
    Usage:
        orch = AgentOrchestrator(
            sink=TUIStreamSink(queue),
            config=OrchestratorConfig(agent_type="coding"),
        )
        await orch.start_loop("Fix the auth middleware bug")
        await orch.send_message("Also add tests")
    """
    
    def __init__(
        self,
        sink: StreamSink,
        config: OrchestratorConfig | None = None,
    ):
        self.sink = sink
        self.config = config or OrchestratorConfig()
        self.status = OrchestratorStatus.IDLE
        
        # Core components
        self.context_manager = ContextManager(
            context_window_tokens=self.config.context_window_tokens,
            max_context_chars=self.config.max_context_chars,
            session_id=self.config.session_id,
        )
        self.message_queue = MessageQueue(max_size=50)
        self.permission_gate = PermissionGate(
            agent_name=f"agent-{self.config.agent_type}"
        )
        
        # State
        self._loop_task: asyncio.Task | None = None
        self._loop_running = False
        self._accumulated_context: str = ""
        self._iteration_count = 0
        self._last_result: str | None = None
        self._last_error: str | None = None
    
    # ─── Execution Pipeline ─────────────────────────────
    
    async def run(
        self,
        task: str,
        agent_type: str | None = None,
    ) -> str:
        """Execute a single agent task with full pipeline.
        
        Pipeline:
          1. ContextBundle: inject project context
          2. SmartRouter: select best model
          3. SessionStore: load conversation history
          4. Execute agent (with streaming, permissions, fallback)
          5. Save response to session
          6. Return result
        """
        if agent_type:
            self.config.agent_type = agent_type
        
        self.status = OrchestratorStatus.RUNNING
        self._last_error = None
        
        await self.sink.emit_status("starting", {"task": task[:100]})
        
        try:
            # 1. Project context injection
            task_with_context = await self._inject_project_context(task)
            
            # 2. Model routing
            if self.config.use_router:
                await self._route_model(task_with_context)
            
            # 3. Session context
            task_with_context = await self._inject_session_context(task_with_context)
            
            # 4. Register in context manager
            self.context_manager.add_block(
                BlockType.USER_MESSAGE,
                task_with_context[:3000],
                summary=task[:80].replace("\n", " "),
                importance=0.9,
            )
            
            # 5. Execute with fallback
            result = await self._execute(task_with_context)
            
            # 6. Register result
            if result:
                self.context_manager.add_block(
                    BlockType.ASSISTANT_RESPONSE,
                    result[:4000],
                    summary=result[:80].replace("\n", " "),
                    importance=0.6,
                )
                self._last_result = result
            
            # 7. Save to session
            await self._save_to_session(task, result)
            
            self.status = OrchestratorStatus.COMPLETED
            await self.sink.emit_status("completed")
            
            return result or ""
            
        except Exception as e:
            self.status = OrchestratorStatus.ERROR
            self._last_error = str(e)
            await self.sink.emit_error(str(e), recoverable=False)
            logger.exception("AgentOrchestrator.run failed")
            raise
    
    async def start_loop(self, task: str) -> None:
        """Start continuous agent loop with message queue.
        
        The agent stays alive, processing messages from the queue.
        Use send_message() to add new instructions.
        """
        self._loop_running = True
        self._accumulated_context = ""
        self._iteration_count = 0
        
        await self.sink.emit_status("loop_starting")
        
        # Enqueue initial task
        await self.send_message(task)
        
        # Start the loop
        self._loop_task = asyncio.create_task(self._agent_loop())
    
    async def send_message(
        self,
        message: str,
        priority: int = MessagePriority.NORMAL,
    ) -> None:
        """Send a message to the running agent.
        
        Priority:
          0-4  : NORMAL — appended to accumulated context
          5-9  : HIGH — processed next
          10+  : INTERRUPT — clears context, fresh start
        """
        msg = PendingMessage(
            role="user",
            content=message,
            priority=priority,
        )
        await self.message_queue.enqueue(msg)
        
        if msg.is_interrupt:
            self._accumulated_context = ""
            self._iteration_count = 0
            await self.sink.emit_status("interrupted")
        
        await self.sink.emit_status("message_queued", {
            "priority": priority,
            "pending": self.message_queue.pending_count,
        })
    
    async def stop_loop(self) -> None:
        """Stop the agent loop."""
        self._loop_running = False
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
        self.status = OrchestratorStatus.KILLED
        await self.sink.emit_status("killed")
    
    # ─── Pipeline Steps ────────────────────────────────
    
    async def _inject_project_context(self, task: str) -> str:
        """Inject project context (git, tree, language) into the task."""
        if not self.config.use_context:
            return task
        
        try:
            from ai_workspace.agents.context import ContextBundle
            
            bundle = ContextBundle(cwd=self.config.cwd)
            ctx = await bundle.build(session_id=self.config.session_id)
            
            if ctx and len(ctx) > 50:
                self.context_manager.add_block(
                    BlockType.PROJECT_CONTEXT,
                    ctx,
                    summary=f"Project: {Path(self.config.cwd).name}",
                    importance=0.8,
                )
                await self.sink.emit_status("context_injected")
                return f"{ctx}\n\n---\n\n{task}"
        except Exception as e:
            await self.sink.emit_error(
                f"Context injection failed: {e}",
                recoverable=True,
            )
        
        return task
    
    async def _route_model(self, task: str) -> None:
        """Select the best model for the task."""
        try:
            from ai_workspace.agents.router import get_router
            
            router = get_router()
            decision = router.route(
                task,
                task_type=self.config.agent_type,
            )
            
            if decision.model != self.config.model:
                old = self.config.model
                self.config.model = decision.model
                self.config.provider = decision.provider
                await self.sink.emit_status("routing", {
                    "from": old,
                    "to": decision.model,
                    "reason": decision.reason,
                })
        except Exception as e:
            await self.sink.emit_error(
                f"Router failed, using default: {e}",
                recoverable=True,
            )
    
    async def _inject_session_context(self, task: str) -> str:
        """Load conversation history from session store."""
        if not self.config.session_id:
            return task
        
        try:
            from ai_workspace.agents.session import PersistentAgentSession
            
            session = PersistentAgentSession(
                session_id=self.config.session_id,
                cwd=self.config.cwd,
            )
            context = session._build_context()
            stats = session.get_stats()
            session.close()
            
            if context:
                self.context_manager.add_block(
                    BlockType.SESSION_CONTEXT,
                    context[:4000],
                    summary=f"Session ({stats['entries']} entries, "
                            f"{stats['compactions']} compactions)",
                    importance=0.7,
                )
                await self.sink.emit_status("session_loaded", stats)
                return (
                    "=== PREVIOUS CONVERSATION ===\n"
                    f"{context[:30_000]}\n"
                    "=== CURRENT REQUEST ===\n"
                    f"{task}"
                )
        except Exception as e:
            await self.sink.emit_error(
                f"Session load failed: {e}",
                recoverable=True,
            )
        
        return task
    
    async def _execute(self, task: str) -> str:
        """Execute the agent with fallback and streaming."""
        max_attempts = self.config.max_fallback_attempts if self.config.use_fallback else 1
        last_error: Exception | None = None
        
        for attempt in range(max_attempts):
            try:
                await self.sink.emit_status("executing", {
                    "attempt": attempt + 1,
                    "model": self.config.model,
                })
                
                # Enable streaming
                if self.config.use_streaming:
                    self._enable_streaming()
                
                # Run agent in thread
                result = await asyncio.to_thread(
                    self._run_agent_sync,
                    task,
                )
                
                # Mark success
                if self.config.use_router:
                    try:
                        from ai_workspace.agents.router import get_router
                        get_router().mark_success(
                            self.config.model,
                            self.config.provider,
                        )
                    except Exception:
                        pass
                
                return result
                
            except Exception as e:
                last_error = e
                await self.sink.emit_error(
                    f"Attempt {attempt + 1}/{max_attempts} failed: {e}",
                    recoverable=True,
                )
                
                # Try fallback
                if self.config.use_fallback and attempt < max_attempts - 1:
                    fallback_model = await self._try_fallback(task)
                    if fallback_model:
                        continue
                
                if attempt >= max_attempts - 1:
                    break
            finally:
                if self.config.use_streaming:
                    self._disable_streaming()
        
        # All attempts exhausted
        error_msg = f"All {max_attempts} attempts failed. Last: {last_error}"
        await self.sink.emit_error(error_msg)
        raise RuntimeError(error_msg) from last_error
    
    async def _try_fallback(self, task: str) -> bool:
        """Try the next model in the fallback chain. Returns True if found."""
        try:
            from ai_workspace.agents.router import get_router
            
            router = get_router()
            decision = router.route(task, task_type=self.config.agent_type)
            fallback = router.fallback(decision)
            
            if fallback:
                self.config.model = fallback.model
                self.config.provider = fallback.provider
                await self.sink.emit_status("fallback", {
                    "model": fallback.model,
                    "reason": fallback.reason,
                })
                return True
        except Exception:
            pass
        
        return False
    
    # ─── Agent Loop ────────────────────────────────────
    
    async def _agent_loop(self) -> None:
        """Continuous agent loop for multi-message sessions."""
        logger.info("AgentOrchestrator entering loop mode")
        
        while self._loop_running:
            # Wait for a message
            msg = await self.message_queue.wait_for_message(timeout=2.0)
            
            if msg is None:
                if self._accumulated_context:
                    self.status = OrchestratorStatus.IDLE
                    await self.sink.emit_status("idle")
                continue
            
            # Handle interrupt
            if self.message_queue.is_interrupted:
                self.message_queue.clear_interrupt()
                self._accumulated_context = ""
                self._iteration_count = 0
            
            # Drain extra messages
            extra = await self.message_queue.dequeue_all()
            all_msgs = [msg] + extra
            
            # Check for interrupt in batch
            for m in all_msgs:
                if m.is_interrupt:
                    self._accumulated_context = ""
                    self._iteration_count = 0
                    await self.sink.emit_status("interrupted")
                    all_msgs = [m]
                    break
            
            # Build task
            task = self._build_loop_task(all_msgs)
            if not task.strip():
                continue
            
            self.status = OrchestratorStatus.RUNNING
            self._iteration_count += 1
            
            try:
                result = await self.run(task)
                self._accumulate_result(task, result)
            except Exception as e:
                logger.exception("Loop iteration %d failed", self._iteration_count)
                self._last_error = str(e)
                await self.sink.emit_error(
                    f"Iteration #{self._iteration_count}: {e}",
                    recoverable=True,
                )
                self.status = OrchestratorStatus.IDLE
        
        self.status = OrchestratorStatus.COMPLETED
        logger.info("AgentOrchestrator loop ended")
    
    def _build_loop_task(self, messages: list[PendingMessage]) -> str:
        """Build task from queued messages and accumulated context."""
        parts: list[str] = []
        
        if self._accumulated_context:
            parts.append("=== PREVIOUS WORK ===")
            parts.append(self._accumulated_context[:self.config.max_context_chars])
            parts.append("=== NEW INSTRUCTIONS ===")
        
        if len(messages) == 1:
            parts.append(messages[0].content)
        else:
            parts.append("Multiple new instructions:")
            for i, msg in enumerate(messages, 1):
                note = " [HIGH]" if msg.is_high_priority else ""
                parts.append(f"{i}.{note} {msg.content}")
            parts.append("\nPlease address all instructions.")
        
        return "\n\n".join(parts)
    
    def _accumulate_result(self, task: str, result: str) -> None:
        """Accumulate result for next iteration."""
        task_parts = task.split("=== NEW INSTRUCTIONS ===")
        task_summary = task_parts[-1].strip()[:300]
        result_summary = result[:2000] if result else "(no output)"
        
        new_context = f"Request: {task_summary}\nResult: {result_summary}"
        
        if self._accumulated_context:
            self._accumulated_context += f"\n\n---\n\n{new_context}"
        else:
            self._accumulated_context = new_context
        
        # Trim
        max_chars = self.config.max_context_chars
        if len(self._accumulated_context) > max_chars:
            self._accumulated_context = (
                "...(earlier context trimmed)...\n\n"
                + self._accumulated_context[-(max_chars - 200):]
            )
    
    # ─── Agent Execution (sync, runs in thread) ────────
    
    def _run_agent_sync(self, task: str) -> str:
        """Run the appropriate agent synchronously (called in thread)."""
        if self.config.agent_type == "coding":
            return self._run_coding_agent(task)
        elif self.config.agent_type == "research":
            return self._run_research_agent(task)
        else:
            return self._run_general_agent(task)
    
    def _run_coding_agent(self, task: str) -> str:
        from ai_workspace.agents.swarm import SwarmConfig, coding_crew, _create_crewai_llm

        provider = self.config.provider
        model = self.config.model

        # Build provider-prefixed model string for SwarmConfig
        if provider and provider != "ollama":
            full_model = f"{provider}/{model}"
        else:
            full_model = model

        cfg = SwarmConfig(
            coder_model=full_model,
            default_model=full_model,
            provider=provider,
        )
        crew = coding_crew(task_description=task, cfg=cfg)
        
        if self.config.use_permission_gate:
            for agent in crew.agents:
                if hasattr(agent, 'tools') and agent.tools:
                    agent.tools = self._wrap_tools(list(agent.tools))
        
        return crew.kickoff()
    
    def _run_research_agent(self, query: str) -> str:
        from ai_workspace.search.deep_search import DeepSearchEngine

        provider = self.config.provider
        model = self.config.model

        # Enable semantic cache + budget for the search
        try:
            from ai_workspace.core.cost import CostService
            cost = CostService()
            cost.initialize()
        except Exception:
            cost = None

        engine = DeepSearchEngine(
            max_depth=2,
            provider=provider,
            model=f"ollama/{model}" if provider == "ollama" else model,
            cost_service=cost,
        )
        try:
            result = asyncio.run(engine.research(query))
            return result.summary or "Research completed."
        except Exception:
            from ai_workspace.agents.swarm import create_agent
            from crewai import Task, Crew

            provider = self.config.provider
            model = self.config.model
            if provider and provider != "ollama":
                full_model = f"{provider}/{model}"
            else:
                full_model = model

            agent = create_agent(model=full_model)
            t = Task(
                description=query,
                expected_output="A comprehensive research report.",
                agent=agent,
            )
            crew = Crew(agents=[agent], tasks=[t], verbose=False)
            return crew.kickoff()
    
    def _run_general_agent(self, task: str) -> str:
        from ai_workspace.agents.swarm import create_agent, _create_crewai_llm
        from crewai import Task, Crew

        provider = self.config.provider
        model = self.config.model

        if provider and provider != "ollama":
            full_model = f"{provider}/{model}"
        else:
            full_model = model

        agent = create_agent(model=full_model)
        
        if (
            self.config.use_permission_gate
            and hasattr(agent, 'tools')
            and agent.tools
        ):
            agent.tools = self._wrap_tools(list(agent.tools))
        
        t = Task(
            description=task,
            expected_output="The result of the requested task.",
            agent=agent,
        )
        crew = Crew(agents=[agent], tasks=[t], verbose=False)
        return crew.kickoff()
    
    def _wrap_tools(self, tools: list[Any]) -> list[Any]:
        """Wrap dangerous tools with permission checks."""
        gate = self.permission_gate
        wrapped = []
        
        for tool in tools:
            tool_name = getattr(tool, 'name', None) or tool.__class__.__name__
            dangerous = {'write_file', 'edit_file', 'shell_exec', 'safe_shell_exec'}
            
            if tool_name in dangerous:
                wrapped.append(self._make_gated_tool(tool, gate))
            else:
                wrapped.append(tool)
        
        return wrapped
    
    def _make_gated_tool(self, original_tool: Any, gate: PermissionGate) -> Any:
        """Create a permission-gated tool wrapper."""
        tool_name = getattr(original_tool, 'name', 'unknown')
        original_run = original_tool._run
        orchestrator = self
        
        def gated_run(*args: Any, **kwargs: Any) -> str:
            tool_args: dict[str, Any] = {}
            if args:
                tool_args['arg0'] = str(args[0])[:100]
            tool_args.update({k: str(v)[:200] for k, v in kwargs.items()})
            
            from ai_workspace.tui.permissions import PermissionGate as PG
            from ai_workspace.tui.permissions import PermissionRequest, PermissionVerdict
            
            request = gate.check_tool(tool_name, tool_args)
            
            if request is None:
                return original_run(*args, **kwargs)
            
            # Request permission via sink (blocks until verdict)
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # In async context — create task to request permission
                    future = asyncio.run_coroutine_threadsafe(
                        orchestrator.sink.request_permission(request),
                        loop,
                    )
                    verdict = future.result(timeout=120.0)
                else:
                    # Sync fallback
                    verdict = request.wait(timeout=120.0)
            except Exception:
                verdict = PermissionVerdict.DENY
            
            if verdict == PermissionVerdict.DENY:
                return f"Permission denied for {tool_name}"
            
            if verdict == PermissionVerdict.ALLOW_ALWAYS:
                gate._always_allowed.add(tool_name)
            
            return original_run(*args, **kwargs)
        
        original_tool._run = gated_run
        return original_tool
    
    # ─── Streaming ─────────────────────────────────────
    
    def _enable_streaming(self) -> None:
        """Enable token-level streaming via monkey-patch."""
        try:
            from ai_workspace.tui.streaming import enable_streaming
            
            # Create a queue that feeds the sink
            queue = asyncio.Queue()
            enable_streaming(queue)
            
            # Background task to drain queue into sink
            async def drain():
                while True:
                    try:
                        token = await asyncio.wait_for(queue.get(), timeout=0.1)
                        await self.sink.emit_token(token)
                    except asyncio.TimeoutError:
                        break
                    except Exception:
                        break
            
            try:
                loop = asyncio.get_event_loop()
                asyncio.run_coroutine_threadsafe(drain(), loop)
            except Exception:
                pass
        except Exception:
            pass
    
    def _disable_streaming(self) -> None:
        """Disable token-level streaming."""
        try:
            from ai_workspace.tui.streaming import disable_streaming
            disable_streaming()
        except Exception:
            pass
    
    # ─── Session ───────────────────────────────────────
    
    async def _save_to_session(self, task: str, result: str) -> None:
        """Save request/response to session store."""
        if not self.config.session_id or not result:
            return
        
        try:
            from ai_workspace.core.sessions import SessionStore
            
            store = SessionStore()
            store.initialize()
            store.add_message(
                session_id=self.config.session_id,
                role="user",
                content=task,
            )
            store.add_message(
                session_id=self.config.session_id,
                role="assistant",
                content=result[:50_000],
            )
            store.close()
            await self.sink.emit_status("session_saved")
        except Exception as e:
            await self.sink.emit_error(
                f"Session save failed: {e}",
                recoverable=True,
            )
    
    # ─── Stats ─────────────────────────────────────────
    
    def get_stats(self) -> dict[str, Any]:
        """Get orchestrator statistics."""
        return {
            "status": self.status.name,
            "agent_type": self.config.agent_type,
            "model": self.config.model,
            "provider": self.config.provider,
            "iterations": self._iteration_count,
            "context_blocks": self.context_manager.stats(),
            "pending_messages": self.message_queue.pending_count,
            "loop_running": self._loop_running,
            "last_error": self._last_error,
            "budget_pct": self.context_manager.budget_used_pct,
        }
