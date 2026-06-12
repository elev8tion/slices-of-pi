"""
SQLite persistence layer for Pi Orchestrator.

Single-user, no connection pooling needed. All writes are synchronous
(FastAPI runs async handlers that call sync DB methods — SQLite is
single-writer anyway, so async wouldn't help).
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Fernet encryption for connector auth_state
_FERNET_KEY: bytes | None = None


def _get_fernet_key() -> bytes:
    """Get or derive a Fernet-compatible encryption key from hostname + port."""
    global _FERNET_KEY
    if _FERNET_KEY is not None:
        return _FERNET_KEY
    hostname = os.uname().nodename
    port = os.getenv("PI_ORCHESTRATOR_PORT", "8420")
    raw = hashlib.sha256(f"slice-of-pi-connector-{hostname}-{port}".encode()).digest()
    _FERNET_KEY = base64.urlsafe_b64encode(raw)
    return _FERNET_KEY


def _encrypt_value(plaintext: str) -> str:
    """Encrypt a string value using Fernet. Returns base64 ciphertext."""
    try:
        from cryptography.fernet import Fernet
        return Fernet(_get_fernet_key()).encrypt(plaintext.encode()).decode()
    except ImportError:
        return plaintext  # Fallback: store as-is if cryptography not installed


def _decrypt_value(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted string."""
    try:
        from cryptography.fernet import Fernet, InvalidToken
        return Fernet(_get_fernet_key()).decrypt(ciphertext.encode()).decode()
    except (ImportError, InvalidToken):
        return ciphertext

from typing import Optional

from .config import DATABASE_PATH, DEFAULT_TOOLS


# ═══════════════════════════════════════════════════════════════════
# Schema
# ═══════════════════════════════════════════════════════════════════

SCHEMA = """
CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    persona TEXT,
    model TEXT NOT NULL DEFAULT '',
    tools TEXT NOT NULL DEFAULT '[]',
    skills TEXT DEFAULT '[]',
    extensions TEXT DEFAULT '[]',
    system_prompt TEXT,
    git_repo TEXT,
    schedule_cron TEXT,
    profile_json TEXT DEFAULT '{"static": {}, "dynamic": []}',
    tags TEXT DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'created',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    session_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    last_active TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    agent_name TEXT NOT NULL,
    session_file TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    turns INTEGER DEFAULT 0,
    tokens_in INTEGER DEFAULT 0,
    tokens_out INTEGER DEFAULT 0,
    model TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT
);

CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    agent_name TEXT,
    event_type TEXT NOT NULL,
    event_data TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS schedules (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    cron_expression TEXT NOT NULL,
    message TEXT NOT NULL,
    model TEXT,
    max_turns INTEGER,
    timeout_seconds INTEGER,
    enabled INTEGER NOT NULL DEFAULT 1,
    last_run_at TEXT,
    next_run_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS schedule_executions (
    id TEXT PRIMARY KEY,
    schedule_id TEXT NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
    session_id TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    started_at TEXT NOT NULL,
    completed_at TEXT,
    exit_code INTEGER,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mcp_keys (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    key_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    last_used_at TEXT
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_sessions_agent ON sessions(agent_id);
CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_activities_agent ON activities(agent_id);
CREATE INDEX IF NOT EXISTS idx_activities_created ON activities(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_schedules_agent ON schedules(agent_id);
CREATE INDEX IF NOT EXISTS idx_schedules_enabled ON schedules(enabled);
CREATE INDEX IF NOT EXISTS idx_executions_schedule ON schedule_executions(schedule_id);

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    email TEXT,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tags (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    color TEXT DEFAULT '#9DD522',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent_tags (
    agent_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    tag_id TEXT NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (agent_id, tag_id)
);

CREATE TABLE IF NOT EXISTS credentials (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    value TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT,
    user_id TEXT,
    action TEXT NOT NULL,
    details TEXT,
    ip_address TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS operator_queue (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    agent_name TEXT,
    item_type TEXT NOT NULL,
    description TEXT,
    details TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    resolved_at TEXT,
    resolved_by TEXT,
    resolution TEXT
);

CREATE TABLE IF NOT EXISTS agent_shares (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    permission TEXT NOT NULL DEFAULT 'chat',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS access_requests (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    instance_url TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS connectors (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    label TEXT NOT NULL,
    auth_state TEXT NOT NULL,
    container_tags TEXT NOT NULL DEFAULT '[]',
    enabled INTEGER NOT NULL DEFAULT 1,
    last_sync_at TEXT,
    last_sync_status TEXT,
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS connector_sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    connector_id TEXT NOT NULL REFERENCES connectors(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'running',
    items_found INTEGER DEFAULT 0,
    items_imported INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT
);
"""


