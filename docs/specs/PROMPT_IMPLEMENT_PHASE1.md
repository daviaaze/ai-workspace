# Prompt: Implementação Fase 1 — Fundações v0.2

> Use este prompt para iniciar a implementação da Fase 1 do plano v0.2.

---

## Objetivo

Implementar as 3 fundações da nova arquitetura: **OutputFormatter**, **Result/AiWError**, e **AgentLoop**. São componentes independentes entre si, implementáveis em paralelo ou sequencialmente.

## Pré-requisitos

- [ ] Repositório limpo (executar PROMPT_CLEANUP primeiro)
- [ ] `aiw health` funcional (providers online)
- [ ] PostgreSQL rodando (para testes de RAG na Fase 3, não necessário agora)
- [ ] Ler as specs antes de começar:
  - `docs/specs/SPEC_OUTPUT_MODES.md`
  - `docs/specs/SPEC_ERROR_HANDLING.md`
  - `docs/specs/SPEC_AGENT_LOOP.md`
  - `docs/specs/SPEC_INTEGRATION.md` (mapa de arquivos)

---

## Tarefa 1: `src/ai_workspace/core/output.py`

### O que construir

Módulo de formatação de saída com 3 modos: Rich (terminal), JSON, NDJSON.

### Spec de referência

`docs/specs/SPEC_OUTPUT_MODES.md`

### API

```python
from ai_workspace.core.output import OutputFormatter, OutputEnvelope, OutputMode

# Uso:
fmt = OutputFormatter(mode="json")
envelope = OutputEnvelope(ok=True, command="health", data={...})
fmt.print(envelope)

# NDJSON streaming:
fmt = OutputFormatter(mode="ndjson")
fmt.write_event("start", command="search", query="...")
fmt.write_event("phase", phase="planning", message="...")
fmt.write_event("done", ok=True)
```

### Requisitos

- [ ] `OutputFormatter(mode="rich")` — compatível com comportamento atual (delega para Rich)
- [ ] `OutputFormatter(mode="json")` — `print(json.dumps(envelope.to_dict(), indent=2))`
- [ ] `OutputFormatter(mode="ndjson")` — cada `write_event()` emite uma linha JSON + `\n` + flush
- [ ] `OutputEnvelope` com campos: `ok`, `command`, `timestamp`, `data`, `error`, `warnings`, `meta`
- [ ] NDJSON segue spec oficial: sem newlines internos, UTF-8, `\n` delimiter
- [ ] Testes: `tests/test_core/test_output.py`
  - `test_json_mode_produces_valid_json`
  - `test_ndjson_each_line_is_valid_json`
  - `test_rich_mode_does_not_crash`
  - `test_envelope_with_error`

### Integração

Nesta fase, NÃO modificar o CLI ainda. Só criar o módulo e testar isoladamente. A integração com `cli.py` virá na Fase 2.

---

## Tarefa 2: `src/ai_workspace/core/result.py`

### O que construir

Tipos para tratamento de erro estruturado: `Result[T, E]`, `Success`, `Failure`, `AiWError`.

### Spec de referência

`docs/specs/SPEC_ERROR_HANDLING.md`

### API

```python
from ai_workspace.core.result import Result, Success, Failure, AiWError, ErrorCode

# Uso:
def find_user(id: int) -> Result[User, AiWError]:
    user = db.query(id)
    if user:
        return Success(user)
    return Failure(AiWError(
        code=ErrorCode.NOT_FOUND,
        message=f"User {id} not found",
        recoverable=False,
        suggestion="Check the user ID and try again",
    ))

# Pattern matching:
match find_user(42):
    case Success(user):
        print(user.name)
    case Failure(error):
        logger.warning("%s: %s", error.code, error.message)
```

### Requisitos

- [ ] `Success[T]` e `Failure[E]` dataclasses frozen
- [ ] `type Result[T, E] = Success[T] | Failure[E]` (Python 3.12+ syntax)
- [ ] `AiWError` com campos: `code`, `message`, `detail`, `recoverable`, `suggestion`
- [ ] `ErrorCode` class com constantes para todos os códigos de erro do sistema
- [ ] Testes: `tests/test_core/test_result.py`
  - `test_success_unwrap`
  - `test_failure_pattern_matching`
  - `test_aiw_error_serialization`
  - `test_result_type_narrowing`

### NÃO fazer agora

- NÃO adicionar `@safe` decorator (complexidade desnecessária)
- NÃO migrar código existente para usar Result (Fase 2)
- NÃO integrar com output modes (Fase 2)

---

## Tarefa 3: `src/ai_workspace/agents/loop.py`

### O que construir

O AgentLoop — async generator que substitui crewAI. Implementar 2 padrões primeiro (Direct e ReAct). Plan-Execute e ReWOO vêm depois.

### Spec de referência

`docs/specs/SPEC_AGENT_LOOP.md`

### API

