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
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("aiw.config")

# Default config path
CONFIG_DIR = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config")) / "aiw"
CONFIG_FILE = CONFIG_DIR / "config.toml"


class ProviderKey(BaseModel):
    """API key configuration for a provider."""
    api_key: str = ""
    api_base: str = ""
    default_model: str = ""
    env_var: str = ""  # Which env var to check


# Per-provider default base URLs and models — authoritative single source of truth.
# Used by ProviderRegistry when the user hasn't overridden these in TOML.
PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "deepseek": {
        "api_base": "https://api.deepseek.com/v1",
        "default_model": "deepseek-v4-flash",
        "env_var": "DEEPSEEK_API_KEY",
        "sops_file": "deepseek_api_key",
    },
    "gemini": {
        "api_base": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "default_model": "gemini-2.5-flash",
        "env_var": "GEMINI_API_KEY",
        "sops_file": "gemini_api_key",
    },
    "nvidia": {
        "api_base": "https://integrate.api.nvidia.com/v1",
        "default_model": "minimaxai/minimax-m3",
        "env_var": "NVIDIA_API_KEY",
        "sops_file": "nvidia_api_key",
    },
    "openrouter": {
        "api_base": "https://openrouter.ai/api/v1",
        "default_model": "anthropic/claude-3.7-sonnet",
        "env_var": "OPENROUTER_API_KEY",
        "sops_file": "openrouter_api_key",
    },
    "kimi": {
        "api_base": "https://api.kimi.com/coding/v1",
        "default_model": "kimi-for-coding",
        "env_var": "KIMI_API_KEY",
        "sops_file": "kimi_api_key",
    },
}

def _load_sops_secret(file_name: str) -> str:
    """Try to load a secret from sops-nix secrets dir.

    Returns the trimmed secret string, or '' if the file is missing or
    unreadable. Sops-nix (NixOS) materialises secrets at deploy time to
    ``~/.local/share/sops-nix/secrets/<name>`` with restrictive perms.

    We call ``os.path.expanduser`` on the full path so that tests can
    patch ``expanduser`` to redirect the lookup (as they already do).
    """
    if not file_name:
        return ""
    raw_path = os.path.join(
        os.getenv("AIW_SOPS_DIR", "~/.local/share/sops-nix/secrets"),
        file_name,
    )
    path = os.path.expanduser(raw_path)
    try:
        if os.path.exists(path):
            with open(path) as f:
                return f.read().strip()
    except OSError:
        pass
    return ""


class MCPServerConfig(BaseModel):
    """MCP server configuration from config file."""
    name: str = ""
    command: list[str] | None = None  # stdio transport
    url: str = ""                     # SSE transport
    env: dict[str, str] = Field(default_factory=dict)
    timeout: float = 30.0


class AiwConfig(BaseSettings):
    """User-level AI Workspace configuration.

    Uses Pydantic BaseSettings for automatic env var parsing.
    Environment variables override TOML config entries.

    Env var mapping:
    - AIW_OLLAMA_HOST → ollama_host
    - AIW_LOG_LEVEL → log_level
    - AIW_PARALLELISM → parallelism
    - DEEPSEEK_API_KEY → providers.deepseek.api_key
    - GEMINI_API_KEY → providers.gemini.api_key
    - etc.
    """

    model_config = SettingsConfigDict(
        env_prefix="AIW_",
        env_file=".env",
        extra="ignore",
    )

    providers: dict[str, ProviderKey] = Field(default_factory=dict)
    mcp_servers: dict[str, MCPServerConfig] = Field(default_factory=dict)
    ollama_host: str = "http://localhost:11434"
    parallelism: int = 2
    log_level: str = "INFO"

    @classmethod
    def load(cls, config_path: Path | None = None) -> AiwConfig:
        """Load configuration from TOML file, env vars, and defaults.

        Priority: env vars > TOML > defaults
        """
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

        # MCP server definitions
        if "mcp" in data:
            mcp_data = data["mcp"]
            if "servers" in mcp_data:
                for name, srv in mcp_data["servers"].items():
                    self.mcp_servers[name] = MCPServerConfig(
                        name=name,
                        command=list(srv.get("command", [])),
                        url=str(srv.get("url", "")),
                        env=dict(srv.get("env", {})),
                        timeout=float(srv.get("timeout", 30.0)),
                    )

        # General settings
        if "settings" in data:
            settings = data["settings"]
            self.ollama_host = str(settings.get("ollama_host", self.ollama_host))
            self.parallelism = int(settings.get("parallelism", self.parallelism))
            self.log_level = str(settings.get("log_level", self.log_level))

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides + sops-nix secrets.

        Priority for each provider: env var > TOML > sops file.
        Defaults (api_base, default_model) come from PROVIDER_DEFAULTS
        when nothing is supplied.
        """
        # Ollama host — AIW_OLLAMA_HOST auto-parsed by BaseSettings, but we also
        # honor raw OLLAMA_HOST for backward compat.
        if os.getenv("OLLAMA_HOST"):
            self.ollama_host = os.getenv("OLLAMA_HOST", self.ollama_host)

        for name, defaults in PROVIDER_DEFAULTS.items():
            env_var = defaults["env_var"]
            key = os.getenv(env_var, "")
            # Backfill defaults so providers[name] always carries api_base/model
            entry = self.providers.get(name) or ProviderKey()
            if not entry.api_base:
                entry.api_base = defaults["api_base"]
            if not entry.default_model:
                entry.default_model = defaults["default_model"]
            entry.env_var = env_var
            # Resolve api_key: env > TOML > sops file
            if not key:
                key = entry.api_key
            if not key:
                key = _load_sops_secret(defaults["sops_file"])
            if key:
                entry.api_key = key
                self.providers[name] = entry

    def get_api_key(self, provider: str) -> str:
        """Get API key for a provider (respects priority).

        Priority: env var > TOML > sops file > None.
        """
        defaults = PROVIDER_DEFAULTS.get(provider, {})
        env_key = os.getenv(defaults.get("env_var", ""), "")
        if env_key:
            return env_key

        # Config file (already merged with sops in _apply_env_overrides)
        if provider in self.providers:
            return self.providers[provider].api_key

        # Last-ditch: try sops directly
        sops_file = defaults.get("sops_file", "")
        if sops_file:
            return _load_sops_secret(sops_file)

        return ""

    def get_provider(self, provider: str) -> ProviderKey | None:
        """Get the resolved ProviderKey entry for a provider, or None."""
        return self.providers.get(provider)

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

[mcp.servers]
# Example: stdio MCP server (local subprocess)
# my-tools = { command = ["python", "-m", "my_mcp_server"], timeout = 30 }
# Example: SSE MCP server (remote)
# weather = { url = "http://localhost:8080/sse", timeout = 15 }

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
            "mcp_servers": list(self.mcp_servers.keys()),
            "ollama_host": self.ollama_host,
            "parallelism": self.parallelism,
            "log_level": self.log_level,
        }


# Singleton
_config: AiwConfig | None = None


def get_config() -> AiwConfig:
    """Get or create the global config singleton."""
    global _config
    if _config is None:
        _config = AiwConfig.load()
    return _config


def reset_config() -> None:
    """Reset the config singleton (test helper).

    Forces next ``get_config()`` call to re-read from disk/environment.
    """
    global _config
    _config = None
