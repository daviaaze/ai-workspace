#!/usr/bin/env bash
# AI Workspace — Bootstrap script
# Run once after NixOS rebuild to start all background services.
set -euo pipefail

echo "╔══════════════════════════════════════════════════╗"
echo "║     AI Workspace — Background Services          ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ─── 1. Check prerequisites ───
echo "1. Checking prerequisites..."

if ! systemctl is-active --quiet postgresql; then
    echo "   ❌ PostgreSQL is not running"
    exit 1
fi
echo "   ✅ PostgreSQL"

if ! systemctl is-active --quiet ollama; then
    echo "   ⚠️  Ollama is not running (models won't be available)"
else
    echo "   ✅ Ollama"
fi

echo ""

# ─── 2. Initialize database (if needed) ───
echo "2. Initializing database..."

if psql -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw ai_workspace; then
    echo "   ✅ ai_workspace database exists"
else
    echo "   Creating ai_workspace database..."
    createdb ai_workspace 2>/dev/null || sudo -u postgres createdb ai_workspace
    echo "   ✅ Created"
fi

echo ""

# ─── 3. Run aiw init (creates tables, directories) ───
echo "3. Initializing AI Workspace..."
aiw init 2>/dev/null || echo "   ⚠️  aiw not found in PATH (will work after rebuild)"

echo ""

# ─── 4. Enable and start systemd services ───
echo "4. Enabling background services..."

SERVICES=(
    "aiw-worker.service"
    "aiw-sync.timer"
    "aiw-vault-sync.timer"
    "aiw-telemetry-snapshot.timer"
)

for svc in "${SERVICES[@]}"; do
    if systemctl --user is-enabled "$svc" 2>/dev/null || systemctl is-enabled "$svc" 2>/dev/null; then
        echo "   ✅ $svc (already enabled)"
    else
        # Try user first, then system
        if systemctl --user enable "$svc" 2>/dev/null; then
            systemctl --user start "$svc" 2>/dev/null || true
            echo "   ✅ $svc (user)"
        elif sudo systemctl enable "$svc" 2>/dev/null; then
            sudo systemctl start "$svc" 2>/dev/null || true
            echo "   ✅ $svc (system)"
        else
            echo "   ⚠️  $svc (could not enable — will work after rebuild)"
        fi
    fi
done

echo ""

# ─── 5. Status report ───
echo "5. Status report:"
echo ""

echo "   Services:"
systemctl --user status aiw-worker.service 2>/dev/null | head -3 || \
    systemctl status aiw-worker.service 2>/dev/null | head -3 || \
    echo "   ⚠️  aiw-worker not found yet (run after nixos-rebuild)"

echo ""
echo "   Timers:"
systemctl --user list-timers 'aiw-*' 2>/dev/null || \
    systemctl list-timers 'aiw-*' 2>/dev/null || \
    echo "   ⚠️  No timers yet"

echo ""
echo "   Sync status:"
aiw sync status 2>/dev/null || echo "   ⚠️  aiw CLI not available yet"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  ✅ Bootstrap complete!                         ║"
echo "║                                                 ║"
echo "║  Running in background:                         ║"
echo "║    aiw-worker        — tasks + schedules        ║"
echo "║    aiw-sync          — KB sync (every 30min)    ║"
echo "║    aiw-vault-sync    — Vault git (every hour)   ║"
echo "║    aiw-telemetry     — Metrics (9:00 BRT)       ║"
echo "║                                                 ║"
echo "║  Check logs:  journalctl -u aiw-worker -f       ║"
echo "║  Sync now:    aiw sync both                     ║"
echo "║  Status:      aiw sync status                   ║"
echo "╚══════════════════════════════════════════════════╝"
