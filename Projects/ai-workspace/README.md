# Project: ai-workspace

**Status:** onboarded
**Date:** 2026-05-04
**Type:** Knowledge base + AI agent workspace
**Language:** Markdown
**Framework:** Obsidian vault + OMP coding agent harness

## Architecture

This is a personal knowledge management system optimized for AI-assisted development. It has three integrated layers:

```
+------------------------------------------+
|  Layer 3: AI Agent Harness (OMP)       |
|  - AGENTS.md (agent context)            |
|  - Skills (on-demand workflows)         |
|  - Prompts (quick commands)              |
+------------------------------------------+
|  Layer 2: Workspace (Obsidian vault)    |
|  - Folders for every dev activity       |
|  - Templates for consistent docs        |
|  - References for quick lookup          |
+------------------------------------------+
|  Layer 1: Infrastructure (Nix)          |
|  - Home Manager module                  |
|  - Declarative config management        |
+------------------------------------------+
```

## Folder Structure

| Folder | Purpose | Used By |
|--------|---------|---------|
| `Development/Features/` | Feature lifecycle (Backlog → In-Progress → Done) | `feature-dev` skill |
| `Projects/` | Project context and architecture docs | `onboard` skill |
| `Research/` | Spikes, POCs, benchmarks | `research` prompt |
| `Technical-Decisions/` | Architecture Decision Records | `adr` prompt |
| `References/` | Cheat sheets and quick lookup | Manual reference |
| `Templates/` | Reusable document models | Template engine |
| `memory/` | Persistent learnings and corrections | `learn` skill |
| `Processing/` | Raw content inbox | Manual workflow |
| `Ideas-and-Backlog/` | Raw ideas | Manual capture |
| `Code-Reviews/` | Review notes | Manual capture |
| `Prompts/` | Saved prompts | Manual capture |
| `.omp/skills/` | Project skill source | OMP and AI Workspace |
| `.obsidian/` | Obsidian vault config | Obsidian app |
| `.pi/` | Project-level PI settings | PI agent |

## Key Files

| File | Role |
|------|------|
| `README.md` | Workspace map — folder purposes, workflows, quick tips |
| `.omp/skills/` | Project skill source for the agent and AI Workspace |
| `.obsidian/app.json` | Obsidian behavior (new file locations, link updates) |
| `.obsidian/core-plugins.json` | Enabled Obsidian plugins |

## Hotspots

| Area | Why It's Critical |
|------|-----------------|
| `~/.omp/agent/AGENTS.md` | Loaded in every OMP session. Contains workspace path, conventions, and graph tool rules. |
| `memory/conventions.md` | Accumulated rules read by agent sessions outside the workspace. Corrections here persist across projects. |
| `Development/Features/` | Active work lives here. The `feature-dev` skill creates, moves, and manages these folders. |

## Entry Points

| Workflow | Trigger | Entry File |
|----------|---------|------------|
| Start a feature | `/feature <name>` or `implement` | `Development/Features/Backlog/<name>/ticket.md` |
| Research spike | `/research <topic>` | `Research/<topic>.md` |
| Create ADR | `/adr <title>` | `Technical-Decisions/ADR-NNN-<title>.md` |
| Save learning | `/learn [topic]` | `memory/conventions.md` or `project-patterns.md` or `learning-log.md` |
| Analyze repo | `/skill:onboard` | `Projects/<repo-name>/README.md` |
| Review code | `/review` | Inline analysis |
| Explain code | `/explain <file>` | Inline explanation |
| Generate tests | `/test <file>` | Inline test output |
| Plan refactor | `/refactor <file>` | Inline plan |

## Obsidian Integration

The workspace doubles as an Obsidian vault:
- **Graph view**: Visualize links between documents (`Ctrl+Shift+G`)
- **Templates**: Insert via `/` command, hotkey `Ctrl+T`
- **Quick capture**: Drop files into `Processing/` or `Media-Inbox/`
- **Backlinks**: See which documents reference each other


## Decisions

- **Markdown over structured DB**: Plain text, git-friendly, portable
- **OMP skills over custom scripts**: Agent Skills standard, works across harnesses
- **Obsidian over custom UI**: Mature, plugin ecosystem, graph view

## Risks

| Risk | Status | Mitigation |
|------|--------|------------|
| Skills source | Active | Project skills live in `.omp/skills/` |
| AGENTS.md gets too large | Monitoring | Currently ~4KB, room for growth |
| No code-review-graph for markdown | Accepted | Not applicable — workspace is docs, not code |
| Obsidian config not in Nix | Accepted | `.obsidian/` is manually managed |
