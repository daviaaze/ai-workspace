# Spec: Integration — How Everything Connects

> **Status:** 📋 Spec | **Data:** 2026-06-18
> **Dependências:** SPEC_AGENT_LOOP, SPEC_OUTPUT_MODES, SPEC_ERROR_HANDLING, SPEC_TUI_V5, SPEC_RAG, SPEC_AGENT_MCP_TOOL

---

## 🎯 Objetivo

Mostrar como as 6 specs se conectam entre si e com o código existente. Este documento é o "mapa" — cada seta é uma dependência ou fluxo de dados.

---

## 📐 Arquitetura de alto nível

```
                         ┌──────────────────┐
                         │     CLI (typer)   │
                         │  aiw ask|agent|   │
                         │  search|tui|kb    │
                         └────────┬─────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                    ▼             ▼             ▼
          ┌─────────────┐ ┌───────────┐ ┌───────────┐
          │ Output       │ │ AgentLoop │ │ TUI v5    │
          │ Formatter    │ │ (core)    │ │ (Textual) │
          │ (SPEC_OUTPUT)│ │ (SPEC_LOOP)│ │ (SPEC_TUI) │
          └──────┬───────┘ └─────┬─────┘ └─────┬─────┘
                 │               │             │
                 │    ┌──────────┼──────────┐  │
                 │    │          │          │  │
                 ▼    ▼          ▼          ▼  ▼
          ┌────────────────────────────────────────┐
          │            Providers Layer              │
          │  ollama │ deepseek │ gemini │ openrouter│
          │  (código existente: providers/ + router) │
          └────────────────────────────────────────┘
                 │          │          │
                 ▼          ▼          ▼
          ┌────────────────────────────────────────┐
          │              Data Layer                 │
          │  PostgreSQL + pgvector (RAG, sessions,  │
          │  telemetry, budget, cache)              │
          └────────────────────────────────────────┘
                 │
                 ▼
          ┌────────────────────────────────────────┐
          │            External APIs                │
          │  MCP Server │ REST │ WebSocket          │
          │  (SPEC_AGENT_MCP_TOOL)                  │
          └────────────────────────────────────────┘
```

---

## 🔗 Conexão 1: AgentLoop ↔ Providers (código existente)

O `AgentLoop` não chama APIs diretamente. Ele usa a camada de providers existente (`providers/__init__.py`).

```python
# src/ai_workspace/agents/loop.py

async def _call_model_stream(messages: list[dict], params: LoopParams) -> AsyncGenerator:
    """Chama o modelo via camada de providers existente."""
    from ai_workspace.providers import ProviderRegistry
    
    registry = ProviderRegistry()
    provider = registry.get(params.provider)  # ← código existente
    model = params.model
    
    # Streaming nativo via httpx (substitui monkey-patching atual)
    async for chunk in provider.stream_chat(
        model=model,
        messages=messages,
        temperature=params.temperature,
        tools=params.tools,
    ):
        yield _parse_chunk(chunk, params)
```

**O que muda:** O streaming atual usa monkey-patching (`tui/streaming.py`). O novo AgentLoop chama o streaming nativo do provider via `provider.stream_chat()`.

**Arquivo afetado:** `providers/__init__.py` — adicionar método `stream_chat()`

---

## 🔗 Conexão 2: AgentLoop ↔ Orchestrator (substituição)

O `AgentOrchestrator` atual delega para `crew.kickoff()`. O novo delegará para `agent_loop()`.

