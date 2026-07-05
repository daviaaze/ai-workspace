# Learning Log

## 2026-06-15 — Nix `substituteInPlace --replace-fail` out of sync with pyproject.toml

**What happened**: `nixos-rebuild` failed with `substituteStream() ERROR: pattern "crewai[tools]>=0.80.0,<1.0" doesn't match anything in file 'pyproject.toml'`. The cascade took down 14 derivations.

**Root cause**: `nix/ai-workspace/package.nix` `prePatch` used `--replace-fail` with patterns that matched an older version of `pyproject.toml`. The deps had been updated (crewai constraint changed from `<1.0` to `>=1.0`) but the Nix packaging wasn't updated to match.

**Fix**:
1. Diff the `prePatch` patterns against the actual `pyproject.toml` content
2. Update mismatched patterns (crewai constraint, comment wording)
3. If the package is pulled via a flake input, push the fix and update `flake.lock`

**Prevention**: When changing dependencies in `pyproject.toml`, always check the corresponding Nix package definition for `substituteInPlace` patterns that may reference the old values. The `--replace-fail` flag makes stale patterns a hard build error rather than a silent no-op.

**Secondary issue**: Same session hit a `shade-shell` pnpm deps hash mismatch (`fetchPnpmDeps` hash stale). Same class of problem — lockfile/content changed but the Nix fixed-output hash wasn't updated. Fix: copy the "got" hash from the error into the derivation.

---
## First Learning
*2026-07-03 20:10 UTC*  

Content 1

---
## Second Learning
*2026-07-03 20:10 UTC*  

Content 2

---
## First Learning
*2026-07-03 20:21 UTC*  

Content 1

---
## Second Learning
*2026-07-03 20:21 UTC*  

Content 2

---
## First Learning
*2026-07-03 20:30 UTC*  

Content 1

---
## Second Learning
*2026-07-03 20:30 UTC*  

Content 2

---
## First Learning
*2026-07-03 21:10 UTC*  

Content 1

---
## Second Learning
*2026-07-03 21:10 UTC*  

Content 2

---
## First Learning
*2026-07-03 21:53 UTC*  

Content 1

---
## Second Learning
*2026-07-03 21:53 UTC*  

Content 2

---
## First Learning
*2026-07-03 21:58 UTC*  

Content 1

---
## Second Learning
*2026-07-03 21:58 UTC*  

Content 2

---
## First Learning
*2026-07-03 22:04 UTC*  

Content 1

---
## Second Learning
*2026-07-03 22:04 UTC*  

Content 2

---
## First Learning
*2026-07-03 22:08 UTC*  

Content 1

---
## Second Learning
*2026-07-03 22:08 UTC*  

Content 2

---
## First Learning
*2026-07-03 22:11 UTC*  

Content 1

---
## Second Learning
*2026-07-03 22:11 UTC*  

Content 2

---
## First Learning
*2026-07-03 22:17 UTC*  

Content 1

---
## Second Learning
*2026-07-03 22:17 UTC*  

Content 2

---
## First Learning
*2026-07-03 22:19 UTC*  

Content 1

---
## Second Learning
*2026-07-03 22:19 UTC*  

Content 2

---
## First Learning
*2026-07-03 22:20 UTC*  

Content 1

---
## Second Learning
*2026-07-03 22:20 UTC*  

Content 2

---
## First Learning
*2026-07-03 22:22 UTC*  

Content 1

---
## Second Learning
*2026-07-03 22:22 UTC*  

Content 2

---
## First Learning
*2026-07-03 22:24 UTC*  

Content 1

---
## Second Learning
*2026-07-03 22:24 UTC*  

Content 2

---
## First Learning
*2026-07-03 22:30 UTC*  

Content 1

---
## Second Learning
*2026-07-03 22:30 UTC*  

Content 2

---
## First Learning
*2026-07-03 22:32 UTC*  

Content 1

---
## Second Learning
*2026-07-03 22:32 UTC*  

Content 2

