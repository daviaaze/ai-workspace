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
    # Skip 00-global.md — it's loaded via AGENTS.md symlink below
    [[ "$name" == "00-global.md" ]] && continue
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
}

deploy_settings() {
  local root="$1"
  local settings_profile="$SCRIPT_DIR/settings-profile.json"
  local models_profile="$SCRIPT_DIR/models-profile.json"
  local settings_target="$root/settings.json"
  local models_target="$root/models.json"

  echo ""
  echo "==> Provider Settings Transport"
  echo ""

  if $DRY_RUN; then
    echo "  DRY-RUN: Would merge $settings_profile into $settings_target (if exists)"
    echo "  DRY-RUN: Would merge $models_profile into $models_target (if exists)"
    echo ""
  fi

  # Merge settings-profile.json into settings.json — merge keys, don't overwrite whole file
  if [ -f "$settings_profile" ]; then
    if [ ! -f "$settings_target" ]; then
      echo "  Creating $settings_target from profile"
      run cp "$settings_profile" "$settings_target"
    else
      echo "  Merging profile keys into $settings_target"
      # Use python3 to merge profile keys into existing settings.json
      run python3 -c "
import json
with open('$settings_profile') as f:
    profile = json.load(f)
with open('$settings_target') as f:
    target = json.load(f)
# Merge profile keys into target (profile keys override target)
target.update({k: v for k, v in profile.items() if k != 'packages' or len(v) > 0})
with open('$settings_target', 'w') as f:
    json.dump(target, f, indent=2)
print('  Merged ' + str(len(profile)) + ' profile keys into settings.json')
"
    fi
  fi

  # Merge models-profile.json into models.json (atlas-cloud provider)
  if [ -f "$models_profile" ]; then
    if [ ! -f "$models_target" ]; then
      echo "  Creating $models_target from profile"
      run cp "$models_profile" "$models_target"
    else
      echo "  Merging atlas-cloud models into $models_target"
      run python3 -c "
import json
with open('$models_profile') as f:
    profile = json.load(f)
with open('$models_target') as f:
    target = json.load(f)
# Merge atlas-cloud provider from profile into target
if 'atlas-cloud' in profile:
    target.setdefault('providers', {})['atlas-cloud'] = profile['atlas-cloud']
with open('$models_target', 'w') as f:
    json.dump(target, f, indent=2)
print('  Merged atlas-cloud provider into models.json')
"
    fi
  fi

  echo ""
  echo "  == Auth Setup (manual) =="
  echo "  Atlas Cloud: run '/set-key atlas-cloud <your-api-key>' in PI"
  echo "  Or edit: $root/auth.json"
  echo ""
  echo "  == NPM Packages (installed by PI from settings.json) =="
  local pkgs
  pkgs=$(python3 -c "import json; d=json.load(open('$settings_profile')); print('\n'.join(d.get('packages',[])))" 2>/dev/null || echo "(check settings-profile.json)")
  echo "$pkgs"
  echo ""
}

deploy "$PI_DIR"
deploy_settings "$PI_DIR"

# Symlink the global rule as AGENTS.md (loaded automatically by PI at session start)
GLOBAL_RULE="$SCRIPT_DIR/rules/00-global.md"
AGENTS_TARGET="$PI_DIR/AGENTS.md"
if [ -f "$GLOBAL_RULE" ]; then
  echo "==> Linking AGENTS.md -> rules/00-global.md"
  link_item "$GLOBAL_RULE" "$AGENTS_TARGET"
fi

echo "==> Done. Source of truth: $SCRIPT_DIR"
echo "==> Restart PI or run /reload to pick up changes."
