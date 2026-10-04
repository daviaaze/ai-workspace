---
name: commit
description: Create a safe git commit with a conventional commit message. Use when the user says commit, wants to save changes, or asks to stage and commit.
---

# Safe Commit Workflow

## Trigger
Commit, save changes, stage and commit.

## Workflow

1. **Verify branch** — `git branch --show-current`. If `main`/`master`, STOP and warn.
2. **Rebase-first** — before staging, ensure you're up to date with `main`:
   ```bash
   git fetch origin main && git rebase origin/main
   ```
   Do **not** merge main into your branch — rebase only.  Resolve conflicts interactively.
3. **Review changes** — `git status` + `git diff` (or `--cached`). Summarize in user-friendly terms.
4. **Atomicity check** — each commit must represent exactly one logical change:
   - Refactors must be in a separate commit from new features or bug fixes.
   - Do not bundle formatting/whitespace changes with logic changes.
   - If the diff mixes concerns, offer to split into multiple commits.
5. **Stage** — ask which files, or stage all if confirmed.
6. **Generate message** — determine type (`feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `security`). Short description ≤50 chars. Bullet points for details.
   - **No duplicate commit messages.** Never have consecutive commits with the same description. Each commit message must uniquely describe the change.
7. **Commit** — execute `git commit`. Confirm success.
8. **Suggest next** — `/skill:create-pr` or `git push` (with escalation check).

## Conventional Commit Types
- `feat:` — new feature
- `fix:` — bug fix
- `refactor:` — code change that neither fixes a bug nor adds a feature
- `docs:` — documentation only
- `test:` — adding or correcting tests
- `chore:` — maintenance, deps, tooling
- `perf:` — performance improvement
- `security:` — security fix
