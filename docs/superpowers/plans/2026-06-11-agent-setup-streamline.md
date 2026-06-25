# Agent Setup Streamline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce the pi agent setup from 29 scattered skills + 1,184 lines of unused agent config to ~22 consolidated skills in a single directory with a proper catalog.

**Architecture:** Delete dead weight (SDD agents/chains, duplicate find-skills, empty workspace dirs), demote cv-review to reference doc, merge 10 overlapping skills into 4 unified workflows, move all user-authored skills into `.pi/agent/skills/` as single source of truth, rebuild catalog.

**Tech Stack:** Bash (mv, rm), Markdown editing, git

---

### Task 1: Delete SDD agents and chains (dead weight)

**Files:**
- Delete: `~/.pi/agent/agents/sdd-init.md`
- Delete: `~/.pi/agent/agents/sdd-explore.md`
- Delete: `~/.pi/agent/agents/sdd-proposal.md`
- Delete: `~/.pi/agent/agents/sdd-design.md`
- Delete: `~/.pi/agent/agents/sdd-spec.md`
- Delete: `~/.pi/agent/agents/sdd-tasks.md`
- Delete: `~/.pi/agent/agents/sdd-apply.md`
- Delete: `~/.pi/agent/agents/sdd-verify.md`
- Delete: `~/.pi/agent/agents/sdd-status.md`
- Delete: `~/.pi/agent/agents/sdd-sync.md`
- Delete: `~/.pi/agent/agents/sdd-archive.md`
- Delete: `~/.pi/agent/agents/sdd-onboard.md`
- Delete: `~/.pi/agent/chains/sdd-full.chain.md`
- Delete: `~/.pi/agent/chains/sdd-plan.chain.md`
- Delete: `~/.pi/agent/chains/sdd-verify.chain.md`

- [ ] **Remove all 12 agent files and 3 chain files**

  ```bash
  rm ~/.pi/agent/agents/sdd-*.md
  rm ~/.pi/agent/chains/sdd-*.chain.md
  ```

  Expected: `ls ~/.pi/agent/agents/` is empty; `ls ~/.pi/agent/chains/` is empty

- [ ] **Commit**

  ```bash
  cd /home/daviaaze/Projects/pessoal/ai-workspace
  git add -A && git commit -m "chore(agent): remove unused SDD agents and chains (1,184 lines, zero usage)"
  ```

  Expected: clean commit

---

### Task 2: Remove duplicate find-skills and demote cv-review to reference

**Files:**
- Delete: `~/.pi/agent/skills/find-skills/SKILL.md`
- Create: `/home/daviaaze/Projects/pessoal/ai-workspace/References/cv-review.md`
- Delete: `~/.pi/agent/skills/cv-review/SKILL.md`

- [ ] **Remove duplicate find-skills from `.pi/agent/skills/`**

  ```bash
  rm ~/.pi/agent/skills/find-skills/SKILL.md
  rmdir ~/.pi/agent/skills/find-skills
  ```

  Expected: directory gone. The pi-managed copy remains at `.agents/skills/find-skills/SKILL.md`

- [ ] **Move cv-review content to workspace References and delete skill**

  ```bash
  cp ~/.pi/agent/skills/cv-review/SKILL.md /home/daviaaze/Projects/pessoal/ai-workspace/References/cv-review.md
  rm ~/.pi/agent/skills/cv-review/SKILL.md
  rmdir ~/.pi/agent/skills/cv-review
  ```

  Expected: content lives in `References/cv-review.md`, skill directory removed

- [ ] **Commit**

  ```bash
  cd /home/daviaaze/Projects/pessoal/ai-workspace
  git add -A && git commit -m "chore(skills): remove duplicate find-skills, demote cv-review to reference"
  ```

---

### Task 3: Move standalone user-authored skills from `.agents/skills/` to `.pi/agent/skills/`

**Files (5 skills to move as-is, no merging needed):**
- Move: `~/.agents/skills/brainstorming/` → `~/.pi/agent/skills/brainstorming/`
- Move: `~/.agents/skills/systematic-debugging/` → `~/.pi/agent/skills/systematic-debugging/`
- Move: `~/.agents/skills/test-driven-development/` → `~/.pi/agent/skills/test-driven-development/`
- Move: `~/.agents/skills/using-git-worktrees/` → `~/.pi/agent/skills/using-git-worktrees/`
- Move: `~/.agents/skills/using-superpowers/` → `~/.pi/agent/skills/using-superpowers/`

