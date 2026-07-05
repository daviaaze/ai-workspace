"""
MCP Client Extended Tests — connection lifecycle, tool discovery,
error handling, server management, and transport fallback.

Tests use no real MCP servers — all external I/O is mocked.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_workspace.mcp_client.client import MCPClient, MCPTool, MCPServerConfig


# ═══════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════


@pytest.fixture
def client():
    """Empty MCPClient."""
    return MCPClient()


@pytest.fixture
def client_with_tools(client):
    """MCPClient with pre-populated tools."""
    client._tools["weather:get_forecast"] = MCPTool(
        name="get_forecast",
        description="Get weather forecast",
        input_schema={
            "type": "object",
            "properties": {
                "city": {"type": "string"},
                "days": {"type": "integer"},
            },
            "required": ["city"],
        },
        server_name="weather",
    )
    client._tools["db:query"] = MCPTool(
        name="query",
        description="Query the database",
        input_schema={
            "type": "object",
            "properties": {
                "sql": {"type": "string"},
            },
            "required": ["sql"],
        },
        server_name="db",
    )
    return client


# ═══════════════════════════════════════════════════════════
# 1. Server Management
# ═══════════════════════════════════════════════════════════


class TestServerManagement:
    """Adding, removing, and querying MCP servers."""

    def test_add_stdio_server(self, client):
        client.add_server("my-tools", command=["python", "tools.py"])
        status = client.status()
        assert "my-tools" in status
        assert status["my-tools"]["transport"] == "stdio"
        assert status["my-tools"]["connected"] is False

    def test_add_sse_server(self, client):
        client.add_server("remote", url="http://localhost:10101/sse")
        status = client.status()
        assert status["remote"]["transport"] == "sse"

    def test_add_duplicate_name_replaces(self, client):
        client.add_server("dup", command=["echo"])
        client.add_server("dup", command=["cat"])
        status = client.status()
        # After replacement, the tool count resets
        assert "dup" in status

    def test_remove_server(self, client):
        client.add_server("temp", command=["echo"])
        client.remove_server("temp")
        assert "temp" not in client.status()

    def test_remove_nonexistent(self, client):
        client.remove_server("does-not-exist")  # should not raise

    def test_status_empty_initial(self, client):
        assert client.status() == {}

    def test_multiple_servers_unique(self, client):
        client.add_server("s1", command=["python", "s1.py"])
        client.add_server("s2", url="http://localhost:8080")
        client.add_server("s3", command=["python", "s3.py"])
        status = client.status()
        assert len(status) == 3

    def test_server_config_with_env(self, client):
        client.add_server("with-env", command=["python", "run.py"], env={"KEY": "VAL"})
        cfg = client._servers["with-env"]
        assert cfg.env == {"KEY": "VAL"}

    def test_server_config_with_timeout(self, client):
        client.add_server("slow", command=["sleep"], timeout=60.0)
        assert client._servers["slow"].timeout == 60.0


# ═══════════════════════════════════════════════════════════
# 2. Tool Discovery & Conversion
# ═══════════════════════════════════════════════════════════


class TestToolDiscovery:
    """Tool definitions and OpenAI format conversion."""

    def test_tool_creation(self):
        tool = MCPTool(
            name="echo",
            description="Echo input",
            input_schema={"type": "object", "properties": {}},
            server_name="utils",
        )
        assert tool.name == "echo"
        assert tool.server_name == "utils"

    def test_to_openai_format(self):
        tool = MCPTool(
            name="search",
            description="Search the knowledge base",
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            server_name="search-server",
        )
        openai = tool.to_openai_tool()
        assert openai["function"]["name"] == "mcp_search-server_search"
        assert "[MCP:search-server]" in openai["function"]["description"]

    def test_get_tools_for_agent_empty(self, client):
        assert client.get_tools_for_agent() == []

    def test_get_tools_for_agent_multiple(self, client_with_tools):
        tools = client_with_tools.get_tools_for_agent()
        assert len(tools) == 2
        names = [t["function"]["name"] for t in tools]
        assert "mcp_weather_get_forecast" in names
        assert "mcp_db_query" in names

    def test_tool_name_unique_prefix(self, client_with_tools):
        """Tool names should be prefixed with mcp_{server}_{name}."""
        tools = client_with_tools.get_tools_for_agent()
        for t in tools:
            name = t["function"]["name"]
            assert name.startswith("mcp_")
            parts = name.split("_", 2)
            assert len(parts) == 3  # mcp, server_name, tool_name

    def test_tool_removed_with_server(self, client):
        """Removing a server should also remove its tools."""
        client._tools["server1:tool1"] = MCPTool(
            name="tool1", description="", input_schema={}, server_name="server1",
        )
        client.remove_server("server1")
        assert client.get_tools_for_agent() == []


# ═══════════════════════════════════════════════════════════
# 3. Tool Calling
# ═══════════════════════════════════════════════════════════


class TestToolCalling:
    """Calling tools on MCP servers."""

    @pytest.mark.asyncio
    async def test_call_tool_server_not_found(self, client):
        result = await client.call_tool("nonexistent", "tool", {})
        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_call_tool_server_no_transport(self, client):
        """A server with no command or url should return an error."""
        client.add_server("broken", command=None)
        result = await client.call_tool("broken", "tool", {})
        assert "error" in result.lower()


# ═══════════════════════════════════════════════════════════
# 4. Tool Discovery Process
# ═══════════════════════════════════════════════════════════


class TestToolDiscoveryProcess:
    """Discovering tools from servers (mocked)."""

    @pytest.mark.asyncio
    async def test_list_tools_discovery(self, client):
        """list_tools should attempt to discover from registered servers."""
        client.add_server("test", command=["python", "server.py"])

        with patch.object(client, "_discover_stdio", new=AsyncMock(return_value=[
            MCPTool(name="greet", description="Say hello",
                    input_schema={}, server_name="test"),
        ])):
            tools = await client.list_tools()

            assert len(tools) == 1
            assert tools[0].name == "greet"

    @pytest.mark.asyncio
    async def test_list_tools_failure_handling(self, client):
        """If a server fails to respond, list_tools should not crash."""
        client.add_server("failing", command=["python", "fail.py"])

        with patch.object(client, "_discover_stdio",
                          side_effect=RuntimeError("Connection refused")):
            tools = await client.list_tools()

            assert tools == []

    @pytest.mark.asyncio
    async def test_discovery_updates_connected_status(self, client):
        """Successful discovery should set connected=True."""
        client.add_server("good", command=["python", "good.py"])

        with patch.object(client, "_discover_stdio", new=AsyncMock(return_value=[
            MCPTool(name="ok", description="", input_schema={}, server_name="good"),
        ])):
            await client.list_tools()

            status = client.status()
            assert status["good"]["connected"] is True

    @pytest.mark.asyncio
    async def test_discovery_failure_sets_disconnected(self, client):
        """Failed discovery should set connected=False."""
        client.add_server("bad", command=["python", "bad.py"])

        with patch.object(client, "_discover_stdio",
                          side_effect=RuntimeError("fail")):
            await client.list_tools()

            status = client.status()
            assert status["bad"]["connected"] is False

    @pytest.mark.asyncio
    async def test_discover_sse_tools(self, client):
        """SSE-based discovery should work."""
        client.add_server("web", url="http://localhost:8080/sse")

        with patch.object(client, "_discover_sse", new=AsyncMock(return_value=[
            MCPTool(name="status", description="Get status",
                    input_schema={}, server_name="web"),
        ])):
            tools = await client.list_tools()

            assert len(tools) == 1

    @pytest.mark.asyncio
    async def test_discovery_caches_tools(self, client):
        """Tools should be cached after discovery."""
        client.add_server("cache-test", command=["echo"])

        with patch.object(client, "_discover_stdio", new=AsyncMock(return_value=[
            MCPTool(name="cached", description="", input_schema={}, server_name="cache-test"),
        ])):
            await client.list_tools()

        assert "cache-test:cached" in client._tools


# ═══════════════════════════════════════════════════════════
# 5. Error Handling & Edge Cases
# ═══════════════════════════════════════════════════════════


class TestErrorHandling:
    """Graceful handling of server failures."""

    @pytest.mark.asyncio
    async def test_discovery_timeout(self, client):
        """Timeout during discovery should not crash."""
        client.add_server("slow", command=["python", "slow.py"])

        with patch.object(client, "_discover_stdio",
                          side_effect=asyncio.TimeoutError):
            tools = await client.list_tools()

            assert tools == []
            status = client.status()
            assert status["slow"]["connected"] is False

    @pytest.mark.asyncio
    async def test_call_tool_error(self, client):
        """Failed tool call should return error message."""
        client.add_server("failing", command=["python", "fail.py"])

        with patch.object(client, "_call_stdio",
                          side_effect=RuntimeError("Something broke")):
            result = await client.call_tool("failing", "tool", {})

            assert "error" in result.lower()

    def test_status_reflects_connection(self, client):
        """Server status should show connected state."""
        cfg = MCPServerConfig(name="offline", command=["echo"])
        client._servers["offline"] = cfg
        status = client.status()
        assert status["offline"]["connected"] is False

    @pytest.mark.asyncio
    async def test_tool_discovery_no_servers(self, client):
        """list_tools with no servers should return empty list."""
        tools = await client.list_tools()
        assert tools == []


# ═══════════════════════════════════════════════════════════
# 6. MCPServerConfig
# ═══════════════════════════════════════════════════════════


class TestMCPServerConfig:
    """Transport configuration validation."""

    def test_stdio_requires_command(self):
        cfg = MCPServerConfig(name="stdio-server", command=["python", "serve.py"])
        assert cfg.command is not None
        assert cfg.url is None

    def test_sse_requires_url(self):
        cfg = MCPServerConfig(name="sse-server", url="http://localhost:8080/sse")
        assert cfg.url is not None
        assert cfg.command is None

    def test_env_variables(self):
        cfg = MCPServerConfig(
            name="with-env",
            command=["python", "run.py"],
            env={"TOKEN": "abc123", "URL": "http://api.example.com"},
        )
        assert cfg.env["TOKEN"] == "abc123"

    def test_timeout_default(self):
        cfg = MCPServerConfig(name="default-timeout", command=["echo"])
        assert cfg.timeout == 30.0

    def test_custom_timeout(self):
        cfg = MCPServerConfig(name="custom-timeout", command=["echo"], timeout=5.0)
        assert cfg.timeout == 5.0
