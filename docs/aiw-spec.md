# aiw Design Spec — What This Workspace Should Be

**Status:** Draft
**Date:** 2026-06-15

## The Problem

We've been porting pi features one-by-one (rules, learn workflow) without asking: what should `aiw` actually be?

The answer: aiw and pi are **complementary, not competitors**.

## Division of Labor

| Layer | aiw | pi |
|-------|-----|-----|
| **Knowledge** | PostgreSQL + pgvector + Obsidian + markdown memory | Reads from aiw knowledge store |
| **Research** | Deep search pipeline (crewAI swarm) | Web access, codebase graph analysis |
| **Workflows** | DAG engine + Huey scheduling (systemd timers) | Skill-based agent workflows |
| **LLM** | Multi-provider abstraction (Ollama, DeepSeek, Kimi) | Model routing per task |
| **Memory** | Persistent markdown files + vector search | Session memory + context injection |
| **Coding** | ❌ Not aiw's job | Code editing, review, debugging |
| **Git** | ❌ Not aiw's job | Commit, PR, branch management |
| **Safety** | Database transactions, input validation | Permission gates, protected paths |
| **System** | NixOS module, systemd integration | NixOS config management |

## What aiw Owns

### 1. Knowledge Backbone

The single source of truth for everything learned:

```
PostgreSQL (structured, searchable)
    ├── knowledge_entries (everything: notes, research, briefings)
    ├── agent_memory (mem0-like: facts, preferences, learnings)
    ├── tasks (with cron scheduling)
    ├── research_entries (deep search results)
    ├── workflow_runs (execution history)
    └── workflow_step_logs (per-step telemetry)

Markdown files (human-readable, git-tracked, offline)
    ├── memory/conventions.md       Rules and standards
    ├── memory/project-patterns.md  Workflows and approaches
    └── memory/learning-log.md      Discoveries and lessons

Obsidian vault (personal knowledge graph)
    └── Synced from knowledge_entries via 'aiw obsidian sync'
```

### 2. Research & Intelligence

```
aiw search "rust async patterns"
    → DeepSearchEngine
        → Planner Agent → 3-5 sub-questions
        → Parallel Researcher Agents → answers
        → Synthesizer Agent → report
        → KnowledgeBase → stored with embeddings

aiw ask "explain nix flakes"
    → Provider chat (Ollama, DeepSeek, or Kimi)
    → Simple, fast, no workflow overhead
```

### 3. Workflow Orchestration

Scheduled via Huey + systemd timers (NixOS integration):

```
07:00 daily_briefing    → Collect activity → generate briefing → store
08:00 daily_research    → Auto-research configured topics
02:00 continuous_learning → Extract patterns → update memory
**:** obsidian_sync     → Sync DB → Obsidian vault
```

Ad-hoc workflows:

```
aiw wf run deep_research --query "quantum computing in Rust"
aiw wf run learn --observation "Never use \" in nested f-strings"
```

### 4. Task Management

```
aiw task add "Write aiw spec" --priority 8 --tags planning
aiw task list
aiw task due              # What's due now (cron-based)
aiw task update 42 done
```

## What pi Owns

pi doesn't need to be rebuilt in aiw. pi already does these well:

- **Code editing** — The entire reason pi exists. aiw shouldn't touch code.
- **Code review** — Graph-based analysis, impact radius, review context
- **Debugging** — Hypothesis-driven, systematic root-cause tracing
- **Git** — Conventional commits, PR creation, branch management
- **NixOS** — System configuration, package management
- **Safety** — Permission gates, protected paths, auto-commit

## Integration Points

### aiw → pi

pi can call aiw as a CLI tool to get knowledge:

```bash
# pi queries aiw for context before code review
context=$(aiw kb search "code-review patterns" --limit 5)
aiw memory add "pattern found in $REPO" --type pattern
```

### pi → aiw

When pi learns something, it feeds it into aiw's knowledge store:

```bash
# After a debugging session, persist the learning
aiw wf run learn --observation "$(cat /tmp/pi-session-learning.txt)"
```

### Shared storage

