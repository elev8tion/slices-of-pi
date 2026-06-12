"""
Connectors Router — manage external data connectors for agents.

Provides CRUD for connector configurations + plugin discovery.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from typing import Optional

from fastapi import APIRouter, HTTPException

from .. import database as db
from ..services.connectors.registry import get as get_connector_plugin, list_available

router = APIRouter(prefix="/api/connectors", tags=["connectors"])


@router.get("/available")
async def available_connectors():
    """List all available connector plugins (installed + built-in)."""
    return {"connectors": list_available()}


@router.get("/reload")
async def reload_plugins():
    """Force rediscovery of all connector plugins."""
    from ..services.connectors.registry import reload as reload_registry
    reload_registry()
    return {"status": "reloaded"}


@router.get("")
async def list_connectors(agent_id: Optional[str] = None):
    """List all configured connectors, optionally filtered by agent."""
    connectors = db.list_connectors(agent_id=agent_id)
    # Mask auth state
    for c in connectors:
        c["auth_state"] = "••••••••"
    return {"connectors": connectors}


@router.post("", status_code=201)
async def create_connector(body: dict):
    """Create a new connector configuration."""
    errors = []
    for field in ["agent_id", "provider", "label", "auth_state"]:
        if field not in body:
            errors.append(f"{field} is required")
    if errors:
        raise HTTPException(status_code=400, detail=", ".join(errors))

    # Validate agent exists
    agent = db.get_agent(body["agent_id"])
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {body['agent_id']}")

    # Validate provider exists
    plugin = get_connector_plugin(body["provider"])
    if not plugin:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {body['provider']}")

    # Validate auth
    try:
        auth_state = await plugin.authorize(body["auth_state"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    connector = db.create_connector(
        agent_id=body["agent_id"],
        provider=body["provider"],
        label=body.get("label", body["provider"]),
        auth_state=auth_state,
        container_tags=body.get("container_tags"),
    )
    return connector


@router.get("/{connector_id}")
async def get_connector_detail(connector_id: str):
    """Get a single connector's configuration."""
    connector = db.get_connector(connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    connector["auth_state"] = "••••••••"
    return connector


@router.delete("/{connector_id}")
async def delete_connector(connector_id: str):
    """Delete a connector configuration."""
    deleted = db.delete_connector(connector_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Connector not found")
    return {"status": "deleted"}
