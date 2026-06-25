# Project: Nix Home Configuration

**Status:** in-progress
**Date:** 2026-05-04

## Goal
Declarative NixOS and Home Manager configuration managed as a flake.

## Architecture
- `flake.nix` — entry point
- `hosts/` — per-machine configurations
- `home/` — Home Manager modules
- `overlays/` — custom package overrides

## Decisions
- Using flakes for reproducibility
- Home Manager as NixOS module (not standalone)

## Links
- Repo: `~/nixfiles`
- Docs: `references/nix-*.md` (create as needed)