- [ ] **Move 5 standalone skill directories**

  ```bash
  for skill in brainstorming systematic-debugging test-driven-development using-git-worktrees using-superpowers; do
    mv ~/.agents/skills/$skill ~/.pi/agent/skills/$skill
  done
  ```

  Verify:
  ```bash
  ls ~/.pi/agent/skills/ | sort
  ```

  Expected: each skill directory now exists under `.pi/agent/skills/` and no longer under `.agents/skills/`

- [ ] **Commit**

  ```bash
  cd /home/daviaaze/Projects/pessoal/ai-workspace
  git add -A && git commit -m "feat(skills): move standalone user-authored skills to .pi/agent/skills/"
  ```

---

### Task 4: Move merge-target skills from `.agents/skills/` to `.pi/agent/skills/`

**Files (10 skills to move that will later be merged):**
- Move: `~/.agents/skills/pre-review/` → `~/.pi/agent/skills/pre-review/`
- Move: `~/.agents/skills/requesting-code-review/` → `~/.pi/agent/skills/requesting-code-review/`
- Move: `~/.agents/skills/receiving-code-review/` → `~/.pi/agent/skills/receiving-code-review/`
- Move: `~/.agents/skills/writing-plans/` → `~/.pi/agent/skills/writing-plans/`
- Move: `~/.agents/skills/writing-skills/` → `~/.pi/agent/skills/writing-skills/`
- Move: `~/.agents/skills/executing-plans/` → `~/.pi/agent/skills/executing-plans/`
- Move: `~/.agents/skills/verification-before-completion/` → `~/.pi/agent/skills/verification-before-completion/`
- Move: `~/.agents/skills/finishing-a-development-branch/` → `~/.pi/agent/skills/finishing-a-development-branch/`
- Move: `~/.agents/skills/dispatching-parallel-agents/` → `~/.pi/agent/skills/dispatching-parallel-agents/`
- Move: `~/.agents/skills/subagent-driven-development/` → `~/.pi/agent/skills/subagent-driven-development/`

- [ ] **Move 10 merge-target skill directories**

  ```bash
  for skill in pre-review requesting-code-review receiving-code-review writing-plans writing-skills executing-plans verification-before-completion finishing-a-development-branch dispatching-parallel-agents subagent-driven-development; do
    mv ~/.agents/skills/$skill ~/.pi/agent/skills/$skill
  done
  ```

  Verify source dir is clean:
  ```bash
  ls ~/.agents/skills/ | sort
  ```

  Expected: only 3 pi-managed skills remain (find-skills, nixos-best-practices, playwright-best-practices)

- [ ] **Commit**

  ```bash
  cd /home/daviaaze/Projects/pessoal/ai-workspace
  git add -A && git commit -m "feat(skills): move merge-target skills to .pi/agent/skills/"
  ```

---

### Task 5: Create merged `code-review` skill

**Files:**
- Create: `~/.pi/agent/skills/code-review/SKILL.md`
- Delete: `~/.pi/agent/skills/pre-review/SKILL.md`
- Delete: `~/.pi/agent/skills/requesting-code-review/SKILL.md`
- Delete: `~/.pi/agent/skills/receiving-code-review/SKILL.md`

**Merged SKILL.md:**

```markdown
---
name: code-review
description: Self-review before PR, request reviews from peers, and receive review feedback with technical rigor. Covers the full review lifecycle.
---

# Code Review Workflow

Covers three phases: pre-review (self-review before opening), requesting (asking peers to review), and receiving (responding to feedback with verification).

## Phase 1: Pre-Review (Self-Review Before PR)

Run this before opening a PR. Check:
- Diff is minimal — touches only what the task requires
- No commented-out code, debug logs, TODO/FIXME markers
- Tests pass and cover the changes
- Error paths are handled, not just happy paths
- Naming is consistent with codebase conventions

## Phase 2: Requesting Review

When your work is done and tests pass, request peer review:
- Summarize what changed and why
- Highlight areas you're uncertain about
- Include test results in the description

## Phase 3: Receiving Review Feedback

When you receive review comments:
1. **Understand first** — read each comment. Ask clarifying questions.
2. **Verify technically** — check if the suggestion is actually correct. Test it.
3. **Do not blindly implement** — feedback can be wrong or miss context.
4. **Respond** — agree with reasoning or explain why an alternative is better.
5. **Apply and re-verify** — run tests after each change.
```

- [ ] **Create `code-review/SKILL.md` with merged content**

  ```bash
  mkdir -p ~/.pi/agent/skills/code-review
  ```

  Then write the content above to `~/.pi/agent/skills/code-review/SKILL.md`

