"""
MCP Client — connect to external MCP servers and call their tools.

Supports two transport modes:
- **stdio**: Launch a subprocess and communicate via stdin/stdout.
- **sse**: Connect to an HTTP SSE endpoint.

The client discovers tools from connected servers and exposes them
as OpenAI-compatible tool definitions for the agent loop.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("aiw.mcp_client")


# ═══════════════════════════════════════════════════════════
# Data Types
# ═══════════════════════════════════════════════════════════


@dataclass
class MCPTool:
    """A tool discovered from an MCP server."""

    name: str
    description: str
    input_schema: dict[str, Any]
    server_name: str  # Which server this tool belongs to

    def to_openai_tool(self) -> dict[str, Any]:
        """Convert to OpenAI-compatible tool definition."""
        return {
            "type": "function",
            "function": {
                "name": f"mcp_{self.server_name}_{self.name}",
                "description": f"[MCP:{self.server_name}] {self.description}",
                "parameters": self.input_schema,
            },
        }


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server connection."""

    name: str
    # stdio transport
    command: list[str] | None = None
    env: dict[str, str] | None = None
    # sse transport
    url: str | None = None
    # common
    timeout: float = 30.0


# ═══════════════════════════════════════════════════════════
# MCP Client
# ═══════════════════════════════════════════════════════════


