"""
Flixz Router — frame extraction endpoints (system + per-agent).

System-level: POST /api/flixz/extract, GET /api/flixz/runs
Per-agent:    POST /api/agents/{id}/flixz/extract, GET /api/agents/{id}/flixz/runs
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .. import database as db
from ..services.flixz_service import extract_video

router = APIRouter(tags=["flixz"])


class FlixzExtractRequest(BaseModel):
    video_path: str = Field(..., min_length=1)
    max_frames: int = Field(60, ge=1, le=500)
    fps: int = Field(0, ge=0, le=30)
    scene_detect: bool = True
    transcript: str = Field("none", pattern=r"^(none|native)$")
    describe: str = Field("none", pattern=r"^(none|gemini|claude)$")
    describe_model: Optional[str] = Field(None, description="Optional vision model id from pi list")
    timeout_seconds: Optional[int] = Field(None, ge=10, le=3600)


# ═══════════════════════════════════════════════════════════════════
# System-level endpoints
# ═══════════════════════════════════════════════════════════════════


@router.post("/api/flixz/extract")
async def system_flixz_extract(body: FlixzExtractRequest):
    """Run frame extraction at the orchestrator level (no agent scope)."""
    result = await extract_video(
        video_path=body.video_path,
        max_frames=body.max_frames,
        fps=body.fps,
        scene_detect=body.scene_detect,
        transcript=body.transcript,
        describe=body.describe,
        describe_model=body.describe_model,
        agent_id=None,
        timeout_seconds=body.timeout_seconds,
    )
    return result


@router.get("/api/flixz/runs")
async def system_list_runs(limit: int = Query(20, ge=1, le=100)):
    """List all system-level and per-agent flixz runs."""
    runs = db.list_flixz_runs(agent_id=None, limit=limit)
    return {"runs": runs, "count": len(runs)}


@router.get("/api/flixz/runs/{run_id}")
async def system_get_run(run_id: str):
    """Get a single flixz run by ID."""
    run = db.get_flixz_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.delete("/api/flixz/runs/{run_id}")
async def system_delete_run(run_id: str):
    """Delete a flixz run and its output files."""
    deleted = db.delete_flixz_run(run_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"status": "deleted"}


# ═══════════════════════════════════════════════════════════════════
# Per-agent endpoints
# ═══════════════════════════════════════════════════════════════════


@router.post("/api/agents/{agent_id}/flixz/extract")
async def agent_flixz_extract(agent_id: str, body: FlixzExtractRequest):
    """Run frame extraction scoped to a specific agent."""
    agent = db.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    result = await extract_video(
        video_path=body.video_path,
        max_frames=body.max_frames,
        fps=body.fps,
        scene_detect=body.scene_detect,
        transcript=body.transcript,
        describe=body.describe,
        describe_model=body.describe_model,
        agent_id=agent_id,
        timeout_seconds=body.timeout_seconds,
    )
    return result


@router.get("/api/agents/{agent_id}/flixz/runs")
async def agent_list_runs(agent_id: str, limit: int = Query(20, ge=1, le=100)):
    """List flixz runs for a specific agent."""
    agent = db.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    runs = db.list_flixz_runs(agent_id=agent_id, limit=limit)
    return {"runs": runs, "count": len(runs)}
