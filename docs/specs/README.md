# AI Workspace — Specs Index

> **16 specs de implementação | ~80KB | 18 papers referenciados**

---

## Por fase de implementação

### 🔴 Fase 0: Imediato (limpeza)
| # | Spec | O que faz |
|---|------|-----------|
| 0 | `PROMPT_CLEANUP.md` | Mover 15 TUI mortos, arquivar 6 docs velhos |

### 🟡 Fase 1: Fundações (2-3 dias)
| # | Spec | O que faz | Depende de |
|---|------|-----------|-----------|
| 1 | `SPEC_ERROR_HANDLING.md` | Result, Success, Failure, AiWError | — |
| 2 | `SPEC_OUTPUT_MODES.md` | `--output json\|ndjson` em todos comandos | #1 |
| 3 | `SPEC_AGENT_LOOP.md` | Async generator, ReAct + Direct | #2 (providers) |

### 🟢 Fase 2: TUI + Contexto (2-3 dias)
| # | Spec | O que faz | Depende de |
|---|------|-----------|-----------|
| 4 | `SPEC_TUI_V5.md` | Router pattern, AgentMonitor, Conversation | #3 |
| 5 | `SPEC_CONTEXT_COMPACTION.md` | L1 cap + L3 summarize | #3 |
| 6 | `SPEC_CONTEXT_MANAGEMENT.md` | Context Inspector (F4), /ctx commands | #4 |

### 🔵 Fase 3: Search + RAG + Swarm (3-4 dias)
| # | Spec | O que faz | Depende de |
|---|------|-----------|-----------|
| 7 | `SPEC_DEEP_RESEARCH_V2.md` | Graph-based multi-agent research | #3, `SPEC_DAG_EXECUTION` |
| 8 | `SPEC_RAG.md` | pgvector + Ollama embedding search | — |
| 9 | `SPEC_AGENT_MCP_TOOL.md` | Agente como MCP tool | #3 |
| 10 | `SPEC_TOOL_EXECUTION.md` | Paralelismo (partition + batches) | #3 |

### 🟣 Fase 4: Qualidade + Escala (2-3 dias)
| # | Spec | O que faz | Depende de |
|---|------|-----------|-----------|
| 11 | `SPEC_EVAL_HARNESS.md` | Métricas objetivas, pytest | #3 |
| 12 | `SPEC_SAFETY.md` | Sandbox + validação + deception detection | #3 |
| 13 | `SPEC_OBSERVABILITY.md` | Code-level traces, DiffTracker | #4 |

### ⚪ Fase 5+: Futuro
| # | Spec | O que faz |
|---|------|-----------|
| 14 | `SPEC_MEMORY_TREE.md` | Árvore de estado hierárquica (Mage paper) |
| 15 | `SPEC_DAG_EXECUTION.md` | DAG-based orchestration (GraSP + FlowBank) |
| 16 | `SPEC_INTEGRATION.md` | Mapa de conexões entre todos os módulos |

---

## Por área de conhecimento

| Área | Specs |
|------|-------|
| **Agent Loop** | `SPEC_AGENT_LOOP`, `SPEC_TOOL_EXECUTION` |
| **Research** | `SPEC_DEEP_RESEARCH_V2` |
| **Conhecimento** | `SPEC_RAG`, `SPEC_MEMORY_TREE` |
| **Interface** | `SPEC_TUI_V5` |
| **Contexto** | `SPEC_CONTEXT_COMPACTION`, `SPEC_CONTEXT_MANAGEMENT` |
| **Qualidade** | `SPEC_EVAL_HARNESS`, `SPEC_SAFETY`, `SPEC_OBSERVABILITY` |
| **Interoperabilidade** | `SPEC_OUTPUT_MODES`, `SPEC_AGENT_MCP_TOOL` |
| **Fundações** | `SPEC_ERROR_HANDLING`, `SPEC_INTEGRATION` |
| **Estratégia** | `AUDIT_KEEP_VS_KILL`, `CORRECTION_FEATURES_THAT_WORK` |
| **Executáveis** | `PROMPT_CLEANUP`, `PROMPT_IMPLEMENT_PHASE1` |

---

## Fontes de pesquisa referenciadas

| Paper/Produto | Specs que referenciam |
|---------------|----------------------|
| **Claude Code** (query.ts, compact/) | AgentLoop, Compaction, ToolExecution, Context |
| **pi** (agent-loop.ts) | AgentLoop |
| **Cursor** (context engine) | RAG, Context |
| **Kimi K2.6** (swarm, deep research) | DeepResearch, DAG |
| **GPT Researcher** (27.8K★) | DeepResearch |
| **STORM/Stanford** (18K★) | DeepResearch |
| **DuMate/Baidu** (58% SOTA) | DeepResearch |
| **Marco/Alibaba** (8B>30B) | DeepResearch |
| **Mage/Microsoft** (Jun 2026) | MemoryTree |
| **GraSP** (Apr 2026) | DAG |
| **FlowBank** (Jun 2026) | DAG |
| **Operational Safety** (Mai 2026) | Safety |
| **Observability Gap** (CHI 2026) | Observability |
| **peekctx** (TUI inspector) | Context |
| **ContextLens** (profiler) | Context |
| **dry-python/returns** | ErrorHandling |
| **ndjson-spec** | OutputModes |
| **fastmcp-agents** | MCP |
