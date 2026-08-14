# Spec: Integration — Architecture Map

> **Status:** ✅ Documented | **Data:** 2026-06-18
> **Refs:** All 15 implementation specs, 844 tests, 97 source files

---

## Architecture (actual — generated from code)

```
User (CLI / TUI / MCP)
  │
  ▼
┌──────────────────────────────────────────────────────────┐
│                    CLI (cli.py)                           │
│  aiw deep-research | agent | kb | eval | trace | config  │
└──────────┬───────────┬──────────┬───────────┬────────────┘
           │           │          │           │
           ▼           ▼          ▼           ▼
┌──────────────┐ ┌──────────┐ ┌────────┐ ┌──────────────┐
│ Research     │ │ Agent    │ │ RAG    │ │ Eval / Trace │
│ Engine       │ │ Loop     │ │        │ │ / Config     │
└──────┬───────┘ └────┬─────┘ └───┬────┘ └──────────────┘
       │              │           │
       │    ┌─────────┼───────────┼──────────┐
       │    │         │           │          │
       ▼    ▼         ▼           ▼          ▼
┌──────────────────────────────────────────────────────────┐
│                   Core Layer                              │
│  loop.py          agent_loop (async generator)            │
│  tool_execution   partition + parallel semaphore          │
│  memory_tree.py   hierarchical state (Mage)               │
│  dag_executor.py  DAG orchestration (GraSP + FlowBank)    │
│  compaction.py    L1/L2/L3 context compression            │
│  skill_matcher.py pi-compatible prompt injection          │
│  safety.py        sandbox + deception detection           │
│  result.py        Result/Success/Failure/AiWError         │
│  output.py        OutputFormatter (JSON/NDJSON/Rich)      │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│                   Tools (14 + 6 new)                      │
│  code_tools.py    read/write/edit/shell/git/undo          │
│  web_fetch.py     URL → text                              │
│  crawl4ai.py      JS-rendered pages                       │
│  headless_browser Chromium headless                       │
│  marketplace.py   Mercado Livre + OLX                     │
│  filesystem.py    legacy filesystem tools                 │
│  git.py           legacy git tools                        │
│  shell.py         legacy shell tools                      │
│  diff_edit.py     semantic diff edits                     │
│  skill_tool.py    skill discovery + execution             │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│                  Providers (5)                            │
│  ollama         qwen3:14b (GPU, NUM_PARALLEL=2)          │
│  deepseek       v4-flash (3-7x faster than local)        │
│  nvidia         minimaxai/minimax-m3                      │
│  gemini         gemini-2.5-flash                          │
│  openrouter     anthropic/claude-3.7-sonnet               │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│                  Knowledge Layer                          │
│  rag.py          pgvector + nomic-embed (768d)            │
│                  hybrid: dense + BM25 + RRF + rerank      │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│                  Infrastructure                           │
│  PostgreSQL 17   pgvector 0.8.2 (scripts/pg-dev.sh)      │
│  Ollama 0.30.7   nomic-embed-text (768d)                 │
│  NixOS           flake.nix devShell + nixfiles            │
└──────────────────────────────────────────────────────────┘
```

---

## Module dependency graph

