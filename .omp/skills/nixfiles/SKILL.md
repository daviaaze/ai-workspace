---
name: nixfiles
description: Manage and reference personal NixOS configuration, Home Manager modules, and Nix-related setups.
---

# Nix Configuration Management

## Trigger
NixOS, home-manager, Nix, flake, configuration, rebuild.

## Workflow

1. **Understand** — which system/service needs configuration?
2. **Locate** — find the relevant module or config file.
3. **Modify** — follow existing patterns; test with `nix flake check`.
4. **Rebuild** — `sudo nixos-rebuild switch` or `home-manager switch`.
5. **Verify** — check that the change took effect.
