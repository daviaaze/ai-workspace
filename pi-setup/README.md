# Personal PI Setup

PI-native rules, skills, prompts, and extensions for this personal AI Workspace.

## Source of Truth

**Only edit files under `pi-setup/`.**

Do not manually edit `~/.pi/agent/*` — those are deployment targets.

## Runtime Topology

- **Canonical source**: `pi-setup/` in this repo
- **Global runtime target**: `~/.pi/agent/`

This keeps one authoring location.

## Skills

| Skill | Purpose |
|---|---|
| `commit` | Create safe git commits with conventional messages |
| `create-pr` | Open pull requests with descriptions |
| `daily` | Generate stand-up notes from TODOs |
| `debug` | Hypothesis-driven debugging |
| `deploy-checklist` | Pre/post-deploy verification checklists |
| `deep-research` | Deep recursive research via web search |
| `desloppify` | Clean up AI-generated code artifacts |
| `feature-dev` | Start and work through features/tasks |
| `learn` | Persist corrections and learnings to `memory/` |
| `nixfiles` | NixOS configuration management |
| `onboard` | Analyze new repos and create project notes |
| `pre-review` | Self-review code before PR |

Other files in `skills/` (`SKILL_CATALOG.md`, `stack-ref.md`) are reference
documents — not skill entries. They live alongside the skill directories but
aren't deployed as skills.

## Deploy / Repair

```bash
./pi-setup/deploy.sh --dry-run
./pi-setup/deploy.sh
```

What it does:
1. Symlinks pi-setup assets into `~/.pi/agent/`
2. Backs up any non-symlink files before replacing

## Verification

After deploy:

```bash
readlink ~/.pi/agent/skills/commit
readlink ~/.pi/agent/extensions/permission-gate.ts
```

Expected:
- `~/.pi/agent/...` points to this repo's `pi-setup/...`

## Deploy via Nix

On NixOS, you can also add this flake as an input and use the `pi-setup-packages` output to deploy assets during `nixos-rebuild` or `home-manager switch`.