```
agents/loop.py
 ├── agents/tool_execution.py     (parallel tool calls)
 ├── agents/memory_tree.py        (state tracking)
 ├── agents/dag_executor.py       (DAG pattern)
 ├── agents/compaction.py         (context compression)
 ├── agents/skill_matcher.py      (pi-compatible skills)
 ├── agents/safety.py             (sandbox + validation)
 ├── core/result.py               (Result/Success/Failure)
 ├── providers/__init__.py        (5 LLM backends)
 └── tools/                       (lazy imports)

tools/code_tools.py
 ├── crewai.tools.BaseTool        (read_file, write_file, edit_file, shell_exec, git, undo)
 ├── str_replace_editor pattern   (OpenHands CodeAct)
 ├── atomic writes                 (tempfile + os.replace)
 ├── shell sandbox                 (allowlist + dangerous patterns)
 └── undo stack                    (50 reversible edits)

agents/skill_matcher.py
 ├── skills/loader.py             (SKILL.md parser)
 ├── 13 pi skills                  (~/.pi/agent/skills/)
 └── explicit_skill_for_task()    (trigger-word matching)

search/research_engine.py
 ├── agents/loop.py               (agent_loop for sub-tasks)
 ├── Planner → Task DAG → Swarm → Verifier → Reflector → Synthesizer
 ├── parallel semaphore            (asyncio.Semaphore)
 └── confidence heuristic          (response length based)

knowledge/rag.py
 ├── pgvector                      (HNSW index)
 ├── ollama nomic-embed-text       (768-dim embeddings)
 ├── chunkers                      (AST, markdown, generic)
 ├── hybrid search                 (dense + BM25/tsvector + RRF)
 └── rerank                        (cross-encoder)

observability/__init__.py
 ├── DiffTracker                   (code-level diffs)
 ├── AgentTrace                    (full execution record)
 └── TraceStore                    (JSON disk persistence)

evals/__init__.py
 ├── EvalCase + EvalResult
 ├── EvalRunner                    (dry-run mode)
 └── 3 suites, 6 cases             (coding, reasoning, facts)

mcp_server/agent_tools.py
 ├── AgentRecord registry
 ├── aiw_agent_run                 (batch + NDJSON)
 ├── aiw_agent_status
 └── aiw_agent_kill

user_config.py
 ├── TOML config                   (~/.config/aiw/config.toml)
 └── BYOK                          (env var > config file > default)

tui/v5/
 ├── app.py                        (Textual App)
 ├── agent_monitor.py              (collapsible agent bars)
 ├── conversation.py               (chat + token streaming)
 ├── input_bar.py                  (slash commands)
 └── context_inspector.py          (F4 overlay)
```

---

## Data flow — complete agent interaction

```
1. User types task in CLI or TUI
   │
2. Skill Matcher checks against 13 skills
   │  "debug: tests failing" → injects [SKILL: debug] workflow
   │  "commit all changes"   → injects [SKILL: commit] workflow
   │  "hello"                → no skill, direct prompt
   │
3. agent_loop(params) starts
   │
4. Pattern dispatch:
   │  LoopPattern.DIRECT  → single LLM call, no tools
   │  LoopPattern.REACT   → Thought→Action→Observation loop
   │  LoopPattern.DAG     → compile → parallel execute → synthesize
   │
5. MemoryTree tracks each step
   │  grow()      → records tool_call, tool_result, thinking
   │  get_context() → injects into system prompt as [MEMORY CONTEXT]
   │
6. Tools normalized to OpenAI format
   │  crewAI BaseTool → {"type":"function","function":{...}}
   │  Works with all 5 providers (ollama, deepseek, nvidia, gemini, openrouter)
   │
7. Provider streams tokens back
   │  ollama: qwen3:14b with NUM_PARALLEL=2 (6.8x speedup)
   │  deepseek: 3-7x faster than local ollama
   │
8. Safety layer validates:
   │  SafetySandbox     → command allowlist, path confinement
   │  DeceptionDetector → placeholder detection, fabrication markers
   │
9. Context compaction after each turn
   │  L1: cap tool results > 10KB
   │  L2: clear results older than 10 min
   │  L3: summarize when > 80% token budget
   │
10. Observability records:
    │  DiffTracker  → file changes
    │  AgentTrace   → execution record
    │  TraceStore   → JSON persistence
    │
11. Output formatted:
    │  Rich (default)   → colored terminal output
    │  JSON             → structured stdout
    │  NDJSON           → streaming events
    │
12. Result returned to user
```

---

## Integration points — how everything connects

