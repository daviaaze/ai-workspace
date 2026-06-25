# Workspace System Upgrade — Design

**Date:** 2026-06-09
**Status:** Approved design, pending implementation
**Scope:** System upgrade (cleanup + pi-setup transformation + automation + polish)

---

## Overview

Transform the ai-workspace from a functional-but-messy state into a clean, self-documenting,
homelab-deployable personal knowledge base. Five phases, surgical changes only.

---

## Phase 1: Cleanup

Surgical fixes — no-brainer items that clear the clutter.

| Action | Detail | Why |
|--------|--------|-----|
| Remove `References/` (uppercase) | Empty directory, all content in `references/` (lowercase) | Dead duplicate, confusing |
| Fix README title | "AI Workspace — Personal" → "AI Workspace — Personal Knowledge Base" | Truncated on first line |
| Fix `.gitignore` | Add `Knowledge-Base/.docs-index/` (extension cache); add `!.gitkeep` pattern; make inbox handling consistent | `.docs-index/` is an implementation detail that shouldn't be committed |
| Remove `pi-setup/skills/stack-ref/` | Empty stale directory | Dead artifact |
| Add `.gitkeep` to empty dirs | `docs/`, `Follow-ups-and-Blockers/`, `Prompts/`, `Research/`, `Runbooks/`, `Technical-Decisions/`, `Development/Features/Done/` | Preserve folder structure in git |
| Move `Code-Reviews/` → `analysis/` | `analysis/shade-shell/` with all 7 review docs | Better categorization alongside existing analysis files |
| Rename existing `analysis/` refs | README table references `analysis/` correctly — no change needed | Just verify |

---

## Phase 2: pi-setup → Homelab-Ready Source of Truth

Restructure `pi-setup/` into a clean, modular, deployable registry that can be used
in a homelab NixOS setup or standalone.

### Target Structure

```
pi-setup/
├── README.md                 # How to deploy (symlink or nix)
├── deploy.sh                 # Symlinks skills/ → ~/.pi/agent/skills/
│                             # and rules/  → ~/.pi/agent/rules/
├── nix/
│   └── pi-workspace.nix      # Nix module (exists, stays)
├── rules/                    # AGENTS.md? No — these are the raw rule files
│   ├── 00-global.md          # (exists, unchanged)
│   ├── 01-code.md            # (exists, unchanged)
│   └── 02-infra.md           # (exists, unchanged)
├── skills/
│   ├── SKILL_CATALOG.md      # Master list extracted from conventions.md
│   ├── commit/
│   │   └── SKILL.md
│   ├── create-pr/
│   │   └── SKILL.md
│   ├── debug/
│   │   └── SKILL.md
│   ├── desloppify/
│   │   └── SKILL.md
│   ├── feature-dev/
│   │   └── SKILL.md
│   ├── learn/
│   │   └── SKILL.md
│   ├── onboard/
│   │   └── SKILL.md
│   └── pre-review/
│       └── SKILL.md
├── scripts/                  # Placeholder for future deploy helpers
└── templates/                # Placeholder (workspace templates live in Templates/)
```

### What Changes

**Remove (stale/duplicate):**
- `pi-setup/skills/stack-ref/` — empty directory
- `pi-setup/skills/feature-dev/full.md` — derivative, canonical is `feature-dev/SKILL.md`
- `pi-setup/skills/create-pr/template.md` — derivative
- `pi-setup/skills/debug/techniques.md` — derivative
- `pi-setup/skills/pre-review/dimensions.md` — derivative
- `pi-setup/skills/feature-dev.md` — flat file, replaced by directory version
- `pi-setup/skills/commit.md` — flat file, replaced by directory version
- `pi-setup/skills/create-pr.md` — flat file, replaced by directory version
- `pi-setup/skills/debug.md` — flat file, replaced by directory version
- `pi-setup/skills/desloppify.md` — flat file, replaced by directory version
- `pi-setup/skills/learn.md` — flat file, replaced by directory version
- `pi-setup/skills/onboard.md` — flat file, replaced by directory version
- `pi-setup/skills/pre-review.md` — flat file, replaced by directory version

**Keep:**
- `pi-setup/skills/stack-ref.md` — this is actually a reference doc, keep at root level
- `pi-setup/nix/pi-workspace.nix` — stays
- `pi-setup/rules/*` — stays
- `pi-setup/README-INSTALL.md` — stays (deployment instructions)

