"""
AgentWorker — background agent execution for the TUI.

Runs crewAI agents in a separate thread, streaming output
line-by-line to the TUI via an asyncio.Queue.

Usage:
    worker = AgentWorker(lane_id="coding-1", agent_type="coding")
    await worker.run_agent("Fix the auth middleware bug")
    
    # In TUI loop:
    while not worker.queue.empty():
        line = await worker.queue.get()
        lane.append_output(line)
"""

from __future__ import annotations

import asyncio
import io
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

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
            # Run in the event loop's thread — but queue.put is thread-safe
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


class AgentWorker:
    """Background worker that runs an agent and streams output to a queue."""

    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=1000)
        self.status = AgentStatus.IDLE
        self._task: asyncio.Task | None = None
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused initially
        self._kill_event = threading.Event()
        self._result: str | None = None
        self._error: str | None = None

    async def run_agent(self, task_description: str) -> None:
        """Start the agent in a background thread.

        Args:
            task_description: The task to give the agent.
        """
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
            else:
                self.status = AgentStatus.COMPLETED
                await self.queue.put("✅ Agent completed successfully.")

        except Exception as e:
            self.status = AgentStatus.ERROR
            self._error = str(e)
            logger.exception("AgentWorker %s failed", self.config.lane_id)
            await self.queue.put(f"🔴 Error: {e}")

    def _run_crew_sync(self, task_description: str) -> str:
        """Synchronous agent execution with stdout capture.

        This runs in a separate thread. stdout is redirected to QueueStream
        so every print goes to the TUI in real-time.
        """
        import os
        import sys

        stream = QueueStream(self.queue)
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = stream
        sys.stderr = stream

        try:
            # ── Set working directory ──────────────────────
            if self.config.cwd and os.path.isdir(self.config.cwd):
                os.chdir(self.config.cwd)
                self.queue.put_nowait(f"📁 Working dir: {self.config.cwd}")

            # ── Session context injection ──────────────────
            session = None
            if self.config.session_id:
                try:
                    from ai_workspace.agents.session import PersistentAgentSession
                    session = PersistentAgentSession(session_id=self.config.session_id)
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
                    self.queue.put_nowait(f"⚠ Session load failed: {e}")

            # ── Project / worktree setup ───────────────────
            if self.config.project:
                from ai_workspace.core.projects import ProjectManager
                pm = ProjectManager()
                pm.initialize()
                projects = pm.list_projects()
                worktree_path = None
                for p in projects:
                    if p.name == self.config.project:
                        worktree_path = str(p.repos[0].path) if p.repos else None
                        break
                if worktree_path and os.path.isdir(worktree_path):
                    os.chdir(worktree_path)
                    self.queue.put_nowait(f"📁 Working in: {worktree_path}")

            # Build and run the appropriate agent
            if self.config.agent_type == "coding":
                result = self._run_coding_agent(task_description)
            elif self.config.agent_type == "research":
                result = self._run_research_agent(task_description)
            else:
                result = self._run_general_agent(task_description)

            # ── Save response to session ───────────────────
            if session and result:
                try:
                    session.store.add_message(
                        session_id=session.session_id,
                        role="assistant",
                        content=str(result)[:50_000],
                    )
                    self.queue.put_nowait("💾 Response saved to session")
                except Exception as e:
                    self.queue.put_nowait(f"⚠ Session save failed: {e}")
                finally:
                    try:
                        session.close()
                    except Exception:
                        pass

            return result

        finally:
            stream.flush()
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def _run_coding_agent(self, task: str) -> str:
        """Run the coding crew."""
        from ai_workspace.agents.swarm import SwarmConfig, coding_crew

        cfg = SwarmConfig(
            coder_model=f"{self.config.provider}/{self.config.model}",
            default_model=f"{self.config.provider}/{self.config.model}",
        )
        crew = coding_crew(task=task, cfg=cfg)
        return crew.kickoff()

    def _run_research_agent(self, query: str) -> str:
        """Run the research engine."""
        from ai_workspace.search.deep_search import DeepSearchEngine
        import asyncio

        engine = DeepSearchEngine(max_depth=2)
        # run_sync because we're in a thread
        try:
            result = asyncio.run(engine.research(query))
            return result.summary or "Research completed."
        except Exception:
            # Fallback: simpler agent
            from ai_workspace.agents.swarm import create_agent
            agent = create_agent(model=self.config.model)
            from crewai import Task, Crew
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
        t = Task(
            description=task,
            expected_output="The result of the requested task.",
            agent=agent,
        )
        crew = Crew(agents=[agent], tasks=[t], verbose=False)
        return crew.kickoff()

    async def send_message(self, message: str) -> None:
        """Send a user message to the running agent.

        The message is appended to the output and also logged so the
        agent can see it on next iteration (if supported by the agent).
        """
        await self.queue.put(f"> [bold]You:[/] {message}")
        # For now, we just log the message. Future: inject into agent context.
        logger.info("User message to %s: %s", self.config.lane_id, message)

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
        """Kill the running agent."""
        self._kill_event.set()
        self._pause_event.set()  # Unblock if paused
        if self._task:
            self._task.cancel()
        self.status = AgentStatus.KILLED
        logger.info("AgentWorker %s killed", self.config.lane_id)

    @property
    def is_alive(self) -> bool:
        """Check if the agent is still running."""
        return self.status in (AgentStatus.RUNNING, AgentStatus.PAUSED)
