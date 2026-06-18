# Spec: Agent Loop — Core Execution Engine

> **Status:** 📋 Spec | **Data:** 2026-06-18
> **Refs:** Claude Code `query.ts`, pi `agent-loop.ts`, Cursor agent architecture, ReAct/ReWOO/Plan-Execute papers

---

## 🎯 O que aprendemos das implementações reais

### Claude Code (Anthropic) — 1 arquivo, 1 função

O loop inteiro do Claude Code está em **um único arquivo**: `query.ts` (~1,730 linhas). Uma async generator function chamada `query()`.

```typescript
// O coração do sistema — toda interação passa por aqui
async function* query(params: LoopParams): AsyncGenerator<Message | Event, TerminalReason> {
    let state: LoopState = { messages: [], turnCount: 0, ... };
    
    while (true) {
        // 1. Chama o modelo (streaming)
        const stream = await callModel(state.messages, params.prompt);
        
        // 2. Consome tokens e identifica tool calls
        for await (const event of stream) {
            if (event.type === 'tool_use') {
                // 3. Executa ferramentas (paralelo quando possível)
                const results = await executeTools(event.tools, state);
                state.messages.push(...results);
            }
            yield event; // ← backpressure: pausa se consumidor ocupado
        }
        
        // 4. Decide se continua ou termina
        if (shouldStop(state)) {
            return { reason: 'completed', messages: state.messages };
        }
        state.turnCount++;
    }
}
```

**Decisões arquiteturais:**
- **Async generator** (não callback/event emitter) → backpressure nativa, retorno tipado
- **Single entry point** — REPL, SDK, sub-agents, headless: tudo chama a mesma função
- **State object** mutável com 10+ campos (messages, turnCount, recovery counters, compaction tracking)
- **10 terminal states** tipados (normal, user_abort, token_budget, max_turns, error, etc.)
- **Streaming tool execution** — executa ferramentas enquanto o modelo ainda está gerando
- **Parallel buckets** — tools são particionadas em `concurrency_safe` e `serial`, executadas em paralelo quando possível

### pi (coding agent) — Loop + State Machine

```typescript
// packages/agent/src/agent-loop.ts
async function runLoop(state: AgentState): Promise<AgentFinish> {
    while (true) {
        // 1. Transforma mensagens para formato LLM
        const llmMessages = convertToLlm(state.messages);
        
        // 2. Chama LLM com streaming
        const stream = await streamFn(llmMessages, state.tools);
        
        // 3. Processa resposta
        for await (const event of stream) {
            if (event.type === 'tool_call') {
                // 4. Executa tools (paralelo por padrão)
                const results = await executeTools(event.tools, {
                    mode: state.toolExecution, // 'parallel' | 'sequential'
                    hooks: state.hooks,        // beforeToolCall, afterToolCall
                });
                state.messages.push(...results);
            }
            yield event;
        }
    }
}
```

**Eventos do ciclo de vida:**
```
agent_start → turn_start → message_start → message_update* → message_end
  → tool_execution_start → tool_execution_update* → tool_execution_end
  → turn_end → agent_end
```

**Características:**
- `agentLoopContinue` — resume de um contexto que terminou em user/toolResult (essencial para retry)
- `PendingMessageQueue` — fila mensagens que chegam enquanto agente está ocupado
- Tool execution modes: `sequential` e `parallel` (parallel é default)

### Cursor — Orquestrador, não um loop

Cursor não tem um loop central como Claude/pi. É uma **camada de orquestração**:

```
User message → Context Engine (inject files, git, rules, linter) 
  → Router (select model) → ReAct Loop (tool calls) → Summarizer → Response
```

**Context Engine** — o diferencial:
- Vector embeddings + Tree-sitter para busca semântica no codebase
- 2-stage retrieval: vector search (candidates) → AI rerank (top-k)
- Injeção silenciosa de contexto: open files, git, rules, linter errors, terminal state

### Comparação das 3 implementações

| Aspecto | Claude Code | pi | Cursor |
|---------|------------|-----|--------|
| **Arquitetura** | Generator monólito | State machine + eventos | Orquestrador de serviços |
| **Loop type** | while(true) com yield | while(true) com yield | ReAct + context engine |
| **Streaming** | Native (SSE) | Native (SSE) | Via API |
| **Tool exec** | Parallel (buckets) | Parallel (default) | Sequential/Parallel |
| **Context** | 4-layer compaction | contextTransform() | Vector + Tree-sitter + rerank |
| **Sub-agents** | Fork + prompt cache | N/A | Task tool (parallel) |
| **Entry points** | 1 função (REPL/SDK/headless) | 1 função + Agent class | IDE plugin |
| **Error recovery** | 10 terminal states | agentLoopContinue | Retry + fallback |

