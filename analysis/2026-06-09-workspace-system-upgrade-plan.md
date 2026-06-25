# Workspace System Upgrade — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clean, restructure, and automate the ai-workspace into a homelab-deployable personal knowledge base.

**Architecture:** Five sequential phases — cleanup, pi-setup transformation, template polish, git automation, final commit. Each phase is independent and verifiable.

**Tech Stack:** Bash, Markdown, Git hooks

**Reference:** Design spec at `analysis/2026-06-09-workspace-system-upgrade-design.md`

---

## File Structure

### Files to Delete
- `References/` (entire empty directory)
- `pi-setup/skills/stack-ref/` (empty directory)
- `pi-setup/skills/feature-dev/full.md`
- `pi-setup/skills/create-pr/template.md`
- `pi-setup/skills/debug/techniques.md`
- `pi-setup/skills/pre-review/dimensions.md`
- `pi-setup/skills/feature-dev.md`
- `pi-setup/skills/commit.md`
- `pi-setup/skills/create-pr.md`
- `pi-setup/skills/debug.md`
- `pi-setup/skills/desloppify.md`
- `pi-setup/skills/learn.md`
- `pi-setup/skills/onboard.md`
- `pi-setup/skills/pre-review.md`

### Files to Move
- `Code-Reviews/shade-shell-*.md` → `analysis/shade-shell/`

### Files to Modify
- `README.md` — fix title
- `.gitignore` — add `.docs-index/`, standardize inbox handling, add `.gitkeep` pattern
- `memory/conventions.md` — update skills catalog to reference SKILL_CATALOG.md

### Files to Create
- `.gitkeep` in: `docs/`, `Follow-ups-and-Blockers/`, `Prompts/`, `Research/`, `Runbooks/`, `Technical-Decisions/`, `Development/Features/Done/`, `Media-Inbox/`
- `pi-setup/skills/SKILL_CATALOG.md`
- `pi-setup/deploy.sh`
- `pi-setup/skills/commit/SKILL.md`
- `pi-setup/skills/create-pr/SKILL.md`
- `pi-setup/skills/debug/SKILL.md`
- `pi-setup/skills/desloppify/SKILL.md`
- `pi-setup/skills/feature-dev/SKILL.md`
- `pi-setup/skills/learn/SKILL.md`
- `pi-setup/skills/onboard/SKILL.md`
- `pi-setup/skills/pre-review/SKILL.md`
- `.gitmessage` (commit template)
- `.git-hooks/pre-commit` (branch guard hook)
- `Templates/skill.md`

---

## Tasks

### Task 1: Remove empty `References/` directory (uppercase dupe)

**Files:**
- Delete: `References/` (entire empty directory)

- [ ] **Step 1: Remove the empty directory**

The `References/` directory is empty — `references/` (lowercase) has all the content.

Run:
```bash
rmdir /home/daviaaze/Projects/pessoal/ai-workspace/References
```

Verify:
```bash
ls /home/daviaaze/Projects/pessoal/ai-workspace/References
# Expected: "ls: cannot access '.../References': No such file or directory"
```

---

### Task 2: Fix README title

**Files:**
- Modify: `README.md` — line 1 title

- [ ] **Step 1: Fix the truncated title**

Edit `README.md` line 1:
`# AI Workspace — Personal` → `# AI Workspace — Personal Knowledge Base`

Verify:
```bash
head -1 /home/daviaaze/Projects/pessoal/ai-workspace/README.md
# Expected: "# AI Workspace — Personal Knowledge Base"
```

---

### Task 3: Fix `.gitignore`

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Add `.docs-index/` and standardize inbox patterns**

Edit `.gitignore`:
- Add `Knowledge-Base/.docs-index/` entry
- Change `Media-Inbox/*` to use same README pattern as Processing (or use `.gitkeep` consistently)
- Add global `.gitkeep` exception if missing

