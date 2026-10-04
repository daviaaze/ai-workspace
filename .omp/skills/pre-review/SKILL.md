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
4. **Assign risk score** — if the `review-risk-framework` skill is available
   (work scope), use it for the canonical 1-5 score, escalators, and
   human/service-owner review boundary. Otherwise assess a 1-5 score inline from
   blast radius (traffic, irreversibility, complexity) using `get_impact_radius`.

5. **If delegating to reviewer subagents** — always prefer a focused handoff over inherited scratch files:
   - pass `reads:false`
   - provide explicit changed-file paths and short diff snippets only
   - cap GitHub/test output before delegation
   - prefer `output:file` + `outputMode:file-only` for long reviews

   Example:

   ```json
   {
     "agent": "reviewer",
     "task": "Review only these files for correctness, tests, regressions, and edge cases: src/a.ts, tests/a.test.ts. Use the supplied diff summary; do not assume plan/progress files exist.",
     "reads": false,
     "output": "artifacts/reviewer.md",
     "outputMode": "file-only"
   }
   ```

6. **Use capped inputs** — avoid raw `gh pr view --comments`, full GraphQL dumps, and huge test logs. Summarize locally first.

7. **Self-check** — evaluate against quality dimensions tailored to the change.
   Focus on the 3-5 most relevant:
   - Correctness, readability, test coverage, error handling, performance, security, maintainability, consistency, documentation, observability, backward compatibility, edge cases
8. **PR description check** — does the commit log + diff tell a clear story?
   Would a reviewer understand what changed and why from the PR alone? Flag 🔴 if
   the description is missing or is only a bare ticket link with no context.
9. **UI changes** — if the diff includes React/Next.js frontend code, a screenshot or video walkthrough is required. Flag 🔴 if missing.
10. **CI auto-review parity check** — if the repo has a CI auto-review
   workflow, ask: what would it flag? Would it assign a higher risk score than you
   did? Are there inline-comment-worthy issues in the diff?
11. **Flag issues**:
   - 🟢 Pass — meets standard
   - 🟡 Warning — could be improved
   - 🔴 Block — must fix before PR
12. **Report** — files changed, risk score, critical/warning counts, overall status.
13. **Suggest fixes** — offer to apply 🔴/🟡 automatically with user confirmation.

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