# ═══════════════════════════════════════════════════════════════════
# Connection Management
# ═══════════════════════════════════════════════════════════════════

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """Get or create a thread-local connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(str(DATABASE_PATH))
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
    return _local.conn


def _now_iso() -> str:
    """UTC now as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    """Generate a unique ID."""
    return secrets.token_urlsafe(16)


# ═══════════════════════════════════════════════════════════════════
# Init
# ═══════════════════════════════════════════════════════════════════


def init_db() -> None:
    """Run schema migrations. Idempotent — safe to call at every startup."""
    conn = _get_conn()
    conn.executescript(SCHEMA)
    # Migrate: add profile_json column if missing
    try:
        conn.execute("ALTER TABLE agents ADD COLUMN profile_json TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    # Migrate: add tags column if missing
    try:
        conn.execute("ALTER TABLE agents ADD COLUMN tags TEXT DEFAULT '[]'")
    except sqlite3.OperationalError:
        pass  # Column already exists
    conn.commit()\


# ═══════════════════════════════════════════════════════════════════
# Agents
# ═══════════════════════════════════════════════════════════════════


def create_agent(
    name: str,
    model: str = "",
    persona: Optional[str] = None,
    tools: Optional[list[str]] = None,
    skills: Optional[list[str]] = None,
    extensions: Optional[list[str]] = None,
    system_prompt: Optional[str] = None,
    git_repo: Optional[str] = None,
    schedule_cron: Optional[str] = None,
) -> dict:
    conn = _get_conn()
    agent_id = _new_id()
    now = _now_iso()
    conn.execute(
        """INSERT INTO agents (id, name, persona, model, tools, skills, extensions,
           system_prompt, git_repo, schedule_cron, status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'created', ?, ?)""",
        (
            agent_id, name, persona, model,
            json.dumps(tools or DEFAULT_TOOLS),
            json.dumps(skills or []),
            json.dumps(extensions or []),
            system_prompt, git_repo, schedule_cron,
            now, now
        )
    )
    conn.commit()
    return get_agent(agent_id)


def get_agent(agent_id: str) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
    return dict(row) if row else None


def list_agents(status: Optional[str] = None) -> list[dict]:
    conn = _get_conn()
    if status:
        rows = conn.execute(
            "SELECT * FROM agents WHERE status = ? ORDER BY created_at DESC", (status,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM agents ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def update_agent_status(agent_id: str, status: str) -> None:
    conn = _get_conn()
    conn.execute(
        "UPDATE agents SET status = ?, updated_at = ?, last_active = ? WHERE id = ?",
        (status, _now_iso(), _now_iso(), agent_id)
    )
    conn.commit()


def update_agent(agent_id: str, tags: Optional[list[str]] = None) -> None:
    """Update agent fields. Currently supports updating tags.

    When tags is provided, syncs to BOTH the agents.tags JSON column
    AND the normalized tags + agent_tags tables for queryability.
    """
    conn = _get_conn()
    if tags is not None:
        # Update JSON column (fast path for pi_session_service)
        conn.execute(
            "UPDATE agents SET tags = ?, updated_at = ? WHERE id = ?",
            (json.dumps(tags), _now_iso(), agent_id)
        )
        # Sync to normalized tables (queryable path)
        conn.execute("DELETE FROM agent_tags WHERE agent_id = ?", (agent_id,))
        for tag_name in tags:
            # Upsert tag
            existing = conn.execute(
                "SELECT id FROM tags WHERE name = ?", (tag_name,)
            ).fetchone()
            if existing:
                tag_id = existing["id"]
            else:
                tag_id = _new_id()
                conn.execute(
                    "INSERT INTO tags (id, name) VALUES (?, ?)",
                    (tag_id, tag_name)
                )
            # Link agent to tag
            conn.execute(
                "INSERT OR IGNORE INTO agent_tags (agent_id, tag_id) VALUES (?, ?)",
                (agent_id, tag_id)
            )
    conn.commit()


def update_session_file(session_id: str, session_file: str) -> None:
    """Update the session file path after process spawn."""
    conn = _get_conn()
    conn.execute(
        "UPDATE sessions SET session_file = ? WHERE id = ?",
        (session_file, session_id)
    )
    conn.commit()


def update_agent_tokens(agent_id: str, tokens: int) -> None:
    conn = _get_conn()
    conn.execute(
        "UPDATE agents SET total_tokens = total_tokens + ?, updated_at = ? WHERE id = ?",
        (tokens, _now_iso(), agent_id)
    )
    conn.commit()


def increment_session_count(agent_id: str) -> None:
    conn = _get_conn()
    conn.execute(
        "UPDATE agents SET session_count = session_count + 1, updated_at = ? WHERE id = ?",
        (_now_iso(), agent_id)
    )
    conn.commit()


def delete_agent(agent_id: str) -> bool:
    conn = _get_conn()
    cursor = conn.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
    conn.commit()
    return cursor.rowcount > 0


# ═══════════════════════════════════════════════════════════════════
# Agent Profiles
# ═══════════════════════════════════════════════════════════════════


def get_agent_profile(agent_id: str) -> dict:
    """Get the profile JSON for an agent. Returns default if none set."""
    conn = _get_conn()
    row = conn.execute("SELECT profile_json FROM agents WHERE id = ?", (agent_id,)).fetchone()
    if not row or not row["profile_json"]:
        return {"static": {}, "dynamic": []}
    try:
        return json.loads(row["profile_json"])
    except (json.JSONDecodeError, TypeError):
        return {"static": {}, "dynamic": []}


def update_agent_profile(agent_id: str, profile: dict) -> None:
    """Replace the entire profile JSON for an agent."""
    conn = _get_conn()
    conn.execute(
        "UPDATE agents SET profile_json = ?, updated_at = ? WHERE id = ?",
        (json.dumps(profile), _now_iso(), agent_id)
    )
    conn.commit()


def append_agent_memory(agent_id: str, fact: str, fact_type: str = "dynamic") -> None:
    """Append a fact to an agent's dynamic memory.

    Deduplicates: if the fact already exists (static or dynamic), skip it.
    Caps dynamic array at 50 entries (oldest rotated out).
    """
    profile = get_agent_profile(agent_id)
    static = profile.get("static", {})
    dynamic = profile.get("dynamic", [])

    if fact_type == "static":
        key = fact.split(":")[0].strip() if ":" in fact else fact
        static[key] = fact
    else:
        if fact in dynamic:
            return
        dynamic.append(fact)
        if len(dynamic) > 50:
            dynamic = dynamic[-50:]

    profile["static"] = static
    profile["dynamic"] = dynamic
    update_agent_profile(agent_id, profile)


# ═══════════════════════════════════════════════════════════════════
# Sessions
# ═══════════════════════════════════════════════════════════════════


def create_session(
    agent_id: str,
    agent_name: str,
    session_file: str,
    model: str,
) -> dict:
    conn = _get_conn()
    session_id = _new_id()
    now = _now_iso()
    conn.execute(
        """INSERT INTO sessions (id, agent_id, agent_name, session_file, status,
           model, started_at) VALUES (?, ?, ?, ?, 'running', ?, ?)""",
        (session_id, agent_id, agent_name, session_file, model, now)
    )
    conn.commit()
    return get_session(session_id)


def get_session(session_id: str) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    return dict(row) if row else None


def list_sessions(agent_id: Optional[str] = None, limit: int = 50) -> list[dict]:
    conn = _get_conn()
    if agent_id:
        rows = conn.execute(
            "SELECT * FROM sessions WHERE agent_id = ? ORDER BY started_at DESC LIMIT ?",
            (agent_id, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM sessions ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def update_session(
    session_id: str,
    status: Optional[str] = None,
    turns: Optional[int] = None,
    tokens_in: Optional[int] = None,
    tokens_out: Optional[int] = None,
    ended_at: Optional[str] = None,
) -> None:
    conn = _get_conn()
    updates = []
    params = []
    if status is not None:
        updates.append("status = ?")
        params.append(status)
    if turns is not None:
        updates.append("turns = ?")
        params.append(turns)
    if tokens_in is not None:
        updates.append("tokens_in = tokens_in + ?")
        params.append(tokens_in)
    if tokens_out is not None:
        updates.append("tokens_out = tokens_out + ?")
        params.append(tokens_out)
    if ended_at is not None:
        updates.append("ended_at = ?")
        params.append(ended_at)
    if not updates:
        return
    params.append(session_id)
    conn.execute(f"UPDATE sessions SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()


# ═══════════════════════════════════════════════════════════════════
# Activities
# ═══════════════════════════════════════════════════════════════════


def record_activity(
    agent_id: str,
    event_type: str,
    agent_name: Optional[str] = None,
    event_data: Optional[dict] = None,
) -> None:
    conn = _get_conn()
    conn.execute(
        "INSERT INTO activities (agent_id, agent_name, event_type, event_data) VALUES (?, ?, ?, ?)",
        (agent_id, agent_name, event_type, json.dumps(event_data) if event_data else None)
    )
    conn.commit()


def list_activities(limit: int = 20, agent_id: Optional[str] = None) -> list[dict]:
    conn = _get_conn()
    if agent_id:
        rows = conn.execute(
            "SELECT * FROM activities WHERE agent_id = ? ORDER BY created_at DESC LIMIT ?",
            (agent_id, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM activities ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════════
# Schedules
# ═══════════════════════════════════════════════════════════════════


def create_schedule(
    agent_id: str,
    cron_expression: str,
    message: str,
    model: Optional[str] = None,
    max_turns: Optional[int] = None,
    timeout_seconds: Optional[int] = None,
) -> dict:
    conn = _get_conn()
    schedule_id = _new_id()
    now = _now_iso()
    conn.execute(
        """INSERT INTO schedules (id, agent_id, cron_expression, message, model,
           max_turns, timeout_seconds, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (schedule_id, agent_id, cron_expression, message, model,
         max_turns, timeout_seconds, now, now)
    )
    conn.commit()
    return get_schedule(schedule_id)


def get_schedule(schedule_id: str) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM schedules WHERE id = ?", (schedule_id,)).fetchone()
    return dict(row) if row else None


def list_schedules(agent_id: Optional[str] = None) -> list[dict]:
    conn = _get_conn()
    if agent_id:
        rows = conn.execute(
            "SELECT * FROM schedules WHERE agent_id = ? ORDER BY created_at DESC",
            (agent_id,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM schedules ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def update_schedule(
    schedule_id: str,
    cron_expression: Optional[str] = None,
    message: Optional[str] = None,
    enabled: Optional[bool] = None,
    model: Optional[str] = None,
    max_turns: Optional[int] = None,
    timeout_seconds: Optional[int] = None,
) -> None:
    conn = _get_conn()
    updates = ["updated_at = ?"]
    params = [_now_iso()]
    if cron_expression is not None:
        updates.append("cron_expression = ?")
        params.append(cron_expression)
    if message is not None:
        updates.append("message = ?")
        params.append(message)
    if enabled is not None:
        updates.append("enabled = ?")
        params.append(1 if enabled else 0)
    if model is not None:
        updates.append("model = ?")
        params.append(model)
    if max_turns is not None:
        updates.append("max_turns = ?")
        params.append(max_turns)
    if timeout_seconds is not None:
        updates.append("timeout_seconds = ?")
        params.append(timeout_seconds)
    params.append(schedule_id)
    conn.execute(f"UPDATE schedules SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()


def delete_schedule(schedule_id: str) -> bool:
    conn = _get_conn()
    cursor = conn.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
    conn.commit()
    return cursor.rowcount > 0


def record_schedule_execution_start(schedule_id: str) -> str:
    conn = _get_conn()
    execution_id = _new_id()
    conn.execute(
        "INSERT INTO schedule_executions (id, schedule_id, status, started_at) VALUES (?, ?, 'running', ?)",
        (execution_id, schedule_id, _now_iso())
    )
    conn.commit()
    return execution_id


def record_schedule_execution_end(
    execution_id: str,
    status: str,
    session_id: Optional[str] = None,
    exit_code: Optional[int] = None,
    error_message: Optional[str] = None,
) -> None:
    conn = _get_conn()
    conn.execute(
        """UPDATE schedule_executions
           SET status = ?, session_id = ?, completed_at = ?, exit_code = ?, error_message = ?
           WHERE id = ?""",
        (status, session_id, _now_iso(), exit_code, error_message, execution_id)
    )
    conn.commit()


def list_schedule_executions(schedule_id: str, limit: int = 20) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM schedule_executions WHERE schedule_id = ? ORDER BY started_at DESC LIMIT ?",
        (schedule_id, limit)
    ).fetchall()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════════
# Users
# ═══════════════════════════════════════════════════════════════════


def get_user(user_id: str) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def get_user_by_username(username: str) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    return dict(row) if row else None


def get_user_by_email(email: str) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return dict(row) if row else None


def create_user(username: str, email: str, password_hash: str, role: str = "user") -> dict:
    conn = _get_conn()
    user_id = _new_id()
    conn.execute(
        "INSERT INTO users (id, username, email, password_hash, role) VALUES (?, ?, ?, ?, ?)",
        (user_id, username, email, password_hash, role)
    )
    conn.commit()
    return get_user(user_id)


def list_users() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("SELECT id, username, email, role FROM users ORDER BY username").fetchall()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════════
# Agent Count (for health endpoint)
# ═══════════════════════════════════════════════════════════════════


def agent_count() -> int:
    conn = _get_conn()
    row = conn.execute("SELECT COUNT(*) as cnt FROM agents").fetchone()
    return row["cnt"]


def active_session_count() -> int:
    conn = _get_conn()
    row = conn.execute("SELECT COUNT(*) as cnt FROM sessions WHERE status = 'running'").fetchone()
    return row["cnt"]


# ═══════════════════════════════════════════════════════════════════
# Connectors
# ═══════════════════════════════════════════════════════════════════


def list_connectors(enabled_only: bool = False, agent_id: Optional[str] = None) -> list[dict]:
    conn = _get_conn()
    if agent_id:
        rows = conn.execute(
            "SELECT * FROM connectors WHERE agent_id = ? ORDER BY created_at DESC",
            (agent_id,)
        ).fetchall()
    elif enabled_only:
        rows = conn.execute("SELECT * FROM connectors WHERE enabled = 1 ORDER BY created_at DESC").fetchall()
    else:
        rows = conn.execute("SELECT * FROM connectors ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def get_connector(connector_id: str) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM connectors WHERE id = ?", (connector_id,)).fetchone()
    result = dict(row) if row else None
    if result and result.get("auth_state"):
        try:
            result["auth_state"] = json.loads(_decrypt_value(result["auth_state"]))
        except (json.JSONDecodeError, TypeError):
            pass
    return result


def create_connector(
    agent_id: str, provider: str, label: str,
    auth_state: dict, container_tags: list[str] | None = None,
) -> dict:
    conn = _get_conn()
    connector_id = _new_id()
    now = _now_iso()
    encrypted_auth = _encrypt_value(json.dumps(auth_state))
    conn.execute(
        """INSERT INTO connectors (id, agent_id, provider, label, auth_state,
           container_tags, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (connector_id, agent_id, provider, label, encrypted_auth,
         json.dumps(container_tags or []), now, now)
    )
    conn.commit()
    result = get_connector(connector_id)
    # Mask auth_state in the returned dict
    if result:
        result["auth_state"] = "••••••••"
    return result


def delete_connector(connector_id: str) -> bool:
    conn = _get_conn()
    cursor = conn.execute("DELETE FROM connectors WHERE id = ?", (connector_id,))
    conn.commit()
    return cursor.rowcount > 0


# ═══════════════════════════════════════════════════════════════════
# Connection Cleanup
# ═══════════════════════════════════════════════════════════════════


def prune_connector_sync_logs(retention_days: int = 30) -> int:
    """Remove connector sync log entries older than retention_days."""
    conn = _get_conn()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()
    cursor = conn.execute(
        "DELETE FROM connector_sync_log WHERE started_at < ?", (cutoff,)
    )
    conn.commit()
    return cursor.rowcount


def close_connections() -> None:
    """Close all thread-local database connections. Called at shutdown."""
    if hasattr(_local, "conn") and _local.conn is not None:
        _local.conn.close()
        _local.conn = None
