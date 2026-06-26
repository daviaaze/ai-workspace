#!/usr/bin/env bash
# Validate pi-setup integrity
# Run from workspace root:  ./pi-setup/validate.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PI_DIR="${PI_DIR:-$HOME/.pi/agent}"
WORKSPACE="${WORKSPACE:-$HOME/Projects/ai-workspace}"
ERRORS=0

pass() { echo "  ✅ $1"; }
fail() { echo "  ❌ $1"; ERRORS=$((ERRORS + 1)); }
heading() { echo; echo "--- $1 ---"; }

heading "Symlinks in ~/.pi/agent"
for kind in skills extensions prompts rules; do
  count=0
  for target in "$PI_DIR/$kind"/*; do
    [ -e "$target" ] || continue
    if [ -L "$target" ]; then
      src=$(readlink "$target")
      if [ -e "$src" ]; then
        count=$((count + 1))
      else
        fail "$target → BROKEN ($src)"
      fi
    else
      fail "$target is NOT a symlink"
    fi
  done
  pass "$count $kind entries, all symlinked"
done

heading "AGENTS.md"
if [ -L "$PI_DIR/AGENTS.md" ]; then
  src=$(readlink "$PI_DIR/AGENTS.md")
  if [ "$src" = "$SCRIPT_DIR/rules/00-global.md" ]; then
    pass "AGENTS.md → rules/00-global.md"
  else
    fail "AGENTS.md points to $src, expected $SCRIPT_DIR/rules/00-global.md"
  fi
else
  fail "AGENTS.md is not a symlink"
fi

heading "Shell injection check"
for f in "$SCRIPT_DIR/extensions"/*.ts "$SCRIPT_DIR/extensions"/*/index.ts; do
  [ -f "$f" ] || continue
  name=$(basename "$(dirname "$f")")/$(basename "$f")
  if grep -qP 'exec(File)?Sync.*\`' "$f" 2>/dev/null; then
    fail "$name uses shell string with execSync"
  else
    pass "$name no shell injection"
  fi
done

heading "try/catch balance"
for f in "$SCRIPT_DIR/extensions"/*.ts "$SCRIPT_DIR/extensions"/*/index.ts; do
  [ -f "$f" ] || continue
  name=$(basename "$(dirname "$f")")/$(basename "$f")
  # Count try/catch/finally in non-template-string code via node
  balance=$(node -e "
const fs = require('fs');
const src = fs.readFileSync('$f', 'utf-8');
const lines = src.split('\n');
let depth = 0, inTpl = false;
for (const line of lines) {
  for (let c = 0; c < line.length; c++) {
    if (line[c] === '\`' && (c === 0 || line[c-1] !== '\\\\')) inTpl = !inTpl;
  }
  if (inTpl) continue;
  const t = line.trim();
  depth += (t.match(/\btry\s*\{/g)||[]).length;
  depth -= (t.match(/\bcatch\b/g)||[]).length;
  depth -= (t.match(/finally\b/g)||[]).length;
}
console.log(depth);
" 2>/dev/null || echo "err")
  if [ "$balance" = "0" ]; then
    pass "$name try/catch balanced"
  elif [ "$balance" = "err" ]; then
    fail "$name could not check balance"
  else
    fail "$name unbalanced (depth=$balance)"
  fi
done

heading "Stale path references"
stale=$(grep -rn "pessoal\|Lux/ai-workspace" "$SCRIPT_DIR" --include="*.md" --include="*.ts" --include="*.nix" --include="*.sh" --exclude="validate.sh" 2>/dev/null || true)
if [ -z "$stale" ]; then
  pass "No stale pessoal/Lux path references"
else
  fail "Found stale paths:"
  echo "$stale" | while read -r line; do echo "       $line"; done
fi

heading "workspace-search root resolution"
node -e "
const { resolve } = require('path');
const { homedir } = require('os');
const root = process.env.WORKSPACE || resolve(homedir(), 'Projects/ai-workspace');
const expected = '$WORKSPACE';
if (root === expected) {
  console.log('OK');
  process.exit(0);
} else {
  console.log('MISMATCH: ' + root + ' vs ' + expected);
  process.exit(1);
}
" 2>/dev/null && pass "workspace-search resolves correctly" || fail "workspace-search root mismatch"

heading "Nix module sourcePath option"
if grep -q 'sourcePath = mkOption' "$SCRIPT_DIR/nix/pi-workspace.nix" 2>/dev/null; then
  pass "Nix module has sourcePath option"
else
  fail "Nix module missing sourcePath option"
fi

echo
echo "======================"
if [ "$ERRORS" -eq 0 ]; then
  echo "✅ All checks passed"
else
  echo "❌ $ERRORS failure(s) found"
fi
echo "======================"
exit "$ERRORS"
