# Recursive Learning Skill — Design Spec

**Date:** 2026-06-09
**Status:** Approved
**Type:** Agent skill

## Purpose

A skill that mines past PI session logs for useful information and persists it to workspace memory. Learns recursively: improves its own extraction heuristics over time.

## Output

Writes to existing workspace memory files:
- `conventions.md` — behavioral optimizations, constraints, rules
- `project-patterns.md` — code structure, architecture, file roles
- `learning-log.md` — discoveries, bugs, fixes, tool quirks

## Components

### 1. `analyze_sessions.py` — Deterministic Parser

Pure computation, no LLM calls. Processes session JSONL files.

**Extracts per session:**
- Session fingerprint (first user message, cwd, timestamp)
- Tool call profile (counts by tool, sequences)
- Error signals (isError: true, non-zero bash exits)
- Correction loops (same file read/edit 3+ times in one session)
- Discovery density (first-time file accesses vs prior sessions)
- Token profile (usage blocks from assistant messages, when available)
- Session length (turn count, duration)
- Project files touched (unique file paths)

**Scoring algorithm:**
```
score = (error_count × 10)
      + (correction_loops × 8)
      + (discovery_density × 5)
      + (unique_files_touched × 2)
      - (short_session_penalty)
```

**Output:** Top-N session digests as compact markdown (2–5KB each).

**State tracking:** Reads/writes `.meta-learning/state.json` to skip already-mined sessions and track known files.

### 2. Agent Workflow (LLM Synthesis)

Five phases:

| Phase | Action |
|---|---|
| **Scan** | Run `analyze_sessions.py --mode=scan`, get top 10 digests |
| **Categorize** | Classify findings into 4 buckets: code structure, discoveries, constraints, behavior optimizations |
| **Synthesize** | Filter: skip duplicates, skip single-session anecdotes, keep 2+ session patterns, update existing entries |
| **Write** | Append to appropriate memory file using `learn` skill format |
| **Update state** | Mark sessions as learned in state.json |

**4 buckets → memory mapping:**

| Bucket | Memory file |
|---|---|
| Code structure | `project-patterns.md` or `Projects/<name>/README.md` |
| Discoveries | `learning-log.md` |
| Constraints | `conventions.md` or `Projects/<name>/README.md` |
| Behavior optimizations | `conventions.md` (global) or `memory/project-patterns.md` (per-project) |

### 3. Meta-Learning Loop

Three cycles, increasing depth:

| Cycle | Trigger | Action |
|---|---|---|
| **1** | Every run | Session → Memory: extracts findings, writes to memory |
| **2** | Every 5+ sessions since last review | Memory → Heuristics: reviews extraction gaps, tunes scoring weights, updates `analyze_sessions.py` or `state.json` |
| **3** | Every 3+ heuristic changes | Heuristics → Skill: updates SKILL.md category definitions, red flags, workflow steps |

**Meta-learning journal:** `.meta-learning/journal.md` tracks extraction gaps, false patterns, heuristic tuning decisions.

**State file:** `state.json` tracks mined sessions, discovered files, extraction gaps, cycle counters.

## Directory Structure

```
~/.pi/agent/skills/recursive-learning/
  SKILL.md                    # Agent workflow (Phases 1-5 + meta-learning)
  analyze_sessions.py         # Deterministic parser + scorer
  meta-learning/
    journal.md                # Human-readable meta-learning log
    state.json                # Machine-readable mined state + heuristics
```

Per-project state at `<project>/.meta-learning/state.json`.

## Constraints

- Per-project scope (analyzes only sessions for current working directory)
- Balanced priority across all 4 extraction categories
- Output to workspace memory files only (no direct context injection)
- Python script must handle streaming for large files (2MB+ sessions)
- Must not duplicate existing memory entries
- Session scoring heuristics are tunable via state.json

## Success Criteria

1. Skill correctly identifies high-signal sessions (those with errors, corrections, discoveries)
2. Extracted findings are non-duplicative and correctly categorized
3. Meta-learning loop detects and corrects at least one extraction gap after 5+ runs
4. Token cost per run is < 50K tokens (script + digest processing)
5. Script processes 100+ sessions in under 5 seconds
