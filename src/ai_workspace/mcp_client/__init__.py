"""MCP Client — consume tools from external MCP servers.

Connects to MCP servers via stdio or SSE transport, discovers their tools,
and exposes them as callable tools for the agent loop.

Usage::

    from ai_workspace.mcp_client import MCPClient

    client = MCPClient()
    client.add_server("weather", command=["python", "weather_server.py"])
    client.add_server("database", url="http://localhost:8080/sse")

    # Discover tools from all servers
    tools = await client.list_tools()

    # Call a tool
    result = await client.call_tool("weather", "get_forecast", {"city": "São Paulo"})
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ai_workspace.mcp_client.client import MCPClient, MCPTool

if TYPE_CHECKING:
    from ai_workspace.mcp_client.integration import (
        MCPToolBundle,
        discover_mcp_tools,
        mcp_status_summary,
    )

logger = logging.getLogger("aiw.mcp")


# ── Global cache for TUI / CLI integration ──────────────────────────────
# Populated by init_mcp_from_config() — consumed by build_tools() (sync context).

_MCP_BUNDLE_CACHE: Any = None
_MCP_CLIENT_CACHE: MCPClient | None = None


async def init_mcp_from_config() -> Any:
    """Initialize MCP client from user config and cache discovered tools.

    Call this once at app startup (async context). The cached bundle is
    later consumed by ``build_tools()`` (sync TUI function).

    Returns the bundle, or None if no MCP servers are configured.
    """
    global _MCP_BUNDLE_CACHE, _MCP_CLIENT_CACHE

    try:
        from ai_workspace.mcp_client.integration import MCPToolBundle, discover_mcp_tools
        from ai_workspace.user_config import get_config

        cfg = get_config()
        if not cfg.mcp_servers:
            return None

        client = MCPClient()
        for name, srv_cfg in cfg.mcp_servers.items():
            if srv_cfg.command:
                client.add_server(name, command=srv_cfg.command, env=srv_cfg.env, timeout=srv_cfg.timeout)
            elif srv_cfg.url:
                client.add_server(name, url=srv_cfg.url, timeout=srv_cfg.timeout)

        _MCP_CLIENT_CACHE = client
        bundle = await discover_mcp_tools(client)
        _MCP_BUNDLE_CACHE = bundle

        if bundle.tool_definitions:
            servers_str = ", ".join(
                f"{s}({c}tools)" for s, c in bundle.server_tool_count.items()
            )
            logger.info("MCP initialized: %s", servers_str)
        return bundle
    except Exception as exc:
        logger.warning("MCP init from config failed: %s", exc)
        return None


def get_cached_mcp_client() -> MCPClient | None:
    """Get the cached MCP client (or None if not initialized)."""
    return _MCP_CLIENT_CACHE


def get_cached_mcp_bundle() -> Any:
    """Get the cached MCP tool bundle (or None if not initialized)."""
    return _MCP_BUNDLE_CACHE


__all__ = [
    "MCPClient",
    "MCPTool",
    "MCPToolBundle",
    "discover_mcp_tools",
    "mcp_status_summary",
    "init_mcp_from_config",
    "get_cached_mcp_client",
    "get_cached_mcp_bundle",
    "_MCP_BUNDLE_CACHE",
]
