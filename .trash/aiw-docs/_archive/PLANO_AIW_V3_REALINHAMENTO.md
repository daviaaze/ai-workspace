# AI Workspace v0.2 — Plano de Realinhamento

> **Status:** Rascunho para validação
> **Data:** 2026-06-18
> **Problema:** Planos anteriores desalinhados com padrões reais de agent loop, RAG e TUI.

---

## Diagnóstico: O que está quebrado e por quê

### 1. Agent Loop — crewAI é uma caixa preta frágil

```python
# crewai/agents/crew_agent_executor.py — o loop real:
def _invoke_loop(self):
    if use_native_tools:
        return self._invoke_loop_native_tools()
    return self._invoke_loop_react()  # ← ReAct text-based pattern
```

**Problemas:**
- O loop de agente REAL está enterrado dentro do crewAI (`_invoke_loop_react`), inacessível ao nosso código
- Nosso `AgentOrchestrator` é um wrapper que não controla o loop — só chama `crew.kickoff()` e torce
- Zero visibilidade: não sabemos qual tool foi chamada, qual o reasoning, o que deu errado até o erro estourar
- O loop do crewAI é síncrono (`to_thread`), o que quebra streaming e torna o TUI cego durante execução
- DeepSeek não suporta `response_format` (structured output), mas o crewAI tenta usar `beta.chat.completions.parse()` e explode com `BadRequestError: This response_format type is unavailable now`

**O que deveria ser:**
Um Agent Loop explícito e observável que segue o padrão ReAct ou Plan-Execute, com cada passo (Thought → Action → Observation → Reflection) visível para o TUI e logs.

### 2. RAG — Inexistente

```python
# pyproject.toml diz:
"pgvector>=0.3.5",   # ← Dependência existe
"psycopg2>=2.9.0",   # ← Driver existe

# Mas NENHUM código de RAG no agent loop.
# O agente não recupera documentos. Não indexa. Não busca.
```

**O que deveria ser:**
- Pipeline de indexação: chunk → embed → store (pgvector)
- Pipeline de retrieval: query → embed → hybrid search (BM25 + dense) → rerank
- Integração no agent loop como ferramenta `retrieve_knowledge`
- Agentic RAG: o agente decide QUANDO e O QUE recuperar

### 3. Deep Search — Overengineered e quebrado

O `DeepSearchEngine` tenta fazer tudo:
- Planner → Supervisor → Researcher × N → Source Filter → Synthesizer → Critic (com loop de revisão)
- Tudo via crewAI, com structured output (Pydantic) que o DeepSeek não suporta
- Fallbacks de JSON parsing frágeis por toda parte
- A complexidade é tanta que nunca funciona de ponta a ponta

**O que deveria ser:**
- Search simples com LLM + web tools, sem 7 etapas de pipeline
- Se precisar de profundidade, usar ReAct agent com web tools (o agente decide se precisa buscar mais)
- Structured output só para providers que suportam (OpenAI, Gemini); para Ollama/DeepSeek, usar prompting + parsing robusto

### 4. TUI — Inutilizável como ferramenta real

```python
# tui/app.py — o "dashboard":
class AIWorkspaceApp(App):
    # Uma tela com:
    # - Header (workspace path, git)
    # - Body (lista de AgentLanes)
    # - Footer + Input
    
    # Isso é um CHAT, não um dashboard.
```

**Problemas:**
- Não mostra o estado real do agente (Thought → Action → Observation)
- Não tem métricas (tokens, custo, latência)
- Não tem visibilidade de tools sendo chamadas
- Não tem painel de logs
- Não tem visualização de contexto/knowledge
- "AgentLane" é só uma caixa de texto com scroll

**O que deveria ser:**
Um dashboard multi-pane com:
1. **Agent Grid** — cards de agentes com estado (thinking, acting, observing, idle, error)
2. **Detail Panel** — pensamento atual, tool em execução, output
3. **Timeline/Log** — histórico de ações do agente
4. **Metrics Bar** — tokens, custo, cache hits, latência
5. **Context Panel** — documentos recuperados, contexto atual

### 5. Problemas sistêmicos

