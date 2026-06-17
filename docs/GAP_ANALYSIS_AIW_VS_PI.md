# GAP Analysis — aiw vs pi

> **Atualizado:** 2026-06-16 (4 sessões de implementação)

## Pi Capabilities (target)

| # | Feature | Description | Status |
|---|---------|-------------|--------|
| 1 | Interactive persistent session | Multi-turn chat with memory, agent self-improves | ✅ DONE |
| 2 | Streaming token output | Real-time token-by-token response (not just prints) | ✅ DONE |
| 3 | Automatic tool selection | Auto-detects intent, picks right tools | ⚠️ PARTIAL |
| 4 | Permission/preview system | Shows file edits before applying, asks for approval | ✅ DONE |
| 5 | Safe execution sandbox | Shell runs in sandbox, git changes reversible | ⚠️ PARTIAL |
| 6 | Multi-agent orchestration | Can delegate subtasks to specialized agents | ⚠️ PARTIAL |
| 7 | Context awareness | Understands project structure, git state, open files | ✅ DONE |
| 8 | Model fallback/retry | Tries different providers/models on failure | ✅ DONE |
| 9 | Session persistence | Remembers across restarts, restores state | ⚠️ PARTIAL |
| 10 | MCP server integration | Connects to external MCP tool servers | ❌ MISSING |

## AIW Current State

| # | Feature | Status | Implementation |
|---|---------|--------|---------------|
| 1 | Interactive persistent session | ✅ | `MessageQueue` + `AgentWorker._agent_loop()` + `PersistentAgentSession.start_loop()` — loop contínuo com fila de mensagens, priority system, interrupt (!), acumulação de contexto |
| 2 | Streaming token output | ✅ | `tui/streaming.py` — monkey-patch `litellm.completion` com `stream=True`, tokens fluem para `AgentLane` em tempo real |
| 3 | Automatic tool selection | ⚠️ | Agente crewAI com 18+ ferramentas, modelo escolhe quais usar |
| 4 | Permission/preview system | ✅ | `PermissionGate` + `PermissionModal` + polling 0.5s — diff preview, approve/deny/always, integração CLI+TUI |
| 5 | Safe execution sandbox | ⚠️ | `shell_exec` sandboxed, `edit_file` com preview via PermissionGate |
| 6 | Multi-agent orchestration | ⚠️ | Worktrees isolam agentes, `AgentOrchestrator` unifica pipeline; falta `delegate()` tool |
| 7 | Context awareness | ✅ | `ContextBundle` (git, tree, language) + `ContextManager` (token budget, pin/exclude, snapshots) + `ContextWorkbench` (Ctrl+E, estilo Obsidian graph) |
| 8 | Model fallback/retry | ✅ | `SmartRouter` + `_execute_with_fallback()` — até 3 tentativas com fallback chain (ollama → ollama → deepseek API) |
| 9 | Session persistence | ⚠️ | `SessionStore` (PostgreSQL) + compactação + export JSONL; falta persistir estado do TUI |
| 10 | MCP server integration | ⚠️ | Framework MCP instalado, expõe 11+ tools (read_file, write_file, shell, tests, lint, knowledge search, UI tools) |
| 11 | **Budget enforcement** | ✅ | `BudgetEnforcer` + `CircuitBreaker` — per-call ($0.01), daily ($1.00), monthly ($10.00) limits, per-provider circuit breakers |
| 12 | **Skill system** | ✅ | `SkillLoader` — descobre e executa skills de `pi-setup/skills/`, `~/.agents/skills/`. 13 skills: debug, feature-dev, commit, create-pr, desloppify, pre-review, nixfiles, deep-research, etc. |

### Extras (além do pi)

| # | Feature | Status | Description |
|---|---------|--------|-------------|
| 13 | AgentOrchestrator + StreamSink | ✅ | Pipeline unificado para CLI, TUI, Dashboard, MCP — `StreamSink` protocol com 4 implementações |
| 14 | Context Workbench (observabilidade) | ✅ | Visualização estilo Obsidian da janela de contexto, token budget, pin/exclude, snapshots |
| 15 | Semantic cache (pgvector HNSW) | ✅ | Cache semântico com dual embedding (Ollama nomic-embed-text + sentence-transformers), hash lookup + cosine similarity |

## Implementation Status (2026-06-16)

### ✅ Phase 1 — Interactive Persistent Session (DONE)
- `MessageQueue` (async/thread-safe, priority levels 0-10+, interrupt flag)
- `AgentWorker._agent_loop()` — loop contínuo com dequeue → executa → acumula → check queue
- `PersistentAgentSession.start_loop()` + `enqueue()` — mesmo padrão no CLI
- `send_message(priority=10+)` — zera contexto acumulado, restart fresco
- `!` prefix no TUI → interrupt
- AgentLane mostra `📨N` quando há mensagens pendentes

### ✅ Phase 2 — Streaming Token Output (DONE)
- `tui/streaming.py` — monkey-patch `litellm.completion` com `stream=True`
- Captura cada token chunk → `queue.put_nowait()` → AgentLane renderiza em tempo real
- MockResponse wrapper mantém compatibilidade com crewAI
- Ativado/desativado automaticamente em `_run_crew_sync()`

