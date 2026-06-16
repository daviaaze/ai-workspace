---
name: commit
description: Create a safe git commit with a conventional commit message. Use when the user says commit, wants to save changes, or asks to stage and commit.
---

# Safe Commit Workflow

## Trigger
Commit, save changes, stage and commit.

## Workflow

1. **Verify branch** — `git branch --show-current`. If `main`/`master`, STOP and warn.
2. **Review changes** — `git status` + `git diff` (or `--cached`). Summarize in user-friendly terms.
3. **Stage** — ask which files, or stage all if confirmed.
4. **Generate message** — determine type (`feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `security`). Short description ≤50 chars. Bullet points for details.
5. **Commit** — execute `git commit`. Confirm success.
6. **Suggest next** — `/skill:create-pr` or `git push` (with escalation check).

## Conventional Commit Types
- `feat:` — new feature
- `fix:` — bug fix
- `refactor:` — code change that neither fixes a bug nor adds a feature
- `docs:` — documentation only
- `test:` — adding or correcting tests
- `chore:` — maintenance, deps, tooling
- `perf:` — performance improvement
- `security:` — security fix