| Problema | Impacto |
|----------|---------|
| `try/except: pass` em excesso | Erros silenciosos, comportamento imprevisível |
| `asyncio.run()` dentro de loop async | Crash quando chamado do TUI |
| Streaming quebrado (monkey-patching) | TUI não recebe tokens em tempo real |
| DeepSeek sem structured output | Metade dos pipelines explode |
| crewAI como dependência crítica | Toda a lógica de agentes depende de lib externa |
| Provider config duplicada | Ollama, DeepSeek, Gemini configurados em 3 lugares diferentes |
| Testes não passam | libstdc++ + NumPy quebrado no venv |

---

## Plano de Realinhamento — AI Workspace v0.2

### Princípios

1. **Own the loop** — O agent loop é nosso. crewAI é opcional, não obrigatório.
2. **Visibility first** — Cada passo do agente deve ser observável (TUI, logs, métricas).
3. **Simplicity over complexity** — Menos etapas de pipeline, mais iterações de agente.
4. **RAG como ferramenta** — Recuperação de conhecimento é uma tool como qualquer outra.
5. **Testabilidade** — Cada componente testável isoladamente, sem depender de LLM real.

---

## Fase 1: Estabilização (1-2 dias)

### 1.1 Consertar providers e streaming

**Objetivo:** Fazer `aiw ask` funcionar com qualquer provider sem explodir.

**Ações:**
- [ ] Centralizar config de providers em UM lugar (`src/ai_workspace/providers/registry.py`)
- [ ] Remover `response_format` (structured output) para providers que não suportam (DeepSeek, Ollama)
- [ ] Implementar streaming direto (sem monkey-patching) — usar `httpx` streaming ou Ollama `/api/chat` com `stream: true`
- [ ] Adicionar `aiw ask --stream` que funciona de verdade

### 1.2 Consertar testes

**Objetivo:** `pytest tests/ -q` passar limpo.

**Ações:**
- [ ] Consertar venv (libstdc++ issue) — adicionar `stdenv.cc.cc.lib` ao shell.nix
- [ ] Testes de provider com mock de API (não depende de Ollama rodando)
- [ ] Testes de agente com LLM mockado
- [ ] Remover ou marcar `skip` para testes de integração que dependem de serviços externos

### 1.3 Remover código morto e duplicado

**Objetivo:** Reduzir superfície de código quebrado.

**Ações:**
- [ ] Remover `DeepSearchEngine` (substituir por agente com web tools na Fase 2)
- [ ] Remover `_invoke_loop_react` hacks — não vamos consertar o crewAI, vamos substituí-lo
- [ ] Consolidar `agents/router.py` e `providers/` — um único registry de modelos
- [ ] Remover arquivos TUI não usados (cyberdeck, v2, v3, v4)

---

## Fase 2: Agent Loop próprio (3-4 dias)

### 2.1 Core Loop Engine

**Objetivo:** Um agent loop observável, testável, que não depende de crewAI.

```python
# src/ai_workspace/agents/loop.py

@dataclass
class LoopStep:
    """One step in the agent loop."""
    phase: Literal["think", "act", "observe", "reflect"]
    thought: str          # O que o agente está pensando
    action: str | None    # Tool chamada (ou None se for resposta final)
    action_input: dict | None
    observation: str | None  # Resultado da tool
    reflection: str | None   # O que aprendeu (Reflexion pattern)

class AgentLoop:
    """Observable agent loop.
    
    Patterns:
    - ReAct: think → act → observe → repeat
    - PlanExecute: plan → execute_step → observe → repeat
    - Direct: single LLM call, no tools
    """
    
    def __init__(self, llm, tools, max_iterations=10):
        self.llm = llm
        self.tools = tools
        self.max_iterations = max_iterations
        self.steps: list[LoopStep] = []
        self.on_step: Callable | None = None  # Callback for TUI
    
    async def run(self, task: str, pattern: str = "react") -> LoopStep:
        """Run the loop. Emits on_step for each phase."""
        ...
    
    async def run_react(self, task: str) -> LoopStep:
        """ReAct: interleaved thought → action → observation."""
        ...
    
    async def run_plan_execute(self, task: str) -> LoopStep:
        """Plan-and-Execute: plan once, execute steps."""
        ...
```