- [ ] **Remove the 3 old source skill directories**

  ```bash
  rm -rf ~/.pi/agent/skills/pre-review
  rm -rf ~/.pi/agent/skills/requesting-code-review
  rm -rf ~/.pi/agent/skills/receiving-code-review
  ```

- [ ] **Commit**

  ```bash
  cd /home/daviaaze/Projects/pessoal/ai-workspace
  git add -A && git commit -m "feat(skills): merge pre-review/requesting/receiving into unified code-review skill"
  ```

---

### Task 6: Create merged `authoring` skill

**Files:**
- Create: `~/.pi/agent/skills/authoring/SKILL.md`
- Delete: `~/.pi/agent/skills/writing-plans/SKILL.md`
- Delete: `~/.pi/agent/skills/writing-skills/SKILL.md`

**Merged SKILL.md:**

```markdown
---
name: authoring
description: Write structured documents — implementation plans or skill definitions. Ensures clarity, completeness, and consistency before producing content.
---

# Authoring Workflow

Covers writing implementation plans (from a spec) and writing skill definitions. Both follow the same methodology: understand scope, decompose, write with concrete detail, self-review.

## Mode 1: Writing Implementation Plans

When you have a spec for a multi-step task:
1. **Scope check** — verify the spec is focused enough for one plan
2. **Map file structure** — every file to create/modify with its responsibility
3. **Write bite-sized tasks** — each step is 2-5 minutes with exact code and commands
4. **Self-review** — check spec coverage, placeholder scan, type consistency
5. **Offer execution** — subagent-driven or inline

**Save to:** `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`

## Mode 2: Writing Skills

When creating or editing a skill:
1. **Analyze the gap** — what's missing, overlapping, or broken in existing skills
2. **Design the skill** — single responsibility, clear trigger/description, actionable workflow
3. **Include references** — link to related skills, docs, examples
4. **Verify** — test that pi discovers and routes to the new skill correctly
```

- [ ] **Create `authoring/SKILL.md` and remove old source dirs**

  ```bash
  mkdir -p ~/.pi/agent/skills/authoring
  # write content
  rm -rf ~/.pi/agent/skills/writing-plans
  rm -rf ~/.pi/agent/skills/writing-skills
  ```

- [ ] **Commit**

  ```bash
  cd /home/daviaaze/Projects/pessoal/ai-workspace
  git add -A && git commit -m "feat(skills): merge writing-plans/writing-skills into unified authoring skill"
  ```

---

### Task 7: Create merged `delivery` skill

**Files:**
- Create: `~/.pi/agent/skills/delivery/SKILL.md`
- Delete: `~/.pi/agent/skills/executing-plans/`
- Delete: `~/.pi/agent/skills/verification-before-completion/`
- Delete: `~/.pi/agent/skills/finishing-a-development-branch/`

**Merged SKILL.md:**

```markdown
---
name: delivery
description: Execute implementation plans with review checkpoints, verify before claiming completion, and finish development branches with merge/PR/cleanup. End-to-end delivery pipeline.
---

# Delivery Pipeline

Three sequential phases: execute a plan, verify it works, then finish the branch.

## Phase 1: Execute Plan

When you have a written implementation plan:
1. Work through tasks in order
2. After each task, run tests and verify
3. At checkpoints, run broader verification
4. If something breaks, stop and fix before continuing

## Phase 2: Verify Before Completion

Before claiming any work is done:
1. Run all tests — `npm test`, `pytest`, `cargo test`, etc.
2. Run linter — format check, type check
3. Verify the original failing scenario now passes
4. Confirm no debug logs, no TODO markers, no commented code

## Phase 3: Finish Branch

When implementation is complete and all tests pass:
1. Present options: merge (squash/fast-forward), create PR, or cleanup
2. If merging: verify branch is up-to-date with target
3. If PR: write description, link to ticket, include test results table
4. If cleanup: delete branch locally and remotely
```

- [ ] **Create `delivery/SKILL.md` and remove old source dirs**

  ```bash
  mkdir -p ~/.pi/agent/skills/delivery
  # write content
  rm -rf ~/.pi/agent/skills/executing-plans
  rm -rf ~/.pi/agent/skills/verification-before-completion
  rm -rf ~/.pi/agent/skills/finishing-a-development-branch
  ```

- [ ] **Commit**

  ```bash
  cd /home/daviaaze/Projects/pessoal/ai-workspace
  git add -A && git commit -m "feat(skills): merge executing-plans/verification/finishing into unified delivery skill"
  ```

