# Agent Setup Streamline — Design Spec

**Date:** 2026-06-11
**Status:** Draft
**Goal:** Reduce the pi agent setup from 29 scattered skills + 1,184 lines of unused agent config into a lean, consolidated, documented system with ~20 skills in a single directory.

---

## 1. Removals (Dead Weight)

| Item | Path | Size | Reason |
|---|---|---|---|
| 12 SDD agent definitions | `~/.pi/agent/agents/sdd-*.md` | ~1,000 lines | Zero usage in run history |
| 3 SDD chains | `~/.pi/agent/chains/sdd-*.chain.md` | ~200 lines | Zero usage in run history |
| Duplicate find-skills | `~/.pi/agent/skills/find-skills/` | 133 lines | Identical to pi-managed copy in `.agents/skills/find-skills/` |
| cv-review as active skill | `~/.pi/agent/skills/cv-review/` | 357 lines | Demote to `References/cv-review.md` — it's a reference doc, not a workflow skill |
| Empty workspace dirs | `Follow-ups-and-Blockers/`, `Processing/`, `Ideas-and-Backlog/` | — | Only contain placeholder READMEs |
| Empty feature dirs | `Development/Features/In-Progress/`, `Development/Features/Done/` | — | Structure without content |

## 2. Skill Merges (Consolidation)

| Merge | Into | Rationale |
|---|---|---|
| `pre-review` + `requesting-code-review` + `receiving-code-review` | **`code-review`** | Three phases of the same workflow |
| `writing-plans` + `writing-skills` | **`authoring`** | Both write structured documents |
| `executing-plans` + `verification-before-completion` + `finishing-a-development-branch` | **`delivery`** | Natural pipeline: execute → verify → finish |
| `dispatching-parallel-agents` + `subagent-driven-development` | **`parallel-work`** | Both manage concurrent agent execution |

Net: 10 skills → 4 merged skills.

## 3. Single Source of Truth

- Move all 14 user-authored skills from `.agents/skills/` into `.pi/agent/skills/`
- Keep 3 pi-installed skills in `.agents/skills/` (managed by pi: `find-skills`, `nixos-best-practices`, `playwright-best-practices`)
- Result: `.pi/agent/skills/` is the canonical home for all user-authored skills

## 4. Catalog & Documentation

- **`SKILL_CATALOG.md`** — rebuilt with categories: Core Workflow, Code Quality, Testing, Project Lifecycle, Research, System, Parallel
- **`USAGE.md`** at workspace root — one-page mental model of how the agent works

## 5. Workspace Cleanup

- Delete empty placeholder directories
- Demote `cv-review` content to `References/cv-review.md`

---

## Surviving Skills (~20 total)

After all changes:

| Skill | Origin | Category |
|---|---|---|
| brainstorm | `.agents/` → `.pi/` | Core Workflow |
| authoring (merged) | `.agents/` → `.pi/` | Core Workflow |
| delivery (merged) | `.agents/` → `.pi/` | Core Workflow |
| code-review (merged) | `.agents/` → `.pi/` | Code Quality |
| desloppify | `.pi/` | Code Quality |
| debug | `.pi/` | Code Quality |
| systematic-debugging | `.agents/` → `.pi/` | Code Quality |
| test-driven-development | `.agents/` → `.pi/` | Testing |
| playwright-best-practices | `.agents/` (pi-managed) | Testing |
| feature-dev | `.pi/` | Project Lifecycle |
| onboard | `.pi/` | Project Lifecycle |
| commit | `.pi/` | Project Lifecycle |
| create-pr | `.pi/` | Project Lifecycle |
| deep-research | `.pi/` | Research |
| learn | `.pi/` | Research |
| recursive-learning | `.pi/` | Research |
| nixfiles | `.pi/` | System |
| nixos-best-practices | `.agents/` (pi-managed) | System |
| using-git-worktrees | `.agents/` → `.pi/` | System |
| using-superpowers | `.agents/` → `.pi/` | Core Workflow |
| find-skills | `.agents/` (pi-managed) | Discovery |
| parallel-work (merged) | `.agents/` → `.pi/` | Parallel |

---

## Non-Goals

- Modifying extension code (extensions work fine as-is)
- Changing pi configuration beyond the skills path
- Refactoring the workspace memory system
- Building CI/CD for the setup itself
