# Spec: Agent as MCP Tool

> **Status:** 📋 Spec | **Data:** 2026-06-18 | **Refs:** fastmcp-agents (archived), MCP protocol, aiw mcp_server

---

## 🎯 Motivação

O aiw já tem um MCP server (`mcp_server/server.py`) que expõe tools estáticas (web_fetch, marketplace, scraper). Mas **o agente em si não é uma tool**. Isso significa:

- pi não pode spawnar um sub-agente aiw para pesquisar
- Não dá para compor agentes (um agente pesquisa, outro codifica)
- O TUI é a única interface para o agente — sem API programática

Padrão de referência: [fastmcp-agents](https://github.com/strawgate/fastmcp-agents) (archived Jan 2026). A ideia central:

> "Why teach every Agent how to use every tool? Embed an Expert user of the tools available on the Server, into the Server."

---

## 📐 Design

### Tool MCP: `aiw_agent_run`

Expõe o AgentOrchestrator como uma tool MCP padrão. Qualquer MCP client (pi, Claude, outro agente) pode chamar:

```json
// Request
{
  "method": "tools/call",
  "params": {
    "name": "aiw_agent_run",
    "arguments": {
      "task": "Pesquise as diferenças de performance entre Python e Rust em 2025",
      "agent_type": "research",
      "model": "qwen3:14b",
      "provider": "ollama",
      "stream": true
    }
  }
}
```

### Modos de resposta

**Modo `stream: false`** (default) — retorna resultado completo:
```json
{
  "content": [{"type": "text", "text": "Relatório completo da pesquisa..."}],
  "meta": {
    "confidence": 0.82,
    "sources": ["https://...", "https://..."],
    "iterations": 4,
    "duration_ms": 45230,
    "cost": 0.0,
    "tokens": {"input": 3200, "output": 1800}
  }
}
```

**Modo `stream: true`** — retorna NDJSON via `content[0].text` com eventos progressivos:
```
{"type":"phase","phase":"planning","message":"Generating research plan..."}
{"type":"plan","questions":["...","..."],"total":5}
{"type":"research_start","current":1,"question":"Core design..."}
...
{"type":"done","ok":true,"confidence":0.82}
```

### Tool MCP: `aiw_agent_status`

Consulta o estado de agentes em execução:

```json
// Request
{"method": "tools/call", "params": {"name": "aiw_agent_status", "arguments": {}}}

// Response
{
  "content": [{"type": "text", "text": "..."}],
  "meta": {
    "agents": [
      {"id": "agent-1", "status": "running", "task": "Pesquisar Rust vs Go", "iterations": 3, "model": "qwen3:14b"},
      {"id": "agent-2", "status": "idle", "task": null}
    ]
  }
}
```

### Tool MCP: `aiw_agent_kill`

Mata um agente em execução:

```json
{"method": "tools/call", "params": {"name": "aiw_agent_kill", "arguments": {"agent_id": "agent-1"}}}
```

---

## 🔧 Implementação

### Local: `src/ai_workspace/mcp_server/agent_tools.py` (novo)

Registra as tools no MCP server existente.

```python
"""MCP tools that expose the AI Workspace agent as a callable tool."""

from mcp.types import Tool, TextContent
from ai_workspace.agents.orchestrator import AgentOrchestrator, OrchestratorConfig
from ai_workspace.core.output import ndjson_event  # helper do SPEC_OUTPUT_MODES


async def aiw_agent_run(
    task: str,
    agent_type: str = "general",
    model: str = "qwen3:14b",
    provider: str = "ollama",
    stream: bool = False,
    session_id: str | None = None,
) -> list[TextContent]:
    """Run an AI Workspace agent to perform a task.
    
    Args:
        task: The task description in natural language
        agent_type: 'coding', 'research', or 'general'
        model: Model name (e.g., 'qwen3:14b', 'deepseek-chat')
        provider: 'ollama', 'deepseek', 'gemini', 'openrouter'
        stream: If true, returns NDJSON events as they happen
        session_id: Optional persistent session ID for context
    """
    config = OrchestratorConfig(
        model=model,
        provider=provider,
        agent_type=agent_type,
        session_id=session_id,
    )
    
    if stream:
        # Modo streaming: hook no on_step do AgentLoop
        events: list[str] = []
        
        async def on_event(event: dict):
            events.append(ndjson_event(**event))
        
        orch = AgentOrchestrator(sink=_make_mcp_sink(on_event), config=config)
        result = await orch.run(task)
        
        # Retorna todos os eventos NDJSON como um texto
        return [TextContent(
            type="text",
            text="\n".join(events + [ndjson_event(type="done", ok=True)])
        )]
    else:
        # Modo batch: resultado final
        orch = AgentOrchestrator(
            sink=_make_mcp_sink(),  # sink silencioso
            config=config,
        )
        result = await orch.run(task)
        stats = orch.get_stats()
        
        return [TextContent(
            type="text",
            text=result,
            meta={
                "confidence": getattr(result, "confidence", None),
                "iterations": stats["iterations"],
                "duration_ms": stats.get("duration_ms"),
            }
        )]


def register_agent_tools(mcp_server):
    """Register agent tools on an MCP server instance."""
    
    mcp_server.tool(
        name="aiw_agent_run",
        description="Run an AI agent to research, code, or perform general tasks. "
                    "The agent has access to web search, file system, git, and shell tools.",
    )(aiw_agent_run)
    
    mcp_server.tool(
        name="aiw_agent_status",
        description="Get status of all running AI Workspace agents.",
    )(aiw_agent_status)
    
    mcp_server.tool(
        name="aiw_agent_kill",
        description="Kill a running agent by ID.",
    )(aiw_agent_kill)
```

### Uso pelo pi

Uma vez exposto como MCP tool, qualquer agente pode chamar. Exemplo com pi:

```
Usuário: "pesquise a fundo Rust vs Go e me diga qual usar para uma CLI tool"

pi:
  🤔 Preciso de dados atualizados sobre performance e ecosystem
  🔧 aiw_agent_run(task="Compare Rust and Go for CLI tool development in 2025-2026",
                   agent_type="research", stream=true)
  👁 [recebe eventos NDJSON em tempo real]
  🤔 Confiança 0.82, 5 fontes. Vou sintetizar para o usuário.
  ✅ "Para CLI tools em 2026, recomendo Go se..."
```

---

## 🔗 Integração com o AgentLoop (Fase 2 do plano)

Quando o AgentLoop próprio estiver pronto (Fase 2), a tool MCP ganha superpoderes:

- **Callback por passo**: cada Thought → Action → Observation vira evento NDJSON
- **Controle de ciclo**: pause, resume, kill via MCP
- **Aprovação humana**: `aiw_agent_run` pode pausar e pedir permissão via MCP request
- **Multi-agente**: um agente spawna sub-agentes via MCP e gerencia o swarm

---

## ✅ Critérios de aceitação

- [ ] `aiw_agent_run` aparece em `aiw mcp list-tools` (ou equivalente)
- [ ] MCP client externo consegue chamar `aiw_agent_run` com uma task
- [ ] Modo `stream: false` retorna resultado completo com meta (confidence, sources, tokens)
- [ ] Modo `stream: true` retorna eventos NDJSON progressivos
- [ ] `aiw_agent_status` retorna agentes ativos com estado
- [ ] `aiw_agent_kill` mata agente por ID
- [ ] Agente executado via MCP respeita budget (não gasta mais que o limite)
- [ ] Agente executado via MCP respeita circuit breaker (para após N falhas)
- [ ] Erros retornam no formato MCP padrão (não quebram o server)
- [ ] Funciona com todos os providers (ollama, deepseek, gemini)

---

## 📚 Referências

- [fastmcp-agents](https://github.com/strawgate/fastmcp-agents) — padrão de embedar agente como MCP tool (archived Jan 2026)
- [FastMCP quickstart](https://github.com/jlowin/fastmcp/blob/main/docs/getting-started/quickstart.mdx) — como criar MCP server com tools em Python
- [MCP specification](https://modelcontextprotocol.io/) — protocolo de tools/resources/prompts
- `src/ai_workspace/mcp_server/server.py` — MCP server existente no aiw (tools estáticas)
- `src/ai_workspace/agents/orchestrator.py` — AgentOrchestrator a ser exposto
