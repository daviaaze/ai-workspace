# Spec: Tool Execution — Concurrent & Streaming

> **Status:** 📋 Spec | **Data:** 2026-06-18
> **Refs:** Claude Code `StreamingToolExecutor`, `toolOrchestration.ts`, partition algorithm

---

## 🎯 Motivação

Uma resposta típica do modelo gera 3-5 tool calls. Se cada uma leva 200ms, execução sequencial = 1 segundo. Mas Reads e Greps são independentes — executar em paralelo reduz para 200ms. **Ganho de 5x, grátis.**

Claude Code tem duas camadas de otimização:
1. **Batch orchestration** — particionar tools em grupos concurrent-safe vs serial
2. **Speculative execution** — começar a executar tools ENQUANTO o modelo ainda está gerando

---

## 📐 O algoritmo de partição (Claude Code)

```python
# Traduzido de toolOrchestration.ts

def partition_tool_calls(calls: list[ToolCall], registry: ToolRegistry) -> list[Batch]:
    """
    Particiona tool calls em batches (concurrent ou serial).
    
    Algoritmo: percorre array em ordem. Tools consecutivas seguras
    acumulam no mesmo batch. Qualquer tool insegura quebra o batch.
    
    Exemplo:
    Input:  [Read, Read, Grep, Edit, Read]
    Output: [
        Batch(parallel=True,  calls=[Read, Read, Grep]),
        Batch(parallel=False, calls=[Edit]),
        Batch(parallel=True,  calls=[Read]),
    ]
    """
    batches = []
    
    for call in calls:
        # 1. Lookup tool definition
        tool_def = registry.lookup(call.name)
        
        # 2. Parse input com schema (fail-closed: erro → serial)
        try:
            parsed = tool_def.schema.parse(call.input)
            safe = tool_def.is_concurrency_safe(parsed)
        except Exception:
            safe = False  # conservador: qualquer erro → serial
        
        # 3. Merge ou cria batch
        if safe and batches and batches[-1].parallel:
            batches[-1].calls.append(call)
        else:
            batches.append(Batch(parallel=safe, calls=[call]))
    
    return batches
```

### O que torna uma tool concurrency-safe?

```python
class ToolDefinition:
    def is_concurrency_safe(self, parsed_input: dict) -> bool:
        """Decide se ESTA chamada específica pode rodar em paralelo.
        
        NÃO é uma propriedade global da tool. Depende dos inputs.
        """
        if self.name == "read_file":
            return True  # sempre seguro (read-only)
        
        if self.name == "write_file":
            return False  # nunca seguro (mutação)
        
        if self.name == "shell":
            # Bash: parse command, verifica se é read-only
            return self._is_read_only_command(parsed_input["command"])
        
        if self.name == "web_search":
            return True  # sempre seguro (read-only)
        
        if self.name == "web_fetch":
            return True  # sempre seguro (read-only)
        
        return False  # default conservador
```

---

## 📐 Implementação para o aiw

### Batch Execution

```python
# src/ai_workspace/agents/tool_execution.py

import asyncio
from dataclasses import dataclass
from typing import AsyncGenerator

MAX_CONCURRENCY = 10  # Claude Code default

@dataclass
class ToolCall:
    id: str
    name: str
    input: dict

@dataclass
class Batch:
    parallel: bool
    calls: list[ToolCall]

async def execute_tools(
    calls: list[ToolCall],
    registry: ToolRegistry,
    context: ToolContext,
) -> AsyncGenerator[ToolResult, None]:
    """
    Executa tool calls com particionamento e paralelismo.
    
    Pipeline:
    1. Partition → batches (concurrent vs serial)
    2. Execute each batch:
       - Concurrent: asyncio.gather com semaphore
       - Serial: await sequencial
    3. Yield resultados na ordem original
    """
    batches = partition_tool_calls(calls, registry)
    
    for batch in batches:
        if batch.parallel:
            # Executa em paralelo com limite de concorrência
            sem = asyncio.Semaphore(MAX_CONCURRENCY)
            
            async def run_one(call: ToolCall):
                async with sem:
                    context.mark_in_progress(call.id)
                    result = await execute_single(call, context)
                    context.mark_complete(call.id)
                    return result
            
            results = await asyncio.gather(*[run_one(c) for c in batch.calls])
            for r in results:
                yield r
        else:
            # Executa sequencialmente
            for call in batch.calls:
                context.mark_in_progress(call.id)
                result = await execute_single(call, context)
                context.mark_complete(call.id)
                yield result
```

