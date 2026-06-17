# Interactive Persistent Session — Message Queue + Agent Loop

> **Data:** 2026-06-17 | **Status:** ✅ Implemented | **Arquivos:** `agents/message_queue.py`, `tui/worker.py`, `agents/session.py`

---

## 🎯 Problema

Agentes AIW eram **one-shot**: executavam uma tarefa e morriam. O usuário não podia enviar follow-ups, interromper o agente mid-execution, ou manter conversa contínua entre iterações.

---

## 🧠 Solução: MessageQueue + Agent Loop

### Arquitetura

```
Usuário digita no TUI/CLI
        │
        ▼
┌──────────────────────┐
│    MessageQueue       │  ← agents/message_queue.py
│  Async, thread-safe   │
│  Priority 0-10+       │
│  Interrupt detection  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   AgentWorker         │  ← tui/worker.py
│  _agent_loop():       │
│  1. dequeue message   │
│  2. inject into ctx   │
│  3. run crew/agent    │
│  4. output → queue    │
│  5. check for more    │
│  6. repeat            │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ PersistentAgentSession│  ← agents/session.py
│  SessionStore (PG)    │
│  Auto-compaction      │
│  JSONL export         │
└──────────────────────┘
```

### Priority System

| Nível | Comportamento |
|-------|--------------|
| 0-4 | Normal — appended to accumulated context |
| 5-9 | High — processed next, context preserved |
| 10+ (`!`) | **Interrupt** — clears accumulated context, fresh restart |

### Uso no TUI

```
> fix the auth middleware bug
[agent runs...]
> also add tests for edge cases        ← appended to context
> ! forget all that, just fix the bug  ← priority 10, resets context
```

---

## 📦 Componentes

| Componente | Arquivo | Descrição |
|-----------|---------|-----------|
| `MessageQueue` | `agents/message_queue.py` | Fila async/thread-safe com prioridade, batch drain, interrupt |
| `AgentWorker` | `tui/worker.py` | Loop contínuo: dequeue → executa → output → check queue |
| `PersistentAgentSession` | `agents/session.py` | Multi-turn conversation com history injection e auto-compaction |
| `SessionStore` | `core/sessions.py` | PostgreSQL CRUD + JSONL export (pi-compatible) |

### CLI equivalente

```bash
aiw agent "fix the auth middleware bug"    # one-shot
aiw session start                          # persistent session
aiw session chat "also add tests"          # follow-up
aiw session list                           # list sessions
aiw session export                         # JSONL export
```

---

## 🔗 Integrações

- **SmartRouter**: modelo selecionado antes de cada execução
- **ContextManager**: contexto do projeto injetado automaticamente
- **PermissionGate**: operações perigosas pausam e pedem aprovação
- **BudgetEnforcer**: verificação de orçamento antes de cada chamada LLM