Expected changes:
```gitignore
# Docs cache (custom-docs extension)
Knowledge-Base/.docs-index/

# Inbox items (process then commit or ignore)
Media-Inbox/*
Processing/*

# But keep the READMEs in those folders
!Media-Inbox/.gitkeep
!Processing/README.md

# Keep folder structure with .gitkeep for empty dirs
!.gitkeep
```

Since `.gitkeep` is already in the gitignore exception, we just need to:
1. Add `Knowledge-Base/.docs-index/` line
2. Ensure `Media-Inbox/.gitkeep` exception is present

Verify:
```bash
grep -n "docs-index\|gitkeep\|Media-Inbox" /home/daviaaze/Projects/pessoal/ai-workspace/.gitignore
```

---

### Task 4: Remove stale `pi-setup/skills/stack-ref/` directory

**Files:**
- Delete: `pi-setup/skills/stack-ref/` (empty directory)

- [ ] **Step 1: Remove the empty directory**

Run:
```bash
rmdir /home/daviaaze/Projects/pessoal/ai-workspace/pi-setup/skills/stack-ref
```

Verify:
```bash
ls /home/daviaaze/Projects/pessoal/ai-workspace/pi-setup/skills/stack-ref 2>&1
# Expected: "No such file or directory"
```

---

### Task 5: Add `.gitkeep` files to empty directories

**Files:**
- Create: `.gitkeep` in each empty dir

- [ ] **Step 1: Create `.gitkeep` in all 8 empty directories**

Run:
```bash
for dir in docs Follow-ups-and-Blockers Prompts Research Runbooks Technical-Decisions Development/Features/Done Media-Inbox; do
  touch "/home/daviaaze/Projects/pessoal/ai-workspace/$dir/.gitkeep"
done
```

Verify:
```bash
ls -la /home/daviaaze/Projects/pessoal/ai-workspace/docs/.gitkeep /home/daviaaze/Projects/pessoal/ai-workspace/Follow-ups-and-Blockers/.gitkeep
```

---

### Task 6: Move Code-Reviews shade-shell docs into `analysis/`

**Files:**
- Move: `Code-Reviews/shade-shell-*.md` → `analysis/shade-shell/`

- [ ] **Step 1: Create `analysis/shade-shell/` and move files**

Run:
```bash
mkdir -p /home/daviaaze/Projects/pessoal/ai-workspace/analysis/shade-shell
mv /home/daviaaze/Projects/pessoal/ai-workspace/Code-Reviews/shade-shell-*.md /home/daviaaze/Projects/pessoal/ai-workspace/analysis/shade-shell/
```

Verify:
```bash
ls /home/daviaaze/Projects/pessoal/ai-workspace/analysis/shade-shell/
# Expected: 7 shade-shell markdown files
ls /home/daviaaze/Projects/pessoal/ai-workspace/Code-Reviews/
# Expected: empty (or remove the dir if empty)
```

Also remove the `Code-Reviews/` directory if now empty:
```bash
rmdir /home/daviaaze/Projects/pessoal/ai-workspace/Code-Reviews 2>/dev/null || true
```

---

### Task 7: Remove stale/duplicate skill files from `pi-setup/skills/`

**Files:**
- Delete: 13 stale files (flat `.md` files + nested derivatives)

- [ ] **Step 1: Remove all stale flat files**

Run:
```bash
cd /home/daviaaze/Projects/pessoal/ai-workspace/pi-setup/skills

# Remove flat files (being replaced by directory/ SKILL.md versions)
rm -f commit.md create-pr.md debug.md desloppify.md feature-dev.md learn.md onboard.md pre-review.md

# Remove nested derivatives
rm -f feature-dev/full.md create-pr/template.md debug/techniques.md pre-review/dimensions.md

# Remove empty derivative directories if they're now empty
rmdir feature-dev create-pr debug pre-review 2>/dev/null || true

# The stack-ref/ was already removed in Task 4
```

Verify:
```bash
ls /home/daviaaze/Projects/pessoal/ai-workspace/pi-setup/skills/
# Expected: stack-ref.md (only reference doc remains, no flat .md files)
```

