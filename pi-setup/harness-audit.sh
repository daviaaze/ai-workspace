#!/usr/bin/env bash
# harness-audit.sh — zero-token bloat audit for Pi agent harness.
#
# Reads local files and pi-telemetry.db only. No LLM calls.
# Reports catalog tax, skill sizes, compaction/cost trends, startup profile.
#
# Usage: ./harness-audit.sh                 # full report (default)
#        ./harness-audit.sh --quick          # summary only
#        ./harness-audit.sh --csv            # machine-readable skill rank
#        ./harness-audit.sh --watch          # continuous (re-run every 300s)
#
# Dependencies: bash, coreutils, nixpkgs#sqlite, python3 (for debug log)
set -euo pipefail

# ─── Paths ─────────────────────────────────────────────────────────────────
ROOT="$(cd "$(dirname "$0")" && pwd)"
AGENT="${HOME}/.pi/agent"
WORK_AGENT="${HOME}/.pi/agent-work"
TELEMETRY_DB="${AGENT}/pi-telemetry.db"
DEBUG_LOG="${AGENT}/pi-debug.log"

# ─── Sqlite via nix run ────────────────────────────────────────────────────
SQLITE_CMD=""
if nix run nixpkgs#sqlite -- --version &>/dev/null 2>&1; then
  SQLITE_CMD="nix run nixpkgs#sqlite --"
fi

# ─── Formatting ────────────────────────────────────────────────────────────
BOLD='\033[1m'; DIM='\033[2m'
RED='\033[31m'; GREEN='\033[32m'; YELLOW='\033[33m'
CYAN='\033[36m'; MAGENTA='\033[35m'; RESET='\033[0m'

pass() { printf "  ${GREEN}✓${RESET} %s\n" "$*"; }
warn() { printf "  ${YELLOW}⚠${RESET} %s\n" "$*"; }
fail() { printf "  ${RED}✗${RESET} %s\n" "$*"; }
info() { printf "  ${CYAN}▶${RESET} %s\n" "$*"; }
dim()  { printf "  ${DIM}%s${RESET}\n" "$*"; }
header() { printf "\n${BOLD}${MAGENTA}══════ %s ══════${RESET}\n" "$*"; }
rul()  { printf "  ${DIM}────────────────────────────────────────${RESET}\n"; }

STATUS=0

# ─── Token estimation ─────────────────────────────────────────────────────
# Conservative: Claude ratio ~3.5 chars/token. Overestimates = safer.
est_tokens() { echo $(( (${#1} * 10 + 34) / 35 )); }

# ─── Usage ─────────────────────────────────────────────────────────────────
usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTION]

Zero-token bloat audit for Pi agent harness.

Options:
  --quick     Summary only
  --csv       Machine-readable CSV of skill rank (stdout)
  --watch     Continuous mode (re-run every N s, default 300)
  --help      This message
EOF
  exit 0
}

# ─── Parse args ────────────────────────────────────────────────────────────
MODE="full"
for arg in "$@"; do
  case "$arg" in
    --quick) MODE="quick" ;;
    --csv)   MODE="csv" ;;
    --watch) MODE="watch" ;;
    --help)  usage ;;
  esac
done

# ─── Watch mode ────────────────────────────────────────────────────────────
if [ "$MODE" = "watch" ]; then
  INTERVAL="${2:-300}"
  while true; do
    clear
    echo "=== harness-audit --watch (every ${INTERVAL}s) ==="
    echo "Press Ctrl+C to stop"
    echo ""
    bash "$0" --quick
    sleep "$INTERVAL"
  done
fi

