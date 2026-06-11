"""
Git router — manage agent git repository operations.

Provides endpoints for init, status, commit, push, pull, log, and diff.
All operations scoped to an agent's repo at ~/.pi/agent/repos/<agent_name>/.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import database as db
from ..services import git_service as git

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents/{agent_id}/git", tags=["git"])


class InitRequest(BaseModel):
    repo_url: Optional[str] = None


class CommitRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=200)


# ── Helpers ───────────────────────────────────────────────────────


async def _get_agent(agent_id: str) -> dict:
    agent = db.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


# ── Status ─────────────────────────────────────────────────────────


@router.get("/status")
async def get_status(agent_id: str):
    """Get git status for an agent's repo."""
    agent = await _get_agent(agent_id)
    result = await git.status(agent["name"])
    return result


# ── Log ────────────────────────────────────────────────────────────


@router.get("/log")
async def get_log(agent_id: str, limit: int = 20):
    """Get commit history for an agent's repo."""
    agent = await _get_agent(agent_id)
    commits = await git.log(agent["name"], limit=min(limit, 100))
    return {"commits": commits}


# ── Diff ───────────────────────────────────────────────────────────


@router.get("/diff")
async def get_diff(agent_id: str, hash: str):
    """Get diff for a specific commit."""
    agent = await _get_agent(agent_id)
    result = await git.diff(agent["name"], hash)
    return result


# ── Init ───────────────────────────────────────────────────────────


@router.post("/init")
async def init_repo(agent_id: str, body: InitRequest = InitRequest()):
    """Initialize a git repo for this agent."""
    agent = await _get_agent(agent_id)
    result = await git.init_repo(agent["name"], body.repo_url)
    return result


# ── Commit ─────────────────────────────────────────────────────────


@router.post("/commit")
async def commit_changes(agent_id: str, body: CommitRequest):
    """Stage all changes and commit."""
    agent = await _get_agent(agent_id)
    result = await git.commit(agent["name"], body.message)
    return result


# ── Push ───────────────────────────────────────────────────────────


@router.post("/push")
async def push_changes(agent_id: str):
    """Push to remote."""
    agent = await _get_agent(agent_id)
    result = await git.push(agent["name"])
    return result


# ── Pull ───────────────────────────────────────────────────────────


@router.post("/pull")
async def pull_changes(agent_id: str):
    """Pull from remote."""
    agent = await _get_agent(agent_id)
    result = await git.pull(agent["name"])
    return result
