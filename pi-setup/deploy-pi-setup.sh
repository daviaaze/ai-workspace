#!/usr/bin/env bash
# Symlink pi-setup assets into ~/.pi/agent/
# Used by both the standalone deploy.sh and the Nix derivation.
set -euo pipefail
shopt -s nullglob

PI_DIR="${PI_DIR:-$HOME/.pi/agent}"
PI_SETUP_DIR="${1:-$(cd "$(dirname "$0")" && pwd)}"

mkdir -p "$PI_DIR/skills" "$PI_DIR/rules" "$PI_DIR/prompts" "$PI_DIR/extensions"

# Skills
for skill_dir in "$PI_SETUP_DIR/skills"/*/; do
  name="$(basename "$skill_dir")"
  mkdir -p "$PI_DIR/skills/$name"
  for f in "$skill_dir"/*; do
    base="$(basename "$f")"
    ln -sf "$f" "$PI_DIR/skills/$name/$base"
  done
done

# Rules
for rule in "$PI_SETUP_DIR/rules"/*.md; do
  ln -sf "$rule" "$PI_DIR/rules/$(basename "$rule")"
done

# Prompts
for prompt in "$PI_SETUP_DIR/prompts"/*.md; do
  ln -sf "$prompt" "$PI_DIR/prompts/$(basename "$prompt")"
done

# Extensions
for ext in "$PI_SETUP_DIR/extensions"/*.ts; do
  ln -sf "$ext" "$PI_DIR/extensions/$(basename "$ext")"
done

echo "Pi setup deployed to $PI_DIR"
