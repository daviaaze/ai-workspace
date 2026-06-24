# Plan: Incorporate External Insights from DeepTutor, OpenViking, HALO, OpenSRE, Career-Ops

> **Status:** Proposal | **Date:** 2026-06-24
> **Sources:** HKUDS/DeepTutor, volcengine/OpenViking, Tracer-Cloud/opensre, santifer/career-ops, context-labs/HALO
> **Refs:** AUDIT_KEEP_VS_KILL.md, SPEC_*, existing `src/ai_workspace/`

---

## Executive Summary

This plan identifies **10 concrete incorporation opportunities** across 5 external projects, prioritized by impact vs effort relative to aiw's current codebase and v2 roadmap.

Each opportunity includes:
- **What** to incorporate
- **Source** project and specific module/file pattern
- **Target** aiw module(s)
- **Effort** estimate (Low / Medium / High)
- **Impact** estimate
- **Dependencies** on other plan items
- **Implementation notes** specific to aiw's existing code

---

## Prioritization Framework

Projects are prioritized by **relevance × maturity × architectural alignment**:

| Rank | Project | Why | Why Not |
|------|---------|-----|---------|
| 1 | **DeepTutor** | Near-identical vision (agent workspace), further along, Apache 2.0 | Heavy frontend (Next.js) we don't need |
| 2 | **OpenViking** | Solves a real problem aiw has (token economy, context debuggability) | AGPLv3 (code-at-a-distance), Rust dep optional |
| 3 | **HALO** | Directly fills aiw's biggest gap: no self-improvement cycle | Still early-stage methodology |
| 4 | **OpenSRE** | Rich interaction patterns for TUI/CLI | Domain-specific (SRE), less generalizable |
| 5 | **Career-Ops** | Validates SKILL.md approach, batch processing patterns | Domain-specific (job search) |

---

## Phase 1: High-Impact, Low-Medium Effort (Weeks 1-3)

### 1.1 Slash Command System — OpenSRE → TUI/CLI

**Source:** OpenSRE's `app/cli/interactive_shell/command_registry/` — modular slash command system with `/help`, `/status`, `/cost`, `/sessions`, `/resume`, `/effort`, `/integrations`, `/agents`

**Target:** `tui/command_palette.py` + `cli.py`

**Current state:** aiw has 6 hardcoded commands in `tui/command_palette.py`

