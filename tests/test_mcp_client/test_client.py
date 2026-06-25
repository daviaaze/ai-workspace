"""Tests for MCP Client — connect to external MCP servers."""

import pytest

from ai_workspace.mcp_client.client import MCPClient, MCPTool, MCPServerConfig


# ═══════════════════════════════════════════════════════════
# MCPTool
# ═══════════════════════════════════════════════════════════


class TestMCPTool:
    def test_creation(self):
        tool = MCPTool(
            name="get_weather",
            description="Get weather for a city",
            input_schema={"type": "object", "properties": {"city": {"type": "string"}}},
            server_name="weather",
        )
        assert tool.name == "get_weather"
        assert tool.server_name == "weather"

    def test_to_openai_tool(self):
        tool = MCPTool(
            name="get_weather",
            description="Get weather for a city",
            input_schema={"type": "object", "properties": {"city": {"type": "string"}}},
            server_name="weather",
        )
        openai = tool.to_openai_tool()
        assert openai["type"] == "function"
        assert openai["function"]["name"] == "mcp_weather_get_weather"
        assert "[MCP:weather]" in openai["function"]["description"]
        assert "city" in openai["function"]["parameters"]["properties"]

    def test_to_openai_tool_prefix(self):
        tool = MCPTool(
            name="query",
            description="Query database",
            input_schema={"type": "object", "properties": {}},
            server_name="mydb",
        )
        openai = tool.to_openai_tool()
        assert openai["function"]["name"] == "mcp_mydb_query"


# ═══════════════════════════════════════════════════════════
# MCPClient
# ═══════════════════════════════════════════════════════════


class TestMCPClient:
    def test_add_server_stdio(self):
        client = MCPClient()
        client.add_server("test", command=["python", "server.py"])
        status = client.status()
        assert "test" in status
        assert status["test"]["transport"] == "stdio"
        assert status["test"]["connected"] is False

    def test_add_server_sse(self):
        client = MCPClient()
        client.add_server("web", url="http://localhost:8080/sse")
        status = client.status()
        assert status["web"]["transport"] == "sse"

    def test_remove_server(self):
        client = MCPClient()
        client.add_server("temp", command=["echo"])
        client.remove_server("temp")
        assert "temp" not in client.status()

    def test_empty_tools_initially(self):
        client = MCPClient()
        tools = client.get_tools_for_agent()
        assert tools == []

    def test_status_empty(self):
        client = MCPClient()
        assert client.status() == {}

    def test_multiple_servers(self):
        client = MCPClient()
        client.add_server("s1", command=["echo"])
        client.add_server("s2", url="http://localhost:8080")
        status = client.status()
        assert len(status) == 2
        assert "s1" in status
        assert "s2" in status

    def test_call_tool_server_not_found(self):
        client = MCPClient()
        import asyncio
        result = asyncio.run(client.call_tool("nonexistent", "tool", {}))
        assert "not found" in result.lower()

    def test_get_tools_for_agent_format(self):
        client = MCPClient()
        # Manually add a tool to test format
        client._tools["weather:get_weather"] = MCPTool(
            name="get_weather",
            description="Get weather",
            input_schema={"type": "object", "properties": {}},
            server_name="weather",
        )
        tools = client.get_tools_for_agent()
        assert len(tools) == 1
        assert tools[0]["type"] == "function"
        assert "mcp_weather_get_weather" in tools[0]["function"]["name"]


class TestMCPServerConfig:
    def test_stdio_config(self):
        config = MCPServerConfig(
            name="test",
            command=["python", "server.py"],
            env={"KEY": "value"},
            timeout=10.0,
        )
        assert config.name == "test"
        assert config.command == ["python", "server.py"]
        assert config.env == {"KEY": "value"}
        assert config.timeout == 10.0

    def test_sse_config(self):
        config = MCPServerConfig(
            name="web",
            url="http://localhost:8080/sse",
        )
        assert config.url == "http://localhost:8080/sse"
        assert config.command is None
