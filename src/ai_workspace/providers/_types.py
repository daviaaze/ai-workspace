"""Provider types and configuration for AI Workspace LLM providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


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
