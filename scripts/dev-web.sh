#!/usr/bin/env bash
# Start the AI Workspace PWA development environment.
# Runs both the FastAPI backend and the Vite dev server.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo " AI Workspace PWA Dev Server"
echo "=============================="
echo ""

# 1. Start the API server in the background
echo "[1/2] Starting FastAPI backend on :8000..."
cd "$PROJECT_DIR"
source .venv/bin/activate
python -m api.main &
API_PID=$!

# 2. Start the Vite dev server
echo "[2/2] Starting Vite frontend on :5173..."
cd "$PROJECT_DIR/web"
npx vite --host 0.0.0.0 --port 5173 &
VITE_PID=$!

echo ""
echo " Frontend:  http://localhost:5173"
echo " API:       http://localhost:8000"
echo " API Docs:  http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers."

# Cleanup on exit
trap "kill $API_PID $VITE_PID 2>/dev/null; exit 0" SIGINT SIGTERM

# Wait for either to exit
wait
