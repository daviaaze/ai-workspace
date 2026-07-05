#!/usr/bin/env bash
# pi-setup personal-scope consistency check.
# Run before/after deploy to catch the issues that previously slipped in:
#   P1: dangling skill references (mode-manager/catalog name a skill that doesn't exist)
#   P3: work-specific (Lux/Jira) paths leaking into the personal scope
# Usage: ./check-consistency.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
AGENT="${HOME}/.pi/agent"
STATUS=0

red()   { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
warn()  { printf '\033[33m%s\033[0m\n' "$*"; }

# --- Skill routing conflict check ---
CONF_COUNT=$(bash "$ROOT/skill-conflict-scanner.sh" 2>/dev/null || true)
SCAN_EXIT=$?
if [ "$SCAN_EXIT" -eq 0 ]; then
  green "OK: no skill routing conflicts (Jaccard <= 0.30)"
else
  warn "SKILL-CONFLICT: $SCAN_EXIT skill pairs have Jaccard > 0.30"
  STATUS=1
fi

# --- P3: no work-specific content in personal tracked source ---
# Targets concrete work tokens (paths, domains, ticket tools). Skill *names* are
# allowed because shared skills legitimately reference work skills conditionally;
# dangling skill *usage* is caught by the P1 reference check below.
LEAK=$(grep -rIn 'Projects/Lux\|jtk \|XTRNT-\|luxuryescapes' \
  "$ROOT/skills" "$ROOT/rules" "$ROOT/extensions" "$ROOT/prompts" 2>/dev/null \
  | grep -v '/feature-tester/' || true)
if [ -n "$LEAK" ]; then
  red "FAIL: work-specific content leaked into personal scope:"
  printf '%s\n' "$LEAK"
  STATUS=1
else
  green "OK: no work-specific leaks in personal tracked source"
fi

# --- P1: every skill referenced by catalog + mode-manager must resolve ---
SKILLREFS=$(grep -oE 'skills: \[[^]]+\]' "$AGENT/extensions/mode-manager/index.ts" 2>/dev/null \
  | sed -E 's/skills: \[//; s/\]//; s/"//g' | tr ',' '\n' | sed 's/^ *//;s/ *$//' | sort -u)
CATALOG_REFS=$(grep -oE '`[a-z][a-z0-9-]+`' "$ROOT/skills/SKILL_CATALOG.md" 2>/dev/null \
  | tr -d '`' | sort -u)
ALL_REFS=$(printf '%s\n%s\n' "$SKILLREFS" "$CATALOG_REFS" | sort -u)

for ref in $ALL_REFS; do
  case "$ref" in mode-ask|mode-plan|""|sketch) continue;; esac   # mode placeholders / non-skills
  if [ ! -e "$AGENT/skills/$ref/SKILL.md" ] && [ ! -e "$AGENT/skills/$ref" ]; then
    red "FAIL: skill reference '$ref' has no matching skill in $AGENT/skills"
    STATUS=1
  fi
done
[ "$STATUS" -eq 0 ] && green "OK: all catalog/mode-manager skill references resolve in agent/skills"

# --- work skills must not be sourced from the personal agent (deploy inversion) ---
for s in daily deploy-checklist stack-ref validate-infra validate-migration security-review review-risk-framework confluence; do
  if [ -e "$AGENT/skills/$s" ] && [ "$(readlink -f "$AGENT/skills/$s" 2>/dev/null)" = "$AGENT/skills/$s" ]; then
    red "FAIL: work skill '$s' is a real dir in the personal agent, not a work-scope symlink"
    STATUS=1
  fi
done
[ "$STATUS" -eq 0 ] && green "OK: no work skills inverted into personal agent"

exit $STATUS