```python
# src/ai_workspace/agents/orchestrator.py (REFATORADO)

class AgentOrchestrator:
    """Unified agent execution — agora usa AgentLoop próprio."""
    
    async def run(self, task: str, agent_type: str | None = None) -> str:
        pattern = self._pick_pattern(task, agent_type)
        tools = self._get_tools(agent_type)
        
        params = LoopParams(
            task=task,
            pattern=pattern,
            tools=tools,
            model=self.config.model,
            provider=self.config.provider,
            system_prompt=self._build_system_prompt(agent_type),
            messages=self._load_session_messages(),
            on_step=self._on_loop_event,  # ← alimenta TUI
        )
        
        # Executa o loop
        result_text = []
        async for event in agent_loop(params):
            if event.type == "token":
                await self.sink.emit_token(event.data["text"])
                result_text.append(event.data["text"])
            elif event.type == "thinking":
                await self.sink.emit_thinking(event.data["thought"])
            elif event.type == "tool_call":
                await self.sink.emit_tool_call(event.data["tool"], event.data["args"])
            elif event.type == "tool_result":
                await self.sink.emit_tool_result(event.data["tool"], event.data["result"])
        
        result = "".join(result_text)
        return result
    
    def _pick_pattern(self, task: str, agent_type: str) -> LoopPattern:
        """Escolhe o melhor padrão de loop."""
        if agent_type == "coding":
            return LoopPattern.REACT
        elif agent_type == "research":
            if _has_independent_subtasks(task):
                return LoopPattern.REWOO
            return LoopPattern.PLAN_EXECUTE
        else:
            return suggest_pattern(task, self._get_tools(agent_type))
    
    def _get_tools(self, agent_type: str) -> list:
        """Tool registry unificado."""
        tools = []
        
        # Tools base (sempre disponíveis)
        tools.append(RetrieveKnowledgeTool())  # ← SPEC_RAG
        
        if agent_type == "coding":
            tools.extend([ReadFileTool(), WriteFileTool(), ShellTool(), GitTool()])
        elif agent_type == "research":
            tools.extend([WebSearchTool(), WebFetchTool(), Crawl4AITool()])
        
        return tools
```

**Arquivos afetados:**
- `agents/orchestrator.py` — refatorar para usar AgentLoop
- `agents/swarm.py` — remover dependência de crewAI (ou manter como opcional)
- `tui/worker.py` — usar AgentOrchestrator refatorado

---

## 🔗 Conexão 3: AgentLoop ↔ TUI v5

O TUI se inscreve como observer do loop via callback.

```python
# src/ai_workspace/tui/app.py (TUI v5)

class AIWorkspaceApp(App):
    
    async def spawn_agent(self, task: str):
        # Criar lane visual
        lane = self.conversation.add_agent_lane(f"agent-{self._next_id}")
        
        # Configurar loop
        params = LoopParams(
            task=task,
            tools=self._get_tools_from_config(),
            stream=True,
            on_step=self._on_agent_step,  # ← callback
        )
        
        # Rodar em background thread
        self._loop_task = asyncio.create_task(self._run_loop(params, lane))
    
    async def _run_loop(self, params: LoopParams, lane):
        async for event in agent_loop(params):
            self._on_agent_step(event, lane)
    
    def _on_agent_step(self, event: LoopEvent, lane):
        """Cada evento do loop atualiza a UI."""
        match event.type:
            case "thinking":
                self.agent_monitor.update(lane.id, thought=event.data["thought"])
                lane.add_step("🤔", event.data["thought"])
            case "tool_call":
                self.agent_monitor.update(lane.id, action=event.data["tool"])
                lane.add_step("🔧", f"{event.data['tool']}({event.data['args']})")
            case "tool_result":
                self.agent_monitor.update(lane.id, observation="done")
                lane.add_step("👁", event.data["result"][:200])
            case "token":
                lane.append_token(event.data["text"])
            case "error":
                lane.add_error(event.data)
```

**Arquivos criados:**
- `tui/agent_monitor.py` — NOVO (substitui widgets.py AgentLane)
- `tui/conversation.py` — NOVO (evolui chat.py)
- `tui/input_bar.py` — NOVO

**Arquivos removidos/movidos:**
- 15 arquivos TUI mortos → `tui/_graveyard/`

---

## 🔗 Conexão 4: AgentLoop ↔ MCP Server

O AgentLoop é exposto como MCP tool.

```python
# src/ai_workspace/mcp_server/agent_tools.py (NOVO)

async def aiw_agent_run(
    task: str,
    agent_type: str = "general",
    model: str = "qwen3:14b",
    provider: str = "ollama",
    stream: bool = False,
) -> list[TextContent]:
    """MCP tool: run AI agent."""
    
    params = LoopParams(
        task=task,
        pattern=suggest_pattern(task, []),
        model=model,
        provider=provider,
        stream=stream,
    )
    
    if stream:
        # Modo NDJSON streaming (SPEC_OUTPUT_MODES)
        events = []
        async for event in agent_loop(params):
            events.append(json.dumps({"type": event.type, "data": event.data}))
        return [TextContent(type="text", text="\n".join(events))]
    else:
        # Modo batch
        result = []
        async for event in agent_loop(params):
            if event.type == "token":
                result.append(event.data["text"])
        return [TextContent(type="text", text="".join(result))]
```

**Arquivos afetados:** `mcp_server/server.py` — registrar novas tools

