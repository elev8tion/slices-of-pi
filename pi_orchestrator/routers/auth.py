"""
Authentication router — user registration, login, JWT tokens.

In single-user mode (PI_NO_AUTH=1), all endpoints automatically
authenticate as the default admin user and no login is required.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field

from .. import database as db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ── JWT ──────────────────────────────────────────────────────────

PI_NO_AUTH = os.getenv("PI_NO_AUTH", "").lower() in ("1", "true", "yes")

_SECRET = os.getenv("PI_AUTH_SECRET", "")
if not _SECRET:
    _SECRET = hashlib.sha256(f"slice-of-pi-auth-{os.uname().nodename}".encode()).hexdigest()[:32]
if isinstance(_SECRET, str):
    _SECRET = _SECRET.encode()


def _b64url(data: bytes) -> str:
    return secrets.token_urlsafe(32)


def _sign(data: str) -> str:
    """HMAC-SHA256 signature for a payload string."""
    sig = hmac.new(_SECRET, data.encode(), "sha256").hexdigest()
    return sig


def _make_token(user_id: str, username: str, role: str) -> str:
    """Create a simple JWT-like token: header.payload.signature (base64url)."""
    import json as _json
    import base64

    header = _json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
    payload = _json.dumps({
        "sub": user_id,
        "username": username,
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time()) + 86400,  # 24h
    }).encode()

    b64_header = base64.urlsafe_b64encode(header).rstrip(b"=").decode()
    b64_payload = base64.urlsafe_b64encode(payload).rstrip(b"=").decode()
    signature = _sign(f"{b64_header}.{b64_payload}")

    return f"{b64_header}.{b64_payload}.{signature}"


def _verify_token(token: str) -> dict | None:
    """Verify a JWT token. Returns payload dict or None."""
    import json as _json
    import base64

    parts = token.split(".")
    if len(parts) != 3:
        return None

    b64_header, b64_payload, signature = parts

    # Verify signature
    expected = _sign(f"{b64_header}.{b64_payload}")
    if not hmac.compare_digest(signature, expected):
        return None

    try:
        # Pad back to valid base64
        padded = b64_payload + "=" * (4 - len(b64_payload) % 4)
        payload = _json.loads(base64.urlsafe_b64decode(padded))
    except Exception:
        return None

    # Check expiry
    if payload.get("exp", 0) < time.time():
        return None

    return payload


def _get_default_admin() -> dict:
    """Get or create the default admin user for single-user mode."""
    admin = db.get_user_by_username("admin")
    if not admin:
        pw_hash = hashlib.sha256("admin".encode()).hexdigest()
        admin_raw = db.create_user("admin", "admin@localhost", pw_hash, role="admin")
        admin = db.get_user(admin_raw.get("id", ""))
    return admin or {"id": "default", "username": "admin", "email": "admin@localhost", "role": "admin"}


# ── Dependencies ─────────────────────────────────────────────────


class CurrentUser(BaseModel):
    """Authenticated user info."""
    id: str
    username: str
    email: str
    role: str


async def get_current_user(authorization: Optional[str] = Header(None)) -> CurrentUser:
    """Dependency: extract and verify the current user from the Authorization header.

    If PI_NO_AUTH=1, returns the default admin user without checking the header.
    """
    if PI_NO_AUTH:
        admin = _get_default_admin()
        return CurrentUser(id=admin["id"], username=admin["username"], email=admin.get("email", ""), role=admin.get("role", "admin"))

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")

    token = authorization[7:]
    payload = _verify_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.get_user(payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return CurrentUser(id=user["id"], username=user["username"], email=user["email"], role=user["role"])


async def require_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Dependency: require admin role."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# ── Models ────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    email: str = Field(..., min_length=3, max_length=256)
    password: str = Field(..., min_length=4, max_length=256)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class AuthResponse(BaseModel):
    token: str
    user: CurrentUser


# ── Endpoints ─────────────────────────────────────────────────────


@router.post("/register", response_model=AuthResponse)
async def register(body: RegisterRequest):
    """Register a new user account. Returns JWT token."""
    # Check if username taken
    existing = db.get_user_by_username(body.username)
    if existing:
        raise HTTPException(status_code=409, detail="Username already taken")

    # Check if email taken
    existing_email = db.get_user_by_email(body.email)
    if existing_email:
        raise HTTPException(status_code=409, detail="Email already registered")

    # Hash password
    pw_hash = hashlib.sha256(body.password.encode()).hexdigest()

    # Create user
    user_raw = db.create_user(body.username, body.email, pw_hash, role="user")
    user = db.get_user(user_raw.get("id", ""))
    if not user:
        raise HTTPException(status_code=500, detail="Failed to create user")

    token = _make_token(user["id"], user["username"], user["role"])
    return AuthResponse(
        token=token,
        user=CurrentUser(id=user["id"], username=user["username"], email=user["email"], role=user["role"]),
    )


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest):
    """Login with username and password. Returns JWT token."""
    user = db.get_user_by_username(body.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    pw_hash = hashlib.sha256(body.password.encode()).hexdigest()
    if not hmac.compare_digest(pw_hash, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = _make_token(user["id"], user["username"], user["role"])
    return AuthResponse(
        token=token,
        user=CurrentUser(id=user["id"], username=user["username"], email=user["email"], role=user["role"]),
    )


@router.get("/me", response_model=CurrentUser)
async def me(current_user: CurrentUser = Depends(get_current_user)):
    """Get the currently authenticated user's info."""
    return current_user
