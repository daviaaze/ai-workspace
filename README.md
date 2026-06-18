# AI Workspace (aiw) v0.1.0

**Self-hosted AI agent for research, coding, and knowledge management.**
Runs on NixOS with local LLMs (Ollama) or cloud APIs (DeepSeek, Gemini, OpenRouter).

> **394 tests, 0 failures. Multi-provider SmartRouter. crewAI 1.x. Budget enforcement.**
> Status: **v0.1.0 — core flows work, ready for use.**

## Status Board

| Feature | Status | Notes |
|---------|--------|-------|
| `aiw ask` / `aiw chat` | ✅ **Works** | Ollama native `/api/chat`. Streaming. Multi-provider. |
| `aiw search` | ✅ **Works** | Deep recursive research with web scraping. crewAI + output_pydantic. |
| `aiw agent` | ✅ **Works** | Unified agent with filesystem/git/shell/web tools. |
| `aiw code` | ✅ **Works** | Autonomous coding with edit/write/commit. |
| `aiw tui` | ✅ **Works** | Textual tabbed dashboard (agents, tasks, git). |
| `aiw health` | ✅ **Works** | Providers, cache, budget, sources status. |
| `aiw init` / `aiw budget` / `aiw version` | ✅ **Works** | Setup wizard, cost tracking, version info. |
| `aiw task add/list` | ✅ **Works** | Task manager with cron scheduling (Huey). |
| `aiw source check/endorse/flag` | ✅ **Works** | Source reputation CLI (CRED-1 seed). |
| SmartRouter (multi-provider) | 🟡 **Partial** | Matrix exists; needs API keys for non-Ollama providers. |
| Semantic Cache (pgvector) | 🟡 **Partial** | Code complete; E2E integration pending. |
| Source Reputation (CrediNet) | 🔴 **Planned** | Schema + CRED-1 seed done. CrediNet not installed. |
| Cross-reference scoring | 🔴 **Planned** | Algorithm documented, not implemented. |
| Streamlit Dashboard | 🟡 **Minimal** | Basic page exists. Rich dashboard planned. |
| Agent Swarm (supervisor) | 🔴 **Planned** | Design done, not started. |
| MCP Client (consume tools) | 🔴 **Planned** | Server exists; client-side not started. |
| Laminar Tracing | 🔴 **Planned** | Library imported; self-hosted not deployed. |
| CI/CD (GitHub Actions) | 🔴 **Planned** | `.github/` dir exists; workflow not implemented. |

**Legend:** ✅ Works end-to-end | 🟡 Partial/code exists | 🔴 Planned/not started

## Quick Start

```bash
# NixOS
nix build .#ai-workspace

# Dev shell
nix-shell
source .venv/bin/activate
pip install -e .
aiw init

# Chat (Ollama)
aiw ask "Hello world" --provider ollama -m qwen3:14b

# Chat (DeepSeek — needs DEEPSEEK_API_KEY)
aiw ask "Explain monads" --provider deepseek -m deepseek-chat

# Deep research
aiw search "Rust vs Go performance 2026"

# Coding agent
aiw code "Add type hints to src/ai_workspace/core/db.py"

# System health
aiw health

# Run tests
nix-shell --run "source .venv/bin/activate && python -m pytest tests/ -q"
```

## Architecture

```
CLI (typer)
├─ aiw ask        → ProviderRegistry → Ollama|DeepSeek|Gemini|OpenRouter
├─ aiw agent      → AgentOrchestrator
│   ├─ Context injection (project files, git, session)
│   ├─ SmartRouter model selection + fallback
│   ├─ crewAI execution (coding, research, general)
│   └─ Permission gate for dangerous tools
├─ aiw search     → DeepSearchEngine
│   └─ Plan → Research → Source Filter → Synthesize → Critic
├─ aiw code       → coding_crew() [YAML-driven from agents.yaml]
├─ aiw tui        → Textual 8.x tabbed dashboard
├─ aiw worker     → Huey consumer (systemd service)
└─ aiw dashboard  → Streamlit web UI

Config (YAML):
├─ agents.yaml    → 8 agent definitions (researcher, coder, analyst, etc.)
├─ tasks.yaml     → 12 task templates with {variable} interpolation
└─ loader.py      → load_agent() / load_task()

Infra:
├─ PostgreSQL 15  → pgvector HNSW index (semantic cache + knowledge)
├─ ConnectionPool → ThreadedConnectionPool with health check
├─ Nix flake      → 8 custom Python derivations
└─ Tests          → 425+ pass, 0 fail
```

## Commands

