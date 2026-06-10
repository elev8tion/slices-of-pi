"""
Pi Orchestrator configuration — single-user, no Docker, no Redis.

All paths resolve relative to ~/.pi/agent/.
All settings are environment-variable overridable.
"""

from __future__ import annotations

import os
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────

PI_HOME = Path(os.path.expanduser("~/.pi"))
PI_AGENT_DIR = PI_HOME / "agent"
PI_SESSIONS_DIR = PI_AGENT_DIR / "sessions"
PI_MANAGED_SESSIONS_DIR = PI_SESSIONS_DIR / "managed"
PI_SCHEDULED_SESSIONS_DIR = PI_SESSIONS_DIR / "scheduled"
PI_EXTENSIONS_DIR = PI_AGENT_DIR / "extensions"
PI_SKILLS_DIR = PI_AGENT_DIR / "skills"
PI_AGENTS_CONFIG_DIR = PI_HOME / "agents"
DATABASE_PATH = PI_AGENT_DIR / "orchestrator.db"

# ── Server ─────────────────────────────────────────────────────────

HOST = os.getenv("PI_ORCHESTRATOR_HOST", "127.0.0.1")
PORT = int(os.getenv("PI_ORCHESTRATOR_PORT", "8420"))
CORS_ORIGINS = [
    "http://localhost:5173",   # Vite dev server
    "http://localhost:8420",   # Self (serving static dashboard)
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8420",
]

# ── Pi Binary ──────────────────────────────────────────────────────

# Resolved at startup from PATH or explicit env var
PI_BINARY = os.getenv("PI_BINARY", "pi")

# ── Scheduling ─────────────────────────────────────────────────────

SCHEDULE_POLL_INTERVAL = int(os.getenv("PI_SCHEDULE_POLL_INTERVAL", "30"))

# ── Session Defaults ───────────────────────────────────────────────

# Use empty string to let pi pick its default model.
# Set to a specific model like "sonnet" or "anthropic/claude-sonnet-4" to override.
DEFAULT_MODEL = os.getenv("PI_DEFAULT_MODEL", "")
DEFAULT_TOOLS = ["read", "bash", "edit", "write", "web_search"]
SESSION_TIMEOUT_SECONDS = int(os.getenv("PI_SESSION_TIMEOUT", "900"))


def ensure_directories() -> None:
    """Create required directories if they don't exist."""
    for d in [
        PI_MANAGED_SESSIONS_DIR,
        PI_SCHEDULED_SESSIONS_DIR,
    ]:
        d.mkdir(parents=True, exist_ok=True)
