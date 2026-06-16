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
3. **Self-check** — evaluate against quality dimensions:
   - Correctness, readability, test coverage, error handling, performance, security, maintainability, consistency, documentation, observability, backward compatibility, edge cases
4. **Flag issues**:
   - 🟢 Pass — meets standard
   - 🟡 Warning — could be improved
   - 🔴 Block — must fix before PR
5. **Report** — files changed, critical/warning counts, overall status.
6. **Suggest fixes** — offer to apply 🔴/🟡 automatically with user confirmation.

## Quality Dimensions

1. **Correctness** — Does it do what was asked? Edge cases handled?
2. **Readability** — Can a new engineer understand this in 30 seconds?
3. **Test Coverage** — Tests for happy path and edge cases?
4. **Error Handling** — Graceful errors, properly logged?
5. **Performance** — No N+1 queries, unnecessary blocking ops?
6. **Security** — Input validation, no secrets in code?
7. **Maintainability** — Easy to change without breaking things?
8. **Consistency** — Matches existing codebase patterns?
9. **Documentation** — Complex areas explained?
10. **Observability** — Logs, metrics, traces for debugging?
11. **Backward Compatibility** — Doesn't break existing consumers?
12. **Edge Cases** — Nulls, empty arrays, timeouts, race conditions?