**What to do:**
- Replace hardcoded `COMMANDS` list with a **command registry** pattern (class-based, self-registering)
- Add commands inspired by OpenSRE: `/resume` (restore session), `/cost` (token tracking already in `core/cost.py`), `/sessions`, `/agents` (local agent fleet)
- Support `Ctrl+C` for cancelling in-flight operations without losing session state
- Add streaming investigation output (OpenSRE's pattern of showing tool calls live as they happen)

**Effort:** Low (2-3 days)
**Impact:** Medium — improves daily UX significantly
**Dependencies:** None

**Code reference:**
```
OpenSRE: app/cli/interactive_shell/command_registry/
  ├── agents.py, alerts.py, session_cmds.py, settings_cmds.py
  ├── types.py (base class), slash_catalog.py, suggestions.py

aiw: tui/command_palette.py
  └── 6 commands, flat list, no registry pattern
```

### 1.2 HALO Self-Improvement Loop — Observability → Evals → Agents

**Source:** HALO's loop: `Collect traces → RLM analysis → Report → Fix → Redeploy`

**Target:** `observability/` + `evals/` + new `agents/improvement.py`

**Current state:** aiw has DiffTracker + TraceStore in `observability/` and EvalCase framework in `evals/` — but they don't talk to each other

**What to do:**
- Wire `TraceStore` (observability) → `EvalCase` (evals) into a closed feedback loop
- Add a weekly/monthly `ImprovementCycle` that:
  1. Reads traces from `TraceStore` for the period
  2. Feeds them through a specialized analysis agent (not a general coding agent — this is HALO's RLM insight)
  3. Produces a structured report with: common failure patterns, tool misuse, prompt optimization opportunities
  4. Writes recommendations to `memory/conventions.md` and `memory/project-patterns.md`
- This is **not** a full RLM (we don't build a specialized model) — it's a **meta-agent** that analyzes traces

**Effort:** Low (3-4 days)
**Impact:** High — closes the observability → improvement gap, makes the system self-tuning
**Dependencies:** None (observability + evals already exist)

### 1.3 OpenSRE Integration Catalog Pattern — MCP Discovery

**Source:** OpenSRE's 60+ tool integration catalog with categories, verification, roadmap links

**Target:** `mcp_server/` + `tools/marketplace.py`

**Current state:** aiw has `tools/marketplace.py` (322 lines) but no categorized catalog

**What to do:**
- Extend `marketplace.py` with a categorized registry (LLMs, Observability, Infrastructure, Databases, Communication, etc.)
- Add integration verification (`/integrations verify` pattern from OpenSRE)
- Generate categorized tool matrix as markdown (for `docs/` and TUI help)

**Effort:** Low (1-2 days)
**Impact:** Low-Medium — improves discoverability
**Dependencies:** None

### 1.4 HALO OpenTelemetry-Based Agent Tracing — Observable Observability

**Source:** HALO's OTel-compatible tracing, Langfuse/Arize import, `task env:setup` pattern

**Target:** `observability/` — add OTel export capability

**Current state:** aiw's `observability/__init__.py` writes to JSONL files (TraceStore) but doesn't emit OTel spans

**What to do:**
- Add optional `OpenTelemetryExporter` to `TraceStore` that emits spans compatible with HALO/OpenInference format
- This makes aiw's traces importable into HALO itself (eat your own dog food)
- Support `CATALYST_OTLP_TOKEN` / `HALO_TELEMETRY_PATH` env vars for export destinations

**Effort:** Low (2 days)
**Impact:** Medium — enables HALO analysis of aiw's own agents
**Dependencies:** 1.2 (feeds into the improvement loop)

### 1.5 Career-Ops Batch Processing Pattern — Parallel Swarm Workers

**Source:** Career-Ops `batch/batch-runner.sh` + `batch/batch-prompt.md` — simple parallel worker pattern

**Target:** `agents/swarm.py` — add `BatchSwarm` pattern

**Current state:** aiw's `swarm.py` uses crewAI for swarms; it's YAML-driven and somewhat rigid

**What to do:**
- Add a lightweight `BatchSwarm` class that takes N tasks, spawns M parallel agent workers, collects results
- Model it on Career-Ops' simplicity: a shared context file (`batch-prompt.md`), a runner script, N parallel instances
- Each worker gets its own isolated context slice from `context_manager`
- Results are merged by a collector function

**Effort:** Low (2 days)
**Impact:** Medium — enables parallel task processing for the agent swarm
**Dependencies:** None

### 1.6 DeepTutor Unified Agent Loop — Harmonize aiw's Dispatchers

**Source:** DeepTutor's `ChatOrchestrator` — one loop that runs chat, quiz, research, solve, mastery path

**Target:** `agents/loop.py` + `agents/router.py` + `agents/orchestrator.py`

**Current state:** aiw has 4 separate dispatching mechanisms:
- `agents/loop.py` (AgentLoop with DIRECT, REACT, PLAN_EXECUTE, REWOO)
- `agents/router.py` (route to agent types)
- `agents/orchestrator.py` (orchestrate multi-agent workflows)
- `agents/swarm.py` (crewAI swarms)

**What to do:**
- This is a **harmonization** pass, not a rewrite
- Add a `Capability` concept (matching DeepTutor): a capability declares what tools it needs, what model params, what context sources
- `AgentLoop` can then dispatch to the right capability without changing the loop itself
- Tools are mounted/unmounted based on capability context (rag for knowledge, exec for code, etc.)
- This reduces the need for `router.py` and `orchestrator.py` as separate entry points

**Effort:** Medium (4-5 days — careful refactor)
**Impact:** High — simplifies architecture, reduces code surface
**Dependencies:** None (refactor, not new feature)

---

## Phase 2: Medium-High Impact, Medium Effort (Weeks 3-5)

### 2.1 DeepTutor 3-Layer Persistent Memory — Replace/Extend MemoryTree

**Source:** DeepTutor's `memory/` system:
- **L1**: Append-only event traces (`trace/<surface>/<date>.jsonl`)
- **L2**: Per-surface curated facts (`L2/<surface>.md`)
- **L3**: Cross-surface synthesis (`L3/<profile|recent|scope|preferences>.md`)
- Memory Graph: visual pyramid showing L3→L2→L1 traceability

**Target:** `agents/memory_tree.py` + new `agents/memory.py`

**Current state:** aiw's `memory_tree.py` is execution-scoped (per-session subgoal tree), not persistent.
Files exist in `memory/` dir (conventions.md, project-patterns.md, learning-log.md) but they're unstructured.

**What to do:**
- Add a new `PersistentMemory` system alongside `MemoryTree`:
  - **L1 Trace**: Each agent session writes a JSONL trace to `~/.aiw/memory/l1/`
  - **L2 Facts**: After each session, a light summarizer extracts facts → `~/.aiw/memory/l2/<surface>.md`
  - **L3 Synthesis**: Weekly consolidation across surfaces → `~/.aiw/memory/l3/{profile,recent,scope}.md`
- L2 cites L1, L3 cites L2 — every claim is traceable (this is the key innovation from DeepTutor)
- Add a `Memory Graph` visualization to the TUI (aiw already has `tui/graph.py` for cytoscape-style graphs)
- Keep `MemoryTree` for in-session execution tracking; add `PersistentMemory` for cross-session knowledge

**Effort:** Medium (5-7 days)
**Impact:** Very High — transforms aiw's memory from session-scoped to persistent, auditable, cross-session
**Dependencies:** None (MemoryTree stays, PersistentMemory is additive)

### 2.2 OpenViking Tiered Context Loading — Token Economy

**Source:** OpenViking's L0/L1/L2 tiered loading — on-demand context expansion, directory-based

**Target:** `agents/context_manager.py` + `agents/compaction.py`

**Current state:** aiw's `context_manager.py` tracks context blocks (pin, exclude, trim) but doesn't tier them.
`compaction.py` has L1/L2/L3 defined but they're about compaction pace, not loading tiers.

**What to do:**
- Add a `ContextTier` enum: `L0` (always-injected: system prompt, active task), `L1` (on-demand: KB entries, tool results), `L2` (expanded: full documents, trace details)
- `get_context()` builds context progressively: L0 always, L1 on attention, L2 on explicit request
- Add `directory-based` retrieval as an alternative to flat vector search: organize context by topic directories, retrieve by directory hierarchy + semantic search within
- Add **retrieval trajectory visualization**: when RAG returns context, show *how* it was found (which dir, which search terms, which rank). This addresses OpenViking's "unobservable context" problem.

**Effort:** Medium (4-6 days)
**Impact:** High — directly saves tokens, improves response quality
**Dependencies:** 2.3 (multi-engine RAG gives more retrieval engines to tier)

### 2.3 DeepTutor Multi-Engine RAG — Knowledge Abstraction

**Source:** DeepTutor's `Knowledge Center` — choose engine per KB: LlamaIndex, PageIndex, GraphRAG, LightRAG, LightRAG Server, Obsidian vault

**Target:** `knowledge/rag.py` + `knowledge/store.py`

**Current state:** aiw's `knowledge/rag.py` is pgvector-only with nomic-embed-text + hybrid search. Single engine.

**What to do:**
- Add an abstract `RetrievalEngine` interface with metadata:
  - `engine_type`: `vector`, `graph`, `page_index`, `obsidian`, `lightrag`
  - `supports()`: capabilities query (hybrid search, graph traversal, page-level, etc.)
  - `retrieve(query, kb_id, top_k)`: returns uniform `RetrievalResult[]` regardless of engine
- Implement first additional engine: **LightRAG adapter** (knowledge-graph based, good for relational queries)
- Implement second: **Obsidian vault adapter** (read-in-place, no re-indexing)
- KB creation flow: choose engine when creating, swap only by re-indexing
- Add `SPEC_RAG.md` update: the v0.2 simplification recommendation (from AUDIT_KEEP_VS_KILL) is valid, but we add engine abstraction as v0.3+ architecture

**Effort:** Medium-High (5-8 days)
**Impact:** Very High — unlocks multiple knowledge paradigms
**Dependencies:** 2.2 (tiered loading benefits from multiple engines)

### 2.4 DeepTutor Partner/SOUL.md System — Agent Swarm w/ Personality

**Source:** DeepTutor's `Partners` — persistent companions with `SOUL.md`, own memory, own skills, channel binding, subagent consult

**Target:** `agents/swarm.py` + new `agents/partner.py` + `agents/skill_matcher.py`

**Current state:** aiw's `swarm.py` creates crewAI agents from YAML. No persistent persona, no private memory, no channel binding.

**What to do:**
- Add `Partner` class with:
  - `SOUL.md` — personality, expertise, behavior rules (markdown file in `~/.aiw/partners/<name>/`)
  - Private workspace (`~/.aiw/partners/<name>/workspace/`) with isolated KB, skills, memory
  - Tool policy: allow/deny list per partner (MCP tools, shell access, etc.)
  - Channel binding: optional IM channel (matrix, slack, telegram) for persistent presence
  - `consult_subagent` tool: consult a partner from any chat turn (modeled on DeepTutor's `@` + `consult_subagent`)
- Partners read their owner's memory but write only their own (privacy boundary)
- Add `partners list`, `partners create`, `partners chat` commands to CLI

**Effort:** High (8-12 days)
**Impact:** Very High — directly delivers aiw v2's agent swarm vision
**Dependencies:** 2.1 (PersistentMemory for partner memory), 2.3 (RAG for partner knowledge), 1.6 (unified loop feeds partner chat)

---

## Phase 3: Nice-to-Have / When Validated (Weeks 5+)

### 3.1 Career-Ops Dashboard TUI Patterns — Interaction Design

**Source:** Career-Ops Go + Bubble Tea dashboard — filter tabs, sort modes, grouped/flat view, lazy-loaded previews, inline status changes

**Target:** `tui/dashboard.py` + `tui/workspace.py`

**Current state:** aiw's `tui/dashboard.py` has basic agent status display

**What to do:**
- Add filter tabs (by status, by surface, by model), sort modes, grouped view
- Lazy-loaded previews (don't load full details until selected)
- Inline status changes (click to change, like Career-Ops)
- Catppuccin theme support (aiw already uses similar colors)

**Effort:** Medium (3-5 days)
**Impact:** Medium — UX polish
**Dependencies:** None

### 3.2 OpenViking RAGFS — Context as Filesystem Experiment

**Source:** OpenViking's FUSE-based filesystem for agent context

**Target:** New experimental module `context_fs/`

**What to do:**
- Build an optional FUSE filesystem that mounts `~/.aiw/context/` as a virtual filesystem
- Each knowledge base = directory, each retrieval = file read, write = memory store
- This is an **experimental** feature, gated behind `aiw context-fs mount`
- Requires FUSE bindings (Python's `fusepy` or `pyfuse3`)

**Effort:** Medium (3-4 days)
**Impact:** Low-Medium — novel UX, unproven value
**Dependencies:** None

### 3.3 OpenSRE Synthetic Evaluation Scenarios

**Source:** OpenSRE's synthetic RCA suites with scored root-cause analysis

**Target:** `evals/` — add `synthetic/` scenarios

**Current state:** aiw's `evals/` has 3 suites with 6 cases, all static

**What to do:**
- Add synthetic scenario generation: define failure modes, let agent investigate, score response
- Pattern: `Scenario(symptoms, expected_rca, required_evidence, red_herrings)` → agent investigates → scored
- Start with 5-10 infrastructure failure scenarios (service down, DB slow, config drift)

**Effort:** Medium (3-4 days)
**Impact:** Medium — improves agent reliability testing
**Dependencies:** 1.2 (evaluation → improvement loop)

### 3.4 OpenSRE PII Masking — Security Pattern

**Source:** OpenSRE's reversible identifier masking before external LLM calls

**Target:** `agents/safety.py`

**Current state:** aiw's `agents/safety.py` focuses on deception detection, not PII masking

**What to do:**
- Add `IdentifierMasker` class: scan messages for IPs, hostnames, account IDs, API keys → replace with placeholders → restore in output
- Gated by provider type (only for external/cloud providers, not local Ollama)

**Effort:** Low (1-2 days)
**Impact:** Medium — security improvement
**Dependencies:** None

---

## Dependency Graph

```
Phase 1                    Phase 2                    Phase 3
───────                    ───────                    ───────

1.1 Slash Commands ─┐
                    ├── no deps
1.2 HALO Loop ──────┤
                    │
1.3 Integ Catalog ──┤
                    │
1.4 OTel Tracing ───┤──── feeds into ──→ 1.2
                    │
1.5 Batch Swarm ────┤
                    │
1.6 Unified Loop ───┤──── enables ─────→ 2.4 Partners
                    │
                    ├──────────────────→ 2.1 Persistent Memory
                    │                         │
                    ├──────────────────→ 2.2 Tiered Loading ──→ 2.3 Multi-Engine RAG
                    │                         │
                    └──────────────────→ 2.4 Partners ─────────┘
                                                    │
                                                    └──────────→ 3.1 Dashboard UX
                                                             → 3.2 RAGFS
                                                             → 3.3 Synthetic Evals
                                                             → 3.4 PII Masking
```

---

## Effort Summary

| Phase | Items | Days | Impact |
|-------|-------|------|--------|
| **Phase 1** | 6 items | 14-18 days | High |
| **Phase 2** | 4 items | 22-33 days | Very High |
| **Phase 3** | 4 items | 10-15 days | Low-Medium |
| **Total** | **14 items** | **46-66 days** | |

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Feature creep (too many things at once) | Medium | Phase-gated delivery; each phase must ship before starting next |
| DeepTutor Partners overlap with pi's existing agent system | Medium | Reuse pi's SKILL.md format, don't duplicate what pi already provides |
| AGPLv3 contamination from OpenViking | Low | Use as inspiration/pattern, not code; document boundaries in `docs/ATTRIBUTION.md` |
| Memory system too complex for user value | Medium | Start with L1-only (traces), add L2/L3 incrementally |
| Unified loop refactor breaks existing behavior | Medium | Keep old entry points working; add Capability concept as wrapper, not replacement |

---

## Verification Criteria

Each item ships when:
1. **Tests pass** — existing test suite continues passing
2. **New tests exist** — at least basic coverage for new functionality
3. **Docs updated** — relevant `docs/specs/` and README reflect changes
4. **Manual verification** — a demo scenario works end-to-end
5. **No regressions** — old interfaces still work (backward compat)

---

## Source Files to Touch (Non-Exhaustive)

| File | Owner | Phase |
|------|-------|-------|
| `src/ai_workspace/tui/command_palette.py` | 1.1 | 1 |
| `src/ai_workspace/cli.py` | 1.1 | 1 |
| `src/ai_workspace/observability/__init__.py` | 1.2, 1.4 | 1 |
| `src/ai_workspace/evals/__init__.py` | 1.2 | 1 |
| `src/ai_workspace/agents/__init__.py` (new: `improvement.py`) | 1.2 | 1 |
| `src/ai_workspace/tools/marketplace.py` | 1.3 | 1 |
| `src/ai_workspace/agents/swarm.py` | 1.5 | 1 |
| `src/ai_workspace/agents/loop.py` | 1.6 | 1 |
| `src/ai_workspace/agents/router.py` | 1.6 | 1 |
| `src/ai_workspace/agents/orchestrator.py` | 1.6 | 1 |
| `src/ai_workspace/agents/memory_tree.py` | 2.1 | 2 |
| `src/ai_workspace/agents/__init__.py` (new: `memory.py`) | 2.1 | 2 |
| `src/ai_workspace/agents/context_manager.py` | 2.2 | 2 |
| `src/ai_workspace/agents/compaction.py` | 2.2 | 2 |
| `src/ai_workspace/knowledge/rag.py` | 2.3 | 2 |
| `src/ai_workspace/knowledge/store.py` | 2.3 | 2 |
| `src/ai_workspace/agents/__init__.py` (new: `partner.py`) | 2.4 | 2 |
| `src/ai_workspace/agents/skill_matcher.py` | 2.4 | 2 |
| `src/ai_workspace/tui/dashboard.py` | 3.1 | 3 |
| `src/ai_workspace/agents/safety.py` | 3.4 | 3 |

---

## Immediate Next Steps (If Approved)

1. **Start Phase 1.1** — Refactor `tui/command_palette.py` to use command registry pattern, add `/resume`, `/sessions`, `/cost`, `/agents`
2. **Start Phase 1.2** — Wire `TraceStore` → `EvalCase` → `ImprovementCycle` in `agents/improvement.py`
3. **Start Phase 1.6** — Add `Capability` concept to `agents/loop.py`, harmonize `router.py`/`orchestrator.py` usage
4. **Review Phase 2 scope** — PersistentMemory (2.1) is the highest-value item in Phase 2 and should follow immediately after Phase 1
