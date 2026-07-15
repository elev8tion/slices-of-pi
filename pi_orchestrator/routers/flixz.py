"""
Flixz Router — frame extraction + transcript + discuss endpoints.

System-level: POST /api/flixz/extract, GET /api/flixz/runs
Per-agent:    POST /api/agents/{id}/flixz/extract, GET /api/agents/{id}/flixz/runs
"""

from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .. import database as db
from ..services.flixz_service import (
    build_flixz_brief,
    delete_flixz_run_with_files,
    extract_video,
)
from ..services.parakeet_asr import parakeet_available, resolve_parakeet_model_dir
from ..services.pi_session_service import stream_chat

router = APIRouter(tags=["flixz"])


class FlixzExtractRequest(BaseModel):
    video_path: str = Field(..., min_length=1)
    max_frames: int = Field(60, ge=1, le=500)
    fps: int = Field(0, ge=0, le=30)
    scene_detect: bool = True
    transcript: str = Field(
        "auto",
        pattern=r"^(none|auto|native|mlx|whisper|captions|parakeet|compare)$",
        description=(
            "none|auto|native|mlx|captions|parakeet|compare. "
            "auto never uses parakeet. parakeet=Handy ONNX secondary. "
            "compare=mlx+parakeet side-by-side verification."
        ),
    )
    describe: str = Field(
        "none",
        pattern=r"^(none|claude|openai|openai-codex|grok|xai|xai-auth)$",
        description="Vision backend for frame description",
    )
    describe_model: Optional[str] = Field(None, description="Optional vision model id from pi list")
    timeout_seconds: Optional[int] = Field(None, ge=10, le=3600)
    mode: str = Field(
        "full",
        pattern=r"^(full|frames_only|transcript_only)$",
        description="full = frames+optional STT; transcript_only = audio/captions only; frames_only = no STT",
    )
    trash_source_video: bool = Field(
        True,
        description="After frames extract, move downloaded.mp4 to macOS Trash",
    )


class FlixzTrashRequest(BaseModel):
    what: str = Field(
        "all",
        pattern=r"^(video|frames|all|db_only)$",
        description="video=source mp4; frames=pngs; all=dir+db; db_only=record only",
    )


class FlixzDiscussRequest(BaseModel):
    agent_id: str = Field(..., min_length=1)
    message: str = Field(
        "",
        description="Operator question about this run (optional — brief has a default prompt)",
    )
    stream: bool = Field(True, description="If true, SSE chat stream; if false, return brief only")


# ═══════════════════════════════════════════════════════════════════
# System-level endpoints
# ═══════════════════════════════════════════════════════════════════


@router.get("/api/flixz/stt-status")
async def flixz_stt_status():
    """Report available STT backends (mlx, parakeet/Handy, voicekit)."""
    from ..services.flixz_service import MLX_WHISPER_BINARY, VOICEKIT_CLI
    import os

    pk_ok, pk_detail = parakeet_available()
    return {
        "mlx": {
            "available": os.path.isfile(MLX_WHISPER_BINARY),
            "binary": MLX_WHISPER_BINARY,
        },
        "parakeet": {
            "available": pk_ok,
            "detail": pk_detail,
            "model_dir": str(resolve_parakeet_model_dir()),
            "role": "secondary_explicit",
            "in_auto_chain": False,
        },
        "native": {
            "available": os.path.isfile(VOICEKIT_CLI),
            "binary": VOICEKIT_CLI,
        },
        "compare": {
            "available": pk_ok and os.path.isfile(MLX_WHISPER_BINARY),
            "description": "Runs mlx + parakeet side-by-side for verification",
        },
    }


@router.post("/api/flixz/extract")
async def system_flixz_extract(body: FlixzExtractRequest):
    """Run frame extraction / transcript at the orchestrator level (no agent scope)."""
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
        mode=body.mode,
        trash_source_video=body.trash_source_video,
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


@router.get("/api/flixz/runs/{run_id}/brief")
async def system_get_brief(run_id: str, message: str = ""):
    """Markdown brief for discussing a run with a pi agent."""
    run = db.get_flixz_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    brief = build_flixz_brief(run, extra_message=message)
    return {"run_id": run_id, "brief": brief, "output_dir": run.get("output_dir")}


@router.post("/api/flixz/runs/{run_id}/discuss")
async def system_discuss_run(run_id: str, body: FlixzDiscussRequest):
    """Send Flixz run context + operator message to a local pi agent (SSE chat)."""
    run = db.get_flixz_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    agent = db.get_agent(body.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    brief = build_flixz_brief(run, extra_message=body.message or "")
    # Persist brief next to frames for agent `read`
    out = run.get("output_dir")
    if out:
        try:
            from pathlib import Path
            Path(out).mkdir(parents=True, exist_ok=True)
            (Path(out) / "flixz_brief.md").write_text(brief, encoding="utf-8")
        except Exception:
            pass

    if not body.stream:
        return {
            "run_id": run_id,
            "agent_id": body.agent_id,
            "agent_name": agent.get("name"),
            "brief": brief,
            "prompt": brief,
        }

    async def event_stream():
        async for chunk in stream_chat(
            agent_id=body.agent_id,
            prompt=brief,
        ):
            yield f"data: {json.dumps(chunk)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/api/flixz/runs/{run_id}/trash")
async def system_trash_run(run_id: str, body: FlixzTrashRequest = FlixzTrashRequest()):
    """Move run artifacts to macOS Trash (or delete)."""
    result = await delete_flixz_run_with_files(run_id, what=body.what)
    if result.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Run not found")
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.delete("/api/flixz/runs/{run_id}")
async def system_delete_run(run_id: str, keep_files: bool = Query(False)):
    """Delete a flixz run. By default trashes the output directory too."""
    what = "db_only" if keep_files else "all"
    result = await delete_flixz_run_with_files(run_id, what=what)
    if result.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Run not found")
    return {"status": "deleted", **result}


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
        mode=body.mode,
        trash_source_video=body.trash_source_video,
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
