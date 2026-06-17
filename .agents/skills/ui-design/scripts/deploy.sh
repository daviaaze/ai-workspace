#!/usr/bin/env bash
# deploy-ui-design.sh
# Deploy the UI design skill and pi extension to their locations.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PI_AGENT_DIR="${PI_DIR:-$HOME/.pi/agent}"
PROJECT_DIR="$(cd "$SKILL_DIR/../.." && pwd)"

echo "🎨 Deploying UI Design Skill + MCP Integration"
echo "   Project: $PROJECT_DIR"
echo "   Skill:   $SKILL_DIR"

# ── 1. Deploy Skill to project-local .agents/skills ──
echo ""
echo "📦 [1/3] Deploying skill to project..."
mkdir -p "$PROJECT_DIR/.agents/skills/ui-design"
cp "$SKILL_DIR/SKILL.md" "$PROJECT_DIR/.agents/skills/ui-design/SKILL.md"
mkdir -p "$PROJECT_DIR/.agents/skills/ui-design/references"
cp "$SKILL_DIR/references/"*.md "$PROJECT_DIR/.agents/skills/ui-design/references/"
echo "   ✅ Skill deployed to .agents/skills/ui-design/"

# ── 2. Deploy Extension to pi extensions ──
echo ""
echo "🔌 [2/3] Deploying pi extension..."
mkdir -p "$PI_AGENT_DIR/extensions"
cp "$SKILL_DIR/scripts/ui-design-extension.ts" "$PI_AGENT_DIR/extensions/ui-design.ts"
echo "   ✅ Extension deployed to $PI_AGENT_DIR/extensions/ui-design.ts"

# ── 3. Verify MCP Server ──
echo ""
echo "🔍 [3/3] Verifying MCP server tools..."
MCP_SERVER="$PROJECT_DIR/src/ai_workspace/mcp_server/server.py"
if python -c "
import ast, sys
with open('$MCP_SERVER') as f:
    tree = ast.parse(f.read())
tools = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('handle_ui_')]
print(f'UI MCP tools: {tools}')
sys.exit(0 if tools else 1)
" 2>/dev/null; then
    echo "   ✅ MCP server has UI design tools"
else
    echo "   ⚠️  MCP server check failed (non-blocking). Run 'python -m ai_workspace.mcp_server' to test."
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ UI Design Skill deployed!"
echo ""
echo "What was installed:"
echo "  Skill:     .agents/skills/ui-design/SKILL.md"
echo "  References: .agents/skills/ui-design/references/"
echo "  Extension:  ~/.pi/agent/extensions/ui-design.ts"
echo "  MCP Tools:  src/ai_workspace/mcp_server/server.py (+3 UI tools)"
echo ""
echo "To use:"
echo "  pi:        /skill:ui-design  (or just describe a UI task)"
echo "  Claude:    claude mcp add aiw-dev -- python -m ai_workspace.mcp_server"
echo "  Tools:     ui_component_pattern, ui_accessibility_check, ui_design_tokens"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
