"""
AgentWorker — background agent execution for the TUI.

Runs crewAI agents in a separate thread, streaming output
line-by-line to the TUI via an asyncio.Queue.

Supports two modes:
  1. One-shot: worker.run_agent(task) → runs once → completes
  2. Loop mode: worker.start_loop(task) → continuous agent that
     accepts additional messages via worker.send_message(msg).
     The agent checks the message queue after each kickoff cycle
     and injects new instructions into accumulated context.
     Priority 10+ messages interrupt and reset context.

Usage (one-shot):
    worker = AgentWorker(lane_id="coding-1", agent_type="coding")
    await worker.run_agent("Fix the auth middleware bug")

Usage (loop mode):
    worker = AgentWorker(lane_id="coding-1", agent_type="coding")
    await worker.start_loop("Fix the auth middleware bug")
    # ... user types more messages ...
    await worker.send_message("Also add tests for edge cases")
    await worker.send_message("! forget all that, just fix the one bug", priority=10)
"""

from __future__ import annotations

import asyncio
import io
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from crewai.tools import BaseTool

from ai_workspace.agents.message_queue import (
    MessageQueue,
    MessagePriority,
    PendingMessage,
)

logger = logging.getLogger("aiw.tui.worker")


class AgentStatus(Enum):
    IDLE = auto()
    RUNNING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    ERROR = auto()
    KILLED = auto()


class QueueStream(io.TextIOBase):
    """A write-only text stream that pushes each line to an asyncio.Queue."""

    def __init__(self, queue: asyncio.Queue[str]) -> None:
        self._queue = queue
        self._buffer = ""

    def write(self, text: str) -> int:
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            try:
                self._queue.put_nowait(line)
            except asyncio.QueueFull:
                pass
        return len(text)

    def flush(self) -> None:
        if self._buffer:
            try:
                self._queue.put_nowait(self._buffer)
            except asyncio.QueueFull:
                pass
            self._buffer = ""


@dataclass
class AgentConfig:
    """Configuration for a TUI agent worker."""
    lane_id: str
    agent_type: str = "coding"  # coding, research, general
    project: str | None = None
    model: str = "qwen3:14b"
    provider: str = "ollama"
    auto_cleanup: bool = False
    session_id: str | None = None  # PersistentAgentSession ID
    cwd: str | None = None  # Working directory override
    permission_gate: bool = True  # Enable permission checks for dangerous ops
    use_router: bool = True  # Use SmartRouter for model selection
    use_context: bool = True  # Inject project context automatically
    loop_mode: bool = False  # If True, agent stays alive accepting new messages
    max_context_chars: int = 50_000  # Max accumulated context before resetting
    context_manager: Any = None  # ContextManager for observability (built lazily)