**Padrões implementados:**

| Padrão | Quando usar | LLM calls | Complexidade |
|--------|------------|-----------|-------------|
| **Direct** | Pergunta simples, sem tools | 1 | Baixa |
| **ReAct** | Coding, debugging, tarefas dinâmicas | 3-10 | Média |
| **Plan-Execute** | Tasks estruturadas, múltiplos passos | 2 + N | Média |
| **Reflexion** | Quando precisa melhorar output anterior | ReAct + 2 | Alta |

**Ações:**
- [ ] Implementar `AgentLoop` com ReAct e Plan-Execute
- [ ] Integrar tool registry (tools do aiw, não do crewAI)
- [ ] Callback `on_step` para TUI observar cada fase
- [ ] Max iterations com circuit breaker
- [ ] Testes unitários com LLM mock
- [ ] Integrar no CLI (`aiw agent --loop react`)

### 2.2 Substituir crewAI no Orchestrator

**Objetivo:** `AgentOrchestrator` usa nosso `AgentLoop`, não crewAI.

**Ações:**
- [ ] `_run_agent_sync` → `await loop.run(task)`
- [ ] `_run_coding_agent` → ReAct com file/git/shell tools
- [ ] `_run_research_agent` → ReAct com web tools
- [ ] `_run_general_agent` → Direct ou ReAct conforme complexidade
- [ ] Manter crewAI como opcional (`--backend crewai` para quem quiser)

---

## Fase 3: RAG Integration (3-4 dias)

### 3.1 Pipeline de Indexação

**Objetivo:** Ingerir documentos do workspace no vector store.

```python
# src/ai_workspace/knowledge/rag.py

class DocumentIndexer:
    """Index documents into pgvector for retrieval."""
    
    def index_file(self, path: Path) -> list[str]:
        """Chunk + embed + store a file. Returns chunk IDs."""
        ...
    
    def index_directory(self, path: Path, glob: str = "**/*.py") -> int:
        """Index all matching files. Returns count."""
        ...
    
    def _chunk(self, text: str) -> list[Chunk]:
        """Semantic chunking: split on headings, functions, paragraphs.
        
        Strategy:
        - Python: split on def/class
        - Markdown: split on ## headings
        - Generic: 500 tokens with 10% overlap
        """
        ...
    
    def _embed(self, chunks: list[Chunk]) -> list[list[float]]:
        """Embed chunks using the configured model.
        
        Default: Ollama with nomic-embed-text (free, local)
        Alt: text-embedding-3-small (OpenAI-compatible)
        """
        ...
```

**Chunking Strategy (baseado em pesquisa):**
- Código: split em funções/classes (semantic)
- Markdown: split em headings (semantic)
- Texto genérico: 500 tokens, overlap 10%
- Metadados por chunk: file path, line range, language, type

### 3.2 Pipeline de Retrieval

**Objetivo:** Busca híbrida + reranking.

```python
class KnowledgeRetriever:
    """Hybrid search with reranking."""
    
    async def retrieve(
        self, query: str, k: int = 5, strategy: str = "hybrid"
    ) -> list[RetrievedChunk]:
        """
        1. Embed query → dense vector search (top 50)
        2. BM25 keyword search (top 50)
        3. Reciprocal Rank Fusion → top 20
        4. Cross-encoder rerank → top k
        """
        ...
    
    async def retrieve_with_context(
        self, query: str, k: int = 5
    ) -> str:
        """Retrieve and format as context string for LLM."""
        chunks = await self.retrieve(query, k=k)
        return self._format_context(chunks)
```

**Actions:**
- [ ] Implementar embedding com Ollama (`nomic-embed-text`)
- [ ] Implementar BM25 com `rank_bm25`
- [ ] Implementar RRF (Reciprocal Rank Fusion)
- [ ] Implementar reranking com cross-encoder (opcional, fallback: score-based)
- [ ] Testes com documentos de exemplo

### 3.3 Agentic RAG Tool

**Objetivo:** O agente decide quando recuperar conhecimento.

