# Context Awareness — Project Structure Injection

> **Data:** 2026-06-17 | **Status:** ✅ Implemented | **Arquivos:** `agents/context.py`, `agents/context_manager.py`, `tui/context_workbench.py`

---

## 🎯 Problema

O agente precisa entender o codebase antes de agir: estrutura de diretórios, estado do git, arquivos abertos, linguagem do projeto. Sem isso, o agente gera código genérico que não se integra ao projeto.

---

## 🧠 Solução: Três Camadas de Contexto

```
┌─────────────────────────────────────────────┐
│ 1. ContextBundle (agents/context.py)        │
│    Coleta automática do ambiente:           │
│    • Git: branch, status, last commits      │
│    • Tree: estrutura de diretórios          │
│    • Language: Python/TS/Rust detectado     │
│    • Recent files: últimos arquivos abertos │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│ 2. ContextManager (agents/context_manager)  │
│    Gestão da janela de contexto:            │
│    • Token budget (128K window)             │
│    • add_block / pin / exclude / snapshot   │
│    • Auto-trim quando budget se esgota      │
│    • 480 linhas de lógica de gestão         │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│ 3. ContextWorkbench (tui/context_workbench) │
│    Visualização estilo Obsidian:            │
│    • Tree view dos blocos de contexto       │
│    • Budget bar (% usado)                   │
│    • Detail panel (conteúdo de cada bloco)  │
│    • Ctrl+E para abrir                      │
│    • 380 linhas                             │
└─────────────────────────────────────────────┘
```

---

## 📦 Componentes

| Componente | Linhas | Descrição |
|-----------|--------|-----------|
| `ContextBundle` | `agents/context.py` | Coleta git branch, status, tree, language, recent files |
| `ContextManager` | `agents/context_manager.py` (480) | CRUD de blocos, token budget, pin/exclude, snapshots |
| `ContextWorkbench` | `tui/context_workbench.py` (380) | UI: tree view, budget bar, detail panel, Ctrl+E |

### Token Budget

| Status | % usado | Significado |
|--------|---------|-------------|
| 🟢 | < 50% | Espaço abundante |
| 🟡 | 50-75% | Moderado — monitorar |
| 🟠 | 75-90% | Alto — considerar trim |
| 🔴 | > 90% | Crítico — auto-trim ativa |

### Comandos do Workbench (Ctrl+E)

| Tecla | Ação |
|-------|------|
| `↑↓` | Navegar blocos |
| `p` | Pin (sempre incluir) |
| `x` | Exclude (nunca incluir) |
| `d` | Delete bloco |
| `s` | Salvar snapshot |
| `Enter` | Ver detalhes do bloco |

---

## 🔗 Integrações

- **AgentWorker**: `_run_crew_sync()` injeta contexto antes de cada execução
- **AgentOrchestrator**: `_inject_project_context()` usa ContextBundle
- **PersistentAgentSession**: contexto acumulado entre turnos
