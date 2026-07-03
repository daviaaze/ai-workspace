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

> Core Imperatives, Code Review Graph workflow, and Skills-First Workflow live once in `AGENTS.md` to avoid duplicating always-on context.