Both read from the same workspace:
```
~/Projects/pessoal/ai-workspace/
    memory/          ← pi writes via /learn, aiw reads via KB
    templates/       ← Shared document templates
    analysis/        ← pi produces code reviews, aiw indexes them
    Knowledge-Base/   ← Shared reference docs
```

## What We Should Build

### Phase 1: Foundation (NOW — make aiw usable today)

1. **Rules injection into workflows** — Wire the RulesLoader into the workflow engine so every agent gets behavioral guardrails. Drop the crewai step in LearnWorkflow, use heuristic classification.

2. **Memory CLI** — `aiw memory list` to browse what's been learned (reads from markdown + DB), `aiw memory search "pattern"` for semantic search.

3. **Knowledge search** — `aiw kb search "nix flakes"` works without PostgreSQL (reads from markdown files as fallback).

### Phase 2: Integration (connect aiw ↔ pi)

4. **pi context injection** — pi reads `aiw kb search "context for $TASK"` before starting a feature. Reduces pi's need to re-discover things aiw already knows.

5. **Learning loop** — When pi finishes a debugging session, it calls `aiw wf run learn --observation "..."` to persist the discovery. aiw's continuous_learning workflow picks it up nightly.

### Phase 3: Autonomy (aiw runs itself)

6. **Self-improving knowledge** — The `continuous_learning` workflow genuinely extracts patterns (not just summary text). Uses clustering on vector embeddings to find themes across research.

7. **Proactive briefing** — `daily_briefing` becomes actually useful: surfaces urgent tasks, recent research insights, and knowledge gaps.

### What We Should NOT Build in aiw

| Feature | Why not in aiw | Lives in |
|---------|---------------|----------|
| Code editing agents | pi does this better (graph tools, safety extensions) | pi |
| Code review workflows | pi's graph tools (detect_changes, impact_radius) are purpose-built | pi |
| Git automation | pi has commit/PR skills with safety checks | pi |
| NixOS management | pi has nixfiles skill with system context | pi |
| Test generation | pi has TDD skill with codebase awareness | pi |
| Permission gates | Runtime-level safety, not application-level | pi extensions |

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                      pi (coding agent)                   │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌─────────────┐  │
│  │ skills/   │ │graph-tools│ │safety  │ │ extensions  │  │
│  └─────┬─────┘ └──────────┘ └────────┘ └─────────────┘  │
│        │                                                  │
│        │  reads context from aiw                          │
│        │  writes learnings to aiw                         │
│        ▼                                                  │
│  ┌─────────────────────────────────────────────────────┐ │
│  │                    aiw (knowledge workspace)         │ │
│  │                                                     │ │
│  │  CLI: search | ask | kb | memory | task | wf        │ │
│  │                                                     │ │
│  │  ┌─────────┐  ┌──────────┐  ┌──────────────────┐   │ │
│  │  │PostgreSQL│  │ Markdown │  │  Obsidian Vault  │   │ │
│  │  │+pgvector │  │  memory/ │  │  (synced from DB) │   │ │
│  │  └─────────┘  └──────────┘  └──────────────────┘   │ │
│  │                                                     │ │
│  │  ┌──────────────────────────────────────────────┐   │ │
│  │  │  Workflow Engine (DAG + Huey scheduling)     │   │ │
│  │  │  deep_research | daily_briefing | learn      │   │ │
│  │  │  continuous_learning                         │   │ │
│  │  └──────────────────────────────────────────────┘   │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Migration Path

```
Today:          pi does everything, aiw is a shell
                ↓
Phase 1 (now):  aiw has knowledge backbone + research + workflows
                pi still does coding
                ↓
Phase 2:        pi reads context from aiw before acting
                pi writes learnings to aiw after acting
                ↓
Phase 3:        aiw runs autonomously (scheduled workflows)
                pi becomes more efficient (less rediscovery)
```

## Success Criteria

1. `aiw kb search "any topic"` returns results in < 2 seconds
2. `aiw wf run learn --observation "..."` persists to markdown (works offline)
3. `aiw memory list` shows all learnings across markdown + DB
4. pi can run `aiw kb search "related to <current task>"` and get useful context
5. `continuous_learning` workflow runs nightly and actually finds patterns
