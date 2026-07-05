# Rule: Global Behavior

alwaysApply: true

## Context

Personal workspace: `/home/daviaaze/Projects/ai-workspace`.
Shorthand: `$WORKSPACE` expands to this path in prompts, skills, and templates.

At session start, read `memory/learning-log.md` and relevant workspace notes.

## Tone

- Concise, direct. Match the user's language when practical.
- Present options as numbered lists when multiple valid approaches exist.
- No assumptions. Ask when unclear.

## Escalation

- **STOP** — Ask first: prod DB migrations, infra apply, force push, delete branches, modify CI/CD.
- **CONFIRM** — Inform and wait: commit, push non-main, create PR, install deps, destructive local DB ops.
- **GO** — Auto-execute: read files, run tests, lint, format, dev server, stage files.

## Git

- Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`, `perf:`, `security:`.
- No AI co-authorship.
- Verify branch is not `main`/`master` before committing.
- Keep commits single-concern.

## Workspace

- When inside the workspace, use relative paths per the README.
- When outside it, persistent notes/plans/memory go to `$WORKSPACE`.

## Code Exploration — MANDATORY: Use Graph Tools First

You MUST use the code-review-graph tools for ALL code exploration, review, and modification tasks. Never use grep/find/rg as a first resort when a graph tool can do the job.

**Concrete rules:**
1. DO NOT use `grep`, `find`, or `rg` for finding symbols — call **`semantic_search_nodes`** first.
2. DO NOT read entire files for review — call **`get_review_context`** or **`detect_changes`** first.
3. DO NOT use `find`/`rg` for dependency tracing — call **`query_graph`** (`callers_of`, `callees_of`, `imports_of`).
4. Before ANY modification — call **`get_impact_radius`** first to assess blast radius.
5. When entering a new codebase — call **`build_or_update_graph`** if no graph exists.

**Violations that waste tokens:**
- `grep -rn 'functionName' .` → should be `semantic_search_nodes "functionName"` or `query_graph callers_of "functionName"`
- `cat src/component.tsx | head -100` → should be `get_review_context` or `get_impact_radius`
- `find . -name '*.ts' | xargs grep` → should be `semantic_search_nodes`

> Skills-First Workflow lives once in `AGENTS.md` to avoid duplicating always-on context.