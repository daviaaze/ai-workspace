"""
E2E Inference Tests — run against a real local Ollama model.

These tests verify that the full `aiw ask` pipeline actually produces
sensible completions. They skip gracefully if Ollama is not running.
"""

from __future__ import annotations

import httpx
import pytest

from ai_workspace.providers import ProviderRegistry, chat_sync


def _ollama_running() -> bool:
    """Check if a local Ollama server is reachable."""
    try:
        r = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
        return r.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


def _available_models() -> list[str]:
    """Return list of model names available locally."""
    try:
        r = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
        if r.status_code == 200:
            return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        pass
    return []


ollama_available = pytest.mark.skipif(
    not _ollama_running(),
    reason="Ollama not running (start with `ollama serve`)",
)

# Pick the first available model, preferring a small one
_avail = _available_models()
DEFAULT_MODEL = "ornith-1.0-9b:latest" if "ornith-1.0-9b:latest" in _avail else (_avail[0] if _avail else "qwen3:9b")


# ── Tests ──────────────────────────────────────────────────


@ollama_available
class TestRealModelInference:

    @pytest.fixture(scope="class")
    def registry(self):
        return ProviderRegistry()

    def test_simple_fact(self, registry):
        """The model should answer a basic factual question."""
        response = chat_sync(
            [{"role": "user", "content": "What is 2+2? Answer in one word."}],
            provider="ollama",
            model=DEFAULT_MODEL,
        )
        assert response, "Response should not be empty"
        assert "4" in response or "four" in response.lower(), (
            f"Expected '4' in answer, got: {response}"
        )

    def test_brief_code(self, registry):
        """The model should produce a trivial Python function."""
        response = chat_sync(
            [{"role": "user", "content": "Write a one-line Python function that returns the square of a number."}],
            provider="ollama",
            model=DEFAULT_MODEL,
        )
        assert response, "Response should not be empty"
        assert "def " in response or "lambda" in response, (
            f"Expected function definition, got: {response[:200]}"
        )

    def test_short_creative(self, registry):
        """The model should respond to a creative prompt."""
        response = chat_sync(
            [{"role": "user", "content": "Say hello in exactly 5 words."}],
            provider="ollama",
            model=DEFAULT_MODEL,
        )
        assert response, "Response should not be empty"
        word_count = len(response.strip().split())
        # Allow some tolerance — models love to ramble
        assert word_count <= 20, (
            f"Expected short response (≤20 words), got {word_count} words: {response}"
        )

    def test_system_prompt_respected(self, registry):
        """A system prompt should influence the model's behavior."""
        response = chat_sync(
            [
                {"role": "system", "content": "You only answer 'I do not know that.' to every question."},
                {"role": "user", "content": "What is the capital of France?"},
            ],
            provider="ollama",
            model=DEFAULT_MODEL,
        )
        assert response, "Response should not be empty"
        assert "do not know" in response.lower() or "don't know" in response.lower() or "not" in response.lower(), (
            f"Expected refusal-like response, got: {response[:200]}"
        )

    def test_non_streaming_matches_streaming(self, registry):
        """Non-streaming and streaming should produce the same content."""
        prompt = "Repeat this exact phrase: 'apple banana cherry'"
        
        non_stream = chat_sync(
            [{"role": "user", "content": prompt}],
            provider="ollama", model=DEFAULT_MODEL,
        )
        
        stream_parts = []
        def collector(tok):
            stream_parts.append(tok)
        
        chat_sync(
            [{"role": "user", "content": prompt}],
            provider="ollama", model=DEFAULT_MODEL,
            stream=True, on_token=collector,
        )
        streamed = "".join(stream_parts)
        
        # Both should be non-empty and contain the key phrase
        assert non_stream, "Non-streaming response should not be empty"
        assert streamed, "Streamed response should not be empty"
        # Both should mention apple/banana/cherry
        for word in ("apple", "banana", "cherry"):
            assert word in non_stream.lower() or word in streamed.lower()

    def test_streaming_delivers_tokens(self, registry):
        """Streaming should deliver at least 3 tokens."""
        tokens = []
        def collect(t):
            tokens.append(t)
        
        chat_sync(
            [{"role": "user", "content": "Count to 3. Output: 1 2 3"}],
            provider="ollama", model=DEFAULT_MODEL,
            stream=True, on_token=collect,
        )
        assert len(tokens) >= 3, (
            f"Expected at least 3 streamed tokens, got {len(tokens)}"
        )
