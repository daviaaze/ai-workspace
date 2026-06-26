#!/usr/bin/env bash
# Deploy personal pi-setup assets into ~/.pi/agent
# Source of truth: this repo's pi-setup/ directory.
# Usage: ./pi-setup/deploy.sh [--dry-run]
set -euo pipefail
shopt -s nullglob

PI_DIR="${PI_DIR:-$HOME/.pi/agent}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DRY_RUN=false

if [ "${1:-}" = "--dry-run" ]; then
  DRY_RUN=true
fi

run() {
  if $DRY_RUN; then
    printf 'DRY-RUN: %q ' "$@"
    printf '\n'
  else
    "$@"
  fi
}

backup_if_needed() {
  local target="$1"
  if [ -e "$target" ] && [ ! -L "$target" ]; then
    local backup="${target}.bak"
    if [ ! -e "$backup" ] && [ ! -L "$backup" ]; then
      echo "  Backing up $target -> $backup"
      run mv "$target" "$backup"
    else
      echo "  Removing non-symlink target: $target"
      run rm -rf "$target"
    fi
  fi
}

link_item() {
  local source="$1"
  local target="$2"
  run mkdir -p "$(dirname "$target")"
  backup_if_needed "$target"
  run ln -sfn "$source" "$target"
}

ensure_root_dirs() {
  local root="$1"
  run mkdir -p "$root/skills" "$root/rules" "$root/prompts" "$root/extensions"
}

deploy() {
  local root="$1"
  echo "==> Deploying personal pi-setup assets to $root"
  ensure_root_dirs "$root"

  for skill_dir in "$SCRIPT_DIR/skills"/*/; do
    local name
    name="$(basename "$skill_dir")"
    echo "  Linking skill: $name"
    link_item "$skill_dir" "$root/skills/$name"
  done

  for rule in "$SCRIPT_DIR/rules"/*.md; do
    local name
    name="$(basename "$rule")"
    echo "  Linking rule: $name"
    link_item "$rule" "$root/rules/$name"
  done

  for prompt in "$SCRIPT_DIR/prompts"/*.md; do
    local name
    name="$(basename "$prompt")"
    echo "  Linking prompt: $name"
    link_item "$prompt" "$root/prompts/$name"
  done

  for ext in "$SCRIPT_DIR/extensions"/*.ts; do
    [ -f "$ext" ] || continue
    local name
    name="$(basename "$ext")"
    echo "  Linking extension: $name"
    link_item "$ext" "$root/extensions/$name"
  done

  # Subdirectory extensions (e.g., feature-tester/index.ts)
  for ext_dir in "$SCRIPT_DIR/extensions"/*/; do
    [ -d "$ext_dir" ] || continue
    local name
    name="$(basename "$ext_dir")"
    local index="$ext_dir/index.ts"
    if [ -f "$index" ]; then
      echo "  Linking extension dir: $name"
      link_item "$ext_dir" "$root/extensions/$name"
    fi
  done
}

deploy "$PI_DIR"

# Symlink the global rule as AGENTS.md (loaded automatically by PI at session start)
GLOBAL_RULE="$SCRIPT_DIR/rules/00-global.md"
AGENTS_TARGET="$PI_DIR/AGENTS.md"
if [ -f "$GLOBAL_RULE" ]; then
  echo "==> Linking AGENTS.md -> rules/00-global.md"
  link_item "$GLOBAL_RULE" "$AGENTS_TARGET"
fi

echo "==> Done. Source of truth: $SCRIPT_DIR"
echo "==> Restart PI or run /reload to pick up changes."