| Module A | Module B | Connection |
|----------|----------|------------|
| `cli.py` | `agents/loop.py` | `agent_loop(params)` — async generator |
| `cli.py` | `search/research_engine.py` | `ResearchEngine.research()` |
| `cli.py` | `knowledge/rag.py` | `KnowledgeRetriever.search()` |
| `cli.py` | `observability/` | `TraceStore.list()` |
| `cli.py` | `evals/` | `EvalRunner.run()` |
| `cli.py` | `user_config.py` | `AiwConfig.load()` |
| `agents/loop.py` | `providers/` | `ProviderRegistry.get_client()` |
| `agents/loop.py` | `tools/` | lazy imports via `__getattr__` |
| `agents/loop.py` | `agents/compaction.py` | `ContextCompactor.compact()` |
| `agents/loop.py` | `agents/memory_tree.py` | `MemoryTree.grow()` from events |
| `agents/loop.py` | `agents/dag_executor.py` | `compile_dag_plan()` + `DAGExecutor.execute()` |
| `agents/loop.py` | `agents/skill_matcher.py` | `inject_skill_for_task()` |
| `agents/loop.py` | `agents/safety.py` | `SafetyValidator.validate()` |
| `agents/loop.py` | `core/result.py` | `ErrorCode`, `LoopEvent` |
| `search/research_engine.py` | `agents/loop.py` | `agent_loop()` for sub-tasks |
| `search/research_engine.py` | `tools/` | web_fetch, crawl4ai, etc. |
| `knowledge/rag.py` | `pgvector` | HNSW vector index |
| `knowledge/rag.py` | `ollama` | nomic-embed-text (768d) |
| `mcp_server/` | `agents/loop.py` | `agent_loop()` via MCP protocol |
| `tui/v5/` | `agents/loop.py` | `LoopEvent` → UI updates |
| `evals/` | `agents/loop.py` | `agent_loop()` with fake providers |

---

## File count by layer

| Layer | Files | Lines (est.) |
|-------|-------|-------------|
| agents/ | 12 | ~4,500 |
| tools/ | 14 | ~3,700 |
| providers/ | 5 | ~600 |
| search/ | 3 | ~900 |
| knowledge/ | 2 | ~500 |
| tui/v5/ | 6 | ~1,500 |
| observability/ | 1 | ~300 |
| evals/ | 1 | ~250 |
| mcp_server/ | 2 | ~300 |
| core/ | 2 | ~200 |
| **Total** | **97** | **~12,750** |

---

## Test coverage

| Test file | Tests | Area |
|-----------|-------|------|
| `test_agents/test_loop.py` | 30 | AgentLoop patterns |
| `test_agents/test_tool_execution.py` | 31 | Parallel tool execution |
| `test_agents/test_memory_tree.py` | 27 | Hierarchical state tree |
| `test_agents/test_dag_executor.py` | 27 | DAG orchestration |
| `test_agents/test_compaction.py` | 25 | Context compression |
| `test_agents/test_safety.py` | 26 | Safety sandbox |
| `test_tools/test_code_tools.py` | 41 | Code agent tools |
| `test_search/test_research_engine.py` | 37 | Deep research |
| `test_knowledge/test_rag.py` | 31 | RAG + pgvector |
| `test_evals/test_init.py` | 14 | Eval harness |
| `test_observability/test_init.py` | 18 | Observability |
| `test_mcp/test_agent_tools.py` | 9 | MCP agent tools |
| `test_e2e/test_agent_pipeline.py` | 11 | Integration e2e |
| Others | ~522 | TUI, core, etc. |
| **Total** | **844** | |

---

## Key design decisions

| Decision | Rationale |
|----------|-----------|
| Async generator (`agent_loop()`) | Backpressure, typed return, composable (Claude Code, pi pattern) |
| `asyncio.Queue` for events | Real-time streaming while loop runs in background task |
| PEP 562 lazy imports (`__getattr__`) | Avoid heavy deps (crewAI, playwright) at import time |
| `BaseTool` → OpenAI format normalization | All 5 providers use same client, tools auto-convert |
| str_replace_editor (not full-file overwrite) | Proven by OpenHands CodeAct, SWE-agent ACI |
| Atomic writes (`tempfile + os.replace`) | No partial files, no corruption |
| Must-read-before-write | Safety: agent can't edit files it hasn't seen |
| Shell sandbox (allowlist + patterns) | Prevent `sudo rm -rf /`, fork bombs, pipe-to-shell |
| Skills as prompt injection (not tools) | Mirrors pi architecture: skills are context, tools are execution |
| MemoryTree from events | Non-invasive: grows from events already in the drain loop |
| DAG with local repair | O(depth × branching) replanning vs O(N) for full reset |
