"""
Pi Orchestrator configuration — local single-operator, no Docker, no Redis.

Not a multi-tenant or SaaS configuration surface (see docs/PRODUCT_INTENT.md).
All paths resolve relative to ~/.pi/agent/.
All settings are environment-variable overridable.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any

# ── Paths ──────────────────────────────────────────────────────────

PI_HOME = Path(os.path.expanduser("~/.pi"))
PI_AGENT_DIR = PI_HOME / "agent"
PI_SESSIONS_DIR = PI_AGENT_DIR / "sessions"
PI_MANAGED_SESSIONS_DIR = PI_SESSIONS_DIR / "managed"
PI_SCHEDULED_SESSIONS_DIR = PI_SESSIONS_DIR / "scheduled"
PI_EXTENSIONS_DIR = PI_AGENT_DIR / "extensions"
PI_SKILLS_DIR = PI_AGENT_DIR / "skills"
PI_AGENTS_CONFIG_DIR = PI_HOME / "agents"
PI_PROMPT_TEMPLATES_DIR = PI_AGENT_DIR / "prompt-templates"
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
DEFAULT_TOOLS = ["read", "bash", "edit", "write", "web_search", "web_scrape", "analyze_image"]
SESSION_TIMEOUT_SECONDS = int(os.getenv("PI_SESSION_TIMEOUT", "900"))


def ensure_directories() -> None:
    """Create required directories if they don't exist."""
    for d in [
        PI_MANAGED_SESSIONS_DIR,
        PI_SCHEDULED_SESSIONS_DIR,
    ]:
        d.mkdir(parents=True, exist_ok=True)


# ── Profile Configuration ────────────────────────────────────────

ORCHESTRATOR_CONFIG = PI_AGENT_DIR / "orchestrator.json"


def load_orchestrator_config() -> dict:
    """Load orchestrator config, auto-creating if missing."""
    if not ORCHESTRATOR_CONFIG.exists():
        default = {"current_profile": "default", "profiles": {"default": {}}}
        save_orchestrator_config(default)
        return default
    try:
        return json.loads(ORCHESTRATOR_CONFIG.read_text())
    except (json.JSONDecodeError, OSError):
        return {"current_profile": "default", "profiles": {"default": {}}}


def save_orchestrator_config(config: dict) -> None:
    """Save orchestrator config with secure permissions."""
    ORCHESTRATOR_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    ORCHESTRATOR_CONFIG.write_text(json.dumps(config, indent=2) + "\n")
    os.chmod(ORCHESTRATOR_CONFIG, stat.S_IRUSR | stat.S_IWUSR)


def get_profile_value(key: str, default: Any = None, profile: str | None = None) -> Any:
    """Get a config value. Env var PI_{KEY.upper()} wins over profile config."""
    env_key = f"PI_{key.upper()}"
    env_val = os.environ.get(env_key)
    if env_val is not None:
        return env_val
    config = load_orchestrator_config()
    profile_name = profile or config.get("current_profile", "default")
    profile_data = config.get("profiles", {}).get(profile_name, {})
    return profile_data.get(key, default)


def set_profile_key(key: str, value: Any, profile: str | None = None) -> None:
    """Set a key in the specified or active profile."""
    config = load_orchestrator_config()
    profile_name = profile or config.get("current_profile", "default")
    config.setdefault("profiles", {}).setdefault(profile_name, {})[key] = value
    save_orchestrator_config(config)


def list_profiles() -> list[dict]:
    """List all profiles with metadata."""
    config = load_orchestrator_config()
    current = config.get("current_profile", "default")
    profiles = config.get("profiles", {})
    result = []
    for name, data in profiles.items():
        result.append({
            "name": name,
            "default_model": data.get("default_model", ""),
            "active": name == current,
        })
    return result


def set_active_profile(name: str) -> bool:
    """Switch active profile. Returns False if doesn't exist."""
    config = load_orchestrator_config()
    if name not in config.get("profiles", {}):
        return False
    config["current_profile"] = name
    save_orchestrator_config(config)
    return True


def remove_profile(name: str) -> bool:
    """Remove a profile. Returns False if doesn't exist."""
    config = load_orchestrator_config()
    profiles = config.get("profiles", {})
    if name not in profiles:
        return False
    del profiles[name]
    if config.get("current_profile") == name:
        config["current_profile"] = next(iter(profiles), "default")
    save_orchestrator_config(config)
    return True
