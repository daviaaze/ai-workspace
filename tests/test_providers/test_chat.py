"""
Tests for provider chat — Ollama native API, sync wrapper, streaming.

Covers:
- chat_sync with Ollama (mocked httpx)
- _chat_ollama streaming and non-streaming
- ProviderRegistry.get_client/get_model
- chat_sync error handling
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ═══════════════════════════════════════════════════════
# ProviderRegistry basics
# ═══════════════════════════════════════════════════════


class TestProviderRegistryChat:
    """chat() method with Ollama native API."""

    def test_get_client_ollama(self):
        from ai_workspace.providers import ProviderRegistry
        registry = ProviderRegistry()
        client = registry.get_client("ollama")
        assert client is not None

    def test_get_model_ollama_default(self):
        from ai_workspace.providers import ProviderRegistry
        registry = ProviderRegistry()
        model = registry.get_model("ollama")
        assert model == "qwen3:14b"

    def test_get_model_custom(self):
        from ai_workspace.providers import ProviderRegistry
        registry = ProviderRegistry()
        model = registry.get_model("ollama", model="custom-model")
        assert model == "custom-model"

    def test_get_client_deepseek_with_key(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
        from ai_workspace.providers import ProviderRegistry
        registry = ProviderRegistry()
        assert "deepseek" in registry.providers


# ═══════════════════════════════════════════════════════
# Chat sync wrapper
# ═══════════════════════════════════════════════════════


class TestChatSync:
    """chat_sync() — synchronous wrapper for CLI use."""

    def test_chat_sync_non_streaming(self):
        from ai_workspace.providers import chat_sync
        with patch("ai_workspace.providers.ProviderRegistry.chat") as mock_chat:
            mock_chat.return_value = "Hello, World!"
            result = chat_sync(
                [{"role": "user", "content": "Hi"}],
                provider="ollama",
                model="qwen3:14b",
            )
            assert result == "Hello, World!"
            mock_chat.assert_called_once()

    def test_chat_sync_streaming(self):
        from ai_workspace.providers import chat_sync
        tokens = []
        with patch("ai_workspace.providers.ProviderRegistry.chat") as mock_chat:
            mock_chat.return_value = "Hello World"
            result = chat_sync(
                [{"role": "user", "content": "Hi"}],
                provider="ollama",
                stream=True,
                on_token=lambda t: tokens.append(t),
            )
            assert result == "Hello World"

    def test_chat_sync_deepseek(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
        from ai_workspace.providers import chat_sync
        with patch("ai_workspace.providers.ProviderRegistry.chat") as mock_chat:
            mock_chat.return_value = "DeepSeek response"
            result = chat_sync(
                [{"role": "user", "content": "Hi"}],
                provider="deepseek",
                model="deepseek-chat",
            )
            assert result == "DeepSeek response"


# ═══════════════════════════════════════════════════════
# Ollama native API (mocked HTTP)
# ═══════════════════════════════════════════════════════


class TestOllamaChat:
    """_chat_ollama() with mocked httpx."""

    @pytest.fixture
    def registry(self):
        from ai_workspace.providers import ProviderRegistry
        return ProviderRegistry()

    @pytest.mark.asyncio
    async def test_chat_ollama_non_streaming(self, registry):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": "Hello from Ollama"}
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await registry._chat_ollama(
                [{"role": "user", "content": "Hi"}],
                model="qwen3:14b",
                stream=False,
            )
            assert result == "Hello from Ollama"

    @pytest.mark.asyncio
    async def test_chat_ollama_streaming(self, registry):
        # Simulate streaming NDJSON response
        async def async_lines():
            for line in [
                '{"message": {"content": "Hel"}}\n',
                '{"message": {"content": "lo"}}\n',
                '{"done": true}\n',
            ]:
                yield line

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = MagicMock(return_value=async_lines())

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)

        tokens = []
        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await registry._chat_ollama(
                [{"role": "user", "content": "Hi"}],
                model="qwen3:14b",
                stream=True,
                on_token=lambda t: tokens.append(t),
            )
            assert result == "Hello"
            assert tokens == ["Hel", "lo"]

    @pytest.mark.asyncio
    async def test_chat_ollama_includes_system_prompt(self, registry):
        mock_response = MagicMock()
        mock_response.json.return_value = {"message": {"content": "ok"}}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            await registry._chat_ollama(
                [
                    {"role": "system", "content": "You are helpful."},
                    {"role": "user", "content": "Hi"},
                ],
                model="qwen3:14b",
            )
            call_args = mock_client.post.call_args
            json_data = call_args[1]["json"]
            assert len(json_data["messages"]) == 2
            assert json_data["messages"][0]["role"] == "system"

    @pytest.mark.asyncio
    async def test_chat_ollama_uses_native_api_url(self, registry):
        mock_response = MagicMock()
        mock_response.json.return_value = {"message": {"content": "ok"}}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            await registry._chat_ollama(
                [{"role": "user", "content": "Hi"}],
                model="qwen3:14b",
            )
            call_args = mock_client.post.call_args
            url = call_args[0][0]
            # Should use native /api/chat, not /v1/chat/completions
            assert "/api/chat" in url
            assert "/v1" not in url

    @pytest.mark.asyncio
    async def test_chat_method_routes_ollama_to_native(self, registry):
        """When provider='ollama', chat() should use _chat_ollama."""
        with patch.object(registry, '_chat_ollama') as mock_native:
            mock_native.return_value = "native result"
            result = await registry.chat(
                [{"role": "user", "content": "Hi"}],
                provider="ollama",
                model="qwen3:14b",
            )
            assert result == "native result"
            mock_native.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_method_routes_deepseek_to_openai(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
        from ai_workspace.providers import ProviderRegistry
        registry = ProviderRegistry()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "DeepSeek says hi"

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch.object(registry, 'get_client', return_value=mock_client):
            result = await registry.chat(
                [{"role": "user", "content": "Hi"}],
                provider="deepseek",
                model="deepseek-chat",
            )
            assert result == "DeepSeek says hi"
