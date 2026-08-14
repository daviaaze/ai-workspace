# Prompt: Limpeza do Repositório AI Workspace

> Use este prompt para iniciar uma sessão de limpeza do código.

---

## Objetivo

Remover código morto, arquivar documentação obsoleta, e preparar o repositório para a implementação da Fase 1 do plano v0.2.

## Contexto

O repositório acumulou ~155KB de código TUI não utilizado (15 arquivos) e ~20 documentos de planejamento de fases anteriores que já foram executadas ou abandonadas. A limpeza é necessária antes de começar a implementar a nova arquitetura.

## Tarefas

### 1. Mover arquivos TUI mortos para `src/ai_workspace/tui/_graveyard/`

Estes 15 arquivos NÃO são importados por nenhum outro código e representam versões abandonadas do TUI:

```
agent_grid.py        (10KB) — grid alternativo nunca integrado
agent_inventory.py   (11KB) — inventário nunca integrado
bottom_bar.py         (3KB) — barra inferior separada
context_graph_panel.py (10KB) — grafo de contexto isolado
dashboard.py         (15KB) — dashboard cards (vai virar overlay no v5)
data.py               (7KB) — data layer isolado
git_panel.py          (18KB) — painel git isolado (vai virar overlay no v5)
graph.py              (26KB) — grafo de dependências isolado
header.py             (4KB) — header separado (será reescrito no v5)
help.py               (7KB) — help screen separado
metrics.py            (9KB) — métricas isoladas
research_queue.py     (9KB) — fila de pesquisa isolada
side_panel.py         (17KB) — painel lateral isolado
task_table.py         (9KB) — tabela de tasks isolada (vai virar overlay no v5)
cyberdeck.tcss        (2KB) — tema CSS não usado
```

**Regras:**
- NÃO deletar — apenas mover para `_graveyard/`
- Verificar antes de mover: `grep -r "from.*agent_grid" src/` deve retornar vazio
- Se algum arquivo for importado por `app.py` via import dinâmico, NÃO mover

### 2. Arquivar documentação obsoleta

Mover para `docs/archive/` os documentos que descrevem fases já concluídas ou features que nunca serão implementadas:

```
BUILD_LOG.md                       — log de build, não é spec
REQUIREMENT_SEARCH_KNOWLEDGE_FORMAT.md — substituído pelo plano v3
RESEARCH_MCP.md                    — substituído por SPEC_AGENT_MCP_TOOL
TOOLS_RESEARCH_REPORT.md           — relatório, não spec
PI_INTEGRATION.md                  — integração externa, fora do escopo
CONTEXT_WORKBENCH.md               — feature parcial, será reimplementada
```

**Regras:**
- NÃO arquivar docs de features implementadas e vivas:
  - `BUDGET_ENFORCEMENT.md` (✅ implementado)
  - `CONTEXT_AWARENESS.md` (✅ implementado)
  - `INTERACTIVE_SESSION.md` (✅ implementado)
  - `MESSAGE_QUEUE.md` (✅ implementado)
  - `MODEL_FALLBACK.md` (✅ implementado)
  - `PERMISSION_SYSTEM.md` (✅ implementado)
  - `SEMANTIC_CACHE.md` (✅ implementado)
  - `SKILL_SYSTEM.md` (✅ implementado)
  - `VISION_PIPELINE.md` (📋 design ativo)
  - `PLANO_AIW_V3_REALINHAMENTO.md` (📋 plano atual)

### 3. Verificar se `__init__.py` do TUI ainda funciona

Depois de mover os arquivos, verificar que `from ai_workspace.tui import run_tui` ainda funciona.

### 4. Atualizar `tui/__init__.py`

Remover exports de arquivos movidos (se houver). Manter apenas:
```python
from ai_workspace.tui.app import AIWorkspaceApp, run_tui
```

### 5. Criar `_graveyard/README.md`

Explicar por que os arquivos estão ali e quando podem ser resgatados:
```markdown
# TUI Graveyard

These files were part of TUI v2, v3, and v4 experiments. They are kept for reference.
Some will be resurrected as overlays (ModalScreen) in TUI v5:
- dashboard.py → DashboardScreen (F3 overlay)
- git_panel.py → GitScreen (Ctrl+G overlay)
- task_table.py → TasksScreen (overlay)

Do NOT import from this directory. These files are not maintained.
```

### 6. Commitar

Mensagem: `chore: cleanup dead TUI code and obsolete docs (prep for v0.2 Phase 1)`

## Verificação

Depois da limpeza, verificar:
- [ ] `aiw tui` ainda funciona (abre e fecha sem crash)
- [ ] `aiw health` ainda funciona
- [ ] `git status` mostra apenas arquivos movidos/deletados
- [ ] Nenhum import quebrado (`python -c "from ai_workspace.tui import run_tui"`)
