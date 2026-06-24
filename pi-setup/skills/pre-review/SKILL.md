---
name: pre-review
description: Self-review code before opening a PR. Use when the user says review my code, check this PR, pre-review, or wants to validate changes before publishing.
---

# Pre-Review Workflow

## Trigger
Review my code, check this PR, pre-review, validate changes.

## Workflow

1. **Get diff** — `git diff main...HEAD`. Identify changed files.
2. **Use graph tools** — run `detect_changes` and `get_review_context` for focused review.
3. **Test coverage gate** — every feature or bug fix diff must have a corresponding test change. If the diff has new business logic with no test, flag 🔴 Block.
4. **Assign risk score** — use `review-risk-framework` for the canonical
   1-5 score, automatic escalators, and human/service-owner review boundary.

5. **Self-check** — evaluate against quality dimensions tailored to the change.
   Focus on the 3-5 most relevant:
   - Correctness, readability, test coverage, error handling, performance, security, maintainability, consistency, documentation, observability, backward compatibility, edge cases
6. **PR description check** — does the commit log + diff tell a clear story? Would a reviewer understand what changed and why from the PR alone, or do they need a ticket? Flag 🔴 if description is missing or an empty-Jira-link.
7. **UI changes** — if the diff includes React/Next.js frontend code, a screenshot or video walkthrough is required. Flag 🔴 if missing.
8. **Claude CI parity check** — ask: what would the CI `claude-merge-review` workflow flag? Would it assign a higher risk score than you did? Are there inline-comment-worthy issues in the diff?
9. **Flag issues**:
   - 🟢 Pass — meets standard
   - 🟡 Warning — could be improved
   - 🔴 Block — must fix before PR
10. **Report** — files changed, risk score, critical/warning counts, overall status.
11. **Suggest fixes** — offer to apply 🔴/🟡 automatically with user confirmation.

## Quality Dimensions (Reference)

1. **Correctness** — Does it do what was asked? Edge cases?
2. **Readability** — Can someone understand this in 30 seconds?
3. **Test Coverage** — Happy path + edge cases?
4. **Error Handling** — Graceful errors, properly logged?
5. **Performance** — N+1 queries, unnecessary blocking ops?
6. **Security** — Input validation, no secrets?
7. **Maintainability** — Easy to change without breaking?
8. **Consistency** — Matches existing codebase patterns?
9. **Documentation** — Complex areas explained?
10. **Observability** — Logs, metrics, traces for debugging?
11. **Backward Compatibility** — Doesn't break consumers?
12. **Edge Cases** — Nulls, empty arrays, timeouts, race conditions?