---

## 🔗 Conexão 5: CLI ↔ Output Modes

Todo comando CLI ganha `--output json|ndjson`.

```python
# src/ai_workspace/cli.py (REFATORADO)

@app.callback()
def main(
    ctx: typer.Context,
    output: Annotated[str, typer.Option("--output", "-o")] = "rich",
):
    ctx.obj["output"] = output

@app.command()
def health(ctx: typer.Context):
    mode = ctx.obj["output"]
    
    # Coleta dados (mesmo código para todos os modos)
    providers = _collect_providers()
    cache = _collect_cache()
    budget = _collect_budget()
    
    if mode == "rich":
        _print_health_rich(providers, cache, budget)
    elif mode == "json":
        envelope = OutputEnvelope(ok=True, command="health", data={
            "providers": providers, "cache": cache, "budget": budget
        })
        print(json.dumps(envelope.to_dict(), indent=2))
    elif mode == "ndjson":
        for p in providers:
            _emit_ndjson({"type": "provider", **p})
        _emit_ndjson({"type": "cache", **cache})
        _emit_ndjson({"type": "done", "ok": True})

@app.command()
def search(query: str, ctx: typer.Context):
    mode = ctx.obj["output"]
    
    if mode == "rich":
        _print_search_progress_rich(query)
    # ... (similar para json/ndjson)
```

**Arquivos criados:** `core/output.py`

---

## 🔗 Conexão 6: Error Handling em todos os níveis

```python
# src/ai_workspace/core/result.py (NOVO)

@dataclass
class AiWError:
    code: str        # ErrorCode.PROVIDER_OFFLINE, etc.
    message: str
    detail: str = ""
    recoverable: bool = True
    suggestion: str = ""

type Result[T] = Success[T] | Failure[AiWError]

# Uso no AgentLoop:
async def agent_loop(params: LoopParams):
    try:
        stream = await provider.stream_chat(...)
    except ProviderOfflineError as e:
        yield LoopEvent(type="error", data=AiWError(
            code=ErrorCode.PROVIDER_OFFLINE,
            message=f"Provider {params.provider} is offline",
            detail=str(e),
            recoverable=True,
            suggestion=f"Try: ollama pull {params.model}",
        ))
        return TerminalReason.MODEL_ERROR

# Uso no CLI:
match result:
    case Success(value):
        envelope = OutputEnvelope(ok=True, data=value)
    case Failure(error):
        envelope = OutputEnvelope(ok=False, error={
            "code": error.code, "message": error.message,
            "recoverable": error.recoverable, "suggestion": error.suggestion,
        })

# Uso no TUI:
def _on_agent_step(self, event: LoopEvent):
    if event.type == "error":
        self.conversation.add_error_card(event.data)  # card vermelho com sugestão
```

---

## 📁 Mapa de arquivos: o que muda

```
src/ai_workspace/
├── agents/
│   ├── loop.py              🆕 AgentLoop (substitui crewAI)
│   ├── loop_patterns.py     🆕 Direct, ReAct, Plan-Execute, ReWOO
│   ├── orchestrator.py      ♻️ Refatorado: usa AgentLoop
│   ├── swarm.py             🗑️ Remover dependência de crewAI
│   ├── context.py           ✅ Mantido
│   ├── context_manager.py   ✅ Mantido
│   ├── session.py           ✅ Mantido
│   ├── router.py            ♻️ Simplificado
│   └── message_queue.py     ✅ Mantido
│
├── core/
│   ├── output.py            🆕 OutputFormatter (SPEC_OUTPUT_MODES)
│   ├── result.py            🆕 Result, Success, Failure, AiWError
│   ├── cost.py              ♻️ Adicionar métricas de erro
│   └── sessions.py          ✅ Mantido
│
├── knowledge/
│   ├── rag.py               🆕 DocumentIndexer + KnowledgeRetriever
│   └── store.py             ♻️ Adicionar schema RAG
│
├── mcp_server/
│   ├── agent_tools.py       🆕 aiw_agent_run, aiw_agent_status, aiw_agent_kill
│   └── server.py            ♻️ Registrar novas tools
│
├── providers/
│   ├── __init__.py          ♻️ Adicionar stream_chat()
│   └── ...
│
├── tui/
│   ├── app.py               ♻️ Refatorado: Router pattern, AgentLoop callback
│   ├── agent_monitor.py     🆕 Barra colapsável de agentes
│   ├── conversation.py      🆕 Chat + agent steps (evolui chat.py)
│   ├── input_bar.py         🆕 Input + slash commands
│   ├── help_bar.py          🆕 Barra de atalhos contexto-sensitive
│   ├── overlays/            🆕 ChatScreen, DashboardScreen, FileBrowser, etc.
│   ├── _graveyard/          🗑️ 15 arquivos mortos movidos
│   │   ├── agent_grid.py
│   │   ├── agent_inventory.py
│   │   ├── dashboard.py
│   │   ├── ... (12 outros)
│   └── widgets.py           ♻️ Mantido (PermissionModal, Toast)
│
├── cli.py                   ♻️ Adicionar --output, novos comandos (kb)
│
└── search/
    └── deep_search.py       🗑️ Remover (substituído por AgentLoop + tools)
```

