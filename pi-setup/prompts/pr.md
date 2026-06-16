---
description: Create a pull request description from git history
argument-hint: "[base-branch]"
---

Create a pull request description from the current branch against $1 (default: main).

1. **Summary** — 1-2 sentences describing the change
2. **Motivation** — What problem does this solve? Link to issues/tickets.
3. **Changes** — Bullet list of what was changed and why
4. **Testing** — What was tested, how, and results
5. **Screenshots/Videos** — If UI changes, note what needs visual review
6. **Risks** — What could break? Rollback plan?

Use `git log $1..HEAD --oneline` to get the commits, and `git diff $1..HEAD --stat` for file changes.

> Keep it concise. The PR body should be scannable in under 30 seconds.