```python
# Ferramenta registrada no AgentLoop:
class RetrieveKnowledgeTool:
    name = "retrieve_knowledge"
    description = "Search the knowledge base for relevant documents"
    
    async def run(self, query: str) -> str:
        """Retrieve and return formatted context."""
        retriever = KnowledgeRetriever()
        return await retriever.retrieve_with_context(query)
```

**Actions:**
- [ ] Registrar `retrieve_knowledge` como tool no AgentLoop
- [ ] System prompt instrui o agente a usar retrieve_knowledge antes de responder perguntas técnicas
- [ ] Cache de embeddings para não re-indexar arquivos não modificados
- [ ] CLI: `aiw kb index` e `aiw kb search`

---

## Fase 4: TUI v5 — Dashboard Real (3-4 dias)

### 4.1 Layout

```
┌─ Header: workspace │ git:main +2 ~5 │ 3 agents │ 💰 $0.005 ──────────────┐
├─────────────────────────────────────────────────────────────────────────┤
│ ┌─ Agent Grid ───────────────────────┐ ┌─ Detail Panel ───────────────┐ │
│ │                                    │ │                               │ │
│ │  ┌──────────┐ ┌──────────┐        │ │  🤔 Thinking                  │ │
│ │  │ agent-1  │ │ agent-2  │        │ │  "I need to read the config   │ │
│ │  │ 🔵 coding│ │ 🟢 idle  │        │ │   file first..."              │ │
│ │  │ 3 steps  │ │ qwen3:14b│        │ │                               │ │
│ │  └──────────┘ └──────────┘        │ │  🔧 Acting                    │ │
│ │                                    │ │  read_file(path="config.py")  │ │
│ │  ┌──────────┐                      │ │                               │ │
│ │  │ agent-3  │                      │ │  👁 Observing                 │ │
│ │  │ 🟡 thinking│                    │ │  "DEBUG=True\nPORT=8000..."   │ │
│ │  │ research │                      │ │                               │ │
│ │  └──────────┘                      │ │  ✅ Reflect                   │ │
│ │                                    │ │  "Config loaded. Now I can..." │ │
│ └────────────────────────────────────┘ └───────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────┤
│ ┌─ Timeline ───────────────────────────────────────────────────────────┐ │
│ │ 12:03:45  agent-1  🤔 Think  "Reading config..."                    │ │
│ │ 12:03:46  agent-1  🔧 Act   read_file("config.py")                  │ │
│ │ 12:03:47  agent-1  👁 Observe  37 lines read                         │ │
│ │ 12:03:48  agent-1  🤔 Think  "Now fixing the bug..."                │ │
│ └──────────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────┤
│ ┌─ Metrics Bar ────────────────────────────────────────────────────────┐ │
│ │ Tokens: 1,247 │ Cost: $0.0003 │ Cache: 3 hits │ Latency: 234ms      │ │
│ └──────────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────┤
│ Footer: Ctrl+J spawn │ F2 chat │ Space pause │ Ctrl+K kill │ F1 help   │
│ > _                                                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Componentes

| Componente | Descrição | Estado |
|-----------|-----------|--------|
| **Header** | Path, git info, agent count, budget | Já existe, melhorar |
| **AgentGrid** | Cards de agentes com estado visual | NOVO |
| **DetailPanel** | Pensamento/ação/observação atual | NOVO |
| **Timeline** | Log cronológico de passos do agente | NOVO |
| **MetricsBar** | Tokens, custo, cache, latência | NOVO |
| **ContextPanel** | Documentos recuperados (RAG) | NOVO |
| **Footer + Input** | Comandos e input de tarefa | Já existe |
| **PermissionModal** | Aprovação de operações perigosas | Já existe |

### 4.3 Data Flow

```
AgentLoop.on_step(callback)
  │
  ├─→ TUI: atualiza AgentGrid (estado do agente)
  ├─→ TUI: atualiza DetailPanel (thought/action/obs)
  ├─→ TUI: append Timeline
  ├─→ TUI: atualiza MetricsBar
  └─→ TUI: streaming output (se em modo chat)
