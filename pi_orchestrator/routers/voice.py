"""
Voice Workspace router — lightweight WebSocket for voice session state sync.

Uses browser-native Web Speech API (SpeechRecognition + SpeechSynthesis)
for the actual audio processing. The backend WebSocket provides:
  - Session lifecycle signals (started, ended)
  - Optional text relay to pi chat API
  - Voice state synchronization
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Body
from pydantic import BaseModel

from ..services.ws_ticket_service import ws_ticket_service

logger = logging.getLogger(__name__)

router = APIRouter()

_active_sessions: dict[str, WebSocket] = {}


@router.websocket("/ws/voice/{agent_id}")
async def voice_websocket(websocket: WebSocket, agent_id: str, ticket: str = ""):
    """Lightweight voice session state sync WebSocket.

    Messages from client (JSON):
      {"type": "transcript", "text": "..."}  — speech-to-text result
      {"type": "status", "status": "listening|processing|idle"}  — client state
      {"type": "ping"}  — keepalive

    Messages to client (JSON):
      {"type": "status", "status": "connected"}
      {"type": "text_delta", "content": "..."}  — agent response text
      {"type": "tool_call", "name": "...", "input": "..."}  — tool usage
      {"type": "turn_end", "tokens_used": N}  — response complete
      {"type": "error", "message": "..."}  — error info
      {"type": "pong"}  — keepalive response
    """
    # Validate ticket
    user_id = ws_ticket_service.consume_ticket(ticket)
    if user_id is None:
        await websocket.close(code=4001, reason="Invalid or expired ticket")
        return
    await websocket.accept()
    _active_sessions[agent_id] = websocket
    logger.info(f"Voice session started for agent {agent_id}")

    try:
        # Send initial status
        await websocket.send_json({"type": "status", "status": "connected"})

        while True:
            msg = await websocket.receive()

            if "text" in msg:
                data = json.loads(msg["text"])

                if data["type"] == "ping":
                    await websocket.send_json({"type": "pong"})

                elif data["type"] == "transcript":
                    logger.info(f"[voice/{agent_id}] Transcript: {data.get('text', '')[:60]}...")
                    # The client sends transcripts here for optional server relay
                    # Currently the client sends directly to the chat API
                    await websocket.send_json({"type": "transcript_ack"})

                elif data["type"] == "status":
                    logger.debug(f"[voice/{agent_id}] Status: {data.get('status')}")

    except (WebSocketDisconnect, RuntimeError):
        pass
    except Exception as e:
        logger.exception(f"Voice session error for {agent_id}")
    finally:
        _active_sessions.pop(agent_id, None)
        logger.info(f"Voice session ended for {agent_id}")


def send_to_voice_session(agent_id: str, message: dict) -> None:
    """Send a JSON message to an active voice session (fire-and-forget)."""
    ws = _active_sessions.get(agent_id)
    if ws:
        try:
            asyncio.ensure_future(ws.send_json(message))
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════
# REST endpoint — voice orchestration with session persistence
# ═══════════════════════════════════════════════════════════════════


class VoiceProcessRequest(BaseModel):
    agent_id: str
    transcript: str
    session_id: Optional[str] = None
    model: Optional[str] = None


@router.post("/api/voice/process")
async def voice_process(body: VoiceProcessRequest):
    """Process a voice transcript through the orchestration pipeline.

    Creates a session, sends to agent, collects response, writes
    to agent memory, and returns the full response for TTS playback.
    """
    from ..services.voice_service import process_voice_transcript

    result = await process_voice_transcript(
        agent_id=body.agent_id,
        transcript=body.transcript,
        session_id=body.session_id,
        model=body.model,
    )

    if "error" in result:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=result["error"])

    return result


# ═══════════════════════════════════════════════════════════════════
# TTS endpoint — delegate to mossy
# ═══════════════════════════════════════════════════════════════════


class TtsRequest(BaseModel):
    text: str
    voice_id: Optional[str] = None
    language: Optional[str] = None


@router.post("/api/voice/tts")
async def voice_tts(body: TtsRequest):
    """Synthesize speech via mossy TTS backend.

    Returns base64 WAV audio that the browser can play directly
    via an <audio> element or Web Audio API.
    """
    from ..services.tts_service import synthesize

    result = await synthesize(
        text=body.text,
        voice_id=body.voice_id,
        language=body.language,
    )

    if result["status"] == "unavailable":
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=result["error"])

    if result["status"] == "error":
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=result["error"])

    return result


@router.get("/api/voice/tts/status")
async def voice_tts_status():
    """Check if mossy TTS backend is reachable and warm."""
    from ..services.tts_service import is_available
    available = await is_available()
    return {"available": available}
