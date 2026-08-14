# Context Workbench — Observabilidade da Janela de Contexto

> **Data:** 2026-06-16 | **Status:** ⚪ Pós-fila de mensagens | **Arquivos:** `agents/context_manager.py`, `tui/context_workbench.py`

---

## 🎯 Problema

A janela de contexto do agente é o recurso mais valioso e mais escasso. Cada token enviado ao modelo tem custo financeiro e impacto na qualidade das respostas. Hoje o contexto é gerenciado de forma **opaca** — o usuário não sabe:

- Quanto da janela de 128K tokens está sendo usado
- Quais blocos de contexto consomem mais tokens
- O que pode ser removido sem perder qualidade
- Como preservar contexto valioso entre sessões

---

## 🧠 Solução: Context Workbench

Um sistema de **observabilidade e gestão** da janela de contexto, com visualização estilo grafo do Obsidian, onde cada bloco de contexto é um nó conectado.

### Backend: `ContextManager` (`agents/context_manager.py`)

```
ContextManager
├── _blocks: dict[str, ContextBlock]     ← todos os blocos
├── _block_order: list[str]              ← ordem de injeção
├── _pinned_ids: set[str]                ← blocos fixados (sempre incluídos)
├── _excluded_ids: set[str]              ← blocos excluídos (nunca incluídos)
├── _snapshots: dict[str, ContextSnapshot] ← snapshots salvos
│
├── add_block(type, content, ...) → str  ← adiciona bloco
├── pin_block(id)                        ← fixa (sempre incluir)
├── exclude_block(id)                    ← exclui (nunca incluir)
├── remove_block(id)                     ← remove (recursivo nos filhos)
│
├── total_tokens: int                    ← tokens ativos
├── pinned_tokens: int                   ← tokens fixados
├── budget_used_pct: float               ← % da janela usada
├── budget_status: str                   ← 🟢🟡🟠🔴
├── get_budget_bar(width) → str          ← barra ASCII
│
├── format_for_injection(max_tokens) → str ← formata para o prompt
├── auto_trim(target_tokens) → int       ← auto-trim por importância
├── auto_pin_important(threshold) → int  ← auto-pin blocos importantes
│
├── save_snapshot(label) → str           ← salva estado atual
├── load_snapshot(id) → bool             ← restaura snapshot
└── import_from_session(entries) → int   ← importa do SessionStore
```

### Frontend: `ContextWorkbench` (`tui/context_workbench.py`)

```
┌─ Context Workbench ───────────────────────────────────────────────┐
│ Budget: [████████░░░░░░░░░░] 45%  12,340/128,000 tokens  🟡 Getting│
│                                                                   │
│ Context Tree                      │  Block Detail                  │
│ ───────────────────────────────── │ ────────────────────────────── │
│ 📁 Project Context (500t)         │  Type: User Message            │
│   📄 src/auth.py (200t)           │  Tokens: 340                   │
│ 📝 "Fix the auth bug" (340t) 📌  │  Pinned: Yes 📌               │
│ 🤖 "I'll analyze..." (180t)      │  Importance: 85%               │
│ 🔧 read_file auth.py (50t)       │  ───────────────────────       │
│ 📋 [file content...] (1200t)     │  Fix the auth middleware bug    │
│ ✏️ edit_file auth.py (80t)      │  in the login flow. The JWT    │
│ 📦 [Compaction #1] (600t)        │  validation is failing when...  │
│                                   │                                │
│ [p]in [x]clude [v]iew [s]nap     │  [p] Pin  [x] Exclude          │
│                                   │  [s] Save Snapshot             │
│ ↑↓ nav  p pin  x exclude  Enter detail  v full content             │
│ s snapshot  t auto-trim  a auto-pin  Tab switch  q/Esc close       │
└───────────────────────────────────────────────────────────────────┘
```

### Tipos de Bloco de Contexto

| Tipo | Ícone | Descrição | Exemplo |
|------|-------|-----------|---------|
| `USER_MESSAGE` | 📝 | Mensagem do usuário | "Fix the auth middleware bug" |
| `ASSISTANT_RESPONSE` | 🤖 | Resposta do agente | "I'll analyze the auth flow..." |
| `TOOL_CALL` | 🔧 | Chamada de ferramenta | read_file, write_file, shell_exec |
| `TOOL_RESULT` | 📋 | Resultado da ferramenta | Conteúdo do arquivo lido |
| `FILE_READ` | 📄 | Arquivo lido pelo agente | src/auth.py |
| `FILE_EDIT` | ✏️ | Arquivo editado pelo agente | Edit: adicionar type hints |
| `PROJECT_CONTEXT` | 📁 | Contexto automático do projeto | Git status, tree, branch |
| `SESSION_CONTEXT` | 🧠 | Histórico da sessão | Conversa anterior compactada |
| `COMPACTION` | 📦 | Sumário de compactação | Auto-gerado pelo sistema |
| `PINNED_KB` | 📌 | Bloco fixado pelo usuário | "Sempre usar pytest, não unittest" |
| `SYSTEM_PROMPT` | ⚙️ | Instruções do sistema | System prompt do agente |

---

## 🔗 Integração com o Sistema

### Fluxo de Injeção de Contexto

```
User Message
     │
     ▼
AgentWorker._run_crew_sync()
     │
     ├─→ ContextBundle.build()        ← projeto (git, tree, language)
     ├─→ ContextManager.add_block()   ← registra no manager
     ├─→ SessionStore.get_entries()   ← histórico da sessão
     ├─→ ContextManager.import_from_session()
     ├─→ ContextManager.format_for_injection()
     │
     ▼
Prompt do agente = System Prompt + Contexto formatado + User Message
```

