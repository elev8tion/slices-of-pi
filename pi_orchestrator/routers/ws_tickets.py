"""
WebSocket ticket router — mint single-use tickets for WS auth.

In PI_NO_AUTH=1 mode, always returns a ticket for the admin user.
In auth mode, requires a valid JWT token.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..services.ws_ticket_service import ws_ticket_service
from .auth import PI_NO_AUTH, _verify_token as decode_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ws", tags=["ws"])

_security = HTTPBearer(auto_error=False)


@router.post("/ticket")
async def mint_ticket(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security),
):
    """Mint a single-use 30-second TTL WebSocket ticket.

    In PI_NO_AUTH=1 mode, no auth is required — always returns a ticket
    for the default admin user.

    In auth mode, requires a valid Bearer JWT token. The ticket encodes
    the authenticated user's ID and can only be used once.
    """
    if PI_NO_AUTH:
        user_id = "admin"
    else:
        if credentials is None:
            raise HTTPException(status_code=401, detail="Missing authorization header")
        payload = decode_token(credentials.credentials)
        if payload is None:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        user_id = payload.get("sub", "unknown")

    ticket = ws_ticket_service.mint_ticket(user_id=user_id)
    return {"ticket": ticket}
