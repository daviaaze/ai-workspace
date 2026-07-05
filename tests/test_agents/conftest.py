"""Test fixtures for agent loop tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import pytest

# ═══════════════════════════════════════════════════════════
# Fake stream_chat provider
# ═══════════════════════════════════════════════════════════


class FakeStreamChat:
    """A fake stream_chat callable that returns pre-defined responses.

    Usage::

        fake = FakeStreamChat([
            {"type": "text", "text": "Hello! How can I help?"},
        ])
        params = LoopParams(task="hi", deps={"stream_chat": fake})
    """

    def __init__(self, responses: list[dict[str, Any]]):
        self.responses = responses
        self.call_count = 0
        self.call_args: list[dict] = []

    async def __call__(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.7,
        tools: list[dict] | None = None,
        provider: str = "ollama",
    ) -> AsyncGenerator[dict, None]:
        self.call_args.append({
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "tools": tools,
        })
        self.call_count += 1

        if self.call_count > len(self.responses):
            yield {"type": "text", "text": "Done."}
            return

        # Return the response for this call
        response = self.responses[self.call_count - 1]

        if isinstance(response, list):
            for chunk in response:
                yield chunk
        elif isinstance(response, dict):
            yield response
        elif isinstance(response, str):
            # Simple string → emit as one text chunk
            for word in response.split():
                yield {"type": "text", "text": word + " "}
        else:
            yield {"type": "text", "text": str(response)}


@pytest.fixture
def fake_stream_chat():
    """Fixture that creates a FakeStreamChat factory."""
    def _make(responses: list[dict]) -> FakeStreamChat:
        return FakeStreamChat(responses)
    return _make


# ═══════════════════════════════════════════════════════════
# Fake tool handlers
# ═══════════════════════════════════════════════════════════


@pytest.fixture
def echo_tool():
    """A simple tool that echoes its input."""
    async def echo(message: str) -> str:
        return f"Echo: {message}"
    return echo


@pytest.fixture
def read_file_tool():
    """A simulated read_file tool."""
    async def read_file(path: str) -> str:
        return f"Contents of {path}: ..."
    return read_file


@pytest.fixture
def failing_tool():
    """A tool that always fails."""
    async def fail(reason: str = "unknown") -> str:
        raise RuntimeError(f"Tool failed: {reason}")
    return fail


@pytest.fixture
def sample_tools():
    """Sample tool definitions in OpenAI function-calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": "echo",
                "description": "Echo back the message",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "Message to echo"},
                    },
                    "required": ["message"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to file"},
                    },
                    "required": ["path"],
                },
            },
        },
    ]
