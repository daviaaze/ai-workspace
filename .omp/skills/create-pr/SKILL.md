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
3. **PR description gate** — the description must:
   - Explain **what** changed
   - Explain **why** it's needed
   - A bare ticket link is NOT sufficient on its own
   - If the diff includes UI/frontend code, screenshots or a video walkthrough are required
4. **Risk self-assessment** — assign a risk score (1-5) based on the diff and include it in the PR description. If the `review-risk-framework` skill is available (work scope), use it for the canonical rubric; otherwise score inline from blast radius (traffic, irreversibility, complexity) via `get_impact_radius`. This helps human reviewers and CI auto-review scope their effort.
5. **Generate description** — summarize what changed, why, dependencies, rollout notes, risk score, and reviewer focus.
6. **Build test table** — include automated and manual validation with clear pass/fail status.
7. **Create** — use `gh pr create` or equivalent. Add labels if the repo uses them.
8. **Notify** — share the PR URL and call out manual follow-ups like screenshots, staging checks, or deploy order.

## PR Template

```markdown
## What Changed
Brief description.

## Why
Motivation.

## Risk Score
Self-assessed risk score (1-5)

Reason / escalators:
- 

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
- [ ] Risk score self-assessed
- [ ] Screenshots attached (UI changes only)
```
