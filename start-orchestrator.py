#!/usr/bin/env python3
"""Start the Pi Orchestrator server."""
import sys
from pathlib import Path

# Ensure the project root is on sys.path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from pi_orchestrator.main import app, enable_dashboard_serve, DASHBOARD_DIST
import uvicorn, sys

if __name__ == "__main__":
    if "--serve-dashboard" in sys.argv and DASHBOARD_DIST.exists():
        enable_dashboard_serve()
        print(f"Serving dashboard from {DASHBOARD_DIST}")
    uvicorn.run(app, host="127.0.0.1", port=8420, log_level="info")
