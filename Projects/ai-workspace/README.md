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
|  Layer 3: OMP Agent                    |
|  - Project skills in .omp/skills/       |
|  - User skills from OMP and .agents    |
|  - On-demand workflows                  |
|------------------------------------------|
|  Layer 2: Workspace (Obsidian vault)    |
|  - Folders for every dev activity       |
|  - Templates for consistent docs        |
|  - References for quick lookup          |
+------------------------------------------+
|  Layer 1: Knowledge workspace           |
|  - Obsidian vault and project notes     |
|  - Memory and persistent conventions   |
|  - Reusable templates                   |
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
| `.omp/skills/` | Project OMP skills | OMP agent and AI Workspace skill loader |
| `.obsidian/` | Obsidian vault config | Obsidian app |

## Key Files

| File | Role |
|------|------|
| `README.md` | Workspace map — folder purposes, workflows, quick tips |
| `.omp/skills/*/SKILL.md` | Project skill source (also loaded by the AI Workspace skill loader) |
| `.obsidian/app.json` | Obsidian behavior (new file locations, link updates) |
| `.obsidian/core-plugins.json` | Enabled Obsidian plugins |

## Hotspots

| Area | Why It's Critical |
|------|-----------------|
| `~/.omp/agent/skills/` | Native OMP user skills, loaded in OMP sessions. |
| `memory/conventions.md` | Accumulated rules and workflow guidance. |
| `.omp/skills/` | Project skill source; changes are discovered by the OMP agent and AI Workspace loader. |
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

## OMP Skills

Project skills live in `.omp/skills/`. The AI Workspace loader searches, in order:
`.omp/skills/`, `~/.agents/skills/`, and `~/.omp/agent/skills/`. Earlier sources take
precedence when skill names collide.

## Decisions

- **Markdown over structured DB**: Plain text, git-friendly, portable
- **OMP skills over custom scripts**: Agent Skills standard, works across harnesses
- **Obsidian over custom UI**: Mature, plugin ecosystem, graph view

## Risks

| Risk | Status | Mitigation |
|------|--------|------------|
| Skills drift from workspace source | Active | OMP and AI Workspace loader discover skills from `.omp/skills/` |
| AGENTS.md gets too large | Monitoring | Currently ~4KB, room for growth |
| No code-review-graph for markdown | Accepted | Not applicable — workspace is docs, not code |
| Obsidian config not in Nix | Accepted | `.obsidian/` is manually managed |
