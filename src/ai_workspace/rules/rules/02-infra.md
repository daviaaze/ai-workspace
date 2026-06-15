---
tags: [infra]
always_apply: false
---

# Rule: Infrastructure

Apply when editing: `.nix`, Dockerfile, `docker-compose.yml`, `.env`, Pulumi/Terraform, CI/CD configs, database migrations.

## NixOS
- Use flakes. Keep `flake.nix` at the repo root.
- Avoid `rec` in overlays to prevent infinite recursion.
- If `home-manager.useGlobalPkgs = false`, overlay scope is per-user; prefer `useGlobalPkgs = true`.
- Run `nix flake check` before committing Nix changes.

## Databases
- Never modify production data without a backup.
- All schema changes need a migration file. Rollback instructions required.
- Use transactions for multi-statement operations.
- Don't store secrets in connection strings — use environment variables or secret managers.

## Environment Variables
- `.env` files are local-only. Never commit them.
- Provide `.env.example` with dummy values for reference.
- Use `pydantic-settings` for typed config loading.

## CI/CD
- CI must include: lint, type-check, test, build.
- Deployment to production requires manual approval.
- Keep secrets in CI secret manager, never in config files.

## Docker
- Prefer Nix over Docker where possible. Use Docker only when unavoidable.
- Multi-stage builds to minimize image size.
- Pin base images by digest for reproducibility.
