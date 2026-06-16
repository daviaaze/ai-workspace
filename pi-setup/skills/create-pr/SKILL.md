---
name: create-pr
description: Create a pull request with description and test table. Use when the user says create PR, open pull request, or asks to publish changes after committing.
---

# PR Creation Workflow

## Trigger
Create PR, open pull request, publish changes.

## Workflow

1. **Gather context** — inspect commits, `git diff main...HEAD --stat`, and any repo-local PR template.
2. **Read workspace context** — if a matching feature folder exists, read its `README.md`, `plan.md`, and `notes.md`.
3. **Generate description** — summarize what changed, why, dependencies, rollout notes, and any reviewer focus.
4. **Build test table** — include automated and manual validation with clear pass/fail status.
5. **Create** — use `gh pr create` or equivalent. Add labels if the repo uses them.
6. **Notify** — share the PR URL and call out manual follow-ups like screenshots, staging checks, or deploy order.

## PR Template

```markdown
## What Changed
Brief description.

## Why
Motivation.

## Type
- [ ] feat / fix / refactor / docs / test / chore / perf / security

## Test Results
| Scenario | Status |
|----------|--------|
| | |

## Checklist
- [ ] Tests pass
- [ ] Lint passes
- [ ] Type-check passes
- [ ] Manual testing done
```
