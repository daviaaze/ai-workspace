"""
MessageQueue — async message queue for agent multi-message support.

Enables multiple user messages to be queued while the agent is processing,
with priority-based interruption. Used by AgentWorker (TUI) and
PersistentAgentSession (CLI).

Architecture:
  User types message → enqueue(PendingMessage) → agent loop consumes
  Agent processes → checks queue → injects new messages → continues

Priority levels:
  0-4   : Normal — appended to context, processed in order
  5-9   : High — processed next, but doesn't clear context
  10+   : Interrupt — clears accumulated context, fresh start
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class MessagePriority(IntEnum):
    NORMAL = 0
    HIGH = 5
    INTERRUPT = 10


@dataclass
class PendingMessage:
    """A message queued for the agent to process."""
    role: str          # "user", "system"
    content: str
    priority: int = MessagePriority.NORMAL
    message_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_interrupt(self) -> bool:
        return self.priority >= MessagePriority.INTERRUPT
    
    @property
    def is_high_priority(self) -> bool:
        return self.priority >= MessagePriority.HIGH


class MessageQueue:
    """Async message queue for agent communication.
    
    Thread-safe: can be used from both asyncio and threaded contexts.
    The underlying asyncio.Queue is thread-safe for put_nowait.
    
    Usage:
        queue = MessageQueue(max_size=50)
        await queue.enqueue(PendingMessage(role="user", content="Fix the bug"))
        
        # In agent loop:
        msg = await queue.dequeue()           # Block until message
        msg = await queue.dequeue_or_none()   # Non-blocking, returns None if empty
        msgs = await queue.dequeue_all()      # Drain all pending
    
        # Interrupt:
        await queue.enqueue(PendingMessage(content="STOP", priority=10))
        if queue.is_interrupted:  # True
            queue.clear_interrupt()
    """
    
    def __init__(self, max_size: int = 50):
        self._queue: asyncio.Queue[PendingMessage] = asyncio.Queue(maxsize=max_size)
        self._interrupt_flag = asyncio.Event()
        self._new_message_event = asyncio.Event()
        self._pending_count = 0
    
    async def enqueue(self, msg: PendingMessage) -> None:
        """Enqueue a message for the agent.
        
        If priority >= 10 (INTERRUPT), sets the interrupt flag which
        the agent loop checks to clear context and restart fresh.
        """
        await self._queue.put(msg)
        self._pending_count += 1
        self._new_message_event.set()
        
        if msg.is_interrupt:
            self._interrupt_flag.set()
    
    def enqueue_nowait(self, msg: PendingMessage) -> None:
        """Non-async enqueue (thread-safe). Use from sync threads."""
        try:
            self._queue.put_nowait(msg)
            self._pending_count += 1
            # Can't set asyncio.Event from sync thread reliably,
            # but put_nowait is sufficient for the agent loop to pick up
        except asyncio.QueueFull:
            pass
    
    async def dequeue(self) -> PendingMessage:
        """Block until a message is available."""
        msg = await self._queue.get()
        self._pending_count = max(0, self._pending_count - 1)
        if self._queue.empty():
            self._new_message_event.clear()
        return msg
    
    async def dequeue_or_none(self) -> PendingMessage | None:
        """Non-blocking dequeue. Returns None if empty."""
        try:
            msg = self._queue.get_nowait()
            self._pending_count = max(0, self._pending_count - 1)
            if self._queue.empty():
                self._new_message_event.clear()
            return msg
        except asyncio.QueueEmpty:
            return None
    
    async def dequeue_all(self) -> list[PendingMessage]:
        """Drain all pending messages without blocking."""
        messages: list[PendingMessage] = []
        while True:
            msg = await self.dequeue_or_none()
            if msg is None:
                break
            messages.append(msg)
        return messages
    
    async def wait_for_message(self, timeout: float | None = None) -> PendingMessage | None:
        """Wait for a message with optional timeout."""
        try:
            if timeout is not None:
                return await asyncio.wait_for(self.dequeue(), timeout=timeout)
            return await self.dequeue()
        except asyncio.TimeoutError:
            return None
    
    @property
    def is_interrupted(self) -> bool:
        return self._interrupt_flag.is_set()
    
    def clear_interrupt(self) -> None:
        self._interrupt_flag.clear()
    
    @property
    def has_pending(self) -> bool:
        return not self._queue.empty()
    
    @property
    def pending_count(self) -> int:
        return self._pending_count
    
    @property
    def new_message_event(self) -> asyncio.Event:
        """Event set when a new message is enqueued."""
        return self._new_message_event
    
    def clear(self) -> None:
        """Clear all pending messages and reset state."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        self._pending_count = 0
        self._interrupt_flag.clear()
        self._new_message_event.clear()
