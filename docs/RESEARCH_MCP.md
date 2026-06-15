# AI Workspace — Research Report: Agent & MCP Improvements

**Date:** 2026-06-15
**Source:** GitHub search, code_search, fetch_content on upstream docs

---

## Key Finding: CrewAI now has Native MCP DSL

crewAI 1.14+ ships native MCP integration — **no `MCPServerAdapter` needed**. This is a game-changer for our architecture.

### The new `mcps` field on Agents

```python
from crewai import Agent
from crewai.mcp import MCPServerStdio, MCPServerHTTP, MCPServerSSE

agent = Agent(
    role="Research Analyst",
    goal="Find and analyze information",
    backstory="Expert researcher",
    mcps=[
        # String reference (quick setup)
        "https://api.example.com/mcp",
        
        # Stdio transport for local servers
        MCPServerStdio(
            command="python",
            args=["aiw_mcp_server.py"],
            env={"AIW_DB_URL": "..."},
        ),
        
        # HTTP transport for remote servers
        MCPServerHTTP(
            url="https://homelab:8746/mcp",
            headers={"Authorization": "Bearer token"},
        ),
        
        # SSE transport for streaming
        MCPServerSSE(
            url="https://homelab:8746/mcp/sse",
        ),
    ]
)
```

**Impact on our architecture:**
- Our `swarm.py` agents can directly import `aiw` MCP tools — no adapter needed
- The pi extension approach is still right for pi, but for CrewAI agents, MCP is the native path
- We should build ONE MCP server that serves BOTH pi (via extension → CLI → MCP) AND CrewAI agents (direct `mcps` field)

---

## Projects to Study / Copy From

### 1. CrewAI + MCP Integration Example (nawazahmad20/mcp_example)
⭐ 0 | 🐳 Docker | Python

**Architecture:**
```
CrewAI Agent + MCPServerAdapter → HTTP/MCP → FastMCP Server
```

**What to copy:**
- `mcp_tool_schema_patch.py` — fixes CrewAI's dynamic schemas to Pydantic models for LLM compatibility
- `llm_factory.py` — multi-provider LLM setup pattern
- Docker Compose setup for MCP server + client

**Key insight:** MCP tools need schema patching because CrewAI's `MCPServerAdapter` generates schemas that some LLM providers (Anthropic, OpenAI) reject. The patcher converts them to standard Pydantic models.

### 2. MCPAdapt (grll.github.io/mcpadapt)
Documentation library | Python

**What it does:** Adapts MCP tools to various agent frameworks (CrewAI, LangChain, etc.)

**CrewAI adapter pattern:**
```python
from mcpadapt.core import MCPAdapt
from mcpadapt.crewai_adapter import CrewAIAdapter

with MCPAdapt(
    StdioServerParameters(command="uv", args=["run", "server.py"]),
    CrewAIAdapter(),
) as tools:
    agent = Agent(tools=[tools[0]], ...)
```

**Status:** PR underway to integrate directly into CrewAI's framework.

### 3. ATLAS MCP Server (cyanheads/atlas-mcp-server)
⭐ 477 | TypeScript | Neo4j

**What it does:** Project → Task → Knowledge management system for LLM agents, exposed as MCP server. Three-tier architecture.

**What to copy:**
- **Tool organization pattern** — each tool has its own directory with `index.ts`, `types.ts`, `responseFormat.ts`
- **Deep research integration** — `atlas_deep_research` tool
- **Unified search** — cross-entity search across projects, tasks, knowledge
- **Backup/restore** — full database backup and import via JSON
- **Web UI** — experimental web interface alongside MCP
- **Authentication middleware** for HTTP transport
- **Rate limiting** and **token counting** utilities

**Architecture pattern:**
```
MCP Server (stdio + HTTP transports)
├── Tools (22 tools!)
│   ├── atlas_project_create/list/update/delete
│   ├── atlas_task_create/list/update/delete
│   ├── atlas_knowledge_add/list/delete
│   ├── atlas_unified_search
│   ├── atlas_deep_research
│   └── atlas_database_clean
├── Resources (graph-based)
└── Services (Neo4j driver, search, backup)
```