### ✅ Phase 3 — Permission/Preview System (DONE)
- `PermissionGate` — analisa tool calls, identifica operações perigosas
- `PermissionModal` — mostra diff/command preview, teclas a/A/d
- `_poll_permissions()` — polling 0.5s detecta `worker.pending_permission`
- `PermissionRequest.resolve()` — veredicto flui de volta para worker thread
- `action_view_permissions()` (Ctrl+P) — mostra permissão pendente sob demanda
- Integração CLI via `CLIStreamSink.request_permission()`

### ✅ Phase 4 — Context Awareness (DONE)
- `ContextBundle` — git branch, status, tree, language, recent files
- `ContextManager` — 480 linhas: CRUD de blocos, token budget, pin/exclude, snapshots
- `ContextWorkbench` — 380 linhas: tree view, budget bar, detail panel, Ctrl+E
- `add_block_sync()` — thread-safe, chamado de dentro do worker thread
- Integração em `AgentWorker._run_crew_sync()` e `PersistentAgentSession.send()`
- `AgentOrchestrator._inject_project_context()` — usa ContextBundle

### ✅ Phase 5 — Smart Router / Model Fallback (DONE)
- `SmartRouter` — seleciona melhor modelo por tipo de tarefa + complexidade
- `_execute_with_fallback()` — até 3 tentativas com fallback chain
- `router.fallback(decision)` — desabilita modelo que falhou, tenta próximo
- `router.mark_success()` — aprende quais modelos funcionam
- Integrado no `AgentOrchestrator._execute()`

### ⚠️ Phase 6 — Session Persistence (BACKEND DONE, TUI PENDING)
- ✅ `SessionStore` (PostgreSQL) — CRUD de sessões, mensagens, compactações
- ✅ Auto-compactação quando contexto excede budget
- ✅ Export JSONL (compatível com pi)
- ❌ Persistir estado do TUI (lanes, outputs, task status) ao fechar/abrir

### ❌ Phase 7 — MCP Integration (PENDING)
- Framework MCP instalado mas não integrado ao AgentWorker/Orchestrator
- `MCPStreamSink` já existe no orchestrator para output

### ❌ Phase 8 — Multi-Agent with Delegation (PENDING)
- `AgentOrchestrator` unifica pipeline mas não tem `delegate()` tool ainda
- Worktrees existem para isolamento


## Architecture (implemented)

```
┌─────────────────────────────────────────────────────────────────┐
│                   AgentOrchestrator (unified pipeline)           │
│                                                                  │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐ │
│  │ Context  │   │ Session  │   │ Message  │   │ Permissions  │ │
│  │ Bundle   │   │ Store    │   │ Queue    │   │ Gate         │ │
│  │ (git,    │   │ (PG,     │   │ (prio,   │   │ (preview,    │ │
│  │  tree,   │   │  compact)│   │  int.)   │   │  approve)    │ │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘   └──────┬───────┘ │
│       │              │              │                 │          │
│       └──────────────┴──────────────┴─────────────────┘          │
│                              │                                    │
│       ┌──────────────────────┼──────────────────────┐            │
│       │                      │                      │            │
│  ┌────▼────┐   ┌────────────▼───┐   ┌──────────────▼────────┐  │
│  │ Smart   │   │  LLM Execution  │   │  ContextManager       │  │
│  │ Router  │   │  (streaming,    │   │  (token budget,       │  │
│  │ (select │   │   fallback)     │   │   pin/exclude,        │  │
│  │  + retry│   │                 │   │   snapshots)           │  │
│  └────┬────┘   └───────┬─────────┘   └───────────┬───────────┘  │
│       │                │                         │               │
│       └────────────────┼─────────────────────────┘               │
│                        │                                          │
│              ┌─────────▼─────────┐                               │
│              │   StreamSink      │                               │
│              │   ├ CLIStreamSink │ (Rich terminal)               │
│              │   ├ TUIStreamSink │ (AgentLane)                   │
│              │   ├ MCPStreamSink │ (JSON-RPC)                    │
│              │   └ DashSink      │ (WebSocket)                   │
│              └───────────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Status

| Session | Phase | Deliverable | Status |
|---------|-------|-------------|--------|
| 1 | 1 | MessageQueue + Agent Loop + PersistentAgentSession | ✅ |
| 1 | 7 | ContextBundle + ContextManager + ContextWorkbench | ✅ |
| 2 | 2 | Token streaming (monkey-patch litellm) | ✅ |
| 2 | 3 | PermissionGate + PermissionModal + polling | ✅ |
| 2 | 5 | SmartRouter + _execute_with_fallback() | ✅ |
| 3 | — | AgentOrchestrator + StreamSink protocol | ✅ |
| Next | 6 | TUI state persistence | ⚪ |
| Next | 7 | MCP integration | ⚪ |
| Next | 8 | Multi-agent delegation | ⚪ |