---

## 📐 Design para o aiw

### Princípios (extraídos das 3 implementações)

1. **Single entry point** — uma função de loop que serve CLI, TUI, MCP, SDK
2. **Async generator** — backpressure, return tipado, composable via `yield*`
3. **Streaming-first** — ferramentas executam enquanto modelo gera
4. **Parallel tools** — quando possível, executar em paralelo
5. **State object** — mutável, tipado, carrega contexto entre iterações
6. **Terminal states** — razão exata de por que o loop parou (não só "done")

### API principal

```python
from dataclasses import dataclass, field
from typing import AsyncGenerator, Literal
from enum import Enum

class LoopPattern(Enum):
    """Qual estratégia de loop usar."""
    REACT = "react"           # Thought → Action → Observation → repeat
    PLAN_EXECUTE = "plan"     # Plan once → execute steps
    REWOO = "rewoo"          # Plan tools → execute all → synthesize
    DIRECT = "direct"         # Single LLM call, no tools

class TerminalReason(Enum):
    """Por que o loop terminou."""
    COMPLETED = "completed"           # Resposta final produzida
    MAX_TURNS = "max_turns"           # Atingiu limite de iterações
    TOKEN_BUDGET = "token_budget"     # Estourou orçamento de tokens
    USER_ABORT = "user_abort"         # Usuário interrompeu
    TOOL_ERROR = "tool_error"         # Erro irrecuperável em ferramenta
    MODEL_ERROR = "model_error"       # Erro irrecuperável no modelo
    NO_TOOLS = "no_tools"             # Modelo não chamou ferramentas
    TIMEOUT = "timeout"               # Timeout global

@dataclass
class LoopState:
    """Estado mutável do loop. Carregado entre iterações."""
    messages: list[dict] = field(default_factory=list)
    turn_count: int = 0
    token_count: int = 0
    tool_errors: int = 0          # Contador de erros consecutivos
    recovery_attempts: int = 0    # Tentativas de recovery
    pending_summaries: list = field(default_factory=list)
    aborted: bool = False

@dataclass
class LoopParams:
    """Parâmetros de entrada do loop."""
    task: str
    pattern: LoopPattern = LoopPattern.REACT
    tools: list[callable] = field(default_factory=list)
    system_prompt: str = ""
    messages: list[dict] = field(default_factory=list)
    max_turns: int = 20
    max_tokens: int = 100_000
    temperature: float = 0.7
    model: str = "qwen3:14b"
    provider: str = "ollama"
    stream: bool = True
    parallel_tools: bool = True
    on_step: callable = None       # Callback para TUI/streaming
    deps: dict = field(default_factory=dict)  # Injeção para testes

@dataclass
class LoopEvent:
    """Evento emitido durante o loop."""
    type: str  # 'thinking', 'tool_call', 'tool_result', 'token', 'error'
    data: dict

async def agent_loop(params: LoopParams) -> AsyncGenerator[LoopEvent, TerminalReason]:
    """O loop central. Async generator como Claude Code.
    
    Uso:
        async for event in agent_loop(params):
            tui.on_event(event)  # TUI reage em tempo real
        
        # ou com return value:
        gen = agent_loop(params)
        async for event in gen:
            print(event)
        result = await gen.__anext__()  # pega o TerminalReason (não funciona assim em Python)
    """
    state = LoopState()
    state.messages = params.messages.copy()
    
    while True:
        # 1. Prepara mensagens para o modelo
        llm_messages = _build_messages(state, params)
        
        # 2. Chama o modelo (streaming ou batch)
        if params.stream:
            stream = await _call_model_stream(llm_messages, params)
        else:
            response = await _call_model(llm_messages, params)
            stream = [response]
        
        # 3. Processa resposta e identifica tool calls
        tool_calls = []
        async for chunk in stream:
            if chunk.get("type") == "token":
                yield LoopEvent(type="token", data={"text": chunk["text"]})
            elif chunk.get("type") == "thinking":
                yield LoopEvent(type="thinking", data={"thought": chunk["thought"]})
            elif chunk.get("type") == "tool_call":
                tool_calls.append(chunk)
        
        # 4. Se não houver tool calls, terminou
        if not tool_calls:
            return TerminalReason.COMPLETED
        
        # 5. Executa ferramentas
        if params.parallel_tools and len(tool_calls) > 1:
            results = await _execute_tools_parallel(tool_calls, params, state)
        else:
            results = await _execute_tools_sequential(tool_calls, params, state)
        
        # 6. Adiciona resultados ao estado
        for result in results:
            state.messages.append({"role": "tool", "content": result})
            yield LoopEvent(type="tool_result", data=result)
        
        # 7. Verifica condições de parada
        state.turn_count += 1
        if state.turn_count >= params.max_turns:
            return TerminalReason.MAX_TURNS
        if state.token_count >= params.max_tokens:
            return TerminalReason.TOKEN_BUDGET
        if state.aborted:
            return TerminalReason.USER_ABORT
```