### 4. Other MCP + knowledge base projects

| Project | Stars | DB | Notable |
|---------|-------|-----|---------|
| sdimitrov/mcp-memory | 62 | pgvector | Direct PostgreSQL MCP memory |
| byte5ai/palaia | 18 | pgvector/SQLite | Multi-agent, auto-capture memory |
| Eshaan-Nair/ArcRift | 230 | SQLite | Cross-agent context sync |
| willynikes2/knowledge-base-server | 170 | SQLite | Obsidian sync, self-learning |
| VioletCranberry/coco-search | 32 | pgvector | Code search with hybrid RRF |

---

## How this changes our MCP Server design

### Before (our initial plan):
```
aiw MCP Server → FastMCP
  ├── search_knowledge
  ├── deep_research
  └── remember
```

### After (incorporating learnings):
```
aiw MCP Server → FastMCP
  ├── Tools (copy ATLAS pattern)
  │   ├── aiw_knowledge_search (vector + text hybrid)
  │   ├── aiw_knowledge_add
  │   ├── aiw_deep_research (streaming progress via SSE)
  │   ├── aiw_memory_recall
  │   ├── aiw_memory_remember
  │   ├── aiw_task_create/list/update
  │   ├── aiw_web_fetch
  │   ├── aiw_headless_browser
  │   ├── aiw_mercado_livre
  │   ├── aiw_olx
  │   ├── aiw_paginated_scraper
  │   ├── aiw_telemetry
  │   └── aiw_unified_search (cross-entity)
  ├── Resources
  │   ├── knowledge://entries/{id}
  │   ├── research://history/{id}
  │   └── tasks://pending
  ├── Transports
  │   ├── stdio (for local)
  │   ├── HTTP streamable (for remote/Tailscale)
  │   └── SSE (for streaming progress)
  └── Utilities (copy from ATLAS)
      ├── Authentication middleware
      ├── Rate limiting
      └── Token counting
```

### CrewAI integration path (new!):
```python
# swarm.py — agents get MCP tools natively
from crewai.mcp import MCPServerHTTP

researcher = Agent(
    role="Research Specialist",
    goal="Conduct thorough research",
    backstory="Senior research analyst",
    mcps=[
        MCPServerHTTP(
            url="http://localhost:8746/mcp",
        ),
    ],
    # Now has: aiw_web_fetch, aiw_deep_research, aiw_knowledge_search, etc.
)
```

### Pi integration path (unchanged):
Pi extension → spawns `aiw` CLI → CLI talks to same MCP server

---

## Action items

### Phase 1: Build the MCP server (1-2 days)
1. Create `src/ai_workspace/mcp_server.py` using FastMCP
2. Expose all existing tools as MCP tools
3. Add unified search (cross-entity, copy ATLAS pattern)
4. Add HTTP + stdio transports

### Phase 2: Upgrade CrewAI agents to use MCP (1 day)
5. Replace hardcoded `tools=[WebFetchTool(), ...]` in `workflows.py` with `mcps=[MCPServerStdio(...)]`
6. This makes agents use the same MCP server — tool improvements propagate everywhere

### Phase 3: Schema patching for compatibility (few hours)
7. Copy `mcp_tool_schema_patch.py` pattern for Anthropic/OpenAI compatibility
8. Test with DeepSeek API (already working) + Ollama

### Phase 4: Pi streaming (1 day)
9. Replace `execSync` with `spawn` in pi extension
10. Pipe MCP/CLI output to `onUpdate` callbacks for live progress

---

## Useful references

| Resource | URL |
|----------|-----|
| CrewAI MCP DSL docs | https://docs.crewai.com/en/mcp/overview |
| MCP example repo | https://github.com/nawazahmad20/mcp_example |
| MCPAdapt | https://grll.github.io/mcpadapt/guide/crewai/ |
| ATLAS MCP server | https://github.com/cyanheads/atlas-mcp-server |
| mcp-memory (pgvector) | https://github.com/sdimitrov/mcp-memory |
| thekeystoneproject/stonegate | https://github.com/thekeystoneproject/stonegate |
