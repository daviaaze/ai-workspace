# AI Workspace

> Deep search, agent swarm, knowledge base, task automation, and telemetry — all in Python + PostgreSQL + Nix. Zero containers.

[![Lines](https://img.shields.io/badge/lines-4727-blue)](.)
[![Python](https://img.shields.io/badge/python-3.12+-blue)](.)
[![Nix](https://img.shields.io/badge/nix-flake-blue)](.)

## Architecture

```
aiw (CLI)
├── aiw search <query>          Deep recursive research
├── aiw ask <question>          Quick chat with any model
├── aiw models                  List available models
├── aiw task list|add|due       Task management
├── aiw memory add|recall       Agent memory
├── aiw kb add|search           Knowledge base
├── aiw wf run|status|logs|retry|stats   DAG workflow engine
├── aiw obsidian sync           Obsidian vault sync
├── aiw schedule run|status     Recurring tasks (Huey)
├── aiw worker                  Start task worker
├── aiw telemetry               View metrics snapshot
└── aiw init                    Initialize database
```

## Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Agent Swarm | [crewAI](https://github.com/crewAIInc/crewAI) | Multi-agent orchestration |
| Task Queue | [Huey](https://github.com/coleifer/huey) | Lightweight, SQLite-backed |
| Workflow Engine | Custom DAG engine | Parallel steps, state persistence, retry |
| Knowledge Base | PostgreSQL + pgvector | Vector search, graph memory |
| Telemetry | Langtrace + built-in | Spans, logs, metrics per run |
| LLM Providers | Ollama, DeepSeek, Kimi | Local + cloud fallback |
| Package Manager | Nix flakes | Reproducible builds |

## Quick Start

### 1. Create database
```bash
createdb ai_workspace
```

### 2. Install
```bash
git clone https://github.com/daviaaze/ai-workspace
cd ai-workspace
nix develop    # or: pip install -e .
```

### 3. Initialize
```bash
aiw init
```

### 4. Use
```bash
aiw models                         # List your Ollama models
aiw search "rust async patterns"   # Deep research
aiw ask "explain nix flakes"       # Quick chat
aiw wf run deep_research --query "AI safety 2025"  # DAG workflow
aiw wf logs 1 --workflow deep_research             # View execution logs
aiw worker                         # Start task worker (periodic tasks)
aiw telemetry                      # View metrics
```

## Deep Search Pipeline

```
Query → Planner Agent → Sub-questions (tree)
                          ├── Sub-Q1 → Researcher Agent → Answer
                          ├── Sub-Q2 → Researcher Agent → Answer  (parallel)
                          └── Sub-Q3 → Researcher Agent → Answer
                                          ↓
                              Synthesizer Agent → Report
                                          ↓
                              Store in Knowledge Base
```

## Workflow Engine

Define DAG-based workflows declaratively. Auto-parallel, retry with backoff, state persisted in PostgreSQL.

```python
@workflow
class DeepResearchWorkflow(BaseWorkflow):
    name = "deep_research"
    
    async def step_plan(self, ctx): ...
    async def step_research_q1(self, ctx): ...  # depends on step_plan
    async def step_research_q2(self, ctx): ...  # depends on step_plan
    async def step_synthesize(self, ctx): ...   # depends on all research
    async def step_store(self, ctx): ...        # depends on synthesize

# Dependencies auto-inferred from ctx.get() calls
# Steps with no deps run in parallel
```

```bash
aiw wf run deep_research --query "quantum computing"
aiw wf status deep_research
aiw wf logs 42 --workflow deep_research
aiw wf retry 42            # resume from last completed step
aiw wf stats deep_research # success rate, avg duration, etc.
```

## Agent Swarm

| Agent | Model | Use |
|-------|-------|-----|
| Researcher | `deepseek-r1:14b` | Deep search |
| Coder | `qwen3-coder:30b` | Code generation |
| Analyst | `qwen3:14b` | Pattern detection |
| Writer | `qwen3:14b` | Reports |
| Planner | `deepseek-r1:14b` | Task planning |

## Recurring Tasks (Huey worker)

Run `aiw worker` to process periodic tasks:

| Time (BRT) | Task | What |
|------------|------|------|
| 07:00 | `morning_briefing` | Sync Obsidian + daily briefing |
| 08:00 | `daily_research` | Automated topic research |
| 02:00 | `continuous_learning` | Pattern extraction |
| 09:00 | `telemetry_report` | Metrics snapshot |
| **:00 | `db_task_checker` | Run due DB tasks |

## Knowledge Base

PostgreSQL tables:
- `knowledge_entries` — Curated knowledge (vector embeddings)
- `research_entries` — Deep search results
- `tasks` — Task management with cron scheduling
- `agent_memory` — Agent learnings (mem0-like)
- `workflow_runs` — Workflow execution state
- `workflow_step_logs` — Per-step attempt history
- `workflow_logs` — Structured execution logs

## Telemetry

Every workflow run produces:
- **Langtrace spans** — Auto-instrumented crewAI + Ollama calls
- **Structured logs** — Per-run, per-step, with levels
- **Step history** — Each attempt, duration, output, error
- **Aggregated stats** — Success rate, avg duration, trends

```bash
aiw telemetry           # Snapshot: research, tasks, memories, confidence
aiw wf stats <name>     # Per-workflow: runs, failures, avg duration
```

## Nix Integration

```nix
# flake.nix
inputs.ai-workspace.url = "github:daviaaze/ai-workspace";

# In your NixOS module
features.ai-workspace = {
  enable = true;
  database.enable = true;
  obsidian.enable = true;
  worker.enable = true;       # systemd service for Huey worker
  telemetry.enable = true;    # Langtrace
};
```

## License

MIT
