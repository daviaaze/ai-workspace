# AI Workspace — Specs Index

> **24 specs implementados | 792 testes | 97 source files**

---

## Status dos specs

| Spec | Status |
|------|--------|
| `SPEC_AGENT_LOOP.md` | ✅ Implementado |
| `SPEC_OUTPUT_MODES.md` | ✅ Implementado |
| `SPEC_ERROR_HANDLING.md` | ✅ Implementado |
| `SPEC_TUI_V5.md` | ✅ Implementado |
| `SPEC_CONTEXT_COMPACTION.md` | ✅ Implementado |
| `SPEC_CONTEXT_MANAGEMENT.md` | ✅ Implementado |
| `SPEC_DEEP_RESEARCH_V2.md` | ✅ Implementado |
| `SPEC_RAG.md` | ✅ Implementado |
| `SPEC_AGENT_MCP_TOOL.md` | ✅ Implementado |
| `SPEC_TOOL_EXECUTION.md` | ✅ Implementado |
| `SPEC_EVAL_HARNESS.md` | ✅ Implementado |
| `SPEC_SAFETY.md` | ✅ Implementado |
| `SPEC_OBSERVABILITY.md` | ✅ Implementado |
| `SPEC_MEMORY_TREE.md` | ✅ Implementado |
| `SPEC_DAG_EXECUTION.md` | ✅ Implementado |
| `SPEC_LOOP_PATTERNS.md` | 📋 Spec (nova) |
| `SPEC_WORKTREE_MANAGER.md` | 📋 Spec (nova) |
| `SPEC_JOB_QUEUE_VISUAL_WORKFLOW.md` | 📋 Spec (nova) |
| `SPEC_INTEGRATION.md` | 📋 Spec (arquitetura documentada) |
| `PROMPT_CLEANUP.md` | ✅ Executado |
| `CORRECTION_FEATURES_THAT_WORK.md` | 📋 Análise |

---

## Por área

| Área | Specs |
|------|-------|
| **Agent Operations** | `SPEC_AGENT_LOOP`, `SPEC_TOOL_EXECUTION`, `SPEC_MEMORY_TREE`, `SPEC_DAG_EXECUTION` |
| **Production Loops** | `SPEC_LOOP_PATTERNS`, `SPEC_WORKTREE_MANAGER`, `SPEC_JOB_QUEUE_VISUAL_WORKFLOW` |
| **Research** | `SPEC_DEEP_RESEARCH_V2` |
| **Knowledge** | `SPEC_RAG` |
| **TUI** | `SPEC_TUI_V5` |
| **Context** | `SPEC_CONTEXT_COMPACTION`, `SPEC_CONTEXT_MANAGEMENT` |
| **Quality** | `SPEC_EVAL_HARNESS`, `SPEC_SAFETY`, `SPEC_OBSERVABILITY` |
| **Interop** | `SPEC_OUTPUT_MODES`, `SPEC_AGENT_MCP_TOOL` |
| **Foundations** | `SPEC_ERROR_HANDLING`, `SPEC_INTEGRATION` |
| **Strategy** | `AUDIT_KEEP_VS_KILL`, `CORRECTION_FEATURES_THAT_WORK` |

---

## Arquitetura (atual)

```
src/ai_workspace/
├── agents/
│   ├── loop.py              AgentLoop (DIRECT, REACT, PLAN_EXECUTE, REWOO)
│   ├── tool_execution.py    Tool parallel execution (semaphore)
│   ├── memory_tree.py       Hierarchical state tree (Mage)
│   ├── dag_executor.py      DAG-based orchestration (GraSP + FlowBank)
│   ├── compaction.py        Context compaction (L1/L2/L3)
│   ├── safety.py            Safety sandbox + deception detection
│   ├── rag_tool.py          RAG tool integration
│   └── ...
├── core/
│   ├── result.py            Result, Success, Failure, AiWError
│   └── output.py            OutputFormatter (JSON, NDJSON, Rich)
├── evals/
│   └── __init__.py          Eval harness (3 suites, 6 cases)
├── knowledge/
│   └── rag.py               pgvector + nomic-embed + hybrid search
├── observability/
│   └── __init__.py          DiffTracker, AgentTrace, TraceStore
├── mcp_server/
│   └── agent_tools.py       aiw_agent_run, aiw_agent_status, aiw_agent_kill
├── providers/               5 providers (ollama, deepseek, nvidia, gemini, openrouter)
├── search/
│   └── research_engine.py   Deep research v2 (Planner → Task DAG → Swarm → Verifier → Reflector → Synthesizer)
├── tools/                   14 tools (web_fetch, crawl4ai, headless_browser, etc.)
├── tui/v5/                  TUI v5 (AgentMonitor, Conversation, InputBar, ContextInspector)
└── cli.py                   aiw deep-research, kb, trace, eval
```