### TUI Integration

```
Ctrl+E → abre ContextWorkbench (overlay)
  - Mostra árvore de contexto em tempo real
  - Budget bar atualiza a cada refresh
  - Pin/Exclude afetam a próxima injeção
  - Snapshots salvos podem ser restaurados
```

### AgentWorker Integration

```python
# worker.py — adicionar ao AgentConfig
context_manager: ContextManager | None = None

# worker.py — em _run_crew_sync()
if self.config.context_manager:
    # Registra project context no manager
    for block_data in project_context_blocks:
        self.config.context_manager.add_block(...)
    
    # Usa o manager para formatar em vez de string manual
    context_str = self.config.context_manager.format_for_injection()
```

---

## 📊 Token Budget

### Estratégia de Gestão

| Cenário | Ação |
|---------|------|
| 🟢 < 40% usado | Sem ação — bastante espaço |
| 🟡 40-70% usado | Sugerir trimming de blocos grandes |
| 🟠 70-90% usado | Auto-trim de blocos de baixa importância |
| 🔴 > 90% usado | Compactação forçada + exclusão de tool results |

### Política de Auto-Trim

```python
def auto_trim(target_tokens=80%):
    1. Nunca remove blocos pinned
    2. Ordena por (importância ASC, timestamp ASC)
    3. Remove blocos de menor prioridade até caber no budget
    4. Ferramentas de leitura e resultados são primeiros candidatos
    5. Compactações de histórico são preservadas
```

---

## 💾 Context Snapshots

Salvar e restaurar o estado completo da janela de contexto:

```
ContextManager.save_snapshot("antes do refactor do auth")
  → snapshot_id: "a1b2c3d4"
  → salva todos os blocos com seus estados (pin/exclude)

ContextManager.load_snapshot("a1b2c3d4")
  → restaura exatamente o mesmo estado
  → útil para: continuar sessão, compartilhar contexto entre agentes
```

### Casos de Uso

1. **Pausar e retomar**: Salvar snapshot antes de fechar, restaurar ao abrir
2. **Branching**: Salvar snapshot, explorar caminho alternativo, restaurar se necessário
3. **Compartilhar**: Salvar contexto de debugging para outro agente usar
4. **Template**: Criar snapshot com blocos pinned de convenções do projeto

---

## 🛣️ Roadmap

### ✅ Fase 1 — MVP (hoje)

- [x] `ContextManager` com CRUD, pin/exclude, token budget, snapshots
- [x] `ContextWorkbench` widget TUI com tree, budget bar, detail panel
- [ ] Wire `Ctrl+E` no `tui/app.py` para abrir o workbench
- [ ] Integrar `ContextManager` no `AgentWorker._run_crew_sync()`
- [ ] Conectar `PersistentAgentSession` ao `ContextManager`

### 🔮 Fase 2 — Visualização estilo Obsidian (futuro)

- [ ] Renderizar grafo real (force-directed ou hierarchical)
- [ ] Navegação por grafo com zoom/pan
- [ ] Cores por tipo de bloco
- [ ] Arestas mostrando relações (parent/child, references, affects_file)
- [ ] Filtro por tipo ("mostrar só arquivos editados")
- [ ] Busca textual no grafo

### 🔮 Fase 3 — Gestão Avançada (futuro)

- [ ] Context templates (ex: "python project conventions")
- [ ] Auto-tagging de blocos por conteúdo
- [ ] Métricas de efetividade do contexto (blocos referenciados vs ignorados)
- [ ] Sugestões automáticas de limpeza baseadas em uso
- [ ] Export/import para formato portável
- [ ] Integração com Knowledge Base (blocos pinned viram KB entries)

---

## 📁 Arquivos

| Arquivo | Descrição | Linhas |
|---------|-----------|--------|
| `src/ai_workspace/agents/context_manager.py` | Backend — CRUD, budget, snapshots, formatação | ~480 |
| `src/ai_workspace/tui/context_workbench.py` | Frontend TUI — tree, budget bar, detail, snapshots | ~380 |
| `src/ai_workspace/agents/context.py` | Existente — ContextBundle (project context injection) | ~220 |
| `src/ai_workspace/tui/app.py` | A integrar — wire Ctrl+E, passar ContextManager ao Worker | — |
| `src/ai_workspace/tui/worker.py` | A integrar — usar ContextManager na execução | — |
| `src/ai_workspace/agents/session.py` | A integrar — conectar ao ContextManager | — |

---

## 🔑 Keybindings do ContextWorkbench

| Tecla | Ação |
|-------|------|
| `↑/↓` | Navegar blocos |
| `p` | Toggle pin (📌 fixar) |
| `x` | Toggle exclude (🚫 remover) |
| `Enter` | Expandir detalhes |
| `v` | Ver conteúdo completo |
| `s` | Salvar snapshot |
| `l` | Listar/ocultar snapshots |
| `1-5` | Carregar snapshot por índice |
| `t` | Auto-trim (cortar para caber no budget) |
| `a` | Auto-pin importantes |
| `Tab` | Alternar foco tree ↔ detail |
| `q/Esc` | Fechar workbench |

---

## 📈 Métricas de Sucesso

| Métrica | Atual | Meta |
|---------|-------|------|
| Visibilidade do contexto | 0% (usuário não vê) | 100% (Ctrl+E a qualquer momento) |
| Blocos gerenciáveis | 0 (tudo automático) | pin/exclude/trim manuais |
| Snapshots salvos | N/A | Usuário salva e restaura contexto |
| Token budget awareness | Não reportado | Barra visível + alertas |
| Tempo para encontrar info no contexto | Impossível | Navegação em árvore < 5s |
