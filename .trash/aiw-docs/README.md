# AI Workspace — Documentation

> **Version:** v0.2 — Complete
> **Updated:** 2026-06-18
> **Tests:** 858 passed, 6 skipped
> **Commits:** 152 total | **Specs:** 16/16 documented
> **Modules:** 97 source files, ~12,750 lines

---

## What is AI Workspace?

A multi-agent AI platform for deep research, coding, and knowledge management. Runs locally (ollama + GPU) or with cloud APIs (DeepSeek, Gemini, NVIDIA, OpenRouter).

**Core capabilities:**
- **Coding agent** — read, write, edit, shell, git, undo (OpenHands CodeAct + Aider patterns)
- **Deep research v2** — Planner → Task DAG → Swarm → Verifier → Synthesizer
- **RAG** — pgvector + nomic-embed-text, hybrid search (dense + BM25 + RRF)
- **Multi-provider** — 5 LLM backends, auto tool normalization
- **13 pi-compatible skills** — injected as prompt context (debug, commit, pre-review, etc.)
- **TUI v5** — AgentMonitor, Conversation, InputBar, ContextInspector

---

## Quick Start

```bash
# Source environment
source .envrc

# Run tests
python -m pytest -q

# Start coding agent
aiw agent "Add type hints to core/cost.py"

# Deep research
aiw deep-research "Python asyncio vs threading" --depth 1

# RAG search
aiw kb rag-search "error handling"

# Configure BYOK
aiw config init
```

---

## Architecture

See **[SPEC_INTEGRATION.md](specs/SPEC_INTEGRATION.md)** for the complete architecture map.

```
User (CLI / TUI / MCP)
  │
  ▼
agent_loop() — async generator (DIRECT | REACT | DAG)
  │
  ├── MemoryTree       — hierarchical state tracking (Mage)
  ├── DAGExecutor      — parallel execution + local repair (GraSP)
  ├── Skill Matcher    — pi-compatible prompt injection (13 skills)
  ├── Safety Sandbox   — command allowlist, deception detection
  ├── Compaction       — L1/L2/L3 context compression
  └── Observability    — DiffTracker, AgentTrace, TraceStore
  │
  ▼
Tools (20)              Providers (5)         Knowledge
read/write/edit/shell   ollama (GPU)           pgvector + nomic-embed
git/undo                deepseek (3x faster)   hybrid search + RRF
web_fetch/crawl4ai      nvidia/gemini          chunkers (AST/md)
marketplace/search      openrouter
```

---

## Documentation Index

### Specs (16 — all implemented)
| Spec | Description |
|------|-------------|
| [SPEC_AGENT_LOOP](specs/SPEC_AGENT_LOOP.md) | Async generator loop (DIRECT, REACT, DAG) |
| [SPEC_TOOL_EXECUTION](specs/SPEC_TOOL_EXECUTION.md) | Parallel tool execution with semaphore |
| [SPEC_MEMORY_TREE](specs/SPEC_MEMORY_TREE.md) | Hierarchical state tree (Mage) |
| [SPEC_DAG_EXECUTION](specs/SPEC_DAG_EXECUTION.md) | DAG orchestration (GraSP + FlowBank) |
| [SPEC_DEEP_RESEARCH_V2](specs/SPEC_DEEP_RESEARCH_V2.md) | Multi-agent research engine |
| [SPEC_RAG](specs/SPEC_RAG.md) | pgvector + hybrid search knowledge base |
| [SPEC_TUI_V5](specs/SPEC_TUI_V5.md) | Textual TUI with 4 panels |
| [SPEC_CONTEXT_COMPACTION](specs/SPEC_CONTEXT_COMPACTION.md) | L1/L2/L3 compression pipeline |
| [SPEC_CONTEXT_MANAGEMENT](specs/SPEC_CONTEXT_MANAGEMENT.md) | Context Inspector + /ctx commands |
| [SPEC_EVAL_HARNESS](specs/SPEC_EVAL_HARNESS.md) | Metric evaluation harness |
| [SPEC_SAFETY](specs/SPEC_SAFETY.md) | Sandbox + deception detection |
| [SPEC_OBSERVABILITY](specs/SPEC_OBSERVABILITY.md) | DiffTracker + TraceStore |
| [SPEC_OUTPUT_MODES](specs/SPEC_OUTPUT_MODES.md) | JSON/NDJSON/Rich output |
| [SPEC_ERROR_HANDLING](specs/SPEC_ERROR_HANDLING.md) | Result/Success/Failure pattern |
| [SPEC_AGENT_MCP_TOOL](specs/SPEC_AGENT_MCP_TOOL.md) | Agent as MCP server tool |
| [SPEC_INTEGRATION](specs/SPEC_INTEGRATION.md) | Complete architecture map |

### Archived (v0.1 docs → `_archive/`)
Historical feature docs from v0.1 — superseded by specs above. See `_archive/README.md`.

### Research (`specs/`)
| Doc | Content |
|-----|---------|
| [AUDIT_KEEP_VS_KILL](specs/AUDIT_KEEP_VS_KILL.md) | Feature validation against 312 dev survey |
| [CORRECTION_FEATURES_THAT_WORK](specs/CORRECTION_FEATURES_THAT_WORK.md) | Analysis corrections |

---

## Test Coverage

| Module | Tests |
|--------|-------|
| AgentLoop + patterns | 30 |
| Tool execution | 31 |
| Memory tree | 27 |
| DAG executor | 27 |
| Code tools | 41 |
| Compaction | 25 |
| Safety | 26 |
| Research engine | 37 |
| RAG | 31 |
| Eval harness | 14 |
| Observability | 18 |
| MCP agent tools | 9 |
| Integration e2e | 11 |
| Other (TUI, core, etc.) | 531 |
| **Total** | **858** |

---

## Providers

| Provider | Model | API Key |
|----------|-------|---------|
| ollama | qwen3:14b (GPU, NUM_PARALLEL=2) | local |
| deepseek | deepseek-v4-flash | `DEEPSEEK_API_KEY` |
| nvidia | minimaxai/minimax-m3 | `NVIDIA_API_KEY` |
| gemini | gemini-2.5-flash | `GEMINI_API_KEY` |
| openrouter | anthropic/claude-3.7-sonnet | `OPENROUTER_API_KEY` |

Configure via `aiw config init` → `~/.config/aiw/config.toml` or environment variables.

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Async generator (`agent_loop()`) | Backpressure, typed return, composable |
| PEP 562 lazy imports | Avoid heavy deps at import time |
| str_replace_editor | Proven by OpenHands CodeAct, SWE-agent ACI |
| Atomic writes (`tempfile + os.replace`) | No corrupted partial files |
| Shell sandbox (allowlist + patterns) | Prevent dangerous commands |
| Skills as prompt injection | Mirrors pi architecture |
| MemoryTree from events | Non-invasive state tracking |
| Tool format normalization | All 5 providers use same client |