### Diferentes loops para diferentes tipos de agente

```python
# ═══════════════════════════════════════════════════════════
# Padrão 1: Direct — pergunta simples, sem ferramentas
# ═══════════════════════════════════════════════════════════
# Uso: chat rápido, "explique X", tradução
# LLM calls: 1
# Complexidade: mínima

async def loop_direct(params: LoopParams):
    """Single call, no tools."""
    response = await _call_model(params.messages, params)
    return response


# ═══════════════════════════════════════════════════════════
# Padrão 2: ReAct — coding, debugging, tarefas exploratórias
# ═══════════════════════════════════════════════════════════
# Uso: "conserta o bug X", "adiciona feature Y", "pesquisa Z"
# LLM calls: 3-15 (uma por iteração)
# Complexidade: média

async def loop_react(params: LoopParams):
    """Thought → Action → Observation → repeat."""
    return agent_loop(params)  # usa o loop padrão


# ═══════════════════════════════════════════════════════════
# Padrão 3: Plan-Execute — tarefas estruturadas, previsíveis
# ═══════════════════════════════════════════════════════════
# Uso: "cria um CRUD completo", "migra o banco de dados"
# LLM calls: 2 + N (plano + N passos)
# Complexidade: média-alta

async def loop_plan_execute(params: LoopParams):
    """Plan once, execute steps."""
    # Fase 1: Planejar
    plan = await _call_model([
        {"role": "system", "content": "Create a step-by-step plan."},
        {"role": "user", "content": params.task},
    ], params)
    steps = _parse_steps(plan)  # extrai lista de passos
    
    # Fase 2: Executar cada passo (pode usar ReAct internamente)
    results = []
    for i, step in enumerate(steps):
        step_params = LoopParams(
            task=step,
            pattern=LoopPattern.REACT,  # cada passo usa ReAct
            tools=params.tools,
            max_turns=5,  # limite por passo
        )
        result = await _run_to_completion(agent_loop(step_params))
        results.append(result)
    
    return _synthesize(results)


# ═══════════════════════════════════════════════════════════
# Padrão 4: ReWOO — ferramentas independentes, paralelizáveis
# ═══════════════════════════════════════════════════════════
# Uso: "compare preços de X em 3 sites"
# LLM calls: 2 (plano + síntese)
# Complexidade: baixa-média

async def loop_rewoo(params: LoopParams):
    """Plan tools → execute all → synthesize."""
    # Fase 1: Planejar quais ferramentas usar
    plan = await _call_model([
        {"role": "system", "content": "List tools to call with placeholders."},
        {"role": "user", "content": params.task},
    ], params)
    tool_plan = _parse_tool_plan(plan)
    
    # Fase 2: Executar todas em paralelo
    results = await asyncio.gather(*[
        _execute_tool(t.name, t.args) for t in tool_plan
    ])
    
    # Fase 3: Sintetizar
    synthesis = await _call_model([
        {"role": "system", "content": "Synthesize tool results."},
        {"role": "user", "content": f"Task: {params.task}\nResults: {results}"},
    ], params)
    
    return synthesis
```

### Matriz de decisão: qual loop usar?

| Tipo de tarefa | Exemplo | Loop recomendado | Por quê |
|---------------|---------|-----------------|---------|
| **Chat / Pergunta** | "O que é X?" | Direct | Sem ferramentas, 1 chamada |
| **Coding** | "Corrige o bug Y" | ReAct | Exploratório, precisa iterar |
| **Debugging** | "Por que Z falha?" | ReAct | Precisa observar outputs |
| **Pesquisa simples** | "Preço do produto X" | ReWOO | Busca em paralelo |
| **Pesquisa profunda** | "Compare X vs Y em 2026" | Plan-Execute | Múltiplos ângulos |
| **Tarefa estruturada** | "Cria CRUD de usuários" | Plan-Execute | Passos previsíveis |
| **Code review** | "Revisa esse PR" | ReAct + Reflexion | Precisa auto-crítica |
| **Tradução** | "Traduz esse arquivo" | Direct | Transformação pura |

