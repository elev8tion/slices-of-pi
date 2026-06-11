"""
Tags router — list all agent tags and update tags per agent.

Tags are user-defined labels stored as a JSON array in the agents.tags column.
Provides a unified list endpoint for the dashboard TagCloud and a per-agent
update endpoint for the agent editor.
"""

from __future__ import annotations

import json
import logging
from collections import Counter

from fastapi import APIRouter, HTTPException

from .. import database as db
from ..services.event_bus import event_bus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/tags")
async def list_tags():
    """Return all unique tags across all agents, with count per tag."""
    agents = db.list_agents()
    tag_counter: Counter = Counter()
    for agent in agents:
        raw = agent.get("tags", "[]")
        if isinstance(raw, str):
            try:
                tag_list = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                tag_list = []
        else:
            tag_list = raw or []
        for tag in tag_list:
            tag_counter[tag] += 1

    return {
        "tags": [
            {"name": name, "count": count}
            for name, count in tag_counter.most_common()
        ]
    }


@router.patch("/api/agents/{agent_id}/tags")
async def update_agent_tags(agent_id: str, body: dict):
    """Update tags for a specific agent.

    Body: {"tags": ["tag1", "tag2"]}
    Replaces all tags with the provided list.
    """
    agent = db.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    tags = body.get("tags", [])
    if not isinstance(tags, list):
        raise HTTPException(status_code=422, detail="tags must be a list of strings")

    # Validate all items are strings
    for t in tags:
        if not isinstance(t, str) or not t.strip():
            raise HTTPException(status_code=422, detail="Each tag must be a non-empty string")

    cleaned = [t.strip() for t in tags]
    db.update_agent(agent_id, tags=cleaned)
    await event_bus.publish("agent_updated", {"agent_id": agent_id, "fields": ["tags"]})
    db.record_activity(agent_id, "tags_updated", f"tags={cleaned}")

    return {"status": "ok", "tags": cleaned}