class AgentWorker:
    """Background worker that runs an agent and streams output to a queue.

    In loop_mode, the agent stays alive after completing a task, waiting
    for new messages via the message_queue. Messages are injected into
    the agent's accumulated context and processed iteratively.

    Priority levels for send_message():
      0-4  : Normal — appended to accumulated context
      5-9  : High — processed next, context preserved
      10+  : Interrupt — clears accumulated context, fresh restart
    """

    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=1000)
        self.message_queue = MessageQueue(max_size=50)
        self.status = AgentStatus.IDLE
        self._task: asyncio.Task | None = None
        self._loop_task: asyncio.Task | None = None
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused initially
        self._kill_event = threading.Event()
        self._result: str | None = None
        self._error: str | None = None
        self._accumulated_context: str = ""  # Built up across loop iterations
        self._iteration_count: int = 0
        self._loop_running: bool = False
        self.pending_permission = None  # PermissionRequest | None (for TUI polling)

    # ─── Agent Lifecycle ────────────────────────────────

    async def run_agent(self, task_description: str) -> None:
        """Start the agent in one-shot mode (runs once, then completes).

        Args:
            task_description: The task to give the agent.
        """
        self.config.loop_mode = False
        self._loop_running = False
        await self._start_execution(task_description)

    async def start_loop(self, task_description: str) -> None:
        """Start the agent in loop mode (stays alive accepting new messages).

        The agent processes the initial task, then waits for more messages
        via send_message(). Each new message is injected into accumulated
        context and the agent continues processing.

        Use send_message(priority=10) to interrupt and reset context.
        """
        self.config.loop_mode = True
        self._loop_running = True
        self._accumulated_context = ""
        self._iteration_count = 0

        # Start the persistent loop
        self._loop_task = asyncio.create_task(self._agent_loop())

        # Enqueue the initial task
        await self.send_message(task_description)

    async def _start_execution(self, task_description: str) -> None:
        """Internal: start agent execution (shared by run_agent and loop)."""
        if self.status == AgentStatus.RUNNING:
            logger.warning("AgentWorker %s already running", self.config.lane_id)
            return

        self.status = AgentStatus.RUNNING
        self._kill_event.clear()
        self._pause_event.set()
        self._result = None
        self._error = None

        self._task = asyncio.create_task(
            self._execute_in_thread(task_description)
        )

    async def _execute_in_thread(self, task_description: str) -> None:
        """Run the agent in a thread pool with stdout capture."""
        loop = asyncio.get_running_loop()

        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = loop.run_in_executor(
                    executor,
                    self._run_crew_sync,
                    task_description,
                )
                self._result = await future

            if self._kill_event.is_set():
                self.status = AgentStatus.KILLED
                await self.queue.put("🔴 Agent killed by user.")
            elif not self.config.loop_mode:
                self.status = AgentStatus.COMPLETED
                await self.queue.put("✅ Agent completed successfully.")

        except asyncio.CancelledError:
            self.status = AgentStatus.KILLED
            raise
        except Exception as e:
            self.status = AgentStatus.ERROR
            self._error = str(e)
            logger.exception("AgentWorker %s failed", self.config.lane_id)
            await self.queue.put(f"🔴 Error: {e}")

    # ─── Agent Loop (multi-message mode) ────────────────

    async def _agent_loop(self) -> None:
        """Main agent loop for multi-message sessions.

        Flow:
          1. Wait for a message from the queue
          2. Build task with accumulated context
          3. Execute agent (crewAI kickoff in thread)
          4. Accumulate result into context
          5. Check for more queued messages → continue or go idle
          6. If idle, wait for next message (keep-alive timeout)
        """
        logger.info("AgentWorker %s entering loop mode", self.config.lane_id)

        while self._loop_running and not self._kill_event.is_set():
            # Pause check
            if self.status == AgentStatus.PAUSED:
                self._pause_event.wait()

            # Wait for a message (with timeout for keep-alive check)
            msg = await self.message_queue.wait_for_message(timeout=2.0)

            if msg is None:
                # Timeout — no new messages
                if self._accumulated_context:
                    # We have context but no new messages → go idle
                    if self.status != AgentStatus.IDLE:
                        self.status = AgentStatus.IDLE
                        await self.queue.put(
                            "🤖 [dim]Agent idle — waiting for next instruction...[/]"
                        )
                continue

            # Check for interrupt flag set by previous enqueue
            if self.message_queue.is_interrupted:
                self.message_queue.clear_interrupt()
                self._accumulated_context = ""
                self._iteration_count = 0
                await self.queue.put(
                    "⚡ [bold yellow]Context reset — starting fresh[/]"
                )

            # Drain any additional queued messages (batch processing)
            extra_msgs = await self.message_queue.dequeue_all()
            all_msgs = [msg] + extra_msgs

            # Check for interrupts in the batch
            has_interrupt = any(m.is_interrupt for m in all_msgs)
            if has_interrupt:
                self._accumulated_context = ""
                self._iteration_count = 0
                self.message_queue.clear_interrupt()
                # Take only the last interrupt message's content
                interrupt_msg = next(
                    (m for m in reversed(all_msgs) if m.is_interrupt),
                    all_msgs[-1],
                )
                all_msgs = [interrupt_msg]
                await self.queue.put(
                    "⚡ [bold yellow]Interrupted — starting fresh[/]"
                )

            # Build the combined task
            task = self._build_loop_task(all_msgs)

            if not task.strip():
                continue

            # Execute
            self.status = AgentStatus.RUNNING
            self._iteration_count += 1
            await self.queue.put(
                f"🔄 [dim]Iteration #{self._iteration_count} "
                f"({len(self._accumulated_context)} chars context)[/]"
            )

            try:
                # Run in thread — _execute_in_thread handles completion status
                await self._start_execution(task)

                # Wait for execution to finish
                if self._task and not self._task.done():
                    await self._task

                if self._kill_event.is_set():
                    self.status = AgentStatus.KILLED
                    await self.queue.put("🔴 Agent killed.")
                    break

                result = self._result or ""

                # Accumulate context (trim to prevent overflow)
                self._accumulate_result(task, result)

                await self.queue.put(
                    f"✅ [dim]Iteration #{self._iteration_count} complete[/]"
                )

                # Notify TUI that accumulated context is preserved
                ctx_chars = len(self._accumulated_context)
                if ctx_chars > 1000:
                    await self.queue.put(
                        f"📋 [dim]Context: {ctx_chars} chars across "
                        f"{self._iteration_count} iterations[/]"
                    )

            except asyncio.CancelledError:
                self.status = AgentStatus.KILLED
                break
            except Exception as e:
                logger.exception(
                    "Agent loop iteration %d failed", self._iteration_count
                )
                self._error = str(e)
                await self.queue.put(
                    f"🔴 [bold red]Error in iteration "
                    f"#{self._iteration_count}: {e}[/]"
                )
                # Don't break — agent stays alive for retry
                self.status = AgentStatus.IDLE

        # Loop ended
        if self.status not in (AgentStatus.KILLED, AgentStatus.ERROR):
            self.status = AgentStatus.COMPLETED
        self._loop_running = False
        logger.info(
            "AgentWorker %s loop ended (status=%s)",
            self.config.lane_id,
            self.status.name,
        )

    def _build_loop_task(self, messages: list[PendingMessage]) -> str:
        """Build the task string from queued messages and accumulated context."""
        parts: list[str] = []

        # Accumulated context from previous iterations
        if self._accumulated_context:
            parts.append("=== PREVIOUS WORK ===")
            parts.append(
                self._accumulated_context[: self.config.max_context_chars]
            )
            parts.append("=== NEW INSTRUCTIONS ===")

        # New messages
        if len(messages) == 1:
            parts.append(messages[0].content)
        else:
            parts.append("Multiple new instructions received:")
            for i, msg in enumerate(messages, 1):
                priority_note = (
                    " [HIGH PRIORITY]" if msg.is_high_priority else ""
                )
                parts.append(f"{i}.{priority_note} {msg.content}")
            parts.append("\nPlease address all of the above instructions.")

        return "\n\n".join(parts)

    def _accumulate_result(self, task: str, result: str) -> None:
        """Accumulate the result into context for the next iteration."""
        # Extract the key part of the task (last message)
        task_parts = task.split("=== NEW INSTRUCTIONS ===")
        task_summary = task_parts[-1].strip()[:300]
        result_summary = result[:2000] if result else "(no output)"

        new_context = (
            f"Request: {task_summary}\n"
            f"Result: {result_summary}"
        )

        if self._accumulated_context:
            self._accumulated_context += f"\n\n---\n\n{new_context}"
        else:
            self._accumulated_context = new_context

        # Trim if too large (keep most recent context)
        max_chars = self.config.max_context_chars
        if len(self._accumulated_context) > max_chars:
            self._accumulated_context = (
                "...(earlier context trimmed)...\n\n"
                + self._accumulated_context[-(max_chars - 200):]
            )

    @property
    def pending_message_count(self) -> int:
        """Number of messages waiting in the queue."""
        return self.message_queue.pending_count

    # ─── Messaging ─────────────────────────────────────

    async def send_message(self, message: str, priority: int = 0) -> None:
        """Send a user message to the agent.

        In loop_mode: enqueues the message for the agent to process.
        The agent will pick it up after the current kickoff cycle completes.

        In one-shot mode: logs the message to the output queue but the
        agent won't act on it (one-shot agents don't accept new messages).

        Priority levels:
          0-4  : Normal — appended to context
          5-9  : High — processed next
          10+  : Interrupt — clears accumulated context, fresh restart
        """
        if self.config.loop_mode and self._loop_running:
            msg = PendingMessage(
                role="user",
                content=message,
                priority=priority,
            )
            await self.message_queue.enqueue(msg)

            # Show in output
            if msg.is_interrupt:
                priority_label = "⚡ INTERRUPT"
            elif priority >= 5:
                priority_label = "📨"
            else:
                priority_label = ""

            await self.queue.put(
                f"> [bold]You:[/] {priority_label} {message}"
            )

            if msg.is_interrupt:
                await self.queue.put(
                    "⚠ Interrupt received — clearing context and restarting..."
                )
                self._accumulated_context = ""

            # If agent is IDLE (waiting), wake it up
            if self.status == AgentStatus.IDLE:
                self.status = AgentStatus.RUNNING
        else:
            # One-shot mode: log message but agent won't process it
            await self.queue.put(f"> [bold]You:[/] {message}")
            await self.queue.put(
                "[dim](Agent in one-shot mode — "
                "start a loop session to send follow-ups)[/]"
            )
            logger.info(
                "User message to %s (one-shot, not processed): %s",
                self.config.lane_id,
                message[:100],
            )

    # ─── Control ───────────────────────────────────────

    def pause(self) -> None:
        """Pause the agent (cooperative — agent checks pause_event)."""
        if self.status == AgentStatus.RUNNING:
            self._pause_event.clear()
            self.status = AgentStatus.PAUSED
            logger.info("AgentWorker %s paused", self.config.lane_id)

    def resume(self) -> None:
        """Resume a paused agent."""
        if self.status == AgentStatus.PAUSED:
            self._pause_event.set()
            self.status = AgentStatus.RUNNING
            logger.info("AgentWorker %s resumed", self.config.lane_id)

    def kill(self) -> None:
        """Kill the running agent (works for both one-shot and loop mode)."""
        self._kill_event.set()
        self._loop_running = False
        self._pause_event.set()  # Unblock if paused
        if self._task and not self._task.done():
            self._task.cancel()
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
        self.message_queue.clear()
        self.status = AgentStatus.KILLED
        logger.info("AgentWorker %s killed", self.config.lane_id)

    # ─── Permission Gate ───────────────────────────────

    def _wrap_tools_for_permission(self, tools: list[Any]) -> list[Any]:
        """Wrap dangerous tools with permission checks.

        When a tool like write_file or shell_exec is called, the wrapper
        pauses execution and waits for human approval via the TUI.
        """
        if not self.config.permission_gate:
            return tools

        from ai_workspace.tui.permissions import (
            PermissionGate,
            PermissionVerdict,
        )

        gate = PermissionGate(agent_name=self.config.lane_id)

        wrapped = []
        for tool in tools:
            tool_name = (
                getattr(tool, 'name', None) or tool.__class__.__name__
            )

            dangerous = (
                'write_file', 'edit_file', 'shell_exec', 'safe_shell_exec'
            )
            if tool_name in dangerous:
                wrapped.append(self._make_gated_tool(tool, gate))
            else:
                wrapped.append(tool)

        return wrapped

    def _make_gated_tool(self, original_tool: Any, gate) -> Any:
        """Create a permission-gated wrapper around a tool."""
        tool_name = getattr(original_tool, 'name', 'unknown')
        original_run = original_tool._run
        worker_ref = self  # Capture for closure

        def gated_run(*args: Any, **kwargs: Any) -> str:
            """Wrapper that checks permission before executing."""
            # Reconstruct tool_args from *args/**kwargs
            tool_args: dict[str, Any] = {}
            if args:
                tool_args['arg0'] = str(args[0])[:100]
            tool_args.update(
                {k: str(v)[:200] for k, v in kwargs.items()}
            )

            # Check permission
            from ai_workspace.tui.permissions import (
                PermissionGate,
                PermissionVerdict,
                PermissionRequest,
            )

            request = gate.check_tool(tool_name, tool_args)

            if request is None:
                # Auto-approved
                return original_run(*args, **kwargs)

            # Need human approval — signal TUI
            worker_ref.pending_permission = request
            worker_ref.queue.put_nowait(
                f"🔒 Permission needed: {request.description}"
            )

            # Wait for verdict
            verdict = request.wait(timeout=120.0)
            worker_ref.pending_permission = None

            if verdict == PermissionVerdict.DENY:
                worker_ref.queue.put_nowait(
                    f"🚫 Permission denied: {request.description}"
                )
                return f"Permission denied for {tool_name}"

            if verdict == PermissionVerdict.ALLOW_ALWAYS:
                gate._always_allowed.add(tool_name)
                worker_ref.queue.put_nowait(
                    f"✅ Always allow: {tool_name}"
                )
            else:
                worker_ref.queue.put_nowait(
                    f"✅ Approved: {request.description}"
                )

            return original_run(*args, **kwargs)

        # Create a new tool instance with the gated run method
        original_tool._run = gated_run
        return original_tool

    @property
    def is_alive(self) -> bool:
        """Check if the agent is still running (includes IDLE in loop mode)."""
        if self.config.loop_mode and self._loop_running:
            return self.status in (
                AgentStatus.RUNNING,
                AgentStatus.PAUSED,
                AgentStatus.IDLE,
            )
        return self.status in (AgentStatus.RUNNING, AgentStatus.PAUSED)

    # ─── Agent Execution (sync, runs in thread) ────────

    def _run_crew_sync(self, task_description: str) -> str:
        """Synchronous agent execution with stdout capture and fallback."""
        import os
        import sys

        stream = QueueStream(self.queue)
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = stream
        sys.stderr = stream

        try:
            self._enable_streaming()
            result = self._execute_with_fallback(task_description)
            return result
        finally:
            self._disable_streaming()
            stream.flush()
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def _enable_streaming(self) -> None:
        """Enable token-level streaming for LLM calls."""
        try:
            from ai_workspace.tui.streaming import enable_streaming
            enable_streaming(self.queue)
        except Exception:
            pass

    def _disable_streaming(self) -> None:
        """Disable token-level streaming."""
        try:
            from ai_workspace.tui.streaming import disable_streaming
            disable_streaming()
        except Exception:
            pass
    def _execute_with_fallback(self, task_description: str) -> str:
        """Execute agent with automatic model fallback on failure."""
        import os
        import sys

        max_attempts = 3
        last_error: Exception | None = None

        for attempt in range(max_attempts):
            try:
                # ── Set working directory ──────────────────
                if self.config.cwd and os.path.isdir(self.config.cwd):
                    os.chdir(self.config.cwd)
                    self.queue.put_nowait(
                        f"📁 Working dir: {self.config.cwd}"
                    )

                # ── ContextBundle: project context injection ───
                if self.config.use_context:
                    try:
                        from ai_workspace.agents.context import ContextBundle

                        bundle = ContextBundle(cwd=self.config.cwd or ".")
                        ctx = asyncio.run(
                            bundle.build(session_id=self.config.session_id)
                        )
                        if ctx and len(ctx) > 50:
                            task_description = (
                                f"{ctx}\n\n---\n\n{task_description}"
                            )
                            self.queue.put_nowait(
                                "📋 Project context injected"
                            )
                        # Register in ContextManager
                        if self.config.context_manager:
                            from ai_workspace.agents.context_manager import BlockType
                            self.config.context_manager.add_block_sync(
                                BlockType.PROJECT_CONTEXT,
                                ctx,
                                summary=f"Project: {bundle.cwd.name}",
                                importance=0.8,
                            )
                    except Exception as e:
                        self.queue.put_nowait(
                            f"⚠ Context injection failed: {e}"
                        )

                # ── .rules injection ─────────────────────
                try:
                    from ai_workspace.rules.loader import rules_to_prompt
                    rules_prompt = rules_to_prompt(self.config.cwd)
                    if rules_prompt:
                        task_description = (
                            f"{rules_prompt}\n\n---\n\n{task_description}"
                        )
                        self.queue.put_nowait("📋 Project rules loaded from .rules")
                except Exception:
                    pass

                # ── SmartRouter: model selection ──────────
                if self.config.use_router:
                    try:
                        from ai_workspace.agents.router import get_router

                        router = get_router()
                        
                        # Probe providers (non-blocking check)
                        avail = router.check_availability_sync()
                        logger.info(
                            "Router availability: ollama=%s deepseek=%s gemini=%s or=%s",
                            avail.get("ollama"), avail.get("deepseek"),
                            avail.get("gemini"), avail.get("openrouter"),
                        )
                        
                        decision = router.route(
                            task_description,
                            task_type=self.config.agent_type,
                        )
                        if decision.model != self.config.model:
                            old_model = self.config.model
                            self.config.model = decision.model
                            self.config.provider = decision.provider
                            self.queue.put_nowait(
                                f"🧭 Router: {old_model} → {decision.model} "
                                f"({decision.reason})"
                            )
                    except Exception as e:
                        self.queue.put_nowait(
                            f"⚠ Router failed, using default: {e}"
                        )

                # ── Session context injection ──────────────
                session = None
                if self.config.session_id:
                    try:
                        from ai_workspace.agents.session import (
                            PersistentAgentSession,
                        )

                        session = PersistentAgentSession(
                            session_id=self.config.session_id
                        )
                        context = session._build_context()
                        if context:
                            stats = session.get_stats()
                            self.queue.put_nowait(
                                f"📋 Session: {stats['entries']} entries, "
                                f"{stats['compactions']} compactions"
                            )
                            task_description = (
                                "=== PREVIOUS CONVERSATION ===\n"
                                f"{context[:30_000]}\n"
                                "=== CURRENT REQUEST ===\n"
                                f"{task_description}"
                            )
                    except Exception as e:
                        self.queue.put_nowait(
                            f"⚠ Session load failed: {e}"
                        )

                # ── Project / worktree setup ───────────────
                if self.config.project:
                    from ai_workspace.core.projects import ProjectManager

                    pm = ProjectManager()
                    pm.initialize()
                    projects = pm.list_projects()
                    worktree_path = None
                    for p in projects:
                        if p.name == self.config.project:
                            worktree_path = (
                                str(p.repos[0].path) if p.repos else None
                            )
                            break
                    if worktree_path and os.path.isdir(worktree_path):
                        os.chdir(worktree_path)
                        self.queue.put_nowait(
                            f"📁 Working in: {worktree_path}"
                        )

                # Register task in ContextManager
                if self.config.context_manager:
                    from ai_workspace.agents.context_manager import BlockType
                    self.config.context_manager.add_block_sync(
                        BlockType.USER_MESSAGE,
                        task_description[:3000],
                        summary=task_description[:80].replace("\n", " "),
                        importance=0.9,
                    )

                # ── Budget check ─────────────────────────
                provider = self.config.provider
                est_cost = 0.0  # will be computed below for paid providers
                if provider in ("deepseek", "openrouter"):
                    from ai_workspace.core.cost import (
                        BudgetEnforcer, BudgetExceededError,
                    )
                    budget = BudgetEnforcer()
                    est_tokens = len(task_description) // 4 + 2000
                    est_cost = est_tokens * 0.00014 / 1000
                    allowed, reason = budget.can_call(est_cost, provider)
                    if not allowed:
                        self.queue.put_nowait(
                            f"💰 Budget blocked: {reason}"
                        )
                        raise BudgetExceededError(
                            f"Budget blocked ({provider}): {reason}"
                        )

                # Build and run the appropriate agent
                if self.config.agent_type == "coding":
                    result = self._run_coding_agent(task_description)
                elif self.config.agent_type == "research":
                    result = self._run_research_agent(task_description)
                else:
                    result = self._run_general_agent(task_description)

                # Register result in ContextManager
                if self.config.context_manager and result:
                    from ai_workspace.agents.context_manager import BlockType
                    self.config.context_manager.add_block_sync(
                        BlockType.ASSISTANT_RESPONSE,
                        str(result)[:4000],
                        summary=(str(result)[:80].replace("\n", " ") if result else "(empty)"),
                        importance=0.6,
                    )

                # ── Save response to session ───────────────
                if session and result:
                    try:
                        session.store.add_message(
                            session_id=session.session_id,
                            role="assistant",
                            content=str(result)[:50_000],
                        )
                        self.queue.put_nowait(
                            "💾 Response saved to session"
                        )
                    except Exception as e:
                        self.queue.put_nowait(
                            f"⚠ Session save failed: {e}"
                        )
                    finally:
                        try:
                            session.close()
                        except Exception:
                            pass

                # Success — mark model as working
                if self.config.use_router:
                    try:
                        from ai_workspace.agents.router import get_router
                        get_router().mark_success(self.config.model, self.config.provider)
                    except Exception:
                        pass

                # ── Record cost on success ───────────────
                try:
                    from ai_workspace.core.cost import BudgetEnforcer
                    budget = BudgetEnforcer()
                    budget.record_success(
                        provider=self.config.provider,
                        model=self.config.model,
                        task_type=self.config.agent_type,
                        input_tokens=len(task_description) // 4,
                        output_tokens=len(str(result)) // 4 if result else 0,
                        cost=est_cost,
                    )
                except Exception:
                    pass

                return result

            except Exception as e:
                last_error = e
                self.queue.put_nowait(
                    f"⚠ Attempt {attempt + 1}/{max_attempts} failed: {e}"
                )

                # ── Record failure ──────────────────────
                try:
                    from ai_workspace.core.cost import BudgetEnforcer
                    budget = BudgetEnforcer()
                    budget.record_failure(
                        provider=self.config.provider,
                        model=self.config.model,
                        task_type=self.config.agent_type,
                        error=str(e)[:200],
                    )
                except Exception:
                    pass

                # Try fallback model
                if self.config.use_router and attempt < max_attempts - 1:
                    try:
                        from ai_workspace.agents.router import get_router
                        router = get_router()
                        decision = router.route(
                            task_description,
                            task_type=self.config.agent_type,
                        )
                        fallback = router.fallback(decision)
                        if fallback:
                            self.config.model = fallback.model
                            self.config.provider = fallback.provider
                            self.queue.put_nowait(
                                f"🔄 Fallback → {fallback.model} "
                                f"({fallback.reason})"
                            )
                            continue
                    except Exception as fb_err:
                        self.queue.put_nowait(
                            f"⚠ Fallback routing failed: {fb_err}"
                        )

                # No more fallbacks — will break at loop end

        # All attempts exhausted
        error_msg = f"All {max_attempts} attempts failed. Last error: {last_error}"
        self.queue.put_nowait(f"🔴 {error_msg}")
        raise RuntimeError(error_msg) from last_error


    def _run_coding_agent(self, task: str) -> str:
        """Run the coding crew with step streaming."""
        from ai_workspace.agents.swarm import SwarmConfig, coding_crew

        cfg = SwarmConfig(
            coder_model=f"{self.config.provider}/{self.config.model}",
            default_model=f"{self.config.provider}/{self.config.model}",
        )
        crew = coding_crew(task_description=task, cfg=cfg)

        # Apply permission gate
        if self.config.permission_gate:
            for agent in crew.agents:
                if hasattr(agent, 'tools') and agent.tools:
                    agent.tools = self._wrap_tools_for_permission(
                        list(agent.tools)
                    )

        # Add step callback for streaming
        def on_step(step_output: Any) -> None:
            """Stream agent steps to the queue."""
            output_str = str(step_output) if step_output else ""
            if output_str:
                for line in output_str.split('\n'):
                    if line.strip():
                        self.queue.put_nowait(
                            f"  💭 {line.strip()[:200]}"
                        )

        # Attach callback to each agent
        for agent in crew.agents:
            if hasattr(agent, 'step_callback'):
                agent.step_callback = on_step

        return crew.kickoff()

    def _run_research_agent(self, query: str) -> str:
        """Run the research engine with semantic cache + budget enforcement."""
        from ai_workspace.search.deep_search import DeepSearchEngine
        from ai_workspace.core.cost import CostService

        cost = CostService()
        cost.initialize()

        engine = DeepSearchEngine(
            max_depth=2,
            provider=self.config.provider,
            cost_service=cost,
        )
        try:
            result = asyncio.run(engine.research(query))
            return result.summary or "Research completed."
        except Exception:
            from ai_workspace.agents.swarm import create_agent
            from crewai import Task, Crew

            agent = create_agent(model=self.config.model)
            t = Task(
                description=query,
                expected_output="A comprehensive research report.",
                agent=agent,
            )
            crew = Crew(agents=[agent], tasks=[t], verbose=False)
            return crew.kickoff()

    def _run_general_agent(self, task: str) -> str:
        """Run the general unified agent."""
        from ai_workspace.agents.swarm import create_agent
        from crewai import Task, Crew

        agent = create_agent(model=self.config.model)

        # Apply permission gate to agent's tools
        if (
            self.config.permission_gate
            and hasattr(agent, 'tools')
            and agent.tools
        ):
            agent.tools = self._wrap_tools_for_permission(
                list(agent.tools)
            )

        t = Task(
            description=task,
            expected_output="The result of the requested task.",
            agent=agent,
        )
        crew = Crew(agents=[agent], tasks=[t], verbose=False)
        return crew.kickoff()
