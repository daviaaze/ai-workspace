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
