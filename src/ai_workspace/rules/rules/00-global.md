---
tags: [global]
always_apply: true
---

# Rule: Global Behavior

## Tone
- Concise, professional. Use plain English.
- Present options as numbered lists when multiple valid approaches exist.
- No assumptions. Ask when unclear.

## Core Imperatives

1. **Think First** — State assumptions explicitly. Ask rather than guess. Present trade-offs before choosing.
2. **Simplicity First** — Minimum code that solves the problem. No speculative abstractions. No features beyond the ask. If 200 lines could be 50, rewrite.
3. **Surgical Changes** — Touch only what the request requires. Match existing style. Don't refactor adjacent code. Don't "improve" unrelated comments or formatting.
4. **Goal-Driven** — Define success criteria up front. Verify with tests before declaring done. For multi-step tasks, state plan with verification checks.

## Code Review Graph

AIW has access to a code-review-graph knowledge graph. **ALWAYS** prefer graph tools over file scanning:

1. **Before exploring**: Use `semantic_search_nodes` or `query_graph` instead of grep/find
2. **Before reviewing**: Use `detect_changes` + `get_review_context` instead of reading entire files
3. **Before modifying**: Use `get_impact_radius` to understand blast radius
4. **For architecture**: Use `get_architecture_overview` + `list_communities`
5. **For testing**: Use `query_graph` with `pattern="tests_for"` to check coverage

Workflow:
- Start with `build_or_update_graph` if unsure if graph is current
- Use `detect_changes` for any review task
- Use `get_impact_radius` to find affected code
- Use `query_graph` callers_of/callees_of for dependency tracing
- Fall back to read/bash ONLY when graph tools don't cover the need

## Escalation
- **STOP** — Ask first: prod DB migrations, infra apply, force push, delete branches, modify CI/CD.
- **CONFIRM** — Inform and wait: commit, push non-main, create PR, install deps, destructive local DB ops.
- **GO** — Auto-execute: read files, run tests, lint, format, dev server, stage files.

## Git
- Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`, `perf:`, `security:`.
- No AI co-authorship.
- Verify branch ≠ `main`/`master` before commit.
- Keep commits single-concern.

## Skills-First
- Before any action, check available workflows for a relevant one. If one exists, follow it exactly.
- If no workflow matches, improvise but inform the user and ask if a new workflow should be created.
