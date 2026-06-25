# Project: ai-workspace

**Status:** onboarded
**Date:** 2026-05-04
**Type:** Knowledge base + AI agent workspace
**Language:** Markdown
**Framework:** Obsidian vault + PI coding agent harness

## Architecture

This is a personal knowledge management system optimized for AI-assisted development. It has three integrated layers:

```
+------------------------------------------+
|  Layer 3: AI Agent Harness (PI)         |
|  - AGENTS.md (global context)           |
|  - Skills (8 on-demand workflows)       |
|  - Prompts (10 quick commands)          |
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
| `pi-setup/` | PI configuration source | Nix module |
| `.obsidian/` | Obsidian vault config | Obsidian app |
| `.pi/` | Project-level PI settings | PI agent |

## Key Files

| File | Role |
|------|------|
| `README.md` | Workspace map — folder purposes, workflows, quick tips |
| `.pi/settings.json` | PI project settings (skills, prompts, thinking level) |
| `pi-setup/README-INSTALL.md` | Full setup and customization guide |
| `pi-setup/nix/pi-workspace.nix` | Home Manager module for declarative setup |
| `.obsidian/app.json` | Obsidian behavior (new file locations, link updates) |
| `.obsidian/core-plugins.json` | Enabled Obsidian plugins |

## Hotspots

| Area | Why It's Critical |
|------|-----------------|
| `~/.pi/agent/AGENTS.md` | Loaded in **every** PI session. Contains workspace path, conventions, graph tool rules. Changing this affects all sessions globally. |
| `memory/conventions.md` | Accumulated rules. PI reads this when outside the workspace. Corrections here persist across projects. |
| `pi-setup/nix/pi-workspace.nix` | Single source of truth for the entire PI setup. Changes here require `nixos-rebuild switch` to propagate. |
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

## Nix Integration

The workspace is managed declaratively:
```
pi-setup/nix/pi-workspace.nix → ~/.pi/agent/AGENTS.md
                              → ~/.pi/agent/skills/*/SKILL.md
                              → ~/.pi/agent/prompts/*.md
```

Changes to the Nix module propagate on `nixos-rebuild switch`.

## Decisions

- **Markdown over structured DB**: Plain text, git-friendly, portable
- **PI skills over custom scripts**: Agent Skills standard, works across harnesses
- **Nix over manual install**: Reproducible, versioned, rollback-capable
- **Obsidian over custom UI**: Mature, plugin ecosystem, graph view

## Risks

| Risk | Status | Mitigation |
|------|--------|------------|
| Skills drift from workspace source | Active | Nix module keeps them in sync |
| AGENTS.md gets too large | Monitoring | Currently ~4KB, room for growth |
| No code-review-graph for markdown | Accepted | Not applicable — workspace is docs, not code |
| Obsidian config not in Nix | Accepted | `.obsidian/` is manually managed |
