"""
Sharing router — agent sharing, access control, and access requests.

All endpoints require authentication. Admin and agent owner permissions
are enforced for mutation endpoints.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .. import database as db
from .auth import get_current_user, require_admin, CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents", tags=["sharing"])


# ── Models ────────────────────────────────────────────────────────


class ShareRequest(BaseModel):
    email: str = Field(..., min_length=1)
    permission: str = Field(default="chat", pattern=r"^(chat|admin)$")


class AccessRequestCreate(BaseModel):
    email: str = Field(..., min_length=1)
    message: Optional[str] = None


class AccessRequestResolve(BaseModel):
    action: str = Field(..., pattern=r"^(approve|reject)$")


class ShareSummary(BaseModel):
    agent_id: str
    user_id: str
    permission: str
    shared_at: str
    username: str
    email: str
    user_role: str


# ── Helpers ───────────────────────────────────────────────────────


def _check_agent_access(agent_id: str, user: CurrentUser) -> dict:
    """Check that the user owns or has admin access to an agent."""
    agent = db.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Owners and admins can manage sharing
    if user.role == "admin":
        return agent

    # Check if user has admin permission on this agent
    conn = db._get_conn()
    row = conn.execute(
        "SELECT permission FROM agent_shares WHERE agent_id = ? AND user_id = ?",
        (agent_id, user.id),
    ).fetchone()
    if not row or row["permission"] != "admin":
        raise HTTPException(status_code=403, detail="You don't have permission to manage sharing for this agent")

    return agent


# ── Endpoints ─────────────────────────────────────────────────────


@router.get("/{agent_id}/shares", response_model=list[ShareSummary])
async def list_shares(agent_id: str, current_user: CurrentUser = Depends(get_current_user)):
    """List all users who have access to this agent."""
    _check_agent_access(agent_id, current_user)
    shares = db.list_shares(agent_id)
    result = []
    for s in shares:
        result.append(ShareSummary(
            agent_id=s["agent_id"],
            user_id=s["user_id"],
            permission=s["permission"],
            shared_at=s["shared_at"],
            username=s["username"],
            email=s["email"],
            user_role=s["user_role"],
        ))
    return result


@router.post("/{agent_id}/shares")
async def add_share(agent_id: str, body: ShareRequest, current_user: CurrentUser = Depends(get_current_user)):
    """Share an agent with another user by email."""
    _check_agent_access(agent_id, current_user)

    # Find user by email
    target = db.get_user_by_email(body.email)
    if not target:
        raise HTTPException(status_code=404, detail="User with that email not found")

    if target["id"] == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot share an agent with yourself")

    share = db.share_agent(agent_id, target["id"], body.permission)
    db.record_activity(agent_id, "agent_shared", current_user.username,
                       {"shared_with": body.email, "permission": body.permission})
    return {"status": "shared", "user_id": target["id"], "email": body.email, "permission": body.permission}


@router.delete("/{agent_id}/shares/{user_id}")
async def remove_share(agent_id: str, user_id: str, current_user: CurrentUser = Depends(get_current_user)):
    """Revoke a user's access to an agent."""
    _check_agent_access(agent_id, current_user)

    # Prevent removing yourself
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot remove your own access")

    success = db.unshare_agent(agent_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Share not found")

    db.record_activity(agent_id, "agent_unshared", current_user.username, {"user_id": user_id})
    return {"status": "unshared", "user_id": user_id}


@router.get("/{agent_id}/access-requests")
async def list_access_requests(
    agent_id: str,
    status: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
):
    """List access requests for an agent."""
    _check_agent_access(agent_id, current_user)
    return db.list_access_requests(agent_id, status=status)


@router.post("/{agent_id}/access-requests")
async def create_access_request(
    agent_id: str,
    body: AccessRequestCreate,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Request access to an agent."""
    agent = db.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    req = db.create_access_request(agent_id, body.email, message=body.message)
    return req


@router.patch("/{agent_id}/access-requests/{req_id}")
async def resolve_access_request(
    agent_id: str,
    req_id: str,
    body: AccessRequestResolve,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Approve or reject a pending access request."""
    _check_agent_access(agent_id, current_user)

    req = db.get_access_request(req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Access request not found")

    if req["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {req['status']}")

    if body.action == "approve":
        db.resolve_access_request(req_id, "approved", current_user.id)
        # Auto-share the agent with the requester
        target = db.get_user_by_email(req["requester_email"])
        if target:
            db.share_agent(agent_id, target["id"], "chat")
        return {"status": "approved", "requester_email": req["requester_email"]}
    else:
        db.resolve_access_request(req_id, "rejected", current_user.id)
        return {"status": "rejected", "requester_email": req["requester_email"]}
