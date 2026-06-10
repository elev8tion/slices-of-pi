"""
WebSocket event stream router.

Exposes GET /ws/events for the dashboard to receive real-time updates.
Uses the in-process EventBus — no Redis needed.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..services.event_bus import event_bus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """Stream pi orchestrator events to the dashboard via WebSocket.

    Events are JSON objects:
      {"type": "agent_created", "timestamp": "...", "data": {...}}

    The dashboard connects once and receives all events in real time.
    No auth needed — single-user, bound to localhost.
    """
    await websocket.accept()

    async def send_event(event: dict) -> None:
        """Send an event to the WebSocket client."""
        try:
            await websocket.send_text(json.dumps(event))
        except Exception:
            pass  # Client disconnected, subscriber will be cleaned up

    sub_id = event_bus.subscribe(send_event)

    try:
        # Keep connection alive — wait for client messages (or disconnect)
        while True:
            # We don't expect client messages on this socket, but we
            # need to await something to detect disconnection
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    finally:
        event_bus.unsubscribe(sub_id)
