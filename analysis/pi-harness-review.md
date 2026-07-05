# Pi Harness Review — Skills & Context

**Date:** 2026-07-03
**Scope:** `~/.pi/agent/` (skills, extensions, rules, AGENTS.md) and source at `~/Projects/pessoal/ai-workspace/pi-setup/`.
**Goal:** Identify context bloat, problems, weak/low-value skills; improve skills and agent context.

## 1. Context Bloat (highest impact)

Every session loads `AGENTS.md` (5.6 KB) + `rules/*.md` global files (≈3.9 KB) + ~24 skill descriptions + active extensions. Redundancies:

| # | Issue | Fix |
|---|---|---|
| B1 | `AGENTS.md` duplicates `rules/00-global.md` (Core Imperatives appear verbatim in both). | Keep imperatives in AGENTS.md only; strip from `00-global.md`. |
| B2 | Code-Review-Graph guidelines triple-stated (system prompt + AGENTS.md + rules). | Keep one canonical copy (project-context injection); remove from AGENTS.md. |
| B3 | `using-superpowers` is a Claude/Superpowers port — references `Skill` tool, Gemini, Copilot. Wrong for Pi. | Delete. |
| B4 | `systematic-debugging` ships 1,030 lines/64 KB of side artifacts (CREATION-LOG, test-pressure, academic). | Collapse to single trimmed SKILL.md. |
| B5 | 24 skill descriptions per turn with near-duplicate overlaps. | Consolidate overlaps (§3). |

## 2. Problems / Contradictions

| # | Issue |
|---|---|
| P1 | `review-risk-framework` referenced as canonical rubric in `pre-review`/`create-pr`/`mode-manager` but no such skill/doc exists. |
| P2 | `SKILL_CATALOG.md` and `mode-manager` skills: arrays advertise nonexistent skills (`validate-infra`, `validate-migration`, `security-review`, `testing-strategy`, `review-risk-framework`, `confluence*`, `mode-plan`). |
| P3 | Hard-coded wrong workspace path `~/Projects/Lux/ai-workspace` in `daily` and `feature-dev` (real: `~/Projects/pessoal/ai-workspace`). |
| P4 | `ask-mode`/`plan-mode` exist in both `extensions/` and `extensions.disabled/`. |
| P5 | `debug` (workspace) vs `systematic-debugging` (agent) overlap, no cross-reference. |
| P6 | `code-review` (covers pre-review phase) vs `pre-review` (dedicated) overlap. |

## 3. Weak / Low-Value Skills

- `using-superpowers` — negative value in Pi. **Delete.**
- `recursive-learning`, `parallel-work`, `authoring` — thin; mostly restate AGENTS.md. Fold or remove.
- `stack-ref` — references dir lacks populated references; answers from general knowledge.
- `nixfiles` vs `nixos-best-practices` vs `run-with-nixpkgs` — three overlapping Nix skills. Consolidate to one.
- `systematic-debugging` side files — teaching artifacts, not workflow.

## 4. Recommended Fixes (prioritized)

1. Fix dangling `review-risk-framework` refs → inline rubric, remove name.
2. Reconcile catalog/mode-manager skills arrays with reality.
3. Fix workspace paths `Lux` → `pessoal`.
4. Delete duplicates: `using-superpowers`; merge `debug`→one; merge `code-review`+`pre-review`; clear `extensions.disabled/{ask-mode,plan-mode}`.
5. Single-copy global prompt (Core Imperatives, Graph Guidelines).
6. Trim `systematic-debugging` to one SKILL.md.
7. Consolidate Nix skills into one workspace-authored `nix` skill with `rules/` subfiles.
8. Remove thin low-value skills after secondary confirmation.
9. Add a deploy-time lint check enforcing catalog/path consistency.

## 5. Sync model note

Two classes of skills:
- **Tracked source** in `pi-setup/skills/`, deployed to `~/.pi/agent/skills/` as symlinks: `commit, create-pr, daily, debug, deep-research, deploy-checklist, desloppify, feature-dev, learn, nixfiles, onboard, pre-review`.
- **Live-only** in `~/.pi/agent/skills/` (not in pi-setup, part of Superpowers bundle): `authoring, brainstorming, code-review, delivery, parallel-work, recursive-learning, systematic-debugging, test-driven-development, using-git-worktrees, using-superpowers`.