---

### Task 8: Create skill directory structure with canonical SKILL.md files

**Files:**
- Create: 8 skill directories with `SKILL.md` copied from `~/.pi/agent/skills/`

- [ ] **Step 1: Create directories and copy SKILL.md files**

Run:
```bash
cd /home/daviaaze/Projects/pessoal/ai-workspace/pi-setup/skills

SKILLS="commit create-pr debug desloppify feature-dev learn onboard pre-review"

for skill in $SKILLS; do
  mkdir -p "$skill"
  cp "$HOME/.pi/agent/skills/$skill/SKILL.md" "$skill/SKILL.md"
done
```

Verify:
```bash
for skill in commit create-pr debug desloppify feature-dev learn onboard pre-review; do
  echo "=== $skill ==="
  head -3 "/home/daviaaze/Projects/pessoal/ai-workspace/pi-setup/skills/$skill/SKILL.md"
done
```

---

### Task 9: Create SKILL_CATALOG.md

**Files:**
- Create: `pi-setup/skills/SKILL_CATALOG.md`

- [ ] **Step 1: Create the master catalog**

Content derived from the skill table in `memory/conventions.md`. Categorize skills with name, description, and trigger keywords.

Write the file:
```markdown
# PI Skill Catalog

> Canonical registry of all PI agent skills. Use this for reference and for deploying to homelab instances.

## Core Development Cycle

| Skill | When to Use |
|---|---|
| brainstorming | Before any creative/feature work — explore intent, requirements, design |
| writing-plans | When you have a spec for a multi-step task, before touching code |
| test-driven-development | Before writing implementation code for any feature or bugfix |
| executing-plans | When you have a written plan to execute with review checkpoints |
| verification-before-completion | Before claiming work is done — run verification commands first |
| finishing-a-development-branch | When implementation is complete and tests pass — merge/PR/cleanup |

## Parallel & Delegation

| Skill | When to Use |
|---|---|
| subagent-driven-development | Executing plans with independent tasks in the current session |
| dispatching-parallel-agents | 2+ independent tasks with no shared state or dependencies |
| pi-subagents | Delegate to builtin/custom subagents with chain/parallel workflows |

## Code Quality & Review

| Skill | When to Use |
|---|---|
| pre-review | Self-review before opening a PR |
| requesting-code-review | After completing tasks, before merging |
| receiving-code-review | Before implementing review feedback |

If this skill is installed, `desloppify` is also available for cleaning AI-generated code artifacts.

## Debugging & Fixing

| Skill | When to Use |
|---|---|
| systematic-debugging | Any bug, test failure, or unexpected behavior |
| debug | Tests failing, bug found, something not working |

## Git & Branching

| Skill | When to Use |
|---|---|
| commit | Safe git commit with conventional commit message |
| create-pr | Create a pull request with description and test table |
| using-git-worktrees | Feature work needing isolation from current workspace |

## Workspace Management

| Skill | When to Use |
|---|---|
| feature-dev | Start and work through a feature end-to-end |
| onboard | New repository — analyze and create project context |
| learn | Persist corrections, conventions, or learnings |
| find-skills | Discover and install agent skills |
| writing-skills | Creating or editing skills |

## Domain-Specific

| Skill | When to Use |
|---|---|
| nixos-best-practices | NixOS flakes, overlays, home-manager, config not applying |
| playwright-best-practices | Writing/debugging/maintaining Playwright tests |

## Utility

| Skill | When to Use |
|---|---|
| librarian | Open-source library research — evidence-backed answers with GitHub permalinks |
| cv-review | Review a CV/resume like a top-tier career adviser and recruiter |
| using-superpowers | Starting any conversation — establishes how to find and use skills |
| desloppify | Clean up AI-generated code artifacts |

> **Homelab deploy:** Run `./pi-setup/deploy.sh` to symlink these skills into `~/.pi/agent/skills/`.
```

