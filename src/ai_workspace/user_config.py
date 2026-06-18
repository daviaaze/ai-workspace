"""
User configuration — BYOK (Bring Your Own Key).

Supports:
- TOML config file: ~/.config/aiw/config.toml
- Environment variables (highest priority)
- CLI overrides via --api-key

Priority: CLI > env var > config file > default
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("aiw.config")

# Default config path
CONFIG_DIR = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config")) / "aiw"
CONFIG_FILE = CONFIG_DIR / "config.toml"


@dataclass
class ProviderKey:
    """API key configuration for a provider."""
    api_key: str = ""
    api_base: str = ""
    default_model: str = ""
    env_var: str = ""  # Which env var to check


@dataclass
class AiwConfig:
    """User-level AI Workspace configuration."""
    providers: dict[str, ProviderKey] = field(default_factory=dict)
    ollama_host: str = "http://localhost:11434"
    parallelism: int = 2
    log_level: str = "INFO"

    @classmethod
    def load(cls, config_path: Path | None = None) -> AiwConfig:
        """Load configuration from TOML file, env vars, and defaults."""
        config = cls()

        # 1. Try TOML config file
        path = config_path or CONFIG_FILE
        if path.exists():
            try:
                config._load_toml(path)
            except Exception as exc:
                logger.warning("Failed to load config %s: %s", path, exc)

        # 2. Override with env vars (highest priority)
        config._apply_env_overrides()

        return config

    def _load_toml(self, path: Path) -> None:
        """Parse TOML config file."""
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                logger.debug("No TOML parser available, skipping config file")
                return

        with open(path, "rb") as f:
            data = tomllib.load(f)

        # Provider keys
        if "providers" in data:
            for name, prov_data in data["providers"].items():
                self.providers[name] = ProviderKey(
                    api_key=str(prov_data.get("api_key", "")),
                    api_base=str(prov_data.get("api_base", "")),
                    default_model=str(prov_data.get("default_model", "")),
                    env_var=str(prov_data.get("env_var", "")),
                )

        # General settings
        if "settings" in data:
            settings = data["settings"]
            self.ollama_host = str(settings.get("ollama_host", self.ollama_host))
            self.parallelism = int(settings.get("parallelism", self.parallelism))
            self.log_level = str(settings.get("log_level", self.log_level))

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides."""
        # Ollama host
        if os.getenv("OLLAMA_HOST"):
            self.ollama_host = os.getenv("OLLAMA_HOST", self.ollama_host)

        # Known provider env vars
        env_map = {
            "deepseek": "DEEPSEEK_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "nvidia": "NVIDIA_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
        }
        for name, env_var in env_map.items():
            key = os.getenv(env_var, "")
            if key:
                if name not in self.providers:
                    self.providers[name] = ProviderKey(api_key=key)
                else:
                    self.providers[name].api_key = key

    def get_api_key(self, provider: str) -> str:
        """Get API key for a provider (respects priority)."""
        # Env var always wins
        env_map = {
            "deepseek": "DEEPSEEK_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "nvidia": "NVIDIA_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
        }
        env_key = os.getenv(env_map.get(provider, ""), "")
        if env_key:
            return env_key

        # Config file
        if provider in self.providers:
            return self.providers[provider].api_key

        return ""

    def init_config_dir(self) -> None:
        """Create config directory and example config file if missing."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        if not CONFIG_FILE.exists():
            example = """# AI Workspace configuration
# See docs/README.md for details

[providers.deepseek]
# api_key = "sk-your-deepseek-key"
# api_base = "https://api.deepseek.com/v1"
# default_model = "deepseek-v4-flash"

[providers.gemini]
# api_key = "your-gemini-api-key"
# default_model = "gemini-2.5-flash"

[providers.nvidia]
# api_key = "your-nvidia-key"
# default_model = "mistral-nemo-12b"

[providers.openrouter]
# api_key = "your-openrouter-key"
# default_model = "openai/gpt-5-mini"

[settings]
# ollama_host = "http://localhost:11434"
# parallelism = 2
# log_level = "INFO"
"""
            CONFIG_FILE.write_text(example)
            logger.info("Created example config at %s", CONFIG_FILE)

    def to_dict(self) -> dict[str, Any]:
        """Serialize config to dict for CLI display."""
        return {
            "providers": list(self.providers.keys()),
            "ollama_host": self.ollama_host,
            "parallelism": self.parallelism,
            "log_level": self.log_level,
        }


# Singleton
_config: Optional[AiwConfig] = None


def get_config() -> AiwConfig:
    """Get or create the global config singleton."""
    global _config
    if _config is None:
        _config = AiwConfig.load()
    return _config