### Speculative Execution (futuro)

```python
async def execute_tools_streaming(
    model_stream: AsyncGenerator,  # modelo ainda gerando
    registry: ToolRegistry,
    context: ToolContext,
) -> AsyncGenerator[ToolResult, None]:
    """
    Speculative execution: começa a executar tools assim que
    o tool_use block chega no stream, sem esperar a resposta completa.
    
    Como Claude Code faz: o StreamingToolExecutor identifica tool_use
    blocks incrementalmente e os enfileira para execução imediata.
    """
    pending_tasks = []
    received_all = False
    
    async for chunk in model_stream:
        if chunk["type"] == "tool_use":
            call = ToolCall(id=chunk["id"], name=chunk["name"], input=chunk["input"])
            # Inicia execução IMEDIATAMENTE (não espera o resto da resposta)
            task = asyncio.create_task(execute_single(call, context))
            pending_tasks.append(task)
        
        elif chunk["type"] == "text":
            pass  # texto normal, continua acumulando
        
        elif chunk["type"] == "message_stop":
            received_all = True
    
    # Coleta resultados na ordem
    for task in pending_tasks:
        result = await task
        yield result
```

### Integração no AgentLoop

```python
# agents/loop.py

async def agent_loop(params: LoopParams):
    # ...
    tool_calls = []
    async for chunk in stream:
        if chunk["type"] == "tool_call":
            tool_calls.append(ToolCall(
                id=chunk["id"],
                name=chunk["name"],
                input=chunk["input"],
            ))
    
    if tool_calls:
        if params.parallel_tools and len(tool_calls) > 1:
            # Particiona e executa em paralelo
            async for result in execute_tools(tool_calls, registry, context):
                state.messages.append({"role": "tool", "content": result})
                yield LoopEvent(type="tool_result", data=result)
        else:
            # Sequencial (fallback)
            for call in tool_calls:
                result = await execute_single(call, context)
                state.messages.append({"role": "tool", "content": result})
                yield LoopEvent(type="tool_result", data=result)
```

---

## 📊 Benchmark esperado

| Cenário | Sequencial | Paralelo | Ganho |
|---------|-----------|----------|-------|
| 3 Reads (200ms cada) | 600ms | 200ms | 3x |
| 2 Reads + 1 Grep | 600ms | 200ms | 3x |
| Read + Edit + Read | 600ms | 400ms | 1.5x (Edit quebra batch) |
| 5 Reads | 1000ms | 200ms | 5x |

---

## ✅ Critérios de aceitação

- [ ] `partition_tool_calls()` implementado com algoritmo Claude Code
- [ ] `execute_tools()` suporta batches parallel + serial
- [ ] `is_concurrency_safe()` por tool (read_file=True, write_file=False, shell=parse)
- [ ] Semaphore limita concorrência a MAX_CONCURRENCY (10)
- [ ] Resultados yieldados na ordem original das chamadas
- [ ] Integrado no AgentLoop via `params.parallel_tools`
- [ ] Testes: `tests/test_agents/test_tool_execution.py`
  - `test_partition_reads_are_parallel`
  - `test_partition_edit_breaks_batch`
  - `test_partition_mixed_read_write`
  - `test_execute_parallel_faster_than_sequential`
  - `test_shell_read_only_is_safe`

---

## 📚 Referências

- [Claude Code Ch7: Concurrent Tool Execution](https://claude-code-from-source.com/ch07-concurrency/) — algoritmo completo
- [StreamingToolExecutor — Claude Wiki](https://claude-wiki.com/streaming-tool-executor.html) — implementação
- [toolOrchestration.ts source](https://github.com/codeaashu/claude-code/blob/126c31154f72ec9babb39142d173ef8c2a5a9803/src/services/tools/toolOrchestration.ts) — código real
