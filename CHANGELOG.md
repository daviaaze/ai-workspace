# Changelog

All notable changes to AI Workspace (aiw) will be documented in this file.

## [0.2.0] — 2026-06-25

### Added

#### Phase 2-1 Merge: Persistent Memory, RAG Engine, Agent Swarm (+10,280 lines)
- **Persistent Memory L1/L2/L3**: Cross-session memory with append-only traces (L1), curated facts per topic (L2), and cross-surface synthesis (L3). Inspired by DeepTutor.
- **Tiered Context Loader**: OpenViking-inspired L0/L1/L2 progressive context loading with directory-based retrieval and retrieval trajectory tracking.
- **Agent Partners**: Persistent AI companions with SOUL.md persona, private workspace, memory, KB, and tool policy. `consult_subagent` tool for mid-turn consultations.
- **Multi-Engine RAG**: Abstract `RetrievalEngine` interface supporting vector, graph, page-index, Obsidian vault adapters.
- **BatchSwarm**: Lightweight parallel worker pool for batch task processing (Career-Ops inspired).
- **PII Safety**: `IdentifierMasker` for reversible PII masking before external LLM calls. `SafetySandbox` with command validation, path safety, and deception detection.
- **Synthetic Eval Scenarios**: 10 OpenSRE-style root-cause analysis scenarios with `ScenarioScorer` (RCA scoring, evidence tracking, red herring penalty).
- **Self-Improvement Cycle**: `ImprovementCycle` (HALO-inspired) collects traces, analyzes failure patterns, and writes recommendations to memory files. Scheduled weekly via Huey.
- **Slash Command System**: Modular command registry with `/help`, `/status`, `/cost`, `/sessions`, `/resume`, `/effort`, `/integrations`, `/agents`.
- **OTel Exporter**: `OTelExporter` for OpenTelemetry-compatible trace export to HALO, Arize, Langfuse, or local JSONL. Supports `CATALYST_OTLP_TOKEN` and `HALO_TELEMETRY_PATH`.
- **Workflow Engine**: YAML-driven workflow definitions with steps, conditions, and logging.
- **Memory CLI**: `aiw memory` commands for L1/L2/L3 management.

#### Save-Port Work Merge: Rules, Workflows, References (+9,735 lines)
- **Rules System**: Declarative rules engine for code style, architecture patterns, and project conventions.
- **Templates**: Reusable document templates for ADRs, research, features, and daily notes.
- **References**: Curated cheat sheets and command references.
- **Analysis Docs**: Shade shell audit, GTK research, workspace upgrade design.

#### External Project Integration (DeepTutor, OpenViking, HALO, OpenSRE, Career-Ops)
- **TieredContextLoader wired into AgentLoop**: L0/L1 context injected into system prompts for both DIRECT and REACT patterns.
- **PersistentMemory post-session**: Agent loop automatically writes L1 traces after each session completes.
- **consult_subagent tool**: Partners can be consulted mid-turn via tool call with SOUL.md persona and private KB injection.
- **Scheduled ImprovementCycle**: `periodic_improvement_cycle` runs every Sunday 7:00 BRT via Huey.
- **Done event enriched**: `session_id` and `trajectory` metadata in LoopEvent done data.

#### Gemini Rate-Limit Handling
- **Cooldown mechanism**: After hitting rate limit, prevent retries for 60s (min) or 24h (day).
- **429 detection**: `record_rate_limit_hit(provider)` adds burst timestamps + cooldown on HTTP 429.
- **Status API**: `get_rate_limit_status(provider)` returns `within_limits`, `requests_minute`, `requests_day`, `cooldown_remaining`.
- **Availability integration**: `check_availability()` and `check_availability_sync()` reflect real rate-limit state for Gemini.
- **Recovery logging**: Logs when Gemini cooldown expires and provider re-enables.

#### Infrastructure
- **CrediNet**: `credigraph` v0.4.1 installed for domain credibility checking with 7-day cache and 3-retry backoff.
- **Reranker cascade**: Ollama `/api/rerank` → sentence-transformers cross-encoder → keyword overlap fallback. Configurable via `RERANKER_METHOD`.
- **17 E2E Reranker tests**: Keyword backend, Ollama backend (mocked), cross-encoder delegation, fallback chain, KnowledgeRetriever integration.
- **11 Rate-limit tests**: Cooldown, 429 detection, status API, availability integration, reset.

### Changed
- **AgentLoop**: Now initializes `TieredContextLoader` and writes `PersistentMemory` L1 traces post-session.
- **LoopEvent done**: Includes `session_id` and `trajectory` metadata.
- **_run_direct / _run_react**: Inject tiered context (L0/L1) into system prompt before memory tree fallback.
- **Partner.consult()**: Now routes through agent loop with SOUL.md persona (was simulated stub).
- **CHANGELOG**: Updated from v0.1.0 to v0.2.0.

### Fixed
- **Accidental requirements.txt**: Removed (deps live in pyproject.toml).

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