# ═══════════════════════════════════════════════════════════════════════════
# CSV MODE
# ═══════════════════════════════════════════════════════════════════════════
if [ "$MODE" = "csv" ]; then
  echo "skill_name,description_chars,description_tokens_est,body_lines,body_chars,body_tokens_est,scope"
  for pair in "personal:$AGENT" "work:$WORK_AGENT"; do
    sc="${pair%%:*}"; dir="${pair#*:}"
    [ -d "$dir/skills" ] || continue
    for sd in "$dir/skills"/*/; do
      [ -d "$sd" ] || continue
      nm=$(basename "$sd"); [ -f "$sd/SKILL.md" ] || continue
      ct=$(<"$sd/SKILL.md")
      d=$(echo "$ct" | sed -n '/^description: /{s/^description: //;p;}' | head -1)
      dc=${#d}; dt=$(est_tokens "$d")
      bd=$(echo "$ct" | sed -n '/^---$/,/^---$/!p' | sed -n '/^---$/,$p' | tail -n +2)
      [ -z "$bd" ] && bd="$ct"
      bl=$(echo "$bd" | wc -l); bc=${#bd}; bt=$(est_tokens "$bd")
      printf "%s,%d,%d,%d,%d,%d,%s\n" "$nm" "$dc" "$dt" "$bl" "$bc" "$bt" "$sc"
    done
  done
  exit 0
fi

# ═══════════════════════════════════════════════════════════════════════════
# MAIN REPORT
# ═══════════════════════════════════════════════════════════════════════════

echo -e "${BOLD}${MAGENTA}"
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║         Pi Harness Bloat Audit               ║"
echo "  ║         zero-token — offline only             ║"
echo "  ╚══════════════════════════════════════════════╝"
echo -e "${RESET}"
echo "  Agent:   ${AGENT}"
date "+  %Y-%m-%d %H:%M:%S"
echo ""

# ────────────────────────────────────────────────────────────────────────────
# SECTION 1: Startup Profile (from pi-debug.log)
# ────────────────────────────────────────────────────────────────────────────
if [ "$MODE" != "quick" ]; then
  header "1. Startup Profile (loaded resources)"
  if [ -f "$DEBUG_LOG" ] && command -v python3 &>/dev/null; then
    # Use python3 to strip ANSI and extract [Skills] [Prompts] [Extensions]
    # The debug log format has lines like:  [Skills] authoring, brainstorming, ...
    # wrapped at terminal width, with ANSI escapes between.
    read -r SKILLS_RAW PROMPTS_RAW EXTS_RAW <<< $(python3 -c "
import re
with open('$DEBUG_LOG', 'r') as f:
    text = f.read()
# Remove ANSI escapes
clean = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)
# Remove terminal width annotations like [0] (w=189)
clean = re.sub(r'\[\d+\]\s*\(w=\d+\)', '', clean)
# Collect lines by section header
sec = None
out = {'Skills': '', 'Prompts': '', 'Extensions': ''}
for line in clean.split('\n'):
    line = line.strip().strip('\"')
    if 'Skills' in line and ('[' in line or line.startswith('Skills')):
        sec = 'Skills'; out[sec] = ''
    elif 'Prompts' in line and ('[' in line or line.startswith('Prompts')):
        sec = 'Prompts'; out[sec] = ''
    elif 'Extensions' in line and ('[' in line or line.startswith('Extensions')):
        sec = 'Extensions'; out[sec] = ''
    elif sec and line and not any(s in line for s in ['Skills','Prompts','Extensions','Context','Available','Update']):
        out[sec] += line + ' '
print(out['Skills'].strip())
print(out['Prompts'].strip())
print(out['Extensions'].strip())
" 2>/dev/null) || SKILLS_RAW="" PROMPTS_RAW="" EXTS_RAW=""

    if [ -n "$SKILLS_RAW" ]; then
      SKILL_COUNT=$(echo "$SKILLS_RAW" | tr ',' '\n' | wc -w)
      PROMPT_COUNT=$(echo "$PROMPTS_RAW" | tr ',' '\n' | wc -w)
      EXT_COUNT=$(echo "$EXTS_RAW" | tr ',' '\n' | wc -w)
      echo "  Skills:    ${SKILL_COUNT} loaded"
      echo "  Prompts:   ${PROMPT_COUNT} loaded"
      echo "  Extensions: ${EXT_COUNT} loaded"
      [ "$SKILL_COUNT" -gt 30 ] && warn "High skill count (${SKILL_COUNT})"
      [ "$SKILL_COUNT" -gt 20 ] && [ "$SKILL_COUNT" -le 30 ] && warn "Moderate skill count (${SKILL_COUNT})"
      [ "$SKILL_COUNT" -le 20 ] && pass "Skill count: ${SKILL_COUNT}"
      echo ""
      dim "  Skills:     ${SKILLS_RAW}"
      dim "  Prompts:    ${PROMPTS_RAW}"
      dim "  Extensions: ${EXTS_RAW}"
    else
      warn "Could not parse startup profile from pi-debug.log"
    fi
  elif [ -f "$DEBUG_LOG" ]; then
    warn "Install python3 to parse pi-debug.log startup profile"
  else
    warn "pi-debug.log not found (run 'pi' to generate it)"
  fi
fi

# ────────────────────────────────────────────────────────────────────────────
# SECTION 2: Catalog Tax + Skill Size Ranking
# ────────────────────────────────────────────────────────────────────────────
header "2. Skill Size & Catalog Tax"

declare -a ROWS=()
declare -a FAT_SKILLS=()
declare -a LONG_DESCS=()
total_desc_tokens=0
total_skills=0

for pair in "personal:$AGENT" "work:$WORK_AGENT"; do
  sc="${pair%%:*}"; sdir="${pair#*:}"
  [ -d "$sdir/skills" ] || continue
  for sd in "$sdir/skills"/*/; do
    [ -d "$sd" ] || continue
    nm=$(basename "$sd"); total_skills=$((total_skills + 1))
    [ -f "$sd/SKILL.md" ] || continue
    ct=$(<"$sd/SKILL.md")
    d=$(echo "$ct" | sed -n '/^description: /{s/^description: //;p;}' | head -1)
    dc=${#d}; dt=$(est_tokens "$d"); total_desc_tokens=$((total_desc_tokens + dt))
    bd=$(echo "$ct" | sed -n '/^---$/,/^---$/!p' | sed -n '/^---$/,$p' | tail -n +2)
    [ -z "$bd" ] && bd="$ct"
    bl=$(echo "$bd" | wc -l); bt=$(est_tokens "$bd")
    # bloat score: desc_tokens (always-on) + body_tokens/10 (per-activation)
    bs=$(( dt + bt / 10 ))
    ROWS+=("$bs|$nm|$dt|$bl|$bt|$sc")
    [ "$bt" -gt 5000 ] && FAT_SKILLS+=("$nm: ${bl}L / ~${bt} tok")
    [ "$dc" -gt 200 ] && LONG_DESCS+=("$nm (${dc} chars / ~${dt} tok)")
  done
done

# Sort by bloat score descending
IFS=$'\n' SORTED=($(sort -t'|' -k1 -rn <<< "${ROWS[*]}")); unset IFS

# Summary line
echo -e "  ${BOLD}Skills scanned:${RESET} ${total_skills}  |  ${BOLD}Catalog tax:${RESET} ~${total_desc_tokens} tokens (sum of descriptions)"
if [ "$total_desc_tokens" -gt 5000 ]; then
  fail "Catalog tax HIGH (target < 3000)"; STATUS=1
elif [ "$total_desc_tokens" -gt 3000 ]; then
  warn "Catalog tax MODERATE (target < 3000)"
else
  pass "Catalog tax within budget"
fi

# Table (always show)
echo ""
printf "  %-30s %8s %10s %8s %8s\n" "Skill" "Desc.Tok" "Body Lines" "Body.Tok" "Scope"
rul
for e in "${SORTED[@]}"; do
  IFS='|' read -r bs nm dt bl bt sc <<< "$e"
  flag=" "
  [ "$bt" -gt 5000 ] && flag="${RED}⚑${RESET}"
  [ "$bt" -le 5000 ] && [ "$bt" -gt 2000 ] && flag="${YELLOW}~${RESET}"
  printf "  ${flag}%-28s %8d %10d %8d %8s\n" "$nm" "$dt" "$bl" "$bt" "$sc"
done

# Warnings
[ ${#FAT_SKILLS[@]} -gt 0 ] && echo "" && warn "${#FAT_SKILLS[@]} fat skills (>5k tokens):" && for s in "${FAT_SKILLS[@]}"; do dim "  - $s"; done
[ ${#LONG_DESCS[@]} -gt 0 ] && echo "" && warn "${#LONG_DESCS[@]} long descriptions (>200 chars):" && for s in "${LONG_DESCS[@]}"; do dim "  - $s"; done

# ────────────────────────────────────────────────────────────────────────────
# SECTION 3: Telemetry Trends
# ────────────────────────────────────────────────────────────────────────────
header "3. Telemetry Trends (pi-telemetry.db)"

if [ -n "$SQLITE_CMD" ] && [ -f "$TELEMETRY_DB" ]; then
  # --- 3a. Weekly cost (both origins) ---
  echo -e "  ${BOLD}Daily cost - last 14 days${RESET}"
  printf "  %-12s %5s %6s %7s %9s %5s %8s %6s\n" "Date" "Sess" "Turns" "In/Tok" "Out/Tok" "Comp" "Cost" "Scope"
  rul
  $SQLITE_CMD -separator '|' "$TELEMETRY_DB" "
    SELECT substr(last_ts,1,10) AS d,
           COUNT(*) AS n,
           SUM(turns),
           SUM(input_tok),
           SUM(output_tok),
           SUM(compactions),
           ROUND(SUM(cost_total),4),
           CASE WHEN SUM(cost_total) > 0 THEN origin ELSE '' END
    FROM sessions
    WHERE total_tok > 0 AND last_ts >= date('now','-14 days')
    GROUP BY substr(last_ts,1,10), origin
    ORDER BY d DESC, origin;
  " 2>/dev/null | while IFS='|' read -r d n turs inp outp comp cost org; do
    if [ "$(echo "$cost > 10" | bc -l 2>/dev/null)" = "1" ]; then
      printf "  ${RED}%-12s %5s %6s %7s %9s %5s %8s %6s${RESET}\n" "$d" "$n" "$turs" "$inp" "$outp" "$comp" "\$$cost" "$org"
    elif [ "$(echo "$cost > 1" | bc -l 2>/dev/null)" = "1" ]; then
      printf "  ${YELLOW}%-12s %5s %6s %7s %9s %5s %8s %6s${RESET}\n" "$d" "$n" "$turs" "$inp" "$outp" "$comp" "\$$cost" "$org"
    else
      printf "  %-12s %5s %6s %7s %9s %5s %8s %6s\n" "$d" "$n" "$turs" "$inp" "$outp" "$comp" "\$$cost" "$org"
    fi
  done

  # --- 3b. Compactions ---
  echo ""
  echo -e "  ${BOLD}Compaction analysis (bloat symptom)${RESET}"
  read -r HC TS TC TT <<< $($SQLITE_CMD -separator ' ' "$TELEMETRY_DB" "
    SELECT COALESCE(SUM(CASE WHEN compactions>0 THEN 1 ELSE 0 END),0),
           COUNT(*),
           COALESCE(SUM(compactions),0),
           COALESCE(SUM(turns),0)
    FROM sessions WHERE total_tok > 0;
  " 2>/dev/null)
  printf "  %-30s %s / %s\n" "Sessions with compactions:" "$HC" "$TS"
  printf "  %-30s %s\n" "Total compactions:" "$TC"
  if [ "$TT" -gt 0 ] && [ "$TC" -gt 0 ]; then
    CPR=$(( TC * 100 / TT ))
    printf "  %-30s %d/100 turns\n" "Compaction rate:" "$CPR"
    [ "$CPR" -gt 20 ] && fail "High compaction rate (${CPR}/100)" && STATUS=1
    [ "$CPR" -le 20 ] && [ "$CPR" -gt 10 ] && warn "Moderate compaction (${CPR}/100)"
    [ "$CPR" -le 10 ] && pass "Compaction rate ${CPR}/100 turns"
  fi

  # --- 3c. Cost spikes ---
  echo ""
  echo -e "  ${BOLD}Cost analysis${RESET}"
  AVG_C=$($SQLITE_CMD "$TELEMETRY_DB" "SELECT ROUND(AVG(cost_total),4) FROM sessions WHERE cost_total>0;" 2>/dev/null || echo "0")
  SPIKE=$($SQLITE_CMD "$TELEMETRY_DB" "
    SELECT COUNT(*) FROM sessions
    WHERE cost_total > 3 * (SELECT AVG(cost_total) FROM sessions WHERE cost_total>0);
  " 2>/dev/null || echo "0")
  printf "  %-30s \$%s\n" "Avg session cost:" "$AVG_C"
  printf "  %-30s %s\n" "Sessions >3x avg:" "$SPIKE"
  [ "$SPIKE" -gt 3 ] && warn "${SPIKE} cost spikes detected"

  # --- 3d. Most recent 3 sessions (detail) ---
  if [ "$MODE" != "quick" ]; then
    echo ""
    echo -e "  ${BOLD}Last 3 sessions${RESET}"
    printf "  %-12s %-22s %5s %7s %8s %5s %7s\n" "Date" "Model" "Turns" "In/Tok" "Out/Tok" "Comp" "Cost"
    rul
    $SQLITE_CMD -separator '|' "$TELEMETRY_DB" "
      SELECT substr(last_ts,1,10), model, turns, input_tok, output_tok, compactions, ROUND(cost_total,4)
      FROM sessions WHERE total_tok>0 ORDER BY last_ts DESC LIMIT 3;
    " 2>/dev/null | while IFS='|' read -r d m t i o cp c; do
      printf "  %-12s %-22s %5s %7s %8s %5s %7s\n" "$d" "$m" "$t" "$i" "$o" "$cp" "\$$c"
    done
  fi
else
  warn "pi-telemetry.db not found or nixpkgs#sqlite unavailable"
  [ -z "$SQLITE_CMD" ] && dim "  Install: nix run nixpkgs#sqlite"
fi

# ────────────────────────────────────────────────────────────────────────────
# SECTION 4: Recommendations
# ────────────────────────────────────────────────────────────────────────────
header "4. Recommendations"

[ ${#FAT_SKILLS[@]} -gt 0 ] && echo "  • Trim these skills (target < 5k tokens / ~300 lines):" && for s in "${FAT_SKILLS[@]}"; do echo "    - $s"; done
[ "$total_desc_tokens" -gt 3000 ] && echo "  • Shorten descriptions (target < 200 chars each, total < 3k tokens)"
echo "  • Run weekly:  ${DIM}./harness-audit.sh --quick${RESET}"
echo "  • Re-check after model updates (static scores go stale per ACES paper)"
echo ""

# ─── Bloat Score ──────────────────────────────────────────────────────────
header "Bloat Score"
bt="${#FAT_SKILLS[@]}"
bloat_score=0
[ "$total_desc_tokens" -gt 5000 ] && bloat_score=$((bloat_score + 3))
[ "$total_desc_tokens" -gt 3000 ] && bloat_score=$((bloat_score + 2))
[ "$total_desc_tokens" -gt 1000 ] && bloat_score=$((bloat_score + 1))
[ "$bt" -gt 5 ] && bloat_score=$((bloat_score + 3))
[ "$bt" -gt 2 ] && bloat_score=$((bloat_score + 2))
[ "$bt" -gt 0 ] && bloat_score=$((bloat_score + 1))

if [ "$bloat_score" -ge 7 ]; then
  fail "Bloat Score: ${bloat_score}/10 — HIGH (needs attention)"
  STATUS=1
elif [ "$bloat_score" -ge 4 ]; then
  warn "Bloat Score: ${bloat_score}/10 — MODERATE (consider cleanup)"
else
  pass "Bloat Score: ${bloat_score}/10 — LOW (harness is lean)"
fi
echo ""

exit $STATUS
