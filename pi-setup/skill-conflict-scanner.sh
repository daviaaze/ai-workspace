#!/usr/bin/env bash
# skill-conflict-scanner.sh — detecta sobreposição entre skills via n-gram Jaccard.
# Token-free — offline, sem LLM.
# Dependências: bash, coreutils, python3.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
AGENT="${HOME}/.pi/agent"
WORK_AGENT="${HOME}/.pi/agent-work"
THRESHOLD=0.30
MODE="full"

BOLD='\033[1m'; DIM='\033[2m'
RED='\033[31m'; GREEN='\033[32m'; YELLOW='\033[33m'
CYAN='\033[36m'; MAGENTA='\033[35m'; RESET='\033[0m'

pass() { printf "  ${GREEN}✓${RESET} %s\n" "$*"; }
warn() { printf "  ${YELLOW}⚠${RESET} %s\n" "$*"; }
fail() { printf "  ${RED}✗${RESET} %s\n" "$*"; }
header() { printf "\n${BOLD}${MAGENTA}══════ %s ══════${RESET}\n" "$*"; }
rul()  { printf "  ${DIM}────────────────────────────────────────${RESET}\n"; }

usage() { cat <<EOF; exit 0
Usage: $(basename "$0") [OPTION]
  --threshold F   Jaccard threshold (default: 0.30)
  --csv           CSV output
  --help
EOF
}

for arg in "$@"; do
  case "$arg" in --threshold=*) THRESHOLD="${arg#*=}" ;; --csv) MODE="csv" ;; --help) usage ;; esac
done

# ─── Coleta skills → JSON via Python ─────────────────────────────────────
# Escreve um script Python temporário pra evitar problemas de escaping
PY_SCRIPT=$(mktemp); trap "rm -f $PY_SCRIPT" EXIT

cat > "$PY_SCRIPT" << 'PYEOF'
import json, os, re, sys

THRESHOLD = float(sys.argv[1]) if len(sys.argv) > 1 else 0.30

def collect(scope, base):
    skills = []
    sdir = os.path.join(base, 'skills')
    if not os.path.isdir(sdir):
        return skills
    for name in sorted(os.listdir(sdir)):
        sk_file = os.path.join(sdir, name, 'SKILL.md')
        if not os.path.isfile(sk_file):
            continue
        with open(sk_file) as f:
            text = f.read()
        desc = ''
        m = re.search(r'^description:\s*(.+)$', text, re.MULTILINE)
        if m:
            desc = m.group(1).strip()
            desc = desc.strip('"')  # remove surrounding quotes if any
        if not desc:
            desc = name
        skills.append({'name': name, 'desc': desc, 'scope': scope})
    return skills

all_skills = collect('personal', os.path.expanduser('~/.pi/agent'))
all_skills += collect('work', os.path.expanduser('~/.pi/agent-work'))

def trigrams(s):
    s = re.sub(r'[^a-z0-9]', '', s.lower())
    return set(s[i:i+3] for i in range(len(s)-2))

conflicts = []
near_conflicts = []
for i in range(len(all_skills)):
    for j in range(i+1, len(all_skills)):
        t1 = trigrams(all_skills[i]['desc'])
        t2 = trigrams(all_skills[j]['desc'])
        if not t1 or not t2:
            continue
        inter = len(t1 & t2)
        union = len(t1 | t2)
        sim = inter / union if union > 0 else 0.0
        entry = (all_skills[i]['name'], all_skills[j]['name'],
                 all_skills[i]['scope'], all_skills[j]['scope'], round(sim, 4))
        if sim > THRESHOLD:
            conflicts.append(entry)
        elif sim > THRESHOLD * 0.7:
            near_conflicts.append(entry)

# Output all data as JSON
print(json.dumps({
    'total': len(all_skills),
    'pairs': len(all_skills) * (len(all_skills)-1) // 2,
    'conflicts': conflicts,
    'near': near_conflicts
}))
PYEOF

RESULT=$(python3 "$PY_SCRIPT" "$THRESHOLD" 2>/dev/null)

# ─── CSV mode ─────────────────────────────────────────────────────────────
if [ "$MODE" = "csv" ]; then
  echo "$RESULT" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print('skill_a,skill_b,scope_a,scope_b,jaccard,category')
for a,b,sa,sb,s in data['conflicts']:
    print(f'{a},{b},{sa},{sb},{s},conflict')
for a,b,sa,sb,s in data['near']:
    print(f'{a},{b},{sa},{sb},{s},near')
"
  exit 0
fi

# ─── Full report ──────────────────────────────────────────────────────────
TOTAL=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['total'])")
PAIRS=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['pairs'])")
CFLEN=$(echo "$RESULT" | python3 -c "import json,sys; print(len(json.load(sys.stdin)['conflicts']))")
NRLEN=$(echo "$RESULT" | python3 -c "import json,sys; print(len(json.load(sys.stdin)['near']))")

echo -e "${BOLD}${MAGENTA}"
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║     Skill Routing Conflict Scanner            ║"
echo "  ║     n-gram Jaccard — token-free offline       ║"
echo "  ╚══════════════════════════════════════════════╝"
echo -e "${RESET}"
echo "  Skills: $TOTAL  |  Pairs: $PAIRS  |  Threshold: $THRESHOLD"
echo ""

header "CONFLITOS (Jaccard > $THRESHOLD)"
if [ "$CFLEN" -eq 0 ]; then
  pass "Nenhum conflito"
else
  printf "  %-30s %-30s %8s %8s %8s\n" "Skill A" "Skill B" "Scope A" "Scope B" "Jaccard"
  rul
  echo "$RESULT" | python3 -c "
import json, sys
for a,b,sa,sb,s in json.load(sys.stdin)['conflicts']:
    print(f'  \033[31m{a:<30} {b:<30} {sa:>8} {sb:>8} {s:>8.4f}\033[0m')
"
fi

header "BORDERLINE"
if [ "$NRLEN" -eq 0 ]; then
  pass "Nenhum borderline"
else
  printf "  %-30s %-30s %8s %8s %8s\n" "Skill A" "Skill B" "Scope A" "Scope B" "Jaccard"
  rul
  echo "$RESULT" | python3 -c "
import json, sys
for a,b,sa,sb,s in json.load(sys.stdin)['near']:
    print(f'  \033[33m{a:<30} {b:<30} {sa:>8} {sb:>8} {s:>8.4f}\033[0m')
"
fi

echo ""
echo -e "${BOLD}Recomendações:${RESET}"
echo "  • Conflitos: adicione palavras-chave distintas nas descriptions"
echo "  • CI: ./skill-conflict-scanner.sh --threshold 0.30"
echo ""

exit "$CFLEN"