Verify:
```bash
wc -l /home/daviaaze/Projects/pessoal/ai-workspace/pi-setup/skills/SKILL_CATALOG.md
```

---

### Task 10: Create `deploy.sh`

**Files:**
- Create: `pi-setup/deploy.sh`

- [ ] **Step 1: Create the deploy script**

As designed in the spec:
```bash
#!/usr/bin/env bash
# Symlink pi-setup skills and rules into ~/.pi/agent/
# Usage: ./pi-setup/deploy.sh [--dry-run]
set -euo pipefail

PI_DIR="${PI_DIR:-$HOME/.pi/agent}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DRY_RUN=false

if [ "${1:-}" = "--dry-run" ]; then
  DRY_RUN=true
fi

echo "==> Deploying pi-setup to $PI_DIR"

# Symlink skills (backup originals)
for skill_dir in "$SCRIPT_DIR/skills"/*/; do
  name=$(basename "$skill_dir")
  target="$PI_DIR/skills/$name"

  if [ -d "$target" ] && [ ! -L "$target" ]; then
    echo "  Backing up $target → $target.bak"
    $DRY_RUN || mv "$target" "$target.bak"
  fi

  if [ -L "$target" ]; then
    echo "  Updating symlink: $name"
  else
    echo "  Creating symlink: $name → $skill_dir"
  fi
  $DRY_RUN || ln -sfn "$skill_dir" "$target"
done

# Symlink rules
mkdir -p "$PI_DIR/rules"
for rule in "$SCRIPT_DIR/rules"/*.md; do
  name=$(basename "$rule")
  echo "  Linking rule: $name"
  $DRY_RUN || ln -sf "$rule" "$PI_DIR/rules/$name"
done

echo "==> Done. Restart PI or reload context to pick up changes."
echo ""
echo "    To roll back: move .bak directories back to original names"
```

Make executable:
```bash
chmod +x /home/daviaaze/Projects/pessoal/ai-workspace/pi-setup/deploy.sh
```

Verify:
```bash
bash /home/daviaaze/Projects/pessoal/ai-workspace/pi-setup/deploy.sh --dry-run
# Expected: lists what would be linked, no actual changes
```

---

### Task 11: Update memory/conventions.md skills catalog reference

**Files:**
- Modify: `memory/conventions.md` — skills catalog section

- [ ] **Step 1: Update the skills table to reference SKILL_CATALOG.md**

In `memory/conventions.md`, replace the large inline skill table with a concise reference:

```markdown
## Skills-First Workflow

> Full skill catalog at `pi-setup/skills/SKILL_CATALOG.md` — 28+ skills categorized by workflow phase.

Before any action, check available skills for a relevant one. If a skill matches, follow it exactly.
If no skill matches, improvise but inform the user and ask if a new skill should be created.
```

This removes the massive duplication between `memory/conventions.md` and the new `SKILL_CATALOG.md`.

---

### Task 12: Review and update Templates

**Files:**
- Modify: `Templates/feature-ticket.md`, `Templates/feature-plan.md`
- Create: `Templates/skill.md`
- Verify others: `Templates/adr.md`, `Templates/code-review.md`, `Templates/research.md`, `Templates/idea.md`, `Templates/project.md`, `Templates/feature-analysis.md`

- [ ] **Step 1: Standardize `feature-ticket.md` frontmatter**

Add status, priority labels, and tags field.

- [ ] **Step 2: Add rollback strategy section to `feature-plan.md`**

Add a `## Rollback` section between Risks and Testing.

- [ ] **Step 3: Create `Templates/skill.md`**

A template for writing new PI skills:

```markdown
# {{skill-name}} — {{one-line-description}}

## When to Use

{{trigger phrases and scenarios}}

## Workflow

{{step-by-step process}}

## Key Decisions

{{design choices, trade-offs, assumptions}}

## Verification

{{how to confirm it worked}}
```

- [ ] **Step 4: Quick-verify remaining templates**

