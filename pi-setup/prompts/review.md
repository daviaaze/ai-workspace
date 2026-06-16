---
description: Review code changes before committing
argument-hint: "[focus area]"
---

Review the current changes (`git diff` or `git diff --cached`).

Focus areas: $1 (default: all)

Check for:
- Bugs and logic errors
- Security issues (input validation, secrets, injection)
- Error handling gaps
- Performance problems (N+1, blocking ops)
- Test coverage
- Code readability and naming

Use `detect_changes` and `get_review_context` if available.
