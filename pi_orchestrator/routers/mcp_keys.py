"""
MCP Key Management — store, list, and delete MCP server API keys.

Keys are encrypted at rest using Fernet (AES-128-CBC) with a
file-based key derived from the machine's hostname as fallback.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
from datetime import datetime, timezone
from typing import Optional

from cryptography.fernet import Fernet
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import database as db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mcp-keys", tags=["mcp-keys"])

# ── Encryption ────────────────────────────────────────────────────

_KEY_CACHE: Fernet | None = None


def _get_cipher() -> Fernet:
    """Get or create a Fernet cipher from a machine-local key file."""
    global _KEY_CACHE
    if _KEY_CACHE is not None:
        return _KEY_CACHE

    key_dir = db.DATABASE_PATH.parent  # ~/.pi/agent/
    key_file = key_dir / ".mcp_key"

    if not key_file.exists():
        key_dir.mkdir(parents=True, exist_ok=True)
        raw_key = Fernet.generate_key()
        key_file.write_bytes(raw_key)
    else:
        raw_key = key_file.read_bytes()

    _KEY_CACHE = Fernet(raw_key)
    return _KEY_CACHE


def _encrypt_value(plaintext: str) -> str:
    """Encrypt a string value. Returns base64 ciphertext."""
    cipher = _get_cipher()
    return cipher.encrypt(plaintext.encode()).decode()


def _decrypt_value(ciphertext: str) -> str:
    """Decrypt a base64 ciphertext string."""
    cipher = _get_cipher()
    try:
        return cipher.decrypt(ciphertext.encode()).decode()
    except Exception:
        return ""


# ── Models ─────────────────────────────────────────────────────────


class McpKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    value: str = Field(..., min_length=1)


class McpKeyOut(BaseModel):
    id: str
    name: str
    value: str = ""
    created_at: str


# ── Endpoints ─────────────────────────────────────────────────────


@router.get("")
async def list_mcp_keys():
    """List all MCP keys. Values are masked."""
    keys = db.list_mcp_keys()
    result = []
    for k in keys:
        result.append({
            "id": k["id"],
            "name": k["name"],
            "value": "••••••••",
            "created_at": k["created_at"],
        })
    return {"keys": result}


@router.post("")
async def create_mcp_key(body: McpKeyCreate):
    """Add a new MCP key. Value is encrypted before storage."""
    encrypted = _encrypt_value(body.value)
    key_id = secrets.token_hex(12)

    if db.create_mcp_key(key_id, body.name, encrypted):
        logger.info(f"MCP key created: {body.name}")
        return {
            "id": key_id,
            "name": body.name,
            "value": "••••••••",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    raise HTTPException(status_code=409, detail="Key with this name already exists")


@router.delete("/{key_id}")
async def delete_mcp_key(key_id: str):
    """Delete an MCP key by ID."""
    if db.delete_mcp_key(key_id):
        logger.info(f"MCP key deleted: {key_id[:12]}")
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="MCP key not found")
