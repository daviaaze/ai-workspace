# Changelog

All notable changes to AI Workspace (aiw) will be documented in this file.

## [0.1.0] — 2026-06-17

### Added
- **Multi-provider LLM support**: Ollama (local, free), DeepSeek ($0.14/M), Gemini (free tier), OpenRouter via `ProviderRegistry`
- **SmartRouter**: Auto-selects best model per task type (coding, research, extraction, classification, etc.) with 7 routing strategies
- **Cross-provider fallback**: Automatic fallback chain (Ollama → DeepSeek → Gemini → OpenRouter) with failure tracking
- **Gemini rate-limit handling**: Tracks 60 req/min and 1500 req/day limits, auto-disables and falls back when exceeded
- **Semantic Cache**: pgvector HNSW index with dual embedding (Ollama nomic-embed-text + sentence-transformers all-MiniLM-L6-v2), auto-fallback
- **Budget Enforcement**: 3-layer protection (per-call $0.01, daily $1.00, monthly $10.00) with circuit breakers per provider
- **Source Reputation**: CRED-1 seed (2,673 domains) + CrediNet fallback + cross-reference scoring + user feedback (endorse/flag)
- **Deep Search**: Recursive tree research with planning → supervision → research → source filter → synthesis → critic pipeline
- **Agent Orchestrator**: Unified pipeline (CLI/TUI/Dashboard/MCP) with context injection, smart routing, streaming, permissions, fallback
- **19 Tools**: Filesystem (read/write/edit/list/search), Git (status/diff/log/commit/PR), Shell (sandboxed), Web (fetch/browser/scrape/crawl4ai), Marketplace (Mercado Livre, OLX), Code Graph, Diff Edit, Auto-Fix
- **TUI v2 Dashboard**: Tabbed layout (Dashboard, Agents, Tasks, Git) with header bar, bottom bar, 20 keybindings, spawn dialog, chat screen, fuzzy finder, workspace switcher, knowledge graph, context workbench, metrics panel, permission modal
- **Persistent Sessions**: Multi-turn agent conversations with auto-compaction, export/import JSONL, session history
- **Context Manager**: Token budget tracking, pin/exclude blocks, snapshot/restore, auto-trim
- **YAML-driven agents**: 8 agent definitions and 12 task templates editable without Python
- **crewAI 1.x**: output_pydantic, planning, guardrails, retry, step callbacks
- **Task scheduling**: 8 periodic tasks via Huey (morning briefing, daily research, continuous learning, source reputation Mon/Thu, cache cleanup Sun, DB task checker hourly, telemetry report daily)
- **ConnectionPool**: ThreadedConnectionPool with health check and auto-reconnect
- **CLI commands**: `aiw ask`, `aiw search`, `aiw agent`, `aiw code`, `aiw tui`, `aiw dashboard`, `aiw worker`, `aiw health`, `aiw version`, `aiw init`, `aiw budget`, `aiw task`, `aiw source`, `aiw kb`, `aiw memory`, `aiw session`, `aiw models`, `aiw tool`
- **CI/CD**: GitHub Actions pipeline (lint, type check, test with coverage, deploy hook)
- **425+ tests**, 0 failures, 55 E2E tests

### Changed
- **SwarmConfig**: Now parses provider from model prefix (`deepseek/deepseek-chat`, `gemini/gemini-2.5-flash`)
- **AgentOrchestrator**: Now passes provider through to agent execution via SwarmConfig
- **DeepSearchEngine**: Accepts `cost_service` for cache + budget integration
- **TUI data loader**: Falls back to `memory/` markdown files instead of hardcoded demo data
- **TUI agent grid**: Detail panel mounts rich `AgentLane` widget instead of plain text
- **TUI knowledge graph**: Loads from `memory/learning-log.md`, `conventions.md`, `project-patterns.md`
- **README**: Honest status board with ✅/🟡/🔴 indicators and realistic roadmap

### Fixed
- **N1**: Router→crewAI disconnect now passes routed provider/model to agent execution
- **N4**: ConnectionPool now has health check with auto-reconnect
- **N5**: Ollama dependency hell — system now falls back to DeepSeek/Gemini when Ollama is down
- **N6**: Worker→Orchestrator duplication — `AgentWorker._run_crew_sync()` delegates to `AgentOrchestrator._run_agent_sync()`

### Removed
- `tui/app_legacy.py` (984 lines of dead v1 code)

## [0.0.1] — 2026-06-13

### Added
- Initial project structure (Nix flake, pyproject.toml, shell.nix)
- crewAI agent swarm with YAML-driven configuration
- Deep recursive search engine with web scraping
- PostgreSQL + pgvector knowledge store
- MCP server with 11 tools exposed
- Streamlit dashboard (basic)
- Textual TUI v1
- Budget enforcement (SemanticCache + BudgetEnforcer + CircuitBreaker)
- Source reputation schema (CRED-1 seeding)
- Huey task scheduling with 6 periodic tasks
