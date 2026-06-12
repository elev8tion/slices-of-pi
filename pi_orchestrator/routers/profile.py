"""
Agent Profile Router — view and manage per-agent memory profiles.

Provides:
  GET    /api/agents/{agent_id}/profile       — view profile
  DELETE /api/agents/{agent_id}/profile/fact  — forget a specific fact

All data flows through the existing agent_profile_service and database CRUD.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import database as db
from ..services.agent_profile_service import format_profile_as_prompt
from ..services.event_bus import event_bus

router = APIRouter(prefix="/api/agents", tags=["profile"])


@router.get("/{agent_id}/profile")
async def get_agent_profile(agent_id: str):
    """View an agent's full profile (static + dynamic memories).

    Returns the raw profile dict plus a formatted markdown preview
    that shows exactly what gets injected into the agent's system prompt.
    """
    agent = db.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    profile = db.get_agent_profile(agent_id)
    preview = format_profile_as_prompt(agent_id)

    return {
        "agent_id": agent_id,
        "agent_name": agent["name"],
        "profile": profile,
        "preview": preview,
        "static_count": len(profile.get("static", {})),
        "dynamic_count": len(profile.get("dynamic", [])),
        "last_updated": agent.get("updated_at"),
    }


@router.delete("/{agent_id}/profile/fact")
async def forget_profile_fact(agent_id: str, body: dict):
    """Forget a specific fact from an agent's profile.

    Body: {"fact": "Session #42: reviewed PR #84..."}
    Only matches dynamic facts. Static facts cannot be forgotten via this endpoint.
    """
    agent = db.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    fact_text = (body.get("fact") or "").strip()
    if not fact_text:
        raise HTTPException(status_code=400, detail="fact is required")

    profile = db.get_agent_profile(agent_id)
    dynamic = profile.get("dynamic", [])

    if fact_text not in dynamic:
        raise HTTPException(status_code=404, detail="Fact not found in profile")

    dynamic.remove(fact_text)
    profile["dynamic"] = dynamic
    db.update_agent_profile(agent_id, profile)

    await event_bus.publish("profile_updated", {
        "agent_id": agent_id,
        "action": "fact_removed",
        "fact": fact_text[:100],
    })
    db.record_activity(agent_id, "profile_fact_forgotten", agent["name"], {
        "fact": fact_text[:200],
    })

    return {"status": "forgotten", "fact": fact_text}
