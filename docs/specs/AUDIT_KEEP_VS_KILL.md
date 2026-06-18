# Spec Audit: Keep vs Kill — Validação contra dados reais

> **Status:** 📋 Análise crítica | **Data:** 2026-06-18
> **Refs:** Ivern survey (312 devs), Stitch postmortem, AIAgentMinder postmortem, JetBrains survey

---

## 📊 O que os dados dizem

### Survey: 312 desenvolvedores (Ivern, Abril 2026)

**Maiores dores:**
| Dor | % | Nossa spec que ataca |
|-----|---|---------------------|
| "Perder track do que cada agente faz" | 62% | `SPEC_CONTEXT_MANAGEMENT.md` |
| "Copy-paste de contexto entre tools" | 58% | `SPEC_AGENT_MCP_TOOL.md` (interop) |
| "Gastar tempo gerenciando agentes" | 47% | `SPEC_TUI_V5.md` (dashboard) |
| "Agentes sobrescrevendo mudanças" | 41% | `SPEC_CONTEXT_MANAGEMENT.md` (curator) |
| "Estilo de código inconsistente" | 39% | (não atacamos — gap!) |
| "Perdeu trabalho por conflito" | 18% | Permission system existente |

**O que usuários querem (mas não têm):**
- BYOK (traga sua própria chave) — 48% preferem, 36% usam
- Coordenação entre múltiplos agentes
- Dashboard unificado

### Postmortems: o que foi tentado e abandonado

**Stitch (Mar 2026):** Deletaram o classifier de 9 categorias com 150 regex patterns. Motivo: "models got better at reading raw logs. The gap between surgical extraction and raw log closed. The extraction stopped earning its cost."

**AIAgentMinder (2026):** Deletaram 80% do produto. Motivo: Claude Code absorveu nativamente (auto-memory, rules, session memory). "Every token spent on redundant injection is a token not available for actual code."

**Grinta Coding Agent:** Abandonaram deep multi-agent planning. Motivo: "high token costs, slow execution, increased surface area for objective drift."

---

## 🔍 Auditoria das nossas specs

### ✅ KEEP — Alinhadas com dados reais

| Spec | Evidência |
|------|-----------|
| `SPEC_TUI_V5.md` | 62% querem saber o que agente faz. Dashboard = resposta direta |
| `SPEC_CONTEXT_MANAGEMENT.md` | 62% + 41% + 47% das dores atacadas por contexto visível |
| `SPEC_OUTPUT_MODES.md` | NDJSON = interoperabilidade entre tools (73% usam 2+) |
| `SPEC_AGENT_MCP_TOOL.md` | Multi-agente coordenado salva 11.4h/semana vs 5.2h |
| `SPEC_ERROR_HANDLING.md` | Stack traces não estruturados = perda de contexto |
| `SPEC_AGENT_LOOP.md` | Async generator = padrão comprovado (Claude Code, pi) |
| `SPEC_TOOL_EXECUTION.md` | Paralelismo = ganho real mensurável |

### ⚠️ SIMPLIFY — Boas ideias, complexidade questionável

| Spec | Problema | Recomendação |
|------|----------|-------------|
| `SPEC_RAG.md` | Hybrid search + RRF + rerank é overengineered para v0.2. Stitch aprendeu: "raw is better than pre-classified" | **Simplificar:** v0.2 = busca simples (embedding only). RRF e rerank são v0.3 |
| `SPEC_CONTEXT_COMPACTION.md` | 3 níveis é ambicioso. AIAgentMinder: "platform absorbed 80%" | **Simplificar:** v0.2 = L1 (cap tool results) + L3 (summarize). L2 é micro-otimização |
| `SPEC_DAG_EXECUTION.md` | Grinta abandonou deep planning. FlowBank é complexo | **Adiar:** DAG é v0.4+. Manter GraSP como visão de futuro |
| `SPEC_MEMORY_TREE.md` | Mage é paper de Jun 2026, sem implementação real validada | **Adiar:** Conceito promissor mas não validado em produção. RAG simples primeiro |

### ❌ KILL — Ideias que os dados contradizem

| Ideia | Evidência contra |
|-------|-----------------|
| **DeepSearch 7-step pipeline** (código existente) | Stitch: "preprocessor stopped earning its cost." Agente com web tools é melhor |
| **Plan-Execute como padrão principal** | Grinta: "abandoned deep planning." ReAct é mais robusto |
| **Context hooks customizados** | AIAgentMinder: "every token on redundant injection is a token lost." Deixa o modelo decidir |
| **Classificadores/parsers customizados** | Stitch deletou 150 regex patterns. Modelo ficou bom o suficiente |

---

## 🎯 O MVP real (baseado em dados)

O que usuários REALMENTE precisam no dia 1:

```
Prioridade 1 (dores 40%+):
  ✅ Dashboard TUI mostrando agentes ativos     (62% dor)
  ✅ NDJSON output para interoperabilidade       (58% dor)
  ✅ Contexto visível e modificável              (47% dor)

Prioridade 2 (dores 20-40%):
  ✅ MCP para coordenar múltiplos agentes        (41% dor)
  ✅ BYOK / Ollama-first (custo zero)            (48% preferem)

Prioridade 3 (nice to have):
  ⏸ RAG simples (embedding search)
  ⏸ Context compaction (L1 cap apenas)
  ⏸ Eval harness básico
```

**O que NÃO fazer no MVP:**
- ❌ RRF + rerank (overengineered)
- ❌ DAG execution (ninguém pediu)
- ❌ Memory tree (não validado em produção)
- ❌ Deep search pipeline (substituir por ReAct agent)
- ❌ Classificadores/parsers customizados (lição do Stitch)

---

## 📋 Plano de ação revisado

### Fase 0: Limpeza (hoje)
- Mover 15 TUI mortos → `_graveyard/`
- Arquivar 6 docs obsoletos
- Deletar `deep_search.py` (substituído por ReAct agent)

### Fase 1: Fundações (2-3 dias)
- `core/result.py` + `core/output.py` + `agents/loop.py`
- SÓ ReAct e Direct. Plan-Execute é Fase 3+

### Fase 2: TUI v5 mínimo (2-3 dias)
- AgentMonitor + Conversation + HelpBar
- Context ring no header
- SEM overlays complexos (só F1 help e F4 context inspector)

### Fase 3: O que usuários pediram (2-3 dias)
- RAG simples (embedding search, sem RRF)
- MCP agent tool
- Eval harness básico

### Fase 4+: Features avançadas (quando validado)
- RRF + rerank
- DAG execution
- Memory tree
- Context compaction L2-L3
