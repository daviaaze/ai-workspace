# Git Aliases & Workflow

Handy aliases for the PI workflow.

## Add to `~/.gitconfig`

```ini
[alias]
  # Commit
  cm = commit -m
  ca = commit --amend
  can = commit --amend --no-edit

  # Status & Diff
  st = status -sb
  df = diff
  dfs = diff --staged
  dfo = diff --name-only

  # Branch
  br = branch
  co = checkout
  cob = checkout -b
  bd = branch -d
  bD = branch -D

  # Log
  lg = log --oneline --graph --decorate
  lga = log --oneline --graph --decorate --all
  last = log -1 HEAD --stat

  # Stash
  ss = stash
  sp = stash pop
  sl = stash list

  # Sync
  pl = pull
  ps = push
  psf = push --force-with-lease
  fe = fetch

  # Review
  files = diff --name-only main...HEAD
  stat = diff --stat main...HEAD
```

## Conventional Commit Types

| Type | When to use |
|------|-------------|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `refactor:` | Code change, no feature/bug change |
| `docs:` | Documentation only |
| `test:` | Adding/correcting tests |
| `chore:` | Maintenance, deps, tooling |
| `perf:` | Performance improvement |
| `security:` | Security fix |

## Quick Patterns

```bash
# Safe force push
git push --force-with-lease

# Interactive rebase last 3
git rebase -i HEAD~3

# Undo last commit, keep changes
git reset --soft HEAD~1

# Clean untracked files
git clean -fd

# Show commits not on main
git log main..HEAD --oneline
```
