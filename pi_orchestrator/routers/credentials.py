"""
Credentials router — per-agent API key management.

Values are encrypted at rest. List/create/delete return masked values only.
Decrypted values are available only via GET .../values?reveal=1 for the
local operator reveal UI (not for casual unauthenticated scraping).

Note: injection into pi session env is not yet wired in stream_chat;
reveal is for operator inspection on a localhost single-operator setup.
"""

from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from .. import database as db
from ..config import DATABASE_PATH
from ..services.audit_service import log_credential_set, log_credential_deleted

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents/{agent_id}/credentials", tags=["credentials"])

# Local operator may disable reveal entirely: PI_ALLOW_CREDENTIAL_VALUES=0
_ALLOW_REVEAL = os.getenv("PI_ALLOW_CREDENTIAL_VALUES", "1").lower() not in ("0", "false", "no")


# ── Encryption ────────────────────────────────────────────────────


def _get_encryption_key() -> bytes:
    """Get or derive a machine-specific encryption key."""
    key_file = DATABASE_PATH.parent / "orchestrator.key"
    if key_file.exists():
        raw = key_file.read_bytes().strip()
        if len(raw) >= 32:
            import base64
            try:
                decoded = base64.urlsafe_b64decode(raw)
                if len(decoded) == 32:
                    return base64.urlsafe_b64encode(decoded)
            except Exception:
                pass
            import hashlib
            if len(raw) >= 44:
                return raw[:44]
            return base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
    import base64, hashlib, os
    hostname = os.uname().nodename
    port = os.getenv("PI_ORCHESTRATOR_PORT", "8420")
    raw_key = hashlib.sha256(f"slice-of-pi-cred-{hostname}-{port}".encode()).digest()
    return base64.urlsafe_b64encode(raw_key)


def _encrypt_value(plaintext: str) -> str:
    key = _get_encryption_key()
    try:
        from cryptography.fernet import Fernet
        return Fernet(key).encrypt(plaintext.encode()).decode()
    except ImportError:
        import base64
        kb = key[:32] if len(key) >= 32 else key.ljust(32, b"\x00")
        data = plaintext.encode()
        result = bytearray(i ^ kb[i % len(kb)] for i, b in enumerate(data))
        return "xor:" + base64.b64encode(bytes(result)).decode()


def _decrypt_value(encrypted: str) -> str:
    key = _get_encryption_key()
    try:
        from cryptography.fernet import Fernet, InvalidToken
        return Fernet(key).decrypt(encrypted.encode()).decode()
    except (ImportError, InvalidToken):
        if encrypted.startswith("xor:"):
            import base64
            kb = key[:32] if len(key) >= 32 else key.ljust(32, b"\x00")
            data = base64.b64decode(encrypted[4:])
            return bytes(b ^ kb[i % len(kb)] for i, b in enumerate(data)).decode()
        return "[encrypted]"


# ── Endpoints ─────────────────────────────────────────────────────


@router.get("")
async def list_credentials(agent_id: str):
    """List credential names for an agent (values masked as '••••••••')."""
    agent = db.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    conn = db._get_conn()
    rows = conn.execute(
        "SELECT id, agent_id, name, created_at, updated_at FROM credentials WHERE agent_id = ? ORDER BY name",
        (agent_id,),
    ).fetchall()
    return {
        "credentials": [
            {"id": r["id"], "agent_id": r["agent_id"], "name": r["name"],
             "value": "••••••••", "created_at": r["created_at"], "updated_at": r["updated_at"]}
            for r in rows
        ]
    }


@router.post("", status_code=201)
async def set_credential(agent_id: str, body: dict):
    """Create or update a credential. Body: {'name': 'KEY', 'value': 'secret'}."""
    name = (body.get("name") or "").strip()
    value = body.get("value") or ""
    if not name:
        raise HTTPException(status_code=400, detail="Credential name is required")
    if not value:
        raise HTTPException(status_code=400, detail="Credential value is required")
    if not name.replace("_", "").isalnum():
        raise HTTPException(status_code=400,
                            detail="Name must be alphanumeric with underscores (e.g. OPENAI_API_KEY)")
    agent = db.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    conn = db._get_conn()
    now = datetime.now(timezone.utc).isoformat()
    encrypted = _encrypt_value(value)
    existing = conn.execute(
        "SELECT id FROM credentials WHERE agent_id = ? AND name = ?", (agent_id, name)
    ).fetchone()
    if existing:
        db._safe_execute(conn, "UPDATE credentials SET value = ?, updated_at = ? WHERE id = ?",
                         (encrypted, now, existing["id"]))
        row = conn.execute("SELECT * FROM credentials WHERE id = ?", (existing["id"],)).fetchone()
    else:
        cred_id = secrets.token_urlsafe(16)
        db._safe_execute(conn, "INSERT INTO credentials (id,agent_id,name,value,created_at,updated_at) VALUES (?,?,?,?,?,?)",
                         (cred_id, agent_id, name, encrypted, now, now))
        row = conn.execute("SELECT * FROM credentials WHERE id = ?", (cred_id,)).fetchone()
    db._safe_commit(conn)
    db.record_activity(agent_id, "credential_set", agent["name"], {"credential": name})
    log_credential_set(agent_id, name)
    return {"id": row["id"], "agent_id": row["agent_id"], "name": row["name"],
            "value": "••••••••", "created_at": row["created_at"], "updated_at": row["updated_at"]}


@router.delete("/{credential_name}")
async def delete_credential(agent_id: str, credential_name: str):
    """Delete a credential by name."""
    agent = db.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    conn = db._get_conn()
    cursor = db._safe_execute(conn,
        "DELETE FROM credentials WHERE agent_id = ? AND name = ?", (agent_id, credential_name))
    db._safe_commit(conn)
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Credential not found")
    db.record_activity(agent_id, "credential_deleted", agent["name"], {"credential": credential_name})
    log_credential_deleted(agent_id, credential_name)
    return {"status": "deleted", "credential": credential_name}


@router.get("/values")
async def get_credential_values(
    agent_id: str,
    reveal: bool = Query(False, description="Must be true to return decrypted values"),
):
    """Return decrypted credential values (operator reveal only).

    Requires ?reveal=1. Disabled entirely when PI_ALLOW_CREDENTIAL_VALUES=0.
    Without reveal=1, returns 400 so casual GET does not dump secrets.
    """
    if not _ALLOW_REVEAL:
        raise HTTPException(
            status_code=403,
            detail="Credential reveal disabled (PI_ALLOW_CREDENTIAL_VALUES=0)",
        )
    if not reveal:
        raise HTTPException(
            status_code=400,
            detail="Pass ?reveal=1 to decrypt values (local operator confirm)",
        )
    agent = db.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    conn = db._get_conn()
    rows = conn.execute(
        "SELECT name, value FROM credentials WHERE agent_id = ?", (agent_id,)
    ).fetchall()
    logger.info("Credential values revealed for agent %s", agent_id)
    return {r["name"]: _decrypt_value(r["value"]) for r in rows}