```

**Ações:**
- [ ] Implementar `AgentGrid` com cards (Textual `Grid` + `Static`)
- [ ] Implementar `DetailPanel` com fases visuais
- [ ] Implementar `Timeline` com scroll infinito
- [ ] Implementar `MetricsBar`
- [ ] Implementar `ContextPanel` (RAG results)
- [ ] Conectar `AgentLoop.on_step` aos componentes TUI
- [ ] Atalhos de teclado consistentes
- [ ] Testes de snapshot do TUI

---

## Fase 5: Search v2 — Simples e Robusto (2 dias)

### 5.1 Abordagem

Em vez do pipeline complexo (plan → supervisor → research × N → filter → synthesize → critic), usar:

```
Usuário: "Rust vs Go performance 2026"
  │
  ▼
Agente ReAct com web tools:
  🤔 Think: "Preciso buscar benchmarks recentes de Rust vs Go"
  🔧 Act: web_search("Rust vs Go benchmark 2026")
  👁 Observe: [resultados de busca]
  🤔 Think: "Vou ler os top 3 resultados"
  🔧 Act: web_fetch(url1), web_fetch(url2), web_fetch(url3)
  👁 Observe: [conteúdo das páginas]
  🤔 Think: "Agora tenho dados suficientes. Vou sintetizar."
  ✅ Respond: relatório final
```

**Vantagens:**
- O agente decide a profundidade (não um pipeline fixo)
- Funciona com qualquer provider (sem structured output)
- Observável (cada passo é visível no TUI/timeline)
- Mais barato (menos LLM calls desnecessárias)

### 5.2 Implementação

**Ações:**
- [ ] `aiw search "query"` → spawn ReAct agent com web tools
- [ ] Ferramentas: `web_search`, `web_fetch`, `crawl4ai_scrape`
- [ ] Source filtering pós-retrieval (não uma etapa separada)
- [ ] Síntese final como último passo do agente
- [ ] Remover `DeepSearchEngine` inteiro

---

## Fase 6: Polish & Ship (2-3 dias)

- [ ] Documentação atualizada (README, docs/)
- [ ] CHANGELOG
- [ ] Testes end-to-end
- [ ] CI/CD básico (GitHub Actions: lint + test)
- [ ] Tag v0.2.0
- [ ] Nix package update

---

## Resumo: Antes vs Depois

| Aspecto | Antes (v0.1) | Depois (v0.2) |
|---------|-------------|---------------|
| **Agent Loop** | crewAI caixa preta | AgentLoop próprio, observável |
| **Padrões** | Só ReAct (via crewAI) | ReAct, Plan-Execute, Direct |
| **RAG** | Inexistente | Indexação + hybrid search + rerank |
| **Search** | Pipeline 7 etapas quebrado | ReAct agent com web tools |
| **TUI** | Chat glorificado | Dashboard multi-pane com estado real |
| **Streaming** | Monkey-patch frágil | Streaming nativo por provider |
| **Provider** | Config duplicada, DeepSeek quebrado | Registry unificado, fallback robusto |
| **Testes** | 3 errors, não passam | Limpos, mockados, CI |
| **Dependência** | crewAI obrigatório | crewAI opcional |

---

## Dependências Técnicas

```toml
# Manter:
"pgvector>=0.3.5"       # Vector store (RAG)
"psycopg2>=2.9.0"       # PostgreSQL driver
"textual>=8.0"          # TUI framework
"httpx>=0.27.0"         # HTTP client (streaming, web tools)
"pydantic>=2.0.0"       # Data validation

# Adicionar:
"rank-bm25>=0.2.0"      # BM25 keyword search (RAG)
"tiktoken>=0.7.0"       # Token counting (chunking)

# Opcional (não bloquear):
"crewai[tools]>=1.0"    # Backend alternativo (--backend crewai)
```

---

## Próximos Passos

1. **Validar este plano** — faz sentido? Prioridades certas?
2. **Começar Fase 1** — estabilização (consertar providers, testes)
3. **Fase 2** — Agent Loop próprio (o coração do sistema)
4. **Fase 3** — RAG (diferencial)
5. **Fase 4** — TUI v5 (o que o usuário vê)
