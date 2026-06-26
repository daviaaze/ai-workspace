#!/usr/bin/env bash
# deploy-pi-setup.sh — DEPRECATED
#
# This script is a legacy wrapper. Use deploy.sh instead:
#
#   ./pi-setup/deploy.sh          # interactive (with backup + dry-run)
#   ./pi-setup/deploy.sh --dry-run
#
# This wrapper simply delegates to deploy.sh for backward compatibility.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "[deploy-pi-setup.sh] DEPRECATED — use deploy.sh instead" >&2
exec "$SCRIPT_DIR/deploy.sh" "$@"
