"""
Activity router — expose the activity feed via API.

Activities are recorded by pi_session_service (session_start, session_end,
session_timeout, session_error) and other services as they come online.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter

from .. import database as db

router = APIRouter(prefix="/api/activities", tags=["activities"])


@router.get("")
async def list_activities(
    agent_id: Optional[str] = None,
    limit: int = 20,
):
    """List recent activity events. Optionally filter by agent."""
    activities = db.list_activities(limit=limit, agent_id=agent_id)
    return [
        {
            "id": a["id"],
            "agent_id": a["agent_id"],
            "agent_name": a.get("agent_name"),
            "event_type": a["event_type"],
            "event_data": a.get("event_data"),
            "created_at": a["created_at"],
        }
        for a in activities
    ]
