"""
Tests for ProviderRegistry — multi-provider LLM abstraction.

Covers:
- ProviderType enum values
- ProviderConfig dataclass
- ProviderRegistry env/sops loading
- NVIDIA provider registration
- OpenRouter provider registration
- Provider model listing
- sops-nix secret path fallback
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

# ─── ProviderType enum ──────────────────────────────────


def test_provider_type_includes_nvidia():
    from ai_workspace.providers import ProviderType
    assert hasattr(ProviderType, "nvidia")
    assert ProviderType.nvidia.value == "nvidia"


def test_provider_type_includes_openrouter():
    from ai_workspace.providers import ProviderType
    assert hasattr(ProviderType, "openrouter")
    assert ProviderType.openrouter.value == "openrouter"


def test_provider_type_includes_existing_providers():
    from ai_workspace.providers import ProviderType
    assert hasattr(ProviderType, "ollama")
    assert hasattr(ProviderType, "deepseek")
    assert hasattr(ProviderType, "kimi")


# ─── ProviderConfig dataclass ──────────────────────────


def test_provider_config_creation():
    from ai_workspace.providers import ProviderConfig, ProviderType

    cfg = ProviderConfig(
        provider=ProviderType.nvidia,
        base_url="https://example.com/v1",
        api_key="test-key",
        default_model="test-model",
    )
    assert cfg.provider == ProviderType.nvidia
    assert cfg.base_url == "https://example.com/v1"
    assert cfg.api_key == "test-key"
    assert cfg.default_model == "test-model"
    assert cfg.timeout == 120.0  # default


# ─── NVIDIA provider registration ──────────────────────


def test_nvidia_provider_registers_from_env():
    """When NVIDIA_API_KEY env is set, provider registers with correct base URL."""
    from ai_workspace.providers import ProviderRegistry, ProviderType

    with patch.dict(os.environ, {"NVIDIA_API_KEY": "nvapi-test123"}, clear=False):
        # Clear any pre-existing sops file checks
        with patch("os.path.exists", return_value=False):
            registry = ProviderRegistry()
            assert "nvidia" in registry.providers
            cfg = registry.providers["nvidia"]
            assert cfg.base_url == "https://integrate.api.nvidia.com/v1"
            assert cfg.api_key == "nvapi-test123"
            assert cfg.default_model == "minimaxai/minimax-m3"
            assert cfg.provider == ProviderType.nvidia


def test_nvidia_provider_skipped_when_no_key():
    """When neither env nor sops has NVIDIA key, provider is not registered."""
    from ai_workspace.providers import ProviderRegistry

    env_without_nvidia = {k: v for k, v in os.environ.items() if k != "NVIDIA_API_KEY"}
    with patch.dict(os.environ, env_without_nvidia, clear=True):
        with patch("os.path.exists", return_value=False):
            registry = ProviderRegistry()
            assert "nvidia" not in registry.providers


# ─── OpenRouter provider registration ──────────────────


def test_openrouter_provider_registers_from_env():
    """When OPENROUTER_API_KEY env is set, provider registers with correct base URL."""
    from ai_workspace.providers import ProviderRegistry, ProviderType

    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-test123"}, clear=False):
        with patch("os.path.exists", return_value=False):
            registry = ProviderRegistry()
            assert "openrouter" in registry.providers
            cfg = registry.providers["openrouter"]
            assert cfg.base_url == "https://openrouter.ai/api/v1"
            assert cfg.api_key == "sk-or-test123"
            assert cfg.default_model == "anthropic/claude-3.7-sonnet"
            assert cfg.provider == ProviderType.openrouter


def test_openrouter_provider_skipped_when_no_key():
    """When neither env nor sops has OpenRouter key, provider is not registered."""
    from ai_workspace.providers import ProviderRegistry

    env_without_or = {k: v for k, v in os.environ.items() if k != "OPENROUTER_API_KEY"}
    with patch.dict(os.environ, env_without_or, clear=True):
        with patch("os.path.exists", return_value=False):
            registry = ProviderRegistry()
            assert "openrouter" not in registry.providers


# ─── sops-nix fallback ────────────────────────────────


def test_nvidia_sops_fallback_used_when_env_missing():
    """When env is empty, sops-nix path is used as fallback."""
    import tempfile

    from ai_workspace.providers import ProviderRegistry

    env_without_nvidia = {k: v for k, v in os.environ.items() if k != "NVIDIA_API_KEY"}
    with patch.dict(os.environ, env_without_nvidia, clear=True):
        # Write a real temp file that the sops fallback can read
        with tempfile.NamedTemporaryFile(mode="w", suffix=".key", delete=False) as f:
            f.write("nvapi-sops-secret")
            tmp_path = f.name
        try:
            # Patch expanduser to point to our temp file
            with patch("os.path.expanduser", return_value=tmp_path):
                registry = ProviderRegistry()
                assert "nvidia" in registry.providers
                assert registry.providers["nvidia"].api_key == "nvapi-sops-secret"
        finally:
            os.unlink(tmp_path)


def test_openrouter_sops_fallback_used_when_env_missing():
    """When env is empty, sops-nix path is used as fallback."""
    import tempfile

    from ai_workspace.providers import ProviderRegistry

    env_without_or = {k: v for k, v in os.environ.items() if k != "OPENROUTER_API_KEY"}
    with patch.dict(os.environ, env_without_or, clear=True):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".key", delete=False) as f:
            f.write("sk-or-sops-secret")
            tmp_path = f.name
        try:
            with patch("os.path.expanduser", return_value=tmp_path):
                registry = ProviderRegistry()
                assert "openrouter" in registry.providers
                assert registry.providers["openrouter"].api_key == "sk-or-sops-secret"
        finally:
            os.unlink(tmp_path)


# ─── Provider model listing ───────────────────────────


def test_nvidia_model_list_returns_curated_catalog():
    """NVIDIA provider returns its known model catalog."""
    from ai_workspace.providers import ProviderRegistry

    with patch.dict(os.environ, {"NVIDIA_API_KEY": "nvapi-test"}, clear=False):
        with patch("os.path.exists", return_value=False):
            registry = ProviderRegistry()
            models = registry.list_models("nvidia")
            assert len(models) >= 1
            assert any(m["name"] == "minimaxai/minimax-m3" for m in models)


def test_openrouter_model_list_returns_curated_catalog():
    """OpenRouter provider returns its curated model catalog."""
    from ai_workspace.providers import ProviderRegistry

    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-test"}, clear=False):
        with patch("os.path.exists", return_value=False):
            registry = ProviderRegistry()
            models = registry.list_models("openrouter")
            assert len(models) >= 3
            names = [m["name"] for m in models]
            assert "anthropic/claude-3.7-sonnet" in names
            assert "openai/gpt-4o" in names


# ─── get_client/get_model helpers ─────────────────────


def test_get_client_returns_asyncopenai_instance():
    from openai import AsyncOpenAI

    from ai_workspace.providers import ProviderRegistry

    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-test"}, clear=False):
        with patch("os.path.exists", return_value=False):
            registry = ProviderRegistry()
            client = registry.get_client("openrouter")
            assert isinstance(client, AsyncOpenAI)
            # base_url should include /v1
            assert "openrouter" in str(client.base_url)


def test_get_model_returns_default_when_no_override():
    from ai_workspace.providers import ProviderRegistry

    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-test"}, clear=False):
        with patch("os.path.exists", return_value=False):
            registry = ProviderRegistry()
            model = registry.get_model("openrouter")
            assert model == "anthropic/claude-3.7-sonnet"


def test_get_model_returns_override_when_given():
    from ai_workspace.providers import ProviderRegistry

    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-test"}, clear=False):
        with patch("os.path.exists", return_value=False):
            registry = ProviderRegistry()
            model = registry.get_model("openrouter", model="openai/gpt-4o")
            assert model == "openai/gpt-4o"


def test_get_client_unknown_provider_raises():
    from ai_workspace.providers import ProviderRegistry

    registry = ProviderRegistry()
    with pytest.raises(ValueError, match="not configured"):
        registry.get_client("nonexistent_provider_xyz")


def test_list_models_unknown_provider_returns_empty():
    """Unknown providers return empty list, not raise."""
    from ai_workspace.providers import ProviderRegistry

    registry = ProviderRegistry()
    models = registry.list_models("nonexistent_provider_xyz")
    assert models == []