```python
from ai_workspace.agents.loop import (
    agent_loop, LoopParams, LoopPattern, LoopEvent, TerminalReason, suggest_pattern
)

# Uso:
params = LoopParams(
    task="Explain what this code does",
    pattern=LoopPattern.DIRECT,
    model="qwen3:14b",
    provider="ollama",
    stream=True,
)

async for event in agent_loop(params):
    if event.type == "token":
        print(event.data["text"], end="")
    elif event.type == "error":
        print(f"Error: {event.data['message']}")
```

### Requisitos

- [ ] `agent_loop()` é um async generator (como Claude Code `query()`)
- [ ] `LoopParams` dataclass com todos os campos da spec
- [ ] `LoopEvent` dataclass com `type` e `data`
- [ ] `TerminalReason` enum com 8 variantes
- [ ] `LoopPattern` enum: DIRECT, REACT (PLAN_EXECUTE e REWOO são Fase 2+)
- [ ] `suggest_pattern(task, tools)` — heurística para escolher o loop
- [ ] `LoopPattern.DIRECT` — chama o modelo uma vez, sem tools, retorna resposta
- [ ] `LoopPattern.REACT` — loop thought→action→observation (usa tools)
- [ ] Streaming funciona: tokens chegam via `yield LoopEvent(type="token", ...)`
- [ ] Callback `on_step` opcional para TUI
- [ ] `deps` para injeção de dependências (testável com modelo fake)
- [ ] Testes: `tests/test_agents/test_loop.py`
  - `test_direct_pattern_returns_response` (com modelo fake)
  - `test_react_pattern_calls_tools` (com modelo fake que retorna tool_call)
  - `test_max_turns_stops_loop`
  - `test_token_budget_stops_loop`
  - `test_suggest_pattern_direct_for_simple_question`
  - `test_suggest_pattern_react_for_coding_task`

### Modelo fake para testes

```python
# tests/test_agents/conftest.py
class FakeProvider:
    """Provider falso que retorna respostas pré-definidas."""
    
    def __init__(self, responses: list[dict]):
        self.responses = responses
        self.call_count = 0
    
    async def stream_chat(self, model, messages, **kwargs):
        if self.call_count >= len(self.responses):
            yield {"type": "text", "text": "Done."}
            return
        response = self.responses[self.call_count]
        self.call_count += 1
        if isinstance(response, str):
            yield {"type": "text", "text": response}
        else:
            for key, value in response.items():
                yield {"type": key, **value}
```

### NÃO fazer agora

- NÃO integrar com `orchestrator.py` (Fase 2)
- NÃO implementar Plan-Execute e ReWOO (Fase 2+)
- NÃO adicionar streaming tool execution (parallel buckets) — começar com sequential
- NÃO conectar com TUI (Fase 4)
- NÃO implementar context compaction (Fase 2+)

---

## Tarefa 4 (bônus): `providers/__init__.py` — adicionar `stream_chat()`

### O que fazer

Adicionar método `stream_chat()` a cada provider para streaming nativo (substitui o monkey-patching atual em `tui/streaming.py`).

### API

```python
# Ollama provider
async def stream_chat(self, model, messages, temperature=0.7, tools=None):
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST", f"{self.base_url}/api/chat",
            json={"model": model, "messages": messages, "stream": True}
        ) as response:
            async for line in response.aiter_lines():
                if line:
                    yield json.loads(line)

# DeepSeek provider (OpenAI-compatible)
async def stream_chat(self, model, messages, temperature=0.7, tools=None):
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST", f"{self.base_url}/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": model, "messages": messages, "stream": True}
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: ") and line != "data: [DONE]":
                    yield json.loads(line[6:])
```

### Requisitos

- [ ] Ollama provider: `stream_chat()` funcional
- [ ] DeepSeek provider: `stream_chat()` funcional
- [ ] Gemini provider: `stream_chat()` funcional (opcional, se API key disponível)
- [ ] Testes: mock HTTP responses

---

## Ordem de implementação

```
1. core/result.py         (30 min)  — mais simples, sem dependências
2. core/output.py         (45 min)  — depende de result.py para OutputEnvelope.error
3. agents/loop.py         (2-3h)    — depende de providers/__init__.py
4. providers/__init__.py  (1h)      — stream_chat() para ollama + deepseek
```

## Verificação final

- [ ] `python -m pytest tests/test_core/test_result.py -q` passa
- [ ] `python -m pytest tests/test_core/test_output.py -q` passa
- [ ] `python -m pytest tests/test_agents/test_loop.py -q` passa
- [ ] `python -c "from ai_workspace.agents.loop import agent_loop; print('OK')"` não crasha
- [ ] `python -c "from ai_workspace.core.output import OutputFormatter; print('OK')"` não crasha

## Commitar

Mensagem: `feat: Phase 1 foundations — AgentLoop, OutputFormatter, Result types, provider streaming`

---

## Referências

- `docs/specs/SPEC_AGENT_LOOP.md` — API completa do AgentLoop
- `docs/specs/SPEC_OUTPUT_MODES.md` — API do OutputFormatter
- `docs/specs/SPEC_ERROR_HANDLING.md` — API do Result/AiWError
- `docs/specs/SPEC_INTEGRATION.md` — mapa de arquivos e fluxos
- Claude Code: `query.ts` async generator pattern
- pi: `agent-loop.ts` state machine + eventos
