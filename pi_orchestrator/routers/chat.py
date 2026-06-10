"""
Chat router — streaming SSE endpoint for pi agent conversations.

POST /api/agents/{agent_id}/chat → Server-Sent Events stream
GET  /api/agents/{agent_id}/chat/history → Past messages from session JSONL
"""

from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..models import ChatRequest
from ..services.pi_session_service import stream_chat, get_status
from .. import database as db

router = APIRouter(prefix="/api/agents", tags=["chat"])


# ═══════════════════════════════════════════════════════════════════
# Chat (SSE streaming)
# ═══════════════════════════════════════════════════════════════════

@router.post("/{agent_id}/chat")
async def chat_with_agent(agent_id: str, request: ChatRequest):
    """Send a message to an agent and stream the response via SSE.

    Returns text/event-stream with events:
      - data: {"type":"text_delta","content":"Hello..."}
      - data: {"type":"tool_call","tool_name":"read",...}
      - data: {"type":"tool_result","tool_name":"read",...}
      - data: {"type":"turn_end","tokens_used":142,...}
      - data: {"type":"error","content":"..."}

    The client should use EventSource or fetch with ReadableStream.
    """
    agent = await get_status(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    async def event_stream():
        async for chunk in stream_chat(
            agent_id=agent_id,
            prompt=request.message,
            model=request.model,
            timeout_seconds=request.timeout_seconds,
        ):
            yield f"data: {json.dumps(chunk)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


# ═══════════════════════════════════════════════════════════════════
# Chat History
# ═══════════════════════════════════════════════════════════════════


class HistoryResponse(BaseModel):
    agent_id: str
    sessions: list[dict] = Field(default_factory=list)


@router.get("/{agent_id}/chat/history")
async def get_chat_history(agent_id: str, limit: int = 10):
    """Get recent chat sessions for an agent.

    Returns session summaries with the session ID for resuming.
    Full message history is available via GET /api/sessions/:id.
    """
    agent = await get_status(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    sessions = db.list_sessions(agent_id=agent_id, limit=limit)
    return HistoryResponse(
        agent_id=agent_id,
        sessions=[
            {
                "id": s["id"],
                "status": s["status"],
                "model": s["model"],
                "turns": s["turns"],
                "tokens_in": s["tokens_in"],
                "tokens_out": s["tokens_out"],
                "started_at": s["started_at"],
                "ended_at": s.get("ended_at"),
                "session_file": s["session_file"],
            }
            for s in sessions
        ],
    )
