"""
Multi-provider LLM abstraction.

Supported providers:
- Ollama (local models: qwen3-coder:30b, deepseek-r1:14b, etc.)
- DeepSeek API (v4 pro, OpenAI-compatible)
- Kimi API (moonshot, coding, search/fetch)
- HuggingFace (future)

Uses OpenAI-compatible API format where possible for easy model switching.
"""

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
    kimi = "kimi"
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
                default_model="deepseek-chat",
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
        **kwargs,
    ) -> str:
        """Send a chat completion request."""
        client = self.get_client(provider)
        model_name = self.get_model(provider, model)
        
        response = await client.chat.completions.create(
            model=model_name,
            messages=messages,
            stream=stream,
            **kwargs,
        )
        
        if stream:
            # Return accumulated content
            content_parts = []
            async for chunk in response:
                delta = chunk.choices[0].delta
                if delta.content:
                    content_parts.append(delta.content)
            return "".join(content_parts)
        else:
            return response.choices[0].message.content or ""


# Simple sync wrapper for CLI use
def chat_sync(
    messages: list[dict[str, str]],
    provider: str = "ollama",
    model: str | None = None,
    **kwargs,
) -> str:
    """Synchronous chat wrapper for CLI."""
    import asyncio
    registry = ProviderRegistry()
    return asyncio.run(registry.chat(messages, provider=provider, model=model, **kwargs))
