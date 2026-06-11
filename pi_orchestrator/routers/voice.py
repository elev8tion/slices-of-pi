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
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

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
