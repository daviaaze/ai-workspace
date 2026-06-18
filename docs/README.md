# AI Workspace — Documentação

> **Versão:** v0.1 → v0.2 (planejamento)
> **Atualizado:** 2026-06-18

---

## Estrutura

```
docs/
├── 📋 Estratégia & Roadmap
│   ├── PLANO_AIW_V3_REALINHAMENTO.md    ← roadmap completo (fases 0-6)
│   ├── POSITIONING.md                    ← análise competitiva + diferenciação
│   └── VISION_PIPELINE.md               ← visão computacional (futuro)
│
├── 📐 Specs de implementação (16)
│   └── specs/                            ← specs detalhadas com código
│       ├── README.md                     ← índice das specs
│       ├── PROMPT_CLEANUP.md             ← executável: limpar repo
│       ├── PROMPT_IMPLEMENT_PHASE1.md    ← executável: fundações
│       ├── AUDIT_KEEP_VS_KILL.md         ← validação contra dados reais
│       ├── CORRECTION_FEATURES_THAT_WORK.md ← correção da análise
│       │
│       ├── SPEC_AGENT_LOOP.md            ← coração: async generator
│       ├── SPEC_DEEP_RESEARCH_V2.md      ← pesquisa: graph-based multi-agent
│       ├── SPEC_TUI_V5.md                ← interface: router pattern
│       ├── SPEC_RAG.md                   ← conhecimento: pgvector + Ollama
│       ├── SPEC_OUTPUT_MODES.md          ← interoperabilidade: JSON/NDJSON
│       ├── SPEC_ERROR_HANDLING.md        ← robustez: Result pattern
│       ├── SPEC_AGENT_MCP_TOOL.md        ← integração: agente como MCP tool
│       ├── SPEC_INTEGRATION.md           ← conexões entre todos os módulos
│       ├── SPEC_CONTEXT_COMPACTION.md    ← memória longa: pipeline progressivo
│       ├── SPEC_CONTEXT_MANAGEMENT.md    ← visibilidade: inspect + curate + optimize
│       ├── SPEC_TOOL_EXECUTION.md        ← performance: paralelismo
│       ├── SPEC_MEMORY_TREE.md           ← futuro: árvore de estado (Mage)
│       ├── SPEC_DAG_EXECUTION.md         ← futuro: orquestração (GraSP)
│       ├── SPEC_EVAL_HARNESS.md          ← qualidade: métricas objetivas
│       ├── SPEC_SAFETY.md                ← segurança: sandbox + validação
│       └── SPEC_OBSERVABILITY.md         ← debugging: code-level traces
│
├── 🔬 Pesquisa
│   └── research/
│       ├── RESEARCH_WHAT_USERS_WANT.md   ← 312 devs survey
│       ├── RESEARCH_FAILED_FEATURES.md   ← 4 postmortems
│       ├── RESEARCH_PAPERS_2026.md       ← 9 papers analisados
│       └── RESEARCH_PLANNING_AND_DEEP_RESEARCH.md ← 6 papers sobre pesquisa
│
├── ✅ Features implementadas (v0.1)
│   ├── BUDGET_ENFORCEMENT.md
│   ├── CONTEXT_AWARENESS.md
│   ├── INTERACTIVE_SESSION.md
│   ├── MESSAGE_QUEUE.md
│   ├── MODEL_FALLBACK.md
│   ├── PERMISSION_SYSTEM.md
│   ├── SEMANTIC_CACHE.md
│   └── SKILL_SYSTEM.md
│
└── 📦 archive/ (26 documentos históricos)
```

## Ordem de leitura recomendada

**Se você é novo no projeto:**
1. `POSITIONING.md` — o que é isso e por que existe
2. `PLANO_AIW_V3_REALINHAMENTO.md` — o que vamos construir
3. `specs/SPEC_INTEGRATION.md` — como as peças se conectam

**Se você vai implementar:**
1. `specs/PROMPT_CLEANUP.md` — limpar o repo
2. `specs/PROMPT_IMPLEMENT_PHASE1.md` — construir as fundações
3. `specs/README.md` — índice completo das specs

**Se você quer entender as decisões:**
1. `research/RESEARCH_WHAT_USERS_WANT.md` — o que usuários reais pedem
2. `research/RESEARCH_FAILED_FEATURES.md` — o que NÃO fazer
3. `specs/AUDIT_KEEP_VS_KILL.md` — quais specs passaram na validação