---

### Task 8: Create merged `parallel-work` skill

**Files:**
- Create: `~/.pi/agent/skills/parallel-work/SKILL.md`
- Delete: `~/.pi/agent/skills/dispatching-parallel-agents/`
- Delete: `~/.pi/agent/skills/subagent-driven-development/`

**Merged SKILL.md:**

```markdown
---
name: parallel-work
description: Execute independent tasks concurrently using subagents or parallel dispatch. Use when facing 2+ independent tasks or executing plans with review checkpoints.
---

# Parallel Work

Two patterns for concurrent work, depending on isolation needs:

## Pattern 1: Subagent-Driven (in-session)

Use when tasks benefit from shared session context but are independent:
1. Write the implementation plan with clear task boundaries
2. Dispatch a fresh subagent per task
3. Each subagent runs independently with its own task description
4. After all complete, run a consolidated review

## Pattern 2: Parallel Dispatch (worktrees)

Use when tasks need full filesystem isolation:
1. Create isolated git worktrees per task
2. Each worktree gets its own copy of the codebase
3. Tasks run concurrently via parallel dispatch
4. Changes are merged back sequentially after review
```

- [ ] **Create `parallel-work/SKILL.md` and remove old source dirs**

  ```bash
  mkdir -p ~/.pi/agent/skills/parallel-work
  # write content
  rm -rf ~/.pi/agent/skills/dispatching-parallel-agents
  rm -rf ~/.pi/agent/skills/subagent-driven-development
  ```

- [ ] **Commit**

  ```bash
  cd /home/daviaaze/Projects/pessoal/ai-workspace
  git add -A && git commit -m "feat(skills): merge dispatching/subagent-driven into unified parallel-work skill"
  ```

---

### Task 9: Clean up empty agent directories and remove old skill references

