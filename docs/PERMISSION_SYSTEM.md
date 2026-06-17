# Permission/Preview System — Safety Gate for File Operations

> **Data:** 2026-06-17 | **Status:** ✅ Implemented | **Arquivos:** `tui/permissions.py`, `tui/worker.py`

---

## 🎯 Problema

Agentes de código podem modificar arquivos arbitrariamente. Sem um gate de permissão, um agente em loop ou um prompt mal formulado pode causar danos irreversíveis ao codebase.

---

## 🧠 Solução: PermissionGate + PermissionModal

```
Agent tenta edit_file / write_file / shell_exec
        │
        ▼
┌──────────────────────┐
│   PermissionGate      │
│  Analisa tool call    │
│  Identifica ops       │
│  perigosas            │
└──────────┬───────────┘
           │ dangerous?
           ▼
┌──────────────────────┐
│   PermissionModal     │  ← TUI overlay
│  Mostra diff/preview  │
│  Teclas: a/A/d        │
│  a = approve once     │
│  A = approve always   │
│  d = deny             │
└──────────┬───────────┘
           │ verdict flows back
           ▼
     Agent continua (ou aborta)
```

---

## 📦 Componentes

| Componente | Arquivo | Descrição |
|-----------|---------|-----------|
| `PermissionGate` | `tui/permissions.py` | Analisa tool calls, identifica operações perigosas, cria `PermissionRequest` |
| `PermissionModal` | `tui/permissions.py` | TUI modal: diff preview, syntax highlight, approve/deny/always |
| `_poll_permissions()` | `tui/worker.py` | Polling 0.5s: detecta `worker.pending_permission` e mostra modal |

### Verdictos

| Tecla | Significado | Escopo |
|-------|------------|--------|
| `a` | Approve once | Só esta operação |
| `A` | Approve always | Todas as operações deste tipo nesta sessão |
| `d` | Deny | Aborta esta operação |

### Integração CLI

```bash
aiw agent "refactor auth module" --review
# Mostra preview de cada arquivo antes de editar
# Prompt: [a]pprove / [d]eny / [A]pprove all
```

---

## 🔗 Dependências

- **AgentWorker**: intercepta tool calls durante execução
- **TUI**: PermissionModal overlay no terminal
- **CLI**: prompt interativo via `CLIStreamSink.request_permission()`
