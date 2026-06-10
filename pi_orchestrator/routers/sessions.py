"""
Session history router.

Browse, view, and export pi session history.
Sessions are stored as JSONL files at ~/.pi/agent/sessions/managed/.
Metadata is indexed in the sessions table.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from .. import database as db
from ..models import PiSessionSummary, SessionStatus

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _session_to_summary(s: dict) -> dict:
    """Convert database row to session summary dict."""
    return {
        "id": s["id"],
        "agent_id": s["agent_id"],
        "agent_name": s["agent_name"],
        "session_file": s["session_file"],
        "status": s["status"],
        "turns": s.get("turns", 0),
        "tokens_in": s.get("tokens_in", 0),
        "tokens_out": s.get("tokens_out", 0),
        "model": s["model"],
        "started_at": s["started_at"],
        "ended_at": s.get("ended_at"),
    }


@router.get("")
async def list_sessions(
    agent_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
):
    """List recent sessions. Optionally filter by agent or status."""
    sessions = db.list_sessions(agent_id=agent_id, limit=limit)
    if status:
        sessions = [s for s in sessions if s["status"] == status]
    return [_session_to_summary(s) for s in sessions]


@router.get("/{session_id}")
async def get_session(session_id: str):
    """Get session metadata + full message history from the JSONL file."""
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    result = _session_to_summary(session)

    # Try to read the JSONL file for message content
    session_file = session.get("session_file", "")
    messages = []
    if session_file and Path(session_file).exists():
        try:
            with open(session_file) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        # Only include user-visible messages
                        if event.get("type") in ("message_start", "message_delta", "tool_call", "tool_result"):
                            messages.append(event)
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass

    result["messages"] = messages
    return result


@router.get("/{session_id}/export")
async def export_session(session_id: str):
    """Download the raw JSONL session file."""
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session_file = session.get("session_file", "")
    if not session_file or not Path(session_file).exists():
        raise HTTPException(status_code=404, detail="Session file not found")

    return FileResponse(
        path=session_file,
        media_type="application/x-ndjson",
        filename=f"{session_id}.jsonl",
    )