class MCPClient:
    """Connect to MCP servers and call their tools.

    Example::

        client = MCPClient()
        client.add_server("weather", command=["python", "weather.py"])
        client.add_server("db", url="http://localhost:8080/sse")

        tools = await client.list_tools()
        result = await client.call_tool("weather", "get_forecast", {"city": "Lisbon"})
    """

    def __init__(self) -> None:
        self._servers: dict[str, MCPServerConfig] = {}
        self._tools: dict[str, MCPTool] = {}
        self._connected: dict[str, bool] = {}

    # ── Server Management ──────────────────────────────────

    def add_server(
        self,
        name: str,
        command: list[str] | None = None,
        url: str | None = None,
        env: dict[str, str] | None = None,
        timeout: float = 30.0,
    ) -> None:
        """Register an MCP server.

        Args:
            name: Unique server identifier.
            command: Command to launch stdio server.
            url: SSE endpoint URL.
            env: Environment variables for stdio server.
            timeout: Connection timeout in seconds.
        """
        self._servers[name] = MCPServerConfig(
            name=name,
            command=command,
            url=url,
            env=env,
            timeout=timeout,
        )
        self._connected[name] = False
        logger.info("Registered MCP server: %s", name)

    def remove_server(self, name: str) -> None:
        """Remove an MCP server."""
        self._servers.pop(name, None)
        self._connected.pop(name, None)
        # Remove tools from this server
        self._tools = {k: v for k, v in self._tools.items() if v.server_name != name}

    # ── Tool Discovery ─────────────────────────────────────

    async def list_tools(self) -> list[MCPTool]:
        """Discover tools from all connected servers.

        Returns combined tool list from all servers.
        """
        all_tools: list[MCPTool] = []

        for name, config in self._servers.items():
            try:
                tools = await self._discover_tools(config)
                for tool in tools:
                    tool.server_name = name
                    key = f"{name}:{tool.name}"
                    self._tools[key] = tool
                all_tools.extend(tools)
                self._connected[name] = True
                logger.info("Discovered %d tools from server '%s'", len(tools), name)
            except Exception as exc:
                logger.warning("Failed to discover tools from '%s': %s", name, exc)
                self._connected[name] = False

        return all_tools

    async def _discover_tools(self, config: MCPServerConfig) -> list[MCPTool]:
        """Discover tools from a single MCP server."""
        if config.command:
            return await self._discover_stdio(config)
        elif config.url:
            return await self._discover_sse(config)
        else:
            raise ValueError(f"Server '{config.name}' has no command or url")

    async def _discover_stdio(self, config: MCPServerConfig) -> list[MCPTool]:
        """Discover tools via stdio JSON-RPC."""
        import os

        env = {**os.environ, **(config.env or {})}

        proc = await asyncio.create_subprocess_exec(
            *config.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        try:
            # Send initialize
            await self._send_json(proc.stdin, {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "aiw-mcp-client", "version": "0.2.0"},
                },
            })

            # Read initialize response
            await asyncio.wait_for(
                self._read_json(proc.stdout),
                timeout=config.timeout,
            )

            # Send initialized notification
            await self._send_json(proc.stdin, {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            })

            # List tools
            await self._send_json(proc.stdin, {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
            })

            tools_response = await asyncio.wait_for(
                self._read_json(proc.stdout),
                timeout=config.timeout,
            )

            tools = []
            for tool_data in tools_response.get("result", {}).get("tools", []):
                tools.append(MCPTool(
                    name=tool_data["name"],
                    description=tool_data.get("description", ""),
                    input_schema=tool_data.get("inputSchema", {"type": "object", "properties": {}}),
                    server_name=config.name,
                ))
            return tools

        finally:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except TimeoutError:
                proc.kill()

    async def _discover_sse(self, config: MCPServerConfig) -> list[MCPTool]:
        """Discover tools via SSE HTTP transport."""
        try:
            import httpx
        except ImportError:
            raise ImportError("httpx required for SSE transport: pip install httpx")

        async with httpx.AsyncClient(timeout=config.timeout) as client:
            # Initialize session
            await client.post(
                f"{config.url}/messages",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "aiw-mcp-client", "version": "0.2.0"},
                    },
                },
            )

            # List tools
            tools_resp = await client.post(
                f"{config.url}/messages",
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                },
            )

            tools_data = tools_resp.json()
            tools = []
            for tool_data in tools_data.get("result", {}).get("tools", []):
                tools.append(MCPTool(
                    name=tool_data["name"],
                    description=tool_data.get("description", ""),
                    input_schema=tool_data.get("inputSchema", {"type": "object", "properties": {}}),
                    server_name=config.name,
                ))
            return tools

    # ── Tool Calling ───────────────────────────────────────

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> str:
        """Call a tool on a specific MCP server.

        Args:
            server_name: Server identifier.
            tool_name: Tool name (without server prefix).
            arguments: Tool arguments.

        Returns:
            Tool result as string.
        """
        config = self._servers.get(server_name)
        if config is None:
            return f"Error: server '{server_name}' not found"

        try:
            if config.command:
                return await self._call_stdio(config, tool_name, arguments)
            elif config.url:
                return await self._call_sse(config, tool_name, arguments)
            else:
                return f"Error: server '{server_name}' has no transport"
        except Exception as exc:
            logger.warning("Tool call failed: %s/%s: %s", server_name, tool_name, exc)
            return f"Error calling {tool_name}: {exc}"

    async def _call_stdio(
        self,
        config: MCPServerConfig,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> str:
        """Call a tool via stdio."""
        import os

        env = {**os.environ, **(config.env or {})}

        proc = await asyncio.create_subprocess_exec(
            *config.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        try:
            # Initialize
            await self._send_json(proc.stdin, {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "aiw-mcp-client", "version": "0.2.0"},
                },
            })
            await asyncio.wait_for(self._read_json(proc.stdout), timeout=config.timeout)

            await self._send_json(proc.stdin, {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            })

            # Call tool
            await self._send_json(proc.stdin, {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments,
                },
            })

            response = await asyncio.wait_for(
                self._read_json(proc.stdout),
                timeout=config.timeout,
            )

            # Extract text from response
            result = response.get("result", {})
            content = result.get("content", [])
            texts = [c.get("text", "") for c in content if c.get("type") == "text"]
            return "\n".join(texts) if texts else json.dumps(result)

        finally:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except TimeoutError:
                proc.kill()

    async def _call_sse(
        self,
        config: MCPServerConfig,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> str:
        """Call a tool via SSE."""
        try:
            import httpx
        except ImportError:
            return "Error: httpx required for SSE transport"

        async with httpx.AsyncClient(timeout=config.timeout) as client:
            resp = await client.post(
                f"{config.url}/messages",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments,
                    },
                },
            )

            result = resp.json().get("result", {})
            content = result.get("content", [])
            texts = [c.get("text", "") for c in content if c.get("type") == "text"]
            return "\n".join(texts) if texts else json.dumps(result)

    # ── Helpers ────────────────────────────────────────────

    @staticmethod
    async def _send_json(stream: asyncio.StreamWriter, data: dict) -> None:
        """Send a JSON-RPC message."""
        message = json.dumps(data) + "\n"
        stream.write(message.encode())
        await stream.drain()

    @staticmethod
    async def _read_json(stream: asyncio.StreamReader) -> dict:
        """Read a JSON-RPC message."""
        line = await stream.readline()
        if not line:
            raise ConnectionError("MCP server closed connection")
        return json.loads(line.decode())

    # ── Status ─────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        """Get status of all servers."""
        return {
            name: {
                "connected": self._connected.get(name, False),
                "transport": "stdio" if config.command else "sse",
                "tools": len([t for t in self._tools.values() if t.server_name == name]),
            }
            for name, config in self._servers.items()
        }

    def get_tools_for_agent(self) -> list[dict[str, Any]]:
        """Get all discovered tools as OpenAI-compatible tool definitions."""
        return [tool.to_openai_tool() for tool in self._tools.values()]
