# Project Patterns

Workflow patterns and file locations learned during PI sessions.

## nixfiles Code Structure (extracted 2026-06-09)

Key file roles discovered from 61 session analyses:

```
nixfiles/
  flake.nix                     # Flake entry point
  flake.lock                    # Locked inputs
  hosts/dvision-thinkbook/      # ThinkBook host config
    default.nix                 # Main host import
    hardware.nix                # Kernel, firmware, drivers
    performance.nix             # CPU governors, power states
    lenovo.nix                  # Vendor-specific tweaks
    display.nix                 # Display/graphics config
    bluetooth.nix               # Bluetooth config
    services/                   # Host-specific services
      default.nix
      work-environment.nix
  modules/
    flake-parts/                # Flake composition
      overlays.nix              # ← MOST-EDITED file (central customization)
      apps.nix                  # Flake apps
      packages.nix              # Flake packages
      nixos-configurations.nix  # NixOS config registrations
    home/modules/features/      # Feature toggles
      cli.nix, desktop.nix, media.nix, gaming.nix, work.nix
    nixos/
      desktop-manager/
        dshell/default.nix      # dshell session config
        gnome/default.nix       # GNOME session config
      core.nix, default.nix, users.nix, sops.nix
    packages/
      tools/                    # Tool packages (e.g., nix-viz)
      work/                     # Work tools (e.g., atlassian-cli, lux-cli)
    kernel-patches/             # Kernel patches
    shared/package-categories.nix
```

**Key insights:**
- `overlays.nix` is the central customization point — changes affect all hosts
- Package definitions require 5–15 build iterations (high correction loop counts)
- `performance.nix` and `hardware.nix` are host-specific and test-sensitive
- dshell Nix module lives at `~/Projects/pessoal/dshell/nix/module.nix`

## Feature Development Pattern

```
Development/Features/
  Backlog/<feature-name>/
    ticket.md      # Requirements
    analysis.md    # Codebase findings (use graph tools)
    plan.md        # Implementation plan
    notes.md       # Ongoing notes
  In-Progress/<feature-name>/   # Move folder when starting
  Done/<feature-name>/         # Move folder when shipped
```

## Memory Categorization

| What happened | Save to |
|---------------|---------|
| PI broke a convention | `memory/conventions.md` |
| PI didn't know a workflow | `memory/project-patterns.md` |
| One-off bug/fix | `memory/learning-log.md` |
| Architectural decision | `Technical-Decisions/ADR-NNN-*.md` |

## Debugging Methodology

### Trace the data flow, don't guess
When something doesn't work, trace the path from user action → handler → state change → notification → UI update. Every step is either observable (logs, signals) or inferable. Don't skip steps — you don't know which one is broken until you check.

### Isolate what's actually broken
**Before changing any code,** verify:
1. Does the handler fire? (logs, journalctl)
2. Does the state change propagate? (does a binding update?)
3. Is the notification reaching the UI? (does For re-render?)
4. Only THEN fix the specific broken step

### General principles
- **Don't rewrite working components.** If a widget handles user input correctly, the bug is likely upstream in state/notification, not in the widget itself.
- **Complexity is a smell.** Every layer of abstraction is another place for bugs. If the fix feels complex, step back.
- **Go back to last-known-good.** When changes break things, revert to what worked and add minimal changes.
- **Always check runtime logs first** (`journalctl --user _COMM=shade-shell -f`). Keep debug prints until the fix is proven.

> See `memory/learning-log.md` (2026-05-19 AppMixer) for a detailed case study applying all of these principles.

## Gnim For + Local State Trap

`For` re-invokes the callback on every re-render. Local `let` variables are **re-created on each invocation**, losing previous values. Any debounce or drag-guard logic using `let` breaks under frequent re-renders.

**Solution:** Use persistent state mechanisms — `createState`, `$` callbacks (run once per widget), or external Maps.

> See `memory/learning-log.md` (2026-05-19 AppMixer) for the full case study.

## Graph Tool Workflow

1. `build_or_update_graph` — ensure graph is current
2. `detect_changes` — understand what changed
3. `get_impact_radius` — see blast radius before modifying
4. `get_review_context` — focused review

> Detailed rules in `memory/conventions.md` → Graph Tools.

## Custom Extensions

Extensions live in `~/.pi/agent/extensions/` (global) or `.pi/extensions/` (project-local). They can register tools, commands, intercept events, and inject context.

See `memory/conventions.md` → Custom Extensions for the current catalog.

## Skills-First Workflow

> Full skill catalog (28 skills, categorized) in `memory/conventions.md` → Skills-First Workflow.

Before any action, check available skills for a relevant one. If a skill matches, follow it exactly.

## Git Workflow

> Commit conventions, escalation rules, and workspace commit rules are in `memory/conventions.md`.

1. Branch from `main`
2. Conventional commits (`feat:`, `fix:`, etc.)
3. `/skill:pre-review` before PR
4. `/skill:create-pr` to publish
