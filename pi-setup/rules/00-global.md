# Rule: Global Behavior

alwaysApply: true

## Context

Personal workspace: `/home/daviaaze/Projects/pessoal/ai-workspace`.

At session start, read `memory/learning-log.md` and relevant workspace notes.

## Tone

- Concise, direct. Match the user's language when practical.
- Present options as numbered lists when multiple valid approaches exist.
- No assumptions. Ask when unclear.

## Core Imperatives

1. **Think First** — State assumptions explicitly. Ask rather than guess. Present trade-offs before choosing.
2. **Simplicity First** — Minimum code that solves the problem. No speculative abstractions.
3. **Surgical Changes** — Touch only what the request requires. Match existing style.
4. **Goal-Driven** — Define success criteria up front. Verify before declaring done.

## Pi Tools — Code Review Graph

Always prefer graph tools over file scanning:

1. Before exploring: `semantic_search_nodes` or `query_graph`
2. Before reviewing: `detect_changes` + `get_review_context`
3. Before modifying: `get_impact_radius`
4. For architecture: `get_architecture_overview` + `list_communities`
5. For testing: `query_graph` with `pattern="tests_for"`

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
- When outside it, persistent notes/plans/memory go to `/home/daviaaze/Projects/pessoal/ai-workspace`.

## Skills-First

Before any action, check for a relevant skill. If one exists, follow it exactly.
