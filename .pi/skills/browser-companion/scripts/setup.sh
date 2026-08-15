#!/usr/bin/env bash
# Setup browser-companion skill
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"

echo "🔧 Setting up browser-companion skill..."

mkdir -p "$BIN_DIR"
for cmd in browser-companion browser-companion-li; do
    if [ -f "$SCRIPT_DIR/$cmd" ]; then
        cp "$SCRIPT_DIR/$cmd" "$BIN_DIR/$cmd"
        chmod +x "$BIN_DIR/$cmd"
        echo "  Installed $cmd"
    fi
done

# Install Playwright browsers (Chromium for CDP)
echo ""
echo "🌐 Installing Playwright Chromium..."
nix-shell -p python3Packages.playwright --run "playwright install chromium" 2>&1 || true

echo ""
echo "✅ browser-companion installed!"
echo ""
echo "Quick start:"
echo "  1. Start browser with remote debugging:"
echo "     zen --remote-debugging-port=9222"
echo "        or"
echo "     firefox --remote-debugging-port=9222"
echo ""
echo "  2. Navigate pages:"
echo "     browser-companion list"
echo "     browser-companion cdp --url 'https://linkedin.com/jobs/view/123' --action text"
echo "     browser-companion-li search --keywords 'Backend Engineer' --location 'Remote'"
echo ""
echo "  3. Without browser running (cookie mode):"
echo "     browser-companion cookies --browser zen --domain linkedin.com"
echo "     browser-companion session --browser zen --domain linkedin.com --url '...'"
