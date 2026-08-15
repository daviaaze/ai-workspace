#!/usr/bin/env bash
# Setup job-tracker skill: create data dir, install CLI scripts, seed CV from existing analysis.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
DATA_DIR="${JOB_TRACKER_DATA:-$HOME/.pi/data/job-tracker}"
BIN_DIR="$HOME/.local/bin"

echo "🔧 Setting up job-tracker skill..."

# Create data directory
mkdir -p "$DATA_DIR"
echo "📁 Data directory: $DATA_DIR"

# Create empty YAML files if they don't exist
for f in applications.yaml linkedin-inbound.yaml companies.yaml; do
    if [ ! -f "$DATA_DIR/$f" ]; then
        echo "[]" > "$DATA_DIR/$f"
        echo "  Created $f"
    fi
done

# Create config if missing
if [ ! -f "$DATA_DIR/config.yaml" ]; then
    cat > "$DATA_DIR/config.yaml" << 'EOF'
target_roles:
  - Senior Backend Engineer
  - Full Stack Engineer
  - Senior Software Engineer
locations:
  - Remote
  - Sydney
salary_min: 150000
EOF
    echo "  Created config.yaml"
fi

# Seed CV from existing JIRA analysis if available
if [ ! -f "$DATA_DIR/cv.md" ]; then
    JIRA_ANALYSIS="$HOME/Projects/Lux/ai-workspace/Development/Reviews/JIRA-3-YEARS-ANALYSIS.md"
    if [ -f "$JIRA_ANALYSIS" ]; then
        # Extract the CV bullets section
        sed -n '/^## Bullets de CV redigidos/,/^## Próximos passos/p' "$JIRA_ANALYSIS" > "$DATA_DIR/cv.md"
        echo "  ✅ CV seeded from JIRA analysis"
    else
        cat > "$DATA_DIR/cv.md" << 'EOF'
# CV — Davi Azevedo

<!-- Paste your CV here or import from a file -->

## Experience

### Senior Software Engineer — Luxury Escapes
- Built the hotel partner self-service platform (Extranet) serving 500+ agencies
- Co-architected the Agent Hub B2B platform with commission rules engine
- Delivered the Car Hire vertical end-to-end (search → booking → emails)

## Skills
- TypeScript, Node.js, Python, Rust
- Distributed systems, PostgreSQL, Redis, Docker
- AWS, microservices, REST/GraphQL APIs
EOF
        echo "  Created cv.md (template)"
    fi
fi

# Install CLI scripts
mkdir -p "$BIN_DIR"
for cmd in aiw-job aiw-job-linkedin aiw-job-fit aiw-job-company aiw-job-dashboard; do
    if [ -f "$SCRIPT_DIR/$cmd" ]; then
        cp "$SCRIPT_DIR/$cmd" "$BIN_DIR/$cmd"
        chmod +x "$BIN_DIR/$cmd"
        echo "  Installed $cmd → $BIN_DIR/$cmd"
    fi
done

echo ""
echo "✅ job-tracker skill installed!"
echo ""
echo "Quick start:"
echo "  aiw-job init           # re-initialize if needed"
echo "  aiw-job add --company 'Acme' --role 'Backend Engineer' --status applied"
echo "  aiw-job list           # view pipeline"
echo "  aiw-job stats          # pipeline statistics"
echo "  aiw-job-dashboard      # full dashboard"
echo ""
echo "Data: $DATA_DIR"
echo "Bin:  $BIN_DIR"
