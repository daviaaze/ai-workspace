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

from ai_workspace.mcp_client.client import MCPClient, MCPTool

__all__ = ["MCPClient", "MCPTool"]