### Detecção automática (heuristic)

```python
def suggest_pattern(task: str, tools: list) -> LoopPattern:
    """Sugere o melhor loop baseado na tarefa."""
    
    # Se não tem ferramentas, é Direct
    if not tools:
        return LoopPattern.DIRECT
    
    # Palavras-chave de tarefas estruturadas
    structured_keywords = ["criar", "build", "generate", "scaffold", "migrate"]
    if any(kw in task.lower() for kw in structured_keywords):
        return LoopPattern.PLAN_EXECUTE
    
    # Palavras-chave de busca/comparação
    search_keywords = ["compare", "preço", "price", "qual melhor", "vs"]
    if any(kw in task.lower() for kw in search_keywords):
        if _tools_are_independent(tools):
            return LoopPattern.REWOO
    
    # Coding/debugging → ReAct
    code_keywords = ["fix", "debug", "implement", "refactor", "add", "change"]
    if any(kw in task.lower() for kw in code_keywords):
        return LoopPattern.REACT
    
    # Default: ReAct (mais seguro para tarefas desconhecidas)
    return LoopPattern.REACT
```

---

## 🔗 Integração com TUI (AgentMonitor + Conversation)

O callback `on_step` conecta o loop ao TUI:

```python
# No TUI:
async def spawn_agent(self, task: str):
    params = LoopParams(
        task=task,
        pattern=suggest_pattern(task, self.tools),
        tools=self.tools,
        stream=True,
        on_step=self._on_agent_step,  # ← callback
    )
    
    async for event in agent_loop(params):
        # Eventos já são yieldados pelo loop
        # AgentMonitor e Conversation reagem automaticamente
        pass

def _on_agent_step(self, event: LoopEvent):
    """Callback chamado a cada evento do loop."""
    if event.type == "thinking":
        self.agent_monitor.update_thought(event.data["thought"])
        self.conversation.add_agent_thought(event.data["thought"])
    elif event.type == "tool_call":
        self.agent_monitor.update_action(event.data["tool"], event.data["args"])
        self.conversation.add_agent_action(event.data["tool"], event.data["args"])
    elif event.type == "tool_result":
        self.agent_monitor.update_observation(event.data["result"])
        self.conversation.add_agent_observation(event.data["result"])
    elif event.type == "token":
        self.conversation.append_token(event.data["text"])
    elif event.type == "error":
        self.conversation.add_error(event.data)
```

---

## ✅ Critérios de aceitação

- [ ] `agent_loop()` é um async generator (como Claude Code)
- [ ] Suporta 4 padrões: Direct, ReAct, Plan-Execute, ReWOO
- [ ] Callback `on_step` para TUI receber eventos em tempo real
- [ ] `LoopParams` contém todos os parâmetros necessários (task, tools, max_turns, etc.)
- [ ] `TerminalReason` enum com 8+ razões de parada tipadas
- [ ] `LoopState` mutável carrega contexto entre iterações
- [ ] Tools executam em paralelo quando possível (Parallel buckets como Claude)
- [ ] `suggest_pattern()` detecta automaticamente o melhor loop
- [ ] Testável: `deps` permite injetar modelo fake
- [ ] Funciona com qualquer provider (ollama, deepseek, gemini)
- [ ] Streaming funciona (tokens chegam um a um)

---

## 📚 Referências

- [Claude Code from Source — Ch5: The Agent Loop](https://claude-code-from-source.com/ch05-agent-loop/) — arquitetura completa do loop
- [HarrisonSec — Claude Code Deep Dive: query.ts](https://harrisonsec.com/blog/claude-code-deep-dive-query-loop/) — análise detalhada do arquivo
- [pi Agent Loop — DeepWiki](https://deepwiki.com/badlogic/pi-mono/3.1-agent-loop-and-state-machine) — state machine e eventos
- [Cursor Reverse-Engineered — DEV.to](https://dev.to/vikram_ray/i-reverse-engineered-cursors-ai-agent-heres-everything-it-does-behind-the-scenes-3d0a) — context engine e tools
- [ReAct vs Plan-Execute vs ReWOO vs Reflexion](https://theaiengineer.substack.com/p/the-4-single-agent-patterns) — comparação de padrões
- [COMPEL Framework — Agent Loop Patterns](https://www.compelframework.org/articles/agent-loop-patterns-react-plan-execute-reflexion) — taxonomia de loops