**Create:**
- `pi-setup/skills/SKILL_CATALOG.md` — master catalog generated from the skill table in `memory/conventions.md`
- `pi-setup/deploy.sh` — simple script that creates symlinks
- `pi-setup/skills/commit/SKILL.md` — copy from `~/.pi/agent/skills/commit/SKILL.md`
- `pi-setup/skills/create-pr/SKILL.md` — copy from source
- `pi-setup/skills/debug/SKILL.md` — copy from source
- `pi-setup/skills/desloppify/SKILL.md` — copy from source
- `pi-setup/skills/feature-dev/SKILL.md` — copy from source
- `pi-setup/skills/learn/SKILL.md` — copy from source
- `pi-setup/skills/onboard/SKILL.md` — copy from source
- `pi-setup/skills/pre-review/SKILL.md` — copy from source

### deploy.sh Strategy

```bash
#!/usr/bin/env bash
# Symlink pi-setup skills and rules into ~/.pi/agent/
set -euo pipefail

PI_DIR="${PI_DIR:-$HOME/.pi/agent}"

# Symlink skills (backup originals first)
for skill_dir in pi-setup/skills/*/; do
  name=$(basename "$skill_dir")
  if [ -d "$PI_DIR/skills/$name" ]; then
    mv "$PI_DIR/skills/$name" "$PI_DIR/skills/$name.bak"
  fi
  ln -sf "$PWD/$skill_dir" "$PI_DIR/skills/$name"
done

# Symlink rules
for rule in pi-setup/rules/*.md; do
  ln -sf "$PWD/$rule" "$PI_DIR/rules/$(basename "$rule")"
done

echo "Deployed. Restart PI or reload context."
```

---

## Phase 3: Templates & Documentation Pass

### Template Review (7 files)

| File | Change |
|------|--------|
| `Templates/feature-ticket.md` | Standardize frontmatter, add priority labels, status field |
| `Templates/feature-analysis.md` | Already clean, minor consistency tweaks |
| `Templates/feature-plan.md` | Already clean, add rollback strategy section |
| `Templates/adr.md` | Already clean, maybe add `tags:` field |
| `Templates/code-review.md` | Review and verify completeness |
| `Templates/research.md` | Review and verify completeness |
| `Templates/idea.md` | Review and verify completeness |
| `Templates/project.md` | Review and verify completeness |
| New: `Templates/skill.md` | Add template for creating new skills |

### Empty Directory READMEs

| Dir | Action |
|-----|--------|
| `docs/` | Add `.gitkeep` (placeholder for external docs) |
| `Follow-ups-and-Blockers/` | Add `.gitkeep` (placeholder for tracking items) |
| `Prompts/` | Add `.gitkeep` (placeholder for saved prompts) |
| `Research/` | Add `.gitkeep` (placeholder for spikes/POCs) |
| `Runbooks/` | Add `.gitkeep` (placeholder for how-to guides) |
| `Technical-Decisions/` | Add `.gitkeep` (placeholder for ADRs) |
| `Development/Features/Done/` | Add `.gitkeep` (placeholder for shipped features) |
| `Media-Inbox/` | Add `.gitkeep` (consistent with other inbox dirs) |

---

## Phase 4: Git Automation

### Commit Template (`.gitmessage`)

```
# <type>(<scope>): <subject>
# |<---- max 50 chars ---->|
#
# Types: feat, fix, docs, refactor, test, chore, perf, security
# Scopes: memory, workspace, templates, pi-setup, hooks, meta
#
# Body (optional, wrap at 72 chars):
#
# Footer (optional):
# Closes #ISSUE
```

### Pre-commit Hook (`.git-hooks/pre-commit`)

```bash
#!/usr/bin/env bash
# Block commits on main/master
BRANCH=$(git symbolic-ref HEAD 2>/dev/null | sed 's|refs/heads/||')
if [ "$BRANCH" = "main" ] || [ "$BRANCH" = "master" ]; then
  echo "❌ Direct commits to $BRANCH are not allowed."
  echo "   Create a feature branch instead."
  exit 1
fi
```

**Config:**
```bash
git config core.hooksPath .git-hooks/
git config commit.template .gitmessage
```

---

## Phase 5: Commit & Wrap

- Stage all Phase 1-4 changes
- Commit memory file modifications (`docs(memory):`)
- Commit workspace changes (`feat(workspace): system upgrade`)
- Verify homelab deployability of pi-setup/

---

## Sequence

```
Phase 1  →  Phase 2  →  Phase 3  →  Phase 4  →  Phase 5
Cleanup     pi-setup     Templates    Git hooks    Commit
                      + polish       + template
```

Each phase is independent and can be reviewed/rolled back separately.
Phases 1-4 are file operations; Phase 5 is git operations.