- [ ] **Remove empty agents and chains dirs**

  ```bash
  rmdir ~/.pi/agent/agents
  rmdir ~/.pi/agent/chains
  ```

  Expected: both dirs removed (they're now empty)

- [ ] **Verify skills directory is clean**

  ```bash
  ls ~/.pi/agent/skills/ | sort
  ```

  Expected only these skills:
  - authoring
  - brainstorming
  - code-review
  - commit
  - create-pr
  - debug
  - deep-research
  - delivery
  - desloppify
  - feature-dev
  - learn
  - nixfiles
  - onboard
  - parallel-work
  - recursive-learning
  - systematic-debugging
  - test-driven-development
  - using-git-worktrees
  - using-superpowers

- [ ] **Commit**

  ```bash
  cd /home/daviaaze/Projects/pessoal/ai-workspace
  git add -A && git commit -m "chore(agent): remove empty agents/chains dirs, finalize skill consolidation"
  ```

---

### Task 10: Rebuild SKILL_CATALOG.md and write USAGE.md

**Files:**
- Modify: `~/.pi/agent/skills/SKILL_CATALOG.md` (currently at `pi-setup/skills/`)
- Create: `~/.pi/USAGE.md`

Note: The `SKILL_CATALOG.md` currently lives at `/home/daviaaze/Projects/pessoal/ai-workspace/pi-setup/skills/SKILL_CATALOG.md`. Rebuild it in-place. The new `USAGE.md` goes at the workspace root.

- [ ] **Rebuild SKILL_CATALOG.md with new categories**

  Write to `/home/daviaaze/Projects/pessoal/ai-workspace/pi-setup/skills/SKILL_CATALOG.md`:

  ```markdown
  # PI Skill Catalog

  ## Core Workflow
  | Skill | When to Use |
  |---|---|
  | `brainstorming` | Before any creative/feature work |
  | `authoring` | Writing plans or skill definitions |
  | `delivery` | Execute, verify, and finish implementation work |
  | `feature-dev` | End-to-end feature development |
  | `parallel-work` | 2+ independent concurrent tasks |

  ## Code Quality
  | Skill | When to Use |
  |---|---|
  | `code-review` | Self-review, request review, or respond to feedback |
  | `desloppify` | Clean up AI-generated code artifacts |
  | `debug` | Hypothesis-driven debugging |
  | `systematic-debugging` | Root-cause tracing for hard bugs |

  ## Testing
  | Skill | When to Use |
  |---|---|
  | `test-driven-development` | Write tests before implementation |
  | `playwright-best-practices` | E2E testing with Playwright |

  ## Project Lifecycle
  | Skill | When to Use |
  |---|---|
  | `onboard` | Analyze a new repository |
  | `commit` | Create a conventional commit |
  | `create-pr` | Create a pull request |

  ## Research & Learning
  | Skill | When to Use |
  |---|---|
  | `deep-research` | Multi-hop web research |
  | `learn` | Persist corrections and conventions |
  | `recursive-learning` | Mine patterns from session history |

  ## System
  | Skill | When to Use |
  |---|---|
  | `nixfiles` | Manage NixOS configuration |
  | `nixos-best-practices` | NixOS conventions and troubleshooting |
  | `using-git-worktrees` | Isolate work in separate directories |
  | `using-superpowers` | Discover and load skills |
  ```

- [ ] **Write USAGE.md**

  Write to `/home/daviaaze/Projects/pessoal/ai-workspace/USAGE.md` with:
  - What this agent setup is
  - How skills work (trigger-based routing from descriptions)
  - Where skills live (`~/.pi/agent/skills/`)
  - How pi-installed skills work (`~/.agents/skills/` — managed by pi)
  - Quick reference: most-used skills
  - How to maintain (keep it lean, don't add skills that overlap)

- [ ] **Commit**

  ```bash
  cd /home/daviaaze/Projects/pessoal/ai-workspace
  git add -A && git commit -m "docs: rebuild SKILL_CATALOG.md and add USAGE.md with mental model"
  ```

---

### Task 11: Clean up empty workspace directories

**Files:**
- Delete: `/home/daviaaze/Projects/pessoal/ai-workspace/Follow-ups-and-Blockers/`
- Delete: `/home/daviaaze/Projects/pessoal/ai-workspace/Processing/`
- Delete: `/home/daviaaze/Projects/pessoal/ai-workspace/Ideas-and-Backlog/`
- Delete: `/home/daviaaze/Projects/pessoal/ai-workspace/Development/Features/In-Progress/`
- Delete: `/home/daviaaze/Projects/pessoal/ai-workspace/Development/Features/Done/`

- [ ] **Remove empty placeholder directories**

  ```bash
  rm -r /home/daviaaze/Projects/pessoal/ai-workspace/Follow-ups-and-Blockers
  rm -r /home/daviaaze/Projects/pessoal/ai-workspace/Processing
  rm -r /home/daviaaze/Projects/pessoal/ai-workspace/Ideas-and-Backlog
  rm -r /home/daviaaze/Projects/pessoal/ai-workspace/Development/Features/In-Progress
  rm -r /home/daviaaze/Projects/pessoal/ai-workspace/Development/Features/Done
  ```

- [ ] **Commit**

  ```bash
  cd /home/daviaaze/Projects/pessoal/ai-workspace
  git add -A && git commit -m "chore(workspace): remove empty placeholder directories"
  ```

---

### Task 12: Final verification

- [ ] **Verify skill count**

  ```bash
  echo "Skills in .pi/agent/skills/: $(ls ~/.pi/agent/skills/ | wc -l)"
  echo "Skills in .agents/skills/: $(ls ~/.agents/skills/ | wc -l)"
  echo "Pi-managed: $(ls ~/.agents/skills/find-skills ~/.agents/skills/nixos-best-practices ~/.agents/skills/playwright-best-practices 2>&1 | grep -c SKILL.md)/3 expected"
  ```

  Expected: ~19 skills in `.pi/agent/skills/`, 3 pi-managed in `.agents/skills/`

- [ ] **Verify no empty dirs or dead config remain**

  ```bash
  test ! -d ~/.pi/agent/agents && echo "agents dir removed: OK"
  test ! -d ~/.pi/agent/chains && echo "chains dir removed: OK"
  test ! -d ~/.pi/agent/skills/find-skills && echo "duplicate find-skills removed: OK"
  test ! -d ~/.pi/agent/skills/cv-review && echo "cv-review dir removed: OK"
  test -f ~/.pi/agent/skills/code-review/SKILL.md && echo "code-review merged: OK"
  test -f ~/.pi/agent/skills/authoring/SKILL.md && echo "authoring merged: OK"
  test -f ~/.pi/agent/skills/delivery/SKILL.md && echo "delivery merged: OK"
  test -f ~/.pi/agent/skills/parallel-work/SKILL.md && echo "parallel-work merged: OK"
  ```

- [ ] **Final summary commit**

  ```bash
  cd /home/daviaaze/Projects/pessoal/ai-workspace
  git add -A && git status
  # review, then:
  git commit -m "chore(workspace): final cleanup after agent setup streamline"
  ```
