"""
Agent management router.

CRUD operations for managed pi agents. Each agent is a pi session
configuration — name, model, tools, skills, extensions, persona.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from typing import Optional

from ..models import (
    PiAgentConfig,
    PiAgentSummary,
    PiAgentDetail,
)
from ..services.pi_session_service import (
    create_agent as create_agent_service,
    destroy_agent as destroy_agent_service,
    get_status,
)
from ..services.event_bus import event_bus
from .. import database as db

router = APIRouter(prefix="/api/agents", tags=["agents"])


def _agent_to_summary(agent: dict) -> PiAgentSummary:
    """Convert database row to PiAgentSummary."""
    from datetime import datetime
    last_active = None
    if agent.get("last_active"):
        try:
            last_active = datetime.fromisoformat(agent["last_active"])
        except (ValueError, TypeError):
            pass
    created_at = datetime.fromisoformat(agent["created_at"]) if agent.get("created_at") else None
    return PiAgentSummary(
        id=agent["id"],
        name=agent["name"],
        persona=agent.get("persona"),
        status=agent["status"],
        model=agent["model"],
        tokens_used=agent.get("total_tokens", 0),
        session_count=agent.get("session_count", 0),
        last_active=last_active,
        created_at=created_at,
    )


def _agent_to_detail(agent: dict) -> PiAgentDetail:
    """Convert database row to PiAgentDetail."""
    import json
    from datetime import datetime

    last_active = None
    if agent.get("last_active"):
        try:
            last_active = datetime.fromisoformat(agent["last_active"])
        except (ValueError, TypeError):
            pass
    created_at = datetime.fromisoformat(agent["created_at"]) if agent.get("created_at") else None

    tools = agent.get("tools", "[]")
    if isinstance(tools, str):
        tools = json.loads(tools)
    skills = agent.get("skills", "[]")
    if isinstance(skills, str):
        skills = json.loads(skills)
    extensions = agent.get("extensions", "[]")
    if isinstance(extensions, str):
        extensions = json.loads(extensions)

    return PiAgentDetail(
        id=agent["id"],
        name=agent["name"],
        persona=agent.get("persona"),
        status=agent["status"],
        model=agent["model"],
        tokens_used=agent.get("total_tokens", 0),
        session_count=agent.get("session_count", 0),
        last_active=last_active,
        created_at=created_at,
        tools=tools,
        skills=skills,
        extensions=extensions,
        system_prompt=agent.get("system_prompt"),
        git_repo=agent.get("git_repo"),
        schedule=agent.get("schedule_cron"),
    )


@router.post("", status_code=201, response_model=PiAgentSummary)
async def create_agent(config: PiAgentConfig):
    """Create a new managed pi agent."""
    try:
        agent_id = await create_agent_service(config.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    agent = await get_status(agent_id)
    if not agent:
        raise HTTPException(status_code=500, detail="Agent created but not found")

    await event_bus.publish("agent_created", {"agent_id": agent_id, "name": config.name})
    db.record_activity(agent_id, "agent_created", config.name)
    return _agent_to_summary(agent)


@router.get("", response_model=list[PiAgentSummary])
async def list_agents(status: Optional[str] = None):
    """List all managed pi agents. Optionally filter by status."""
    from .. import database as db
    agents = db.list_agents(status=status)
    return [_agent_to_summary(a) for a in agents]


@router.get("/{agent_id}", response_model=PiAgentDetail)
async def get_agent(agent_id: str):
    """Get detailed info for a single agent."""
    agent = await get_status(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _agent_to_detail(agent)


@router.delete("/{agent_id}", status_code=200)
async def delete_agent(agent_id: str):
    """Stop and remove an agent."""
    # Record activity BEFORE delete (agent row must exist for FK)
    db.record_activity(agent_id, "agent_deleted")
    await event_bus.publish("agent_deleted", {"agent_id": agent_id})
    
    deleted = await destroy_agent_service(agent_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"status": "deleted", "agent_id": agent_id}
