"""
Schedules router — CRUD for cron-based pi session schedules.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException

from .. import database as db
from ..models import ScheduleConfig

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


@router.post("", status_code=201)
async def create_schedule(config: ScheduleConfig):
    """Create a new recurring schedule for an agent."""
    agent = db.get_agent(config.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    schedule = db.create_schedule(
        agent_id=config.agent_id,
        cron_expression=config.cron_expression,
        message=config.message,
        model=config.model,
        max_turns=config.max_turns,
        timeout_seconds=config.timeout_seconds,
    )
    if config.enabled:
        db.update_schedule(schedule["id"], enabled=True)
    return schedule


@router.get("")
async def list_schedules(agent_id: Optional[str] = None):
    """List all schedules, optionally filtered by agent."""
    schedules = db.list_schedules(agent_id=agent_id)
    # Enrich with agent names
    for s in schedules:
        agent = db.get_agent(s["agent_id"])
        s["agent_name"] = agent["name"] if agent else None
    return schedules


@router.get("/{schedule_id}")
async def get_schedule(schedule_id: str):
    """Get a single schedule with execution history."""
    schedule = db.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    agent = db.get_agent(schedule["agent_id"])
    schedule["agent_name"] = agent["name"] if agent else None
    schedule["executions"] = db.list_schedule_executions(schedule_id)
    return schedule


@router.patch("/{schedule_id}")
async def update_schedule(schedule_id: str, config: ScheduleConfig):
    """Update an existing schedule."""
    existing = db.get_schedule(schedule_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Schedule not found")

    db.update_schedule(
        schedule_id,
        cron_expression=config.cron_expression,
        message=config.message,
        enabled=config.enabled,
        model=config.model,
        max_turns=config.max_turns,
        timeout_seconds=config.timeout_seconds,
    )
    return db.get_schedule(schedule_id)


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: str):
    """Delete a schedule."""
    if not db.delete_schedule(schedule_id):
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"status": "deleted", "schedule_id": schedule_id}
