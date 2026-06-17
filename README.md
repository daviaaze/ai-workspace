# AI Workspace

AI Workspace (`aiw`) is a self-hosted **everything agent** — research, coding, automation, and knowledge management. Runs on NixOS with local LLMs (Ollama) or cloud APIs (DeepSeek).

> **318 tests, 0 failures. crewAI 1.14.7. YAML-driven agents + skills. Budget enforcement. Browser agent on NixOS.**

## What it does

| Command | What |
|---------|------|
| `aiw ask "..."` | Quick chat with any LLM (Ollama, DeepSeek, OpenRouter) |
| `aiw search "..."` | Deep recursive research with web scraping |
| `aiw agent "..."` | Unified agent — research, code, browse, manage files |
| `aiw code "..."` | Autonomous coding agent (filesystem + git + shell) |
| `aiw task add/list` | Task manager with cron scheduling |
| `aiw source check/endorse/flag/stats/seed` | Source reputation (CRED-1 + empirical tracking) |
| `aiw budget` | Show cost tracking: daily/monthly spend, cache savings |
| `aiw skill list/run` | Run pi-compatible skills as agent workflows |
| `aiw kb search` | Knowledge base with pgvector semantic search |
| `aiw memory add/recall` | Agent memory across sessions |
| `aiw tui` | Terminal dashboard (Textual 8.x) |
| `aiw dashboard` | Web dashboard (Streamlit) |
| `aiw worker` | Background task consumer (Huey, systemd) |

## Architecture

```
CLI (typer)
├─ aiw ask        → ProviderRegistry → Ollama /api/chat (native)
├─ aiw agent      → AgentOrchestrator
│   ├─ Context injection (project files, git)
│   ├─ Smart model routing
│   └─ crewAI execution with fallback
├─ aiw search     → DeepSearchEngine
│   └─ output_pydantic (PlanOutput, ResearchAnswer, SynthesisReport)
├─ aiw code       → coding_crew() [YAML-driven from agents.yaml]
├─ aiw tui        → Textual 8.x Screen API + Footer
└─ aiw worker     → Huey consumer (systemd service)

Config (YAML, non-devs can edit):
├─ agents.yaml    → 14 agent definitions (researcher, coder, browser, supervisor)
├─ tasks.yaml     → 12 task templates with {variable} interpolation
└─ loader.py      → load_agent() / load_task()

Infra:
├─ PostgreSQL 15  → port 2284 (homelab) + pgvector HNSW index
├─ ConnectionPool → ThreadedConnectionPool (transparent, 31 call sites)
├─ Nix flake      → 8 custom Python derivations (browser-use, browser-use-sdk, etc.)
└─ Tests          → 278 pass, 0 fail (agents, core, knowledge, providers, MCP, workflow)
```

## Quick Start

```bash
# NixOS
nix build .#ai-workspace

# Dev shell
nix-shell
source .venv/bin/activate
pip install -e .
aiw init

# Test
aiw ask "Hello world" --provider ollama -m qwen3:14b

# Run tests
nix-shell --run "source .venv/bin/activate && python -m pytest tests/ -q"

# Background worker
aiw worker &

# Pre-commit hooks
pre-commit install
```

## Key features

- **crewAI 1.14.7**: output_pydantic, planning, guardrails, retry
- **YAML-driven agents**: edit prompts without touching Python
- **Semantic cache**: pgvector HNSW with dual embedding (Ollama + sentence-transformers)
- **Budget enforcement**: $0.01/call, $1.00/day, $10.00/month limits with per-provider circuit breakers
- **Skill system**: 13 pi-compatible skills (debug, feature-dev, commit, pre-review, etc.)
- **HNSW index**: 2x faster vector search vs IVFFlat
- **Orchestrator**: unified execution pipeline (CLI/TUI/Dashboard/MCP)

## Roadmap

- [x] crewAI 1.14.7 + output_pydantic
- [x] YAML-driven agents
- [x] Connection pooling
- [x] Browser agent (browser-use on NixOS)
- [x] Explicit workflow DAG (@step decorator)
- [x] Textual 8.x TUI
- [x] Pre-commit hooks
- [ ] DeepSeek credits (for fast cloud research)
- [ ] Agent swarm (supervisor-worker)
- [ ] Web dashboard polish

## License

MIT