| Command | Description |
|---------|-------------|
| `aiw ask <msg>` | Quick chat (supports `--provider` and `--model`) |
| `aiw agent <task>` | General-purpose agent (auto-detects: research, code, browse) |
| `aiw code <task>` | Autonomous coding agent with filesystem/git/shell |
| `aiw search <query>` | Deep recursive research with web scraping |
| `aiw tui` | Terminal dashboard (Textual) |
| `aiw dashboard` | Web dashboard (Streamlit) |
| `aiw health` | System health check (providers, cache, budget) |
| `aiw version` | Show version and dependency info |
| `aiw init` | Initialize database and directories |
| `aiw budget` | Cost tracking (daily/monthly spend) |
| `aiw task add/list` | Task manager with cron scheduling |
| `aiw source check/stats/seed` | Source reputation management |
| `aiw worker` | Background task consumer (Huey) |
| `aiw models` | List available models per provider |

## Key Features

- **Multi-provider LLM**: Ollama (local, free), DeepSeek ($0.14/M), Gemini (free tier), OpenRouter
- **Smart Router**: Auto-selects best model per task type (coding, research, extraction, etc.)
- **crewAI Agents**: YAML-driven agent definitions, output_pydantic, guardrails
- **Semantic Cache**: pgvector HNSW with dual embedding (Ollama + sentence-transformers)
- **Budget Enforcement**: Per-call/daily/monthly limits with circuit breakers
- **19 Tools**: Filesystem (read/write/edit/list/search), Git (status/diff/log/commit/PR), Shell (sandboxed), Web (fetch/browser/scrape/crawl4ai), Marketplace (Mercado Livre, OLX)
- **Agent Orchestrator**: Unified pipeline (CLI/TUI/Dashboard/MCP) with streaming, permissions, fallback
- **Context Manager**: Token budget tracking, pin/exclude blocks, snapshot/restore
- **Persistent Sessions**: Multi-turn agent conversations with auto-compaction
- **TUI Dashboard**: Textual 8.x with tabbed layout, agent lanes, task table, git panel

## Roadmap

### v0.1.0 ✅ (Current)
- [x] Multi-provider LLM (Ollama, DeepSeek, Gemini, OpenRouter)
- [x] SmartRouter with cross-provider fallback
- [x] Deep recursive research with web scraping
- [x] Agent orchestrator (CLI/TUI/Dashboard)
- [x] 19 tools (filesystem, git, shell, web, marketplace)
- [x] Semantic cache (pgvector HNSW)
- [x] Budget enforcement (3 layers + circuit breakers)
- [x] TUI dashboard (Textual 8.x)
- [x] YAML-driven agents and tasks
- [x] Persistent agent sessions
- [x] Context manager with token budget
- [x] Connection pool with health check
- [x] 425+ tests, 0 failures

### v0.2.0 (Next)
- [ ] E2E tests for search pipeline
- [ ] CrediNet integration (source reputation)
- [ ] Cross-reference scoring
- [ ] Gemini rate-limit handling
- [ ] Cache auto-cleanup (scheduled)
- [ ] Streamlit dashboard polish
- [ ] CI/CD pipeline (GitHub Actions)

### v0.3.0+ (Future)
- [ ] Agent swarm (supervisor-worker)
- [ ] MCP client-side (consume external tools)
- [ ] Laminar tracing (self-hosted)
- [ ] Knowledge graph (connect research findings)
- [ ] Multi-workspace sync
- [ ] Plugin system

## Development

```bash
# Setup
nix-shell
source .venv/bin/activate
pip install -e ".[dev]"

# Tests
python -m pytest tests/ -q

# Coverage
python -m pytest tests/ --cov=src/ai_workspace --cov-report=term

# Lint
ruff check src/

# Type check
mypy src/ai_workspace/
```

## Documentation

Detailed design docs in [`docs/`](docs/):

| Doc | Topic |
|-----|-------|
| [MODEL_FALLBACK.md](docs/MODEL_FALLBACK.md) | SmartRouter cross-provider fallback |
| [VISION_PIPELINE.md](docs/VISION_PIPELINE.md) | Image → vision model → reasoning pipeline |
| [SEMANTIC_CACHE.md](docs/SEMANTIC_CACHE.md) | pgvector HNSW semantic cache |
| [BUDGET_ENFORCEMENT.md](docs/BUDGET_ENFORCEMENT.md) | Cost control layer |
| [PERMISSION_SYSTEM.md](docs/PERMISSION_SYSTEM.md) | Safety gate for file operations |
| [MESSAGE_QUEUE.md](docs/MESSAGE_QUEUE.md) | Multi-turn agent message queue |
| [CONTEXT_AWARENESS.md](docs/CONTEXT_AWARENESS.md) | Project structure injection |
| [CONTEXT_WORKBENCH.md](docs/CONTEXT_WORKBENCH.md) | Context window observability |
| [SKILL_SYSTEM.md](docs/SKILL_SYSTEM.md) | Pi-compatible skill workflows |
| [INTERACTIVE_SESSION.md](docs/INTERACTIVE_SESSION.md) | Persistent agent sessions |

## License

MIT
