# Message Queue — Fila de Mensagens Multi-Turn para Agentes

> **Data:** 2026-06-16 | **Status:** ✅ Implementado | **Arquivos:** `agents/message_queue.py`, `tui/worker.py`, `tui/app.py`, `tui/widgets.py`, `agents/session.py`

---

## 🎯 Problema

Agentes AIW eram **one-shot**: executavam uma tarefa e morriam. O usuário não podia:

- Enviar follow-ups enquanto o agente trabalhava
- Interromper e redirecionar o agente mid-execution
- Acumular múltiplas instruções em fila
- Manter conversa contínua com contexto preservado entre iterações

---

## 🧠 Solução: MessageQueue + Agent Loop

### Arquitetura

```
Usuário digita no TUI/CLI
        │
        ▼
┌──────────────────────┐
│    MessageQueue       │  ← agents/message_queue.py
│                       │
│  Async, thread-safe   │
│  Priority levels      │
│  Interrupt detection  │
│  Batch drain          │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   AgentWorker         │  ← tui/worker.py
│                       │
│  _agent_loop():       │
│  1. dequeue message   │
│  2. build task with   │
│     accumulated ctx   │
│  3. execute agent     │
│  4. accumulate result │
│  5. check queue →     │
│     continue or idle  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   AgentLane (TUI)     │  ← tui/widgets.py
│                       │
│  📨N pending counter  │
│  Live streaming       │
│  Context preserved    │
└──────────────────────┘
```

### Priority System

| Priority | Valor | Prefixo | Comportamento |
|----------|-------|---------|---------------|
| `NORMAL` | 0-4 | `texto normal` | Adicionado ao contexto acumulado, processado em ordem |
| `HIGH` | 5-9 | (via API) | Processado antes dos NORMAL, mantém contexto |
| `INTERRUPT` | 10+ | `!texto` | **Zera todo contexto acumulado**, restart fresco |

---

## 📁 Arquivos Implementados

### `agents/message_queue.py` (NOVO)

```python
@dataclass
class PendingMessage:
    role: str           # "user", "system"
    content: str
    priority: int = 0   # 0-4 normal, 5-9 high, 10+ interrupt
    message_id: str
    timestamp: float

class MessageQueue:
    enqueue(msg)           # Async — adiciona à fila
    enqueue_nowait(msg)    # Sync thread-safe
    dequeue() → msg        # Bloqueante
    dequeue_or_none()      # Não-bloqueante
    dequeue_all() → [msg]  # Drena tudo
    wait_for_message(t/o)  # Com timeout
    
    is_interrupted: bool   # Flag de interrupção
    clear_interrupt()
    pending_count: int     # Quantos na fila
    has_pending: bool
```

### `tui/worker.py` — Refatoração Principal

**Antes:**
```python
worker.run_agent(task)     # One-shot: executa, morre
worker.send_message(msg)   # Só loga, não injeta
```

**Depois:**
```python
worker.start_loop(task)        # Loop mode: fica vivo
worker.send_message(msg, 0)    # Enfileira normal
worker.send_message(msg, 10)   # Interrupt — zera contexto

# Loop interno:
_agent_loop():
    while alive:
        msg = await queue.wait_for_message(timeout=2s)
        if interrupt: reset_context()
        drain_extra_messages()
        task = build_loop_task(messages)
        result = execute(task)
        accumulate_result(task, result)
        if queue empty: go IDLE
        else: continue
```

### `tui/app.py` — Integração TUI

| Ação | Antes | Depois |
|------|-------|--------|
| Spawn agent | `worker.run_agent(task)` | `worker.start_loop(task)` |
| Digitar na barra | `worker.send_message(text)` | `worker.send_message(text, priority)` |
| Interromper | ❌ Impossível | `!nova instrução` → priority=10 |
| Indicador de fila | ❌ | `📨N` no header do AgentLane |

### `tui/widgets.py` — AgentLane

- `pending_messages: reactive[int]` — contador de fila
- `📨N` no header quando `pending_messages > 0`
- `_drain_queue()` atualiza o contador do worker

### `agents/session.py` — CLI Session

```python
session = PersistentAgentSession(loop_mode=True)
await session.start_loop()        # Loop contínuo
await session.enqueue("task 1")   # Não bloqueia
await session.enqueue("!reset")   # Interrupt
```

---

## 🔄 Fluxo de uma Sessão com Múltiplas Mensagens

```
T=0s   Usuário: "Fix the auth middleware bug"
         → worker.start_loop("Fix auth...")
         → _agent_loop inicia
         → Dequeue: msg1
         → Executa agente (crewAI kickoff em thread)
         
T=15s  Usuário: "Also check the rate limiter"
         → worker.send_message("Also check...", priority=0)
         → Enfileirado: 📨1
         → AgentLane mostra pending=1
         
T=30s  Usuário: "! forget all that, just fix the JWT validation"
         → worker.send_message("just fix JWT", priority=10)
         → Interrupt flag set
         → Contexto acumulado zerado
         
T=45s  Agente termina kickoff atual
         → Dequeue: msg2 (normal) + msg3 (interrupt)
         → Interrupt detectado → zera contexto
         → Só processa msg3: "just fix the JWT validation"
         → Novo kickoff com contexto limpo
         
T=60s  Agente termina
         → Fila vazia → IDLE
         → "🤖 Agent idle — waiting for next instruction..."
```

---

## 📊 Métricas

| Funcionalidade | Antes | Depois |
|---------------|-------|--------|
| Multi-mensagem | ❌ | ✅ Loop contínuo |
| Fila de mensagens | ❌ | ✅ MessageQueue |
| Interrupção mid-exec | ❌ | ✅ priority=10 |
| Follow-ups sem espera | ❌ | ✅ enfileiramento assíncrono |
| Indicador visual de fila | ❌ | ✅ 📨N no header |
| Contexto acumulado | ❌ | ✅ Acumula entre iterações |
| IDLE state | ❌ | ✅ Agente espera novas mensagens |

---

## 🔗 Integração com Outros Sistemas

- **ContextManager**: O `_accumulate_result()` do AgentLoop alimenta o `ContextManager` com blocos de contexto
- **SessionStore**: Mensagens são persistidas via `PersistentAgentSession`
- **PermissionGate**: Funciona normalmente no loop — permissões são verificadas a cada tool call
- **SmartRouter**: Cada iteração do loop pode re-rotear o modelo se necessário
