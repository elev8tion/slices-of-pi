"""
Slice Operations — bulk agent controls and system status.

Provides management across all slices: stop/restart all agents, pause/resume
the scheduler, and system status summary.
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter

from .. import database as db
from ..services.pi_session_service import kill_all, get_running_sessions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ops", tags=["ops"])

_start_time = time.time()

try:
    from ..services.schedule_service import scheduler as _scheduler
except ImportError:
    _scheduler = None


@router.get("/status")
async def slices_status():
    """Status summary across all slices."""
    agents = db.list_agents()
    running = await get_running_sessions()

    # Build status breakdown
    status_counts: dict[str, int] = {}
    for a in agents:
        s = a.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1

    return {
        "total_agents": len(agents),
        "running_sessions": len(running),
        "agents_by_status": status_counts,
        "scheduler_running": _scheduler is not None and _scheduler._running if _scheduler else False,
        "uptime_hours": round((time.time() - _start_time) / 3600, 1),
    }


@router.post("/agents/stop-all")
async def stop_all_agents():
    """Stop all running pi sessions."""
    running_before = len(await get_running_sessions())
    await kill_all()
    return {"stopped": running_before}


@router.post("/agents/restart-all")
async def restart_all_agents():
    """Restart all agents — kill sessions, agents auto-restart on next chat."""
    await kill_all()
    # Agents are registered in the DB; they'll create new sessions
    # on their next chat request.
    agents = db.list_agents()
    return {"restarted": len(agents), "killed_sessions": None}


@router.post("/scheduler/pause")
async def pause_scheduler():
    """Pause the APScheduler."""
    if _scheduler and _scheduler._scheduler:
        _scheduler._scheduler.pause()
        logger.info("Scheduler paused via API")
        return {"status": "paused"}
    return {"status": "unavailable", "note": "Scheduler not available"}


@router.post("/scheduler/resume")
async def resume_scheduler():
    """Resume the APScheduler."""
    if _scheduler and _scheduler._scheduler:
        _scheduler._scheduler.resume()
        logger.info("Scheduler resumed via API")
        return {"status": "resumed"}
    return {"status": "unavailable", "note": "Scheduler not available"}