---

## 🔄 Fluxo completo de uma interação

```
Usuário digita "fix the auth middleware bug" no TUI
  │
  ▼
TUI: spawn_agent(task) → cria LoopParams
  │
  ▼
AgentLoop: suggest_pattern() → LoopPattern.REACT (coding task)
  │
  ▼
AgentLoop: carrega tools (ReadFile, WriteFile, Shell, Git, RetrieveKnowledge)
  │
  ▼
AgentLoop: chama provider.stream_chat() → tokens chegam
  │  │
  │  ├─→ TUI: on_step("token") → conversation.append_token()
  │  ├─→ TUI: on_step("thinking") → agent_monitor.update(thought=...)
  │  └─→ Output: se --output ndjson → emite linha JSON
  │
  ▼
AgentLoop: modelo decide tool call → "read_file('src/auth.py')"
  │
  ▼
AgentLoop: executa tool → resultado
  │  │
  │  ├─→ TUI: on_step("tool_call") → lane.add_step("🔧", "read_file")
  │  └─→ TUI: on_step("tool_result") → lane.add_step("👁", preview)
  │
  ▼
AgentLoop: alimenta resultado de volta ao modelo
  │
  ▼
... (repetir até terminar) ...
  │
  ▼
AgentLoop: retorna TerminalReason.COMPLETED
  │
  ▼
TUI: agent_monitor.collapse() (se último agente terminou)
  │
  ▼
CLI: envelope JSON/NDJSON com resultado final
```

---

## 📋 Ordem de implementação

```
Fase 1: Fundações (2-3 dias)
  ├── 1. core/output.py        (OutputFormatter)
  ├── 2. core/result.py        (Result, AiWError)
  ├── 3. agents/loop.py        (AgentLoop + 4 padrões)
  └── 4. providers: stream_chat()

Fase 2: Substituição (2-3 dias)
  ├── 5. agents/orchestrator.py refatorado
  ├── 6. cli.py: --output em todos os comandos
  └── 7. tui/worker.py adaptado

Fase 3: RAG (2 dias)
  ├── 8. knowledge/rag.py      (index + retrieve)
  └── 9. AgentLoop: registrar RetrieveKnowledgeTool

Fase 4: TUI v5 (3-4 dias)
  ├── 10. tui/app.py refatorado
  ├── 11. tui/agent_monitor.py
  ├── 12. tui/conversation.py
  ├── 13. tui/input_bar.py + help_bar.py
  └── 14. tui/overlays/

Fase 5: MCP + Polish (1-2 dias)
  ├── 15. mcp_server/agent_tools.py
  ├── 16. Limpeza do repo
  └── 17. Documentação + CHANGELOG
```

---

## ✅ Critérios de aceitação (integração)

- [ ] `aiw ask "hello"` funciona com AgentLoop (Direct mode)
- [ ] `aiw agent "fix bug"` funciona com AgentLoop (ReAct mode)
- [ ] `aiw search "query"` funciona com AgentLoop + web tools
- [ ] `aiw search "query" -o ndjson` emite eventos em tempo real
- [ ] `aiw health -o json` retorna JSON válido
- [ ] `aiw tui` mostra AgentMonitor + Conversation com passos do loop
- [ ] `aiw kb index` indexa workspace no pgvector
- [ ] Agente usa `retrieve_knowledge` antes de responder perguntas sobre o código
- [ ] MCP server expõe `aiw_agent_run` como tool
- [ ] Erros são estruturados (AiWError com code + suggestion)
- [ ] 15 arquivos TUI mortos removidos
- [ ] crewAI é opcional, não obrigatório