Tracked fixes are committed to the workspace repo; live-only deletions/trims are applied directly to the agent dir.
---

## 6. Two-Scope Model (discovered during fix)

There are **two agents**: `~/.pi/agent` (personal, workspace `~/Projects/pessoal/ai-workspace`) and `~/.pi/agent-work` (work, workspace `~/Projects/Lux/ai-workspace`). Each has its own AGENTS.md, rules, extensions/mode-manager, and skills. Each has its own tracked `pi-setup/` source.

**Root cause of the leaks:** a *deployment inversion*. Work-specific skills were sourced from the **personal** `pi-setup/skills/` and deployed into `~/.pi/agent/skills/`, then `agent-work` symlinked them **back** into the personal agent — instead of deploying them from the **work** `pi-setup/skills/` into `agent-work` directly. This is why the personal agent "had work stuff": it was the source of truth for work skills.

### What was done

**Personal scope cleanup (`pessoal` workspace, committed)**
- Removed work skills from personal agent + pessoai `pi-setup/skills/`: `daily`, `deploy-checklist`, `stack-ref` (work pi-setup already owns them).
- Genericized `feature-dev` (dropped Jira/`jtk`/`XTRNT`); work keeps its Jira variant.
- Made `pre-review`/`create-pr` `review-risk-framework` reference **conditional** (shared skills work in both scopes) + fixed pre-review step numbering.
- Cleaned personal `SKILL_CATALOG.md` of work-only entries.
- Deleted `using-superpowers` (wrong tool names for Pi) and `code-review` (overlap with `pre-review`).
- Trimmed `systematic-debugging` → merged into `debug` (one root-cause-first SKILL.md).
- Fixed workspace paths `Lux` → `pessoal` across skills, extensions, prompts.
- Removed duplicated Core Imperatives (rules/00-global) and Graph Guidelines block (AGENTS.md).
- Genericized work-tinted personal prompts (`feature.md`, `learn.md`).
- Fixed personal `mode-manager` skill arrays to only reference personal-available skills.
- Added `pi-setup/check-consistency.sh` lint (P1/P3 + deploy-inversion guard).

**Work scope wiring (`Lux` workspace, left uncommitted for the work flow)**
- `agent-work/skills/` now sources `daily`, `deploy-checklist`, `stack-ref`, `validate-infra`, `validate-migration`, `feature-dev` from the **work** `pi-setup/skills/` (fixed dangling `validate-infra`, de-duplicated `validate-migration`).
- Added shared `deep-research` symlink.
- Moved `feature-tester` extension (Lux staging, `luxuryescapes.com`) from personal → work agent + work `pi-setup/extensions/`.

### Deferred / optional
- Consolidate three Nix skills (`nixfiles`, `nixos-best-practices`, `run-with-nixpkgs`) into one generic Nix skill — generic scope, lower priority.
- Thin generic skills (`recursive-learning`, `parallel-work`, `authoring`) kept — low context cost; revisit if bloat recurs.

## 7. Architectural debt surfaced: dual source of truth (Nix vs deploy.sh)

`pi-setup/nix/pi-workspace.nix` is a Home-Manager module that inlines `AGENTS.md` + 8 skills + prompts as `home.file."...".text`. This is a **parallel source** to the `pi-setup/skills/` files deployed by `deploy.sh` (symlinks).

- **Currently dormant:** live agents are managed by `deploy.sh` symlinks (skills) + a real `AGENTS.md` file; the HM module is not applied (paths are writable, not nix-store symlinks). So deploy.sh edits are live.
- **Latent regression risk:** if the HM module is later enabled (per `README-INSTALL.md`), its inline (now-stale) text would override the deploy.sh symlinks — regressing the fixes here.
- **Recommended unification (needs decision — touches NixOS config):** make `pi-workspace.nix` `source` the `pi-setup/` files via `builtins.readFile`/`fileContents` (single source of truth), or delete the module if `deploy.sh` is the chosen path. Defer to the `nixfiles`/`nixos-best-practices` skills before editing NixOS config.