---
## First Learning
*2026-07-03 22:35 UTC*  

Content 1

---
## Second Learning
*2026-07-03 22:35 UTC*  

Content 2

---
## First Learning
*2026-07-03 22:51 UTC*  

Content 1

---
## Second Learning
*2026-07-03 22:51 UTC*  

Content 2

---
## First Learning
*2026-07-03 22:54 UTC*  

Content 1

---
## Second Learning
*2026-07-03 22:54 UTC*  

Content 2

---
## First Learning
*2026-07-03 22:57 UTC*  

Content 1

---
## Second Learning
*2026-07-03 22:57 UTC*  

Content 2

---
## First Learning
*2026-07-03 23:00 UTC*  

Content 1

---
## Second Learning
*2026-07-03 23:00 UTC*  

Content 2

---
## First Learning
*2026-07-03 23:04 UTC*  

Content 1

---
## Second Learning
*2026-07-03 23:04 UTC*  

Content 2

---
## First Learning
*2026-07-03 23:06 UTC*  

Content 1

---
## Second Learning
*2026-07-03 23:06 UTC*  

Content 2

---
## First Learning
*2026-07-04 00:33 UTC*  

Content 1

---
## Second Learning
*2026-07-04 00:33 UTC*  

Content 2

---
## First Learning
*2026-07-04 00:58 UTC*  

Content 1

---
## Second Learning
*2026-07-04 00:58 UTC*  

Content 2

---
## First Learning
*2026-07-04 19:55 UTC*  

Content 1

---
## Second Learning
*2026-07-04 19:55 UTC*  

Content 2

---
## First Learning
*2026-07-04 19:57 UTC*  

Content 1

---
## Second Learning
*2026-07-04 19:57 UTC*  

Content 2

---
## First Learning
*2026-07-04 20:04 UTC*  

Content 1

---
## Second Learning
*2026-07-04 20:04 UTC*  

Content 2

---
## First Learning
*2026-07-04 20:07 UTC*  

Content 1

---
## Second Learning
*2026-07-04 20:07 UTC*  

Content 2

---
## First Learning
*2026-07-04 20:09 UTC*  

Content 1

---
## Second Learning
*2026-07-04 20:09 UTC*  

Content 2

---
## First Learning
*2026-07-04 20:11 UTC*  

Content 1

---
## Second Learning
*2026-07-04 20:11 UTC*  

Content 2

---
## First Learning
*2026-07-04 20:14 UTC*  

Content 1

---
## Second Learning
*2026-07-04 20:14 UTC*  

Content 2

---
## First Learning
*2026-07-04 20:18 UTC*  

Content 1

---
## Second Learning
*2026-07-04 20:18 UTC*  

Content 2

---
## First Learning
*2026-07-04 20:22 UTC*  

Content 1

---
## Second Learning
*2026-07-04 20:22 UTC*  

Content 2

---
## First Learning
*2026-07-04 21:06 UTC*  

Content 1

---
## Second Learning
*2026-07-04 21:06 UTC*  

Content 2

---
## First Learning
*2026-07-04 21:18 UTC*  

Content 1

---
## Second Learning
*2026-07-04 21:18 UTC*  

Content 2

---
## First Learning
*2026-07-04 21:35 UTC*  

Content 1

---
## Second Learning
*2026-07-04 21:35 UTC*  

Content 2

---
## First Learning
*2026-07-04 21:41 UTC*  

Content 1

---
## Second Learning
*2026-07-04 21:41 UTC*  

Content 2

---
## First Learning
*2026-07-04 21:45 UTC*  

Content 1

---
## Second Learning
*2026-07-04 21:45 UTC*  

Content 2

---
## First Learning
*2026-07-04 22:55 UTC*  

Content 1

---
## Second Learning
*2026-07-04 22:55 UTC*  

Content 2

---
## First Learning
*2026-07-05 00:50 UTC*  

Content 1

---
## Second Learning
*2026-07-05 00:50 UTC*  

Content 2