Read each remaining template, check for stale placeholders, ensure consistent formatting.

---

### Task 13: Create git commit template (`.gitmessage`)

**Files:**
- Create: `.gitmessage` in workspace root

- [ ] **Step 1: Create the commit template**

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
#   Closes #ISSUE
```

---

### Task 14: Create pre-commit hook (`.git-hooks/pre-commit`)

**Files:**
- Create: `.git-hooks/pre-commit`

- [ ] **Step 1: Create the hooks directory and pre-commit script**

```bash
#!/usr/bin/env bash
# Block commits on main/master branch
BRANCH=$(git symbolic-ref HEAD 2>/dev/null | sed 's|refs/heads/||')
if [ "$BRANCH" = "main" ] || [ "$BRANCH" = "master" ]; then
  echo "❌ Direct commits to $BRANCH are not allowed."
  echo "   Create a feature branch instead."
  exit 1
fi
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x /home/daviaaze/Projects/pessoal/ai-workspace/.git-hooks/pre-commit
```

- [ ] **Step 3: Configure git to use the hooks and template**

```bash
git -C /home/daviaaze/Projects/pessoal/ai-workspace config core.hooksPath .git-hooks/
git -C /home/daviaaze/Projects/pessoal/ai-workspace config commit.template .gitmessage
```

Verify:
```bash
git -C /home/daviaaze/Projects/pessoal/ai-workspace config --local core.hooksPath
# Expected: .git-hooks/
git -C /home/daviaaze/Projects/pessoal/ai-workspace config --local commit.template
# Expected: .gitmessage
```

---

### Task 15: Commit memory changes

**Files:**
- Stage: `memory/conventions.md`, `memory/project-patterns.md`, `memory/learning-log.md`

- [ ] **Step 1: Stage and commit memory file modifications**

```bash
git -C /home/daviaaze/Projects/pessoal/ai-workspace add memory/conventions.md memory/project-patterns.md memory/learning-log.md
git -C /home/daviaaze/Projects/pessoal/ai-workspace commit -m "docs(memory): update conventions, patterns, and learning log"
```

---

### Task 16: Commit all workspace upgrade changes

**Files:**
- Stage: all files created/modified in Tasks 1-14

- [ ] **Step 1: Verify you're not on main/master**

```bash
BRANCH=$(git -C /home/daviaaze/Projects/pessoal/ai-workspace rev-parse --abbrev-ref HEAD)
echo "$BRANCH"
# If this is "main" or "master", create a feature branch first
```

- [ ] **Step 2: Stage all changes**

```bash
git -C /home/daviaaze/Projects/pessoal/ai-workspace add -A
```

- [ ] **Step 3: Review what's being committed**

```bash
git -C /home/daviaaze/Projects/pessoal/ai-workspace status
```

- [ ] **Step 4: Commit**

```bash
git -C /home/daviaaze/Projects/pessoal/ai-workspace commit -m "feat(workspace): system upgrade - cleanup, pi-setup restructure, templates, git automation

- Remove duplicate References/ directory
- Fix .gitignore (docs-index, inbox consistency)
- Move Code-Reviews into analysis/
- Restructure pi-setup/ as modular source-of-truth
- Create SKILL_CATALOG.md and deploy.sh
- Add .gitkeep files to preserve empty dir structure
- Add git commit template and pre-commit hook
- Update templates and memory references"
```

---

### Task 17: Final verification

- [ ] **Step 1: Verify workspace structure**

```bash
find /home/daviaaze/Projects/pessoal/ai-workspace -maxdepth 2 -type d | sort
```

- [ ] **Step 2: Verify git status is clean**

```bash
git -C /home/daviaaze/Projects/pessoal/ai-workspace status
# Expected: "nothing to commit, working tree clean"
```

- [ ] **Step 3: Verify deploy.sh works (dry-run)**

```bash
bash /home/daviaaze/Projects/pessoal/ai-workspace/pi-setup/deploy.sh --dry-run
```
