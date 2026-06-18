"""Multi-provider LLM abstraction with OpenAI-compatible API format."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import httpx
from openai import AsyncOpenAI


class ProviderType(str, Enum):
    ollama = "ollama"
    deepseek = "deepseek"
    gemini = "gemini"
    kimi = "kimi"
    nvidia = "nvidia"
    openrouter = "openrouter"
    huggingface = "huggingface"


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider."""
    
    provider: ProviderType
    base_url: str
    api_key: str = ""
    default_model: str = ""
    
    # Provider-specific settings
    timeout: float = 120.0
    max_retries: int = 3


class ProviderRegistry:
    """Registry of available LLM providers, loaded from env/config."""

    def __init__(self):
        self.providers: dict[str, ProviderConfig] = {}
        self._load_from_env()

    def _load_from_env(self) -> None:
        """Load providers from environment variables and existing configs."""

        # Ollama (local)
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.providers["ollama"] = ProviderConfig(
            provider=ProviderType.ollama,
            base_url=f"{ollama_host}/v1",
            api_key="ollama",
            default_model="qwen3:14b",
            timeout=300.0,  # thinking models need longer (load + generation)
        )

        # DeepSeek API
        deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
        # Also check sops-nix secret path
        if not deepseek_key:
            sops_path = os.path.expanduser("~/.local/share/sops-nix/secrets/deepseek_api_key")
            try:
                if os.path.exists(sops_path):
                    deepseek_key = open(sops_path).read().strip()
            except Exception:
                pass

        if deepseek_key:
            self.providers["deepseek"] = ProviderConfig(
                provider=ProviderType.deepseek,
                base_url="https://api.deepseek.com/v1",
                api_key=deepseek_key,
                default_model="deepseek-v4-flash",
            )

        # Kimi (via config.toml or env)
        kimi_key = os.getenv("KIMI_API_KEY", "")
        if kimi_key:
            self.providers["kimi"] = ProviderConfig(
                provider=ProviderType.kimi,
                base_url="https://api.kimi.com/coding/v1",
                api_key=kimi_key,
                default_model="kimi-for-coding",
            )

        # NVIDIA NIM (MiniMax-M3 multimodal, NVIDIA-hosted models)
        # API: https://integrate.api.nvidia.com/v1/chat/completions
        nvidia_key = os.getenv("NVIDIA_API_KEY", "")
        # Also check sops-nix secret path
        if not nvidia_key:
            sops_path = os.path.expanduser("~/.local/share/sops-nix/secrets/nvidia_api_key")
            try:
                if os.path.exists(sops_path):
                    nvidia_key = open(sops_path).read().strip()
            except Exception:
                pass

        if nvidia_key:
            self.providers["nvidia"] = ProviderConfig(
                provider=ProviderType.nvidia,
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=nvidia_key,
                default_model="minimaxai/minimax-m3",
            )

        # Gemini API (Google AI Studio free tier)
        # API: https://generativelanguage.googleapis.com/v1beta/openai/
        # 60 req/min free, 1500/day. Great for cheap extraction & classification.
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        if not gemini_key:
            sops_path = os.path.expanduser("~/.local/share/sops-nix/secrets/gemini_api_key")
            try:
                if os.path.exists(sops_path):
                    gemini_key = open(sops_path).read().strip()
            except Exception:
                pass

        if gemini_key:
            self.providers["gemini"] = ProviderConfig(
                provider=ProviderType.gemini,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                api_key=gemini_key,
                default_model="gemini-2.5-flash",
                timeout=60.0,
            )

        # OpenRouter (gateway to many providers: Claude, GPT-4, Gemini, etc.)
        # API: https://openrouter.ai/api/v1/chat/completions
        # Use --model to pick specific model, e.g. anthropic/claude-3-7-sonnet
        openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        # Also check sops-nix secret path
        if not openrouter_key:
            sops_path = os.path.expanduser("~/.local/share/sops-nix/secrets/openrouter_api_key")
            try:
                if os.path.exists(sops_path):
                    openrouter_key = open(sops_path).read().strip()
            except Exception:
                pass

        if openrouter_key:
            self.providers["openrouter"] = ProviderConfig(
                provider=ProviderType.openrouter,
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_key,
                default_model="anthropic/claude-3.7-sonnet",
            )

    def get_client(self, provider: str = "ollama") -> AsyncOpenAI:
        """Get an OpenAI-compatible client for a provider."""
        cfg = self.providers.get(provider)
        if not cfg:
            raise ValueError(f"Provider '{provider}' not configured. Available: {list(self.providers)}")
        
        return AsyncOpenAI(
            base_url=cfg.base_url,
            api_key=cfg.api_key or "unused",
            timeout=cfg.timeout,
            max_retries=cfg.max_retries,
        )

    def get_model(self, provider: str = "ollama", model: str | None = None) -> str:
        """Get the model name for a provider."""
        cfg = self.providers.get(provider)
        if not cfg:
            raise ValueError(f"Provider '{provider}' not configured.")
        return model or cfg.default_model

    def list_models(self, provider: str = "ollama") -> list[dict[str, Any]]:
        """List available models for a provider (sync wrapper for CLI)."""
        import asyncio
        return asyncio.run(self.list_models_async(provider))

    async def list_models_async(self, provider: str = "ollama") -> list[dict[str, Any]]:
        """List available models for a provider (Ollama-compatible)."""
        cfg = self.providers.get(provider)
        if not cfg:
            return []

        if provider == "ollama":
            # Use Ollama native API for model listing
            ollama_host = cfg.base_url.replace("/v1", "")
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{ollama_host}/api/tags", timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    return [
                        {
                            "name": m["name"],
                            "size": m.get("size"),
                            "family": m.get("details", {}).get("family", ""),
                            "parameter_size": m.get("details", {}).get("parameter_size", ""),
                            "quantization": m.get("details", {}).get("quantization_level", ""),
                        }
                        for m in data.get("models", [])
                    ]

        if provider == "nvidia":
            # NVIDIA NIM has a known model catalog
            return [
                {"name": "minimaxai/minimax-m3", "family": "minimax", "parameter_size": "MoE"},
                {"name": "nvidia/llama-3.1-nemotron-70b-instruct", "family": "llama", "parameter_size": "70B"},
                {"name": "nvidia/nemotron-mini-4b-instruct", "family": "nemotron", "parameter_size": "4B"},
            ]

        if provider == "openrouter":
            # Curated OpenRouter catalog (full list at https://openrouter.ai/models)
            return [
                {"name": "anthropic/claude-3.7-sonnet", "family": "claude", "parameter_size": "200k"},
                {"name": "anthropic/claude-3.5-sonnet", "family": "claude", "parameter_size": "200k"},
                {"name": "openai/gpt-4o", "family": "gpt-4o", "parameter_size": "128k"},
                {"name": "openai/gpt-4o-mini", "family": "gpt-4o", "parameter_size": "128k"},
                {"name": "google/gemini-2.5-pro", "family": "gemini", "parameter_size": "1M"},
                {"name": "meta-llama/llama-3.3-70b-instruct", "family": "llama", "parameter_size": "70B"},
                {"name": "deepseek/deepseek-chat-v3", "family": "deepseek", "parameter_size": "671B"},
                {"name": "qwen/qwen-2.5-coder-32b-instruct", "family": "qwen", "parameter_size": "32B"},
            ]
        
        # For OpenAI-compatible providers, list via /models
        client = self.get_client(provider)
        try:
            models = await client.models.list()
            return [{"name": m.id} for m in models.data]
        except Exception:
            return [{"name": cfg.default_model}]

    async def chat(
        self,
        messages: list[dict[str, str]],
        provider: str = "ollama",
        model: str | None = None,
        stream: bool = False,
        on_token: callable | None = None,
        **kwargs,
    ) -> str:
        """Send a chat completion request.
        
        Args:
            messages: Chat messages
            provider: Provider name
            model: Model name (optional, uses default)
            stream: Whether to stream tokens
            on_token: Callback(token_text) for streaming output
            **kwargs: Additional API parameters
        """
        model_name = self.get_model(provider, model)
        
        # Always use native Ollama API — it handles thinking models
        # (deepseek-r1, qwen3) reliably, avoiding /v1 endpoint timeouts
        if provider == "ollama":
            return await self._chat_ollama(messages, model_name, stream, on_token, **kwargs)
        
        # All other providers use OpenAI-compatible API
        return await self._chat_openai_compatible(
            provider, model_name, messages, stream, on_token, **kwargs
        )
    
    async def _chat_openai_compatible(
        self,
        provider: str,
        model: str,
        messages: list[dict[str, str]],
        stream: bool = False,
        on_token: callable | None = None,
        **kwargs,
    ) -> str:
        """Chat using OpenAI-compatible API (DeepSeek, Gemini, OpenRouter, etc.)."""
        client = self.get_client(provider)
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=stream,
            **kwargs,
        )
        
        if stream:
            content_parts = []
            async for chunk in response:
                delta = chunk.choices[0].delta
                if delta.content:
                    token = delta.content
                    content_parts.append(token)
                    if on_token:
                        on_token(token)
            return "".join(content_parts)
        else:
            return response.choices[0].message.content or ""
    
    async def _chat_ollama(
        self,
        messages: list[dict[str, str]],
        model: str,
        stream: bool = False,
        on_token: callable | None = None,
        **kwargs,
    ) -> str:
        """Chat using native Ollama API — handles thinking models reliably.
        
        The /v1 OpenAI-compatible endpoint struggles with thinking models
        (deepseek-r1, qwen3) that emit reasoning_content tokens. Native
        /api/chat handles these correctly in both stream and non-stream modes.
        """
        cfg = self.providers["ollama"]
        ollama_base = cfg.base_url.replace("/v1", "")
        
        async with httpx.AsyncClient(timeout=cfg.timeout) as client:
            response = await client.post(
                f"{ollama_base}/api/chat",
                json={
                    "model": model,
                    "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
                    "stream": stream,
                    "options": {
                        "temperature": kwargs.get("temperature", 0.7),
                        "flash_attention": True,     # 3x faster prompt eval
                        "num_predict": kwargs.get("max_tokens", 512),  # limit output
                    },
                },
                timeout=httpx.Timeout(cfg.timeout, connect=30.0),
            )
            response.raise_for_status()
            
            if stream:
                content_parts = []
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        if data.get("done"):
                            break
                        token = data.get("message", {}).get("content", "")
                        if token:
                            content_parts.append(token)
                            if on_token:
                                on_token(token)
                    except json.JSONDecodeError:
                        continue
                return "".join(content_parts)
            else:
                data = response.json()
                return data.get("message", {}).get("content", "")


    async def stream_chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        tools: list[dict] | None = None,
        provider: str = "ollama",
    ):
        """Stream chat with normalized chunk format.

        Async generator that yields dicts with a ``type`` field:

        - ``{"type": "text", "text": "..."}`` — a token of assistant text
        - ``{"type": "thinking", "thought": "..."}`` — reasoning content
        - ``{"type": "tool_call", "id": "...", "name": "...", "arguments": "..."}``
        - ``{"type": "error", "code": "...", "message": "..."}``

        This is the canonical streaming interface used by the AgentLoop.
        """
        model_name = self.get_model(provider, model)

        if provider == "ollama":
            async for chunk in self._stream_chat_ollama(
                model_name, messages, temperature, tools
            ):
                yield chunk
        else:
            async for chunk in self._stream_chat_openai(
                provider, model_name, messages, temperature, tools
            ):
                yield chunk

    async def _stream_chat_ollama(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        tools: list[dict] | None = None,
    ):
        """Stream chat via native Ollama /api/chat endpoint."""
        cfg = self.providers["ollama"]
        ollama_base = cfg.base_url.replace("/v1", "")

        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
            "stream": True,
            "options": {"temperature": temperature},
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=cfg.timeout) as client:
            async with client.stream(
                "POST",
                f"{ollama_base}/api/chat",
                json=payload,
                timeout=httpx.Timeout(cfg.timeout, connect=30.0),
            ) as response:
                response.raise_for_status()
                accumulated_tool_calls: dict[int, dict] = {}

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if data.get("done"):
                        break

                    message = data.get("message", {})

                    # Text token
                    content = message.get("content", "")
                    if content:
                        yield {"type": "text", "text": content}

                    # Thinking / reasoning (qwen3, deepseek-r1)
                    thinking = message.get("thinking", "") or message.get(
                        "reasoning_content", ""
                    )
                    if thinking:
                        yield {"type": "thinking", "thought": thinking}

                    # Tool calls (Ollama 0.5+ with tool support)
                    tool_calls_list = message.get("tool_calls", [])
                    for tc in tool_calls_list:
                        fn = tc.get("function", {})
                        yield {
                            "type": "tool_call",
                            "id": tc.get("id", ""),
                            "name": fn.get("name", ""),
                            "arguments": fn.get("arguments", {}),
                        }

    async def _stream_chat_openai(
        self,
        provider: str,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        tools: list[dict] | None = None,
    ):
        """Stream chat via OpenAI-compatible /v1/chat/completions endpoint."""
        client = self.get_client(provider)

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools

        response = await client.chat.completions.create(**kwargs)

        # Track accumulated tool calls across chunks
        accumulated_tool_calls: dict[int, dict] = {}

        async for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta is None:
                continue

            # Collect tool call fragments
            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in accumulated_tool_calls:
                        accumulated_tool_calls[idx] = {
                            "id": tc_delta.id or "",
                            "name": "",
                            "arguments": "",
                        }
                    acc = accumulated_tool_calls[idx]
                    if tc_delta.id:
                        acc["id"] = tc_delta.id
                    if tc_delta.function:
                        if tc_delta.function.name:
                            acc["name"] = tc_delta.function.name
                        if tc_delta.function.arguments:
                            acc["arguments"] += tc_delta.function.arguments
                continue

            # Text token
            if delta.content:
                yield {"type": "text", "text": delta.content}

            # Reasoning content (DeepSeek, o1-style models)
            if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                yield {
                    "type": "thinking",
                    "thought": delta.reasoning_content,
                }

        # Emit accumulated tool calls (they're complete now)
        for tc in accumulated_tool_calls.values():
            # Parse JSON arguments if possible
            args = tc.get("arguments", "{}")
            try:
                args = json.loads(args) if isinstance(args, str) else args
            except (json.JSONDecodeError, TypeError):
                pass  # keep as string if unparseable
            yield {
                "type": "tool_call",
                "id": tc["id"],
                "name": tc["name"],
                "arguments": args,
            }


# Simple sync wrapper for CLI use
def chat_sync(
    messages: list[dict[str, str]],
    provider: str = "ollama",
    model: str | None = None,
    stream: bool = False,
    on_token: callable | None = None,
    **kwargs,
) -> str:
    """Synchronous chat wrapper for CLI."""
    import asyncio
    registry = ProviderRegistry()
    return asyncio.run(registry.chat(
        messages, provider=provider, model=model,
        stream=stream, on_token=on_token, **kwargs
    ))
