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
- **Savepoints** are automatic per-turn (git-checkpoint) — use those for rollback, never auto-commit.
- **Commit contextually:** when a logical unit of work is complete, offer to commit meaningful changes. Close the session cleanly.

## Workspace

- When inside the workspace, use relative paths per the README.
- When outside it, persistent notes/plans/memory go to `$WORKSPACE`.

## Code Exploration

Use the code-review-graph tools when available (see crg-trim extension for details). Prefer graph tools over raw grep/find for symbol search, dependency tracing, and impact analysis.

> Skills-First Workflow lives once in `AGENTS.md` to avoid duplicating always-on context.

## Communication & Reporting

### Lead with summaries, not file-by-file breakdowns
When reporting progress on complex changes (migrations, test fixes, refactors), start with a high-level summary grouped by patterns. Offer details only after the developer asks.

### Narrate multi-file edits
Before editing, state which file(s), what you're changing, and why. After each batch, summarize what was done and the current state. Don't disappear into silent edits.

### Minimal communication on urgency
When the developer says "faster", "just do it", or "do everything", skip verbose planning. Execute in batch, report a consolidated summary after completion.

## Approach & Process

### Batch repetitive file edits
When fixing a recurring pattern across 2+ files, use a batch tool (sed, codemod, multi-file replace) instead of editing one-by-one. Confirm with the developer if there's risk of unintended matches.

### Analyze all failures before fixing tests
When test suites are failing, first analyze ALL failures to identify common patterns. Apply batch fixes. Don't fix one file at a time — it causes regressions. Verify earlier fixes stay intact.

### Syntax-check after every edit
After modifying any JS/TS file, run `node --check <file>` or the project's linter before declaring the change complete. For bulk edits, validate each file immediately.

### Long command output — use the temp file, never head/tail
Bash output is truncated at 50KB. When truncated, **the tool saves the full output to a temp file automatically** — the file path is shown in the truncation notice. Read that temp file with `read` + `offset`/`limit` instead of rerunning.

If you need explicit control over where output is saved (e.g., for test output you'll reference across multiple turns):
- `command > /tmp/output.txt 2>&1; echo "EXIT: $?"` — capture stdout+stderr + exit code
- Use `read` with `offset`/`limit` to page through the file
- **Never** use `head`/`tail` and rerun the same command repeatedly — it's slow, output may change between runs, and it wastes turns