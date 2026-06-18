"""Persistent agent conversation with history, compaction, and model switching."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_workspace.core.sessions import SessionStore, SessionEntry, DEFAULT_COMPACTION_SETTINGS
from ai_workspace.tui.worker import AgentConfig, AgentWorker, AgentStatus
from ai_workspace.agents.message_queue import (
    MessageQueue,
    MessagePriority,
    PendingMessage,
)

logger = logging.getLogger("aiw.agent.session")


class PersistentAgentSession:
    """A persistent, continuous agent conversation with history.
    
    Each user message appends to the session history and the agent
    sees the full context (within the model's context window).
    When the context window nears capacity, older messages are
    auto-compacted into a summary.
    """
    
    def __init__(
        self,
        cwd: str = ".",
        model: str = "qwen3:14b",
        provider: str = "ollama",
        session_id: str | None = None,
        db_url: str | None = None,
        thinking_level: str = "medium",
        auto_compact: bool = True,
        context_window: int = 128_000,
        loop_mode: bool = False,
        context_manager: Any = None,
    ):
        self.cwd = Path(cwd).resolve()
        self.model = model
        self.provider = provider
        self.thinking_level = thinking_level
        self.auto_compact = auto_compact
        self.context_window = context_window
        self.loop_mode = loop_mode
        self.context_manager = context_manager
        
        # Storage
        self.store = SessionStore(db_url)
        self.store.initialize()
        
        # Session
        if session_id:
            existing = self.store.get_session(session_id)
            if existing:
                self.session_id = session_id
                self.model = existing.model or model
            else:
                session = self.store.create_session(cwd=str(self.cwd), model=model)
                self.session_id = session.id
        else:
            session = self.store.create_session(cwd=str(self.cwd), model=model)
            self.session_id = session.id
        
        # Track the last entry id for tree traversal
        self._last_entry_id: str | None = None
        self._worker: AgentWorker | None = None
        
        # Message queue for loop mode
        self.message_queue = MessageQueue(max_size=50)
        self._loop_task: asyncio.Task | None = None
        self._loop_running = False
    

    
    async def start(self) -> None:
        """Initialize the session (load history, prepare context)."""
        entries = self.store.get_entries(self.session_id, limit=10)
        if entries:
            self._last_entry_id = entries[-1].id
            logger.info("Resumed session %s with %d entries", self.session_id, len(entries))
        else:
            logger.info("Started new session %s at %s", self.session_id, self.cwd)
    
    async def send(self, message: str, metadata: dict[str, Any] | None = None) -> str:
        """Send a user message and get the agent's response."""
        # Save user message
        user_entry = self.store.add_message(
            session_id=self.session_id,
            role="user",
            content=message,
            parent_id=self._last_entry_id,
            metadata=metadata,
        )
        self._last_entry_id = user_entry.id
        
        # Register in ContextManager
        if self.context_manager:
            from ai_workspace.agents.context_manager import BlockType
            self.context_manager.add_block_sync(
                BlockType.USER_MESSAGE,
                message,
                summary=message[:80].replace("\n", " "),
                importance=0.9,
            )
        
        # Auto-compact if needed
        if self.auto_compact:
            await self._maybe_compact()
        
        # Build context from history
        context = self._build_context()
        
        # Register session context in manager
        if self.context_manager and context:
            from ai_workspace.agents.context_manager import BlockType
            self.context_manager.add_block_sync(
                BlockType.SESSION_CONTEXT,
                context[:4000],
                summary=f"Session history ({len(context)} chars)",
                importance=0.7,
            )
        
        # Run agent
        response = await self._run_agent_with_context(message, context)
        
        # Save assistant response
        assistant_entry = self.store.add_message(
            session_id=self.session_id,
            role="assistant",
            content=response,
            parent_id=self._last_entry_id,
            tokens=self._estimate_tokens(response),
        )
        self._last_entry_id = assistant_entry.id
        
        # Register response in ContextManager
        if self.context_manager and response:
            from ai_workspace.agents.context_manager import BlockType
            self.context_manager.add_block_sync(
                BlockType.ASSISTANT_RESPONSE,
                str(response)[:4000],
                summary=str(response)[:80].replace("\n", " ") if response else "(response)",
                importance=0.6,
            )
        
        return response
    
    async def send_with_tools(
        self,
        message: str,
        agent_type: str = "general",
        project: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Send a message with full tool access (like pi's tool-using agent).
        
        This spawns a real AgentWorker that can use filesystem, git, shell,
        and web tools. The worker runs in a background thread and streams
        output to a queue.
        """
        # Save user message
        user_entry = self.store.add_message(
            session_id=self.session_id,
            role="user",
            content=message,
            parent_id=self._last_entry_id,
            metadata=metadata,
        )
        self._last_entry_id = user_entry.id
        
        # Auto-compact if needed
        if self.auto_compact:
            await self._maybe_compact()
        
        # Build context and inject into task
        context = self._build_context()
        full_task = self._format_task_with_context(message, context)
        
        # Create and run worker
        config = AgentConfig(
            lane_id=f"session-{self.session_id[:8]}",
            agent_type=agent_type,
            project=project,
            model=self.model,
        )
        config.provider = self.provider
        
        self._worker = AgentWorker(config)
        await self._worker.run_agent(full_task)
        
        # Wait for completion
        while self._worker.is_alive:
            await asyncio.sleep(0.5)
        
        # Collect output
        output_lines = []
        while not self._worker.queue.empty():
            try:
                output_lines.append(self._worker.queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        
        response = "\n".join(output_lines) if output_lines else "No output"
        
        # Save response
        self.store.add_message(
            session_id=self.session_id,
            role="assistant",
            content=response,
            parent_id=self._last_entry_id,
            tokens=self._estimate_tokens(response),
        )
        
        return response
    

    
    def _build_context(self) -> str:
        """Build the conversation context from session history.
        
        Walks the conversation tree from root to the last entry,
        handling compaction entries along the way.
        """
        tree = self.store.get_conversation_tree(
            self.session_id,
            leaf_entry_id=self._last_entry_id,
        )
        
        if not tree:
            return ""
        
        parts = []
        for entry in tree:
            if entry.entry_type == "compaction":
                # Include compaction summary with pi-style markers
                parts.append(
                    "The conversation history before this point was compacted "
                    "into the following summary:\n\n"
                    f"<summary>\n{entry.content}\n</summary>"
                )
            elif entry.entry_type == "branch_summary":
                parts.append(
                    "The following is a summary of a branch:\n\n"
                    f"<summary>\n{entry.content}\n</summary>"
                )
            elif entry.entry_type == "message":
                if entry.role == "user":
                    parts.append(f"[User]: {entry.content}")
                elif entry.role == "assistant":
                    # Truncate long assistant responses for context
                    content = entry.content or ""
                    if len(content) > 4000:
                        content = content[:4000] + "\n... [truncated]"
                    parts.append(f"[Assistant]: {content}")
                elif entry.role == "tool_result":
                    content = entry.content or ""
                    if len(content) > 2000:
                        content = content[:2000] + "\n... [truncated]"
                    tool = (entry.metadata or {}).get("tool_name", "tool")
                    parts.append(f"[Tool Result - {tool}]: {content}")
        
        return "\n\n".join(parts)
    
    def _format_task_with_context(self, message: str, context: str) -> str:
        """Format the full task with session context injected."""
        parts = []
        
        if context:
            parts.append("=== PREVIOUS CONVERSATION ===\n")
            parts.append(context[:30_000])  # Cap at 30K chars
            parts.append("\n=== CURRENT REQUEST ===\n")
        
        parts.append(message)
        
        return "\n".join(parts)
    

    
    async def _maybe_compact(self) -> None:
        """Check if compaction is needed and run it."""
        if not self.store.should_compact(
            self.session_id,
            context_window=self.context_window,
        ):
            return
        
        logger.info("Compacting session %s", self.session_id)
        
        # Get the last compaction entry (if any) for cumulative summary
        entries = self.store.get_entries(self.session_id, limit=1000)
        last_compaction = None
        for e in reversed(entries):
            if e.entry_type == "compaction":
                last_compaction = e
                break
        
        # Find messages to summarize
        messages_to_summarize = []
        first_kept_id = None
        keep_recent_tokens = 0
        
        for entry in reversed(entries):
            if entry.entry_type == "message":
                content_len = len(entry.content or "")
                keep_recent_tokens += self._estimate_tokens(entry.content or "")
                if keep_recent_tokens > DEFAULT_COMPACTION_SETTINGS["keepRecentTokens"]:
                    first_kept_id = entry.id
                    break
                messages_to_summarize.insert(0, entry)
        
        if not messages_to_summarize:
            return
        
        # Actually, summarize entries BEFORE the cut point
        summary_entries = []
        for entry in entries:
            if entry.id == first_kept_id:
                break
            if entry.entry_type == "message":
                summary_entries.append(entry)
        
        if not summary_entries:
            return
        
        # Generate summary
        summary = await self._generate_summary(
            summary_entries,
            last_compaction,
        )
        
        # Save compaction entry
        tokens_before = sum(
            self._estimate_tokens(e.content or "") 
            for e in entries
        )
        self.store.add_compaction(
            session_id=self.session_id,
            summary=summary,
            tokens_before=tokens_before,
            first_kept_entry_id=first_kept_id,
        )
    
    async def _generate_summary(
        self,
        entries: list[SessionEntry],
        previous_summary_entry: SessionEntry | None = None,
    ) -> str:
        """Generate a summary of session entries using a fast model.
        
        Uses pi's summarization prompt pattern.
        """
        # Build serialized conversation
        conversation_lines = []
        for entry in entries:
            if entry.role == "user":
                conversation_lines.append(f"[User]: {entry.content}")
            elif entry.role == "assistant":
                content = entry.content or ""
                if len(content) > 2000:
                    content = content[:2000] + "..."
                conversation_lines.append(f"[Assistant]: {content}")
            elif entry.role == "tool_result":
                content = entry.content or ""
                if len(content) > 1000:
                    content = content[:1000] + "..."
                tool = (entry.metadata or {}).get("tool_name", "tool")
                conversation_lines.append(f"[Tool {tool}]: {content}")
        
        conversation_text = "\n\n".join(conversation_lines)
        
        # Build summarization prompt (pi's pattern)
        prompt = \
            "You are summarizing a coding session conversation. "
        "Create a concise summary that captures:\n"
        "- What the user asked for\n"
        "- What was done (files read, edited, created)\n"
        "- What decisions were made\n"
        "- Any errors encountered and how they were fixed\n"
        "- The current state of the task\n\n"
        
        if previous_summary_entry and previous_summary_entry.content:
            prompt += f"Previous summary:\n{previous_summary_entry.content}\n\n"
        
        prompt += f"Conversation to summarize:\n\n{conversation_text[:20_000]}\n\n"
        prompt += "Summary:"
        
        # Use a fast model for summarization
        try:
            from ai_workspace.agents.swarm import create_agent
            from crewai import Task, Crew
            
            agent = create_agent(model="ministral-3:8b")  # Fast model
            task = Task(
                description=prompt,
                expected_output="A concise summary of the conversation.",
                agent=agent,
            )
            crew = Crew(agents=[agent], tasks=[task], verbose=False)
            result = crew.kickoff()
            return str(result) if result else "Session summary not available."
        except Exception as e:
            logger.warning("Summarization failed: %s", e)
            return f"Session continued. {len(entries)} entries summarized."
    

    
    async def _run_agent_with_context(self, message: str, context: str) -> str:
        """Run the agent with session context injected.
        
        For now, uses the simple ask approach. When TUI is active,
        the AgentWorker handles streaming.
        """
        from ai_workspace.agents.swarm import create_agent
        from crewai import Task, Crew
        
        agent = create_agent(model=self.model)
        
        full_task = message
        if context:
            full_task = (
                "Previous conversation context:\n\n"
                f"{context[:15_000]}\n\n"
                "---\n\n"
                f"Current user request: {message}"
            )
        
        task = Task(
            description=full_task,
            expected_output="A helpful response to the user's request.",
            agent=agent,
        )
        crew = Crew(agents=[agent], tasks=[task], verbose=False)
        result = crew.kickoff()
        return str(result) if result else "No response."
    

    
    def _estimate_tokens(self, text: str) -> int:
        """Quick token estimate: ~4 chars per token."""
        return max(1, len(text or "") // 4)
    
    def switch_model(self, model: str) -> None:
        """Switch the active model mid-session."""
        self.model = model
        self.store.add_model_change(self.session_id, model=model)
        self.store.update_session(self.session_id, model=model)
        logger.info("Session %s: switched model to %s", self.session_id, model)
    
    def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent conversation history."""
        entries = self.store.get_entries(self.session_id, limit=limit)
        return [
            {
                "id": e.id,
                "role": e.role,
                "content": e.content[:500] if e.content else "",
                "type": e.entry_type,
                "created_at": e.created_at,
            }
            for e in entries
            if e.entry_type == "message" and e.role in ("user", "assistant")
        ]
    
    def get_stats(self) -> dict[str, Any]:
        """Get session statistics."""
        session = self.store.get_session(self.session_id)
        if not session:
            return {}
        return {
            "id": session.id,
            "cwd": session.cwd,
            "model": session.model,
            "entries": session.entry_count,
            "tokens": session.total_tokens,
            "compactions": session.compaction_count,
            "created_at": session.created_at,
        }
    
    def export(self, path: Path | None = None) -> Path:
        """Export session to JSONL (pi-compatible)."""
        return self.store.export_jsonl(self.session_id, path)
    
    def close(self) -> None:
        """Close the session and persist final state."""
        self._loop_running = False
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
        if self._worker and self._worker.is_alive:
            self._worker.kill()
        self.store.close()
        logger.info("Session %s closed", self.session_id)



    async def start_loop(self) -> None:
        """Start the session in loop mode for continuous conversation.
        
        In loop mode, the session stays alive and accepts messages via
        enqueue(). Messages are processed iteratively with accumulated
        context, similar to the TUI's AgentWorker loop.
        """
        self.loop_mode = True
        self._loop_running = True
        await self.start()
        self._loop_task = asyncio.create_task(self._session_loop())
    
    async def enqueue(self, message: str, priority: int = 0) -> None:
        """Enqueue a message without waiting for a response.
        
        In loop mode, the message is processed when the session loop
        is ready. Priority 10+ interrupts and clears context.
        
        In non-loop mode, this falls back to synchronous send().
        """
        if self.loop_mode and self._loop_running:
            msg = PendingMessage(
                role="user",
                content=message,
                priority=priority,
            )
            await self.message_queue.enqueue(msg)
        else:
            # Fallback to synchronous send
            return await self.send(message)
    
    async def _session_loop(self) -> None:
        """Main session loop for continuous conversation."""
        logger.info("Session %s entering loop mode", self.session_id)
        
        while self._loop_running:
            msg = await self.message_queue.wait_for_message(timeout=2.0)
            
            if msg is None:
                continue
            
            # Check for interrupt
            if self.message_queue.is_interrupted:
                self.message_queue.clear_interrupt()
            
            # Process the message
            try:
                response = await self.send(msg.content)
                # send() already saves to session history
            except Exception as e:
                logger.exception("Session loop error: %s", e)
        
        logger.info("Session %s loop ended", self.session_id)
