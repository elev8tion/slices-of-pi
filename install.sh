#!/usr/bin/env bash
set -e

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║   Slice of Pi — Install & Start      ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON="${PYTHON:-python3}"

# ── Python dependencies ─────────────────────────────────────────
echo "→ Installing Python dependencies..."
$PYTHON -m pip install fastapi uvicorn pydantic apscheduler pyyaml cryptography aiohttp -q 2>/dev/null || true

# ── Dashboard build ──────────────────────────────────────────────
echo "→ Building dashboard..."
cd "$ROOT/dashboard"
npm install --silent 2>/dev/null || true
npx vite build 2>&1 | tail -1

# ── Start orchestrator ───────────────────────────────────────────
echo "→ Starting orchestrator on http://localhost:8420"
cd "$ROOT"
$PYTHON start-orchestrator.py &
ORCH_PID=$!

# ── Start dashboard dev server ───────────────────────────────────
echo "→ Starting dashboard on http://localhost:5173"
cd "$ROOT/dashboard"
npx vite --host 127.0.0.1 --port 5173 &
VITE_PID=$!

sleep 2
echo ""
echo "  ✅ Slice of Pi ready!"
echo "     Dashboard:     http://localhost:5173"
echo "     API:           http://localhost:8420/health"
echo "     API Docs:      http://localhost:8420/docs"
echo ""
echo "  Press Ctrl+C to stop both services"
echo ""

trap "kill $ORCH_PID $VITE_PID 2>/dev/null; exit" INT TERM
wait
