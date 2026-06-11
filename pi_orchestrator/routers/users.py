"""
Users router — list and search users.

All endpoints require admin access.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query

from .. import database as db
from .auth import get_current_user, require_admin, CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("")
async def list_users(current_user: CurrentUser = Depends(require_admin)):
    """List all registered users. Admin only."""
    return db.list_users()


@router.get("/search")
async def search_users(q: str = Query("", min_length=1), current_user: CurrentUser = Depends(require_admin)):
    """Search users by username or email. Admin only."""
    return db.search_users(q)
