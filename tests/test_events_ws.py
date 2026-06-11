"""
Tests for the WebSocket event stream endpoint.

WebSocket /ws/events — real-time event delivery to dashboard clients.
Uses starlette.testclient.TestClient for WebSocket support.
"""

from __future__ import annotations

import asyncio
import json
import pytest
from fastapi.testclient import TestClient

from pi_orchestrator.services.event_bus import event_bus
from pi_orchestrator.main import app as real_app


class TestEventsWebSocket:
    """WebSocket /ws/events — real-time event streaming."""

    @pytest.fixture(autouse=True)
    def setup_ws(self):
        """Ensure event bus is running for WebSocket tests."""
        event_bus._subscribers.clear()
        event_bus._queues.clear()
        event_bus._running = True
        yield
        event_bus._subscribers.clear()
        event_bus._queues.clear()

    def test_websocket_connect(self):
        """Should be able to connect to the WebSocket endpoint."""
        client = TestClient(real_app)
        with client.websocket_connect("/ws/events") as ws:
            assert ws is not None

    def test_websocket_receives_events(self):
        """After connecting, should receive published events."""
        client = TestClient(real_app)
        with client.websocket_connect("/ws/events") as ws:
            # Publish an event via the event bus (synchronously)
            async def publish():
                await event_bus.publish("test_event", {"key": "value"})

            asyncio.run(publish())
            import time
            time.sleep(0.05)

            # Should receive the event
            data = ws.receive_json()
            assert data["type"] == "test_event"
            assert data["data"] == {"key": "value"}
            assert "timestamp" in data

    def test_websocket_multiple_events(self):
        """Should receive all published events in order."""
        client = TestClient(real_app)

        async def publish_events():
            for i in range(3):
                await event_bus.publish(f"event_{i}", {"idx": i})

        with client.websocket_connect("/ws/events") as ws:
            asyncio.run(publish_events())
            import time
            time.sleep(0.1)

            for i in range(3):
                data = ws.receive_json()
                assert data["type"] == f"event_{i}"
                assert data["data"]["idx"] == i

    def test_websocket_event_types(self):
        """Should receive agent_created events."""
        client = TestClient(real_app)

        async def publish():
            await event_bus.publish("agent_created", {"agent_id": "123", "name": "test"})

        with client.websocket_connect("/ws/events") as ws:
            asyncio.run(publish())
            import time
            time.sleep(0.05)

            data = ws.receive_json()
            assert data["type"] == "agent_created"
            assert data["data"]["name"] == "test"

    def test_websocket_disconnect_cleanup(self):
        """When a client disconnects, the subscriber should be cleaned up."""
        client = TestClient(real_app)
        initial_count = len(event_bus._subscribers)

        with client.websocket_connect("/ws/events") as ws:
            # Connected — subscriber count should increase
            import time
            time.sleep(0.05)
            assert len(event_bus._subscribers) == initial_count + 1

        # After disconnect — subscriber should be removed
        import time
        time.sleep(0.1)
        assert len(event_bus._subscribers) == initial_count
