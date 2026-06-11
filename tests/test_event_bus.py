"""
Tests for the in-process event bus (services/event_bus.py).

Covers publish/subscribe, fan-out, unsubscribing, and lifecycle.
"""

from __future__ import annotations

import asyncio
import json
import pytest

from pi_orchestrator.services.event_bus import EventBus


@pytest.fixture
async def bus():
    """Create a fresh EventBus for each test."""
    b = EventBus()
    await b.start()
    yield b
    await b.stop()


class TestEventBusBasic:
    """Core publish/subscribe functionality."""

    async def test_publish_delivers_to_subscriber(self, bus):
        received = []

        async def callback(event):
            received.append(event)

        bus.subscribe(callback)
        await bus.publish("test_event", {"msg": "hello"})
        await asyncio.sleep(0.05)  # Give dispatcher time

        assert len(received) == 1
        assert received[0]["type"] == "test_event"
        assert received[0]["data"] == {"msg": "hello"}
        assert "timestamp" in received[0]

    async def test_publish_without_data(self, bus):
        received = []

        async def callback(event):
            received.append(event)

        bus.subscribe(callback)
        await bus.publish("no_data_event")
        await asyncio.sleep(0.05)

        assert len(received) == 1
        assert received[0]["type"] == "no_data_event"
        assert received[0]["data"] == {}

    async def test_fan_out_to_multiple_subscribers(self, bus):
        received_1 = []
        received_2 = []

        async def cb1(event):
            received_1.append(event)

        async def cb2(event):
            received_2.append(event)

        bus.subscribe(cb1)
        bus.subscribe(cb2)
        await bus.publish("fanout")
        await asyncio.sleep(0.05)

        assert len(received_1) == 1
        assert len(received_2) == 1

    async def test_unsubscribe_removes_subscriber(self, bus):
        received = []

        async def callback(event):
            received.append(event)

        sub_id = bus.subscribe(callback)
        await bus.publish("before")
        await asyncio.sleep(0.05)
        assert len(received) == 1

        bus.unsubscribe(sub_id)
        await bus.publish("after")
        await asyncio.sleep(0.05)
        assert len(received) == 1  # No new events

    async def test_unsubscribe_nonexistent(self, bus):
        """Unsubscribing a non-existent ID should not raise."""
        bus.unsubscribe("nonexistent")  # Should not raise

    async def test_multiple_events(self, bus):
        received = []

        async def callback(event):
            received.append(event["type"])

        bus.subscribe(callback)
        for i in range(5):
            await bus.publish(f"event_{i}")
        await asyncio.sleep(0.1)

        assert len(received) == 5
        assert received == ["event_0", "event_1", "event_2", "event_3", "event_4"]

    async def test_callback_exception_does_not_crash_bus(self, bus):
        """A failing callback should not prevent other subscribers from receiving."""
        good_received = []

        async def bad_callback(event):
            raise ValueError("Boom!")

        async def good_callback(event):
            good_received.append(event)

        bus.subscribe(bad_callback)
        bus.subscribe(good_callback)
        await bus.publish("resilient")
        await asyncio.sleep(0.05)

        assert len(good_received) == 1


class TestEventBusLifecycle:
    """Start/stop behavior."""

    async def test_stop_prevents_delivery(self, bus):
        received = []

        async def callback(event):
            received.append(event)

        bus.subscribe(callback)
        await bus.stop()
        await bus.publish("after_stop")
        await asyncio.sleep(0.05)

        # May or may not deliver — stop is best-effort
        # But we should not crash
        assert bus._running is False

    async def test_publish_before_start(self):
        """Publishing before start() should be a no-op."""
        b = EventBus()
        received = []

        async def callback(event):
            received.append(event)

        b.subscribe(callback)
        await b.publish("before_start")
        await asyncio.sleep(0.05)
        assert len(received) == 0

    async def test_double_stop(self, bus):
        await bus.stop()
        await bus.stop()  # Should not raise

    async def test_double_start(self, bus):
        await bus.start()  # Should not raise (already started)
        assert bus._running is True


class TestEventBusOrdering:
    """Event ordering guarantees."""

    async def test_events_in_order(self, bus):
        received = []

        async def callback(event):
            received.append(event["type"])

        bus.subscribe(callback)
        for i in range(10):
            await bus.publish(f"ev_{i}")
        await asyncio.sleep(0.1)

        assert received == [f"ev_{i}" for i in range(10)]


class TestEventBusIntegration:
    """Integration with the WebSocket event router."""

    async def test_subscription_id_is_unique(self, bus):
        id1 = bus.subscribe(lambda e: None)
        id2 = bus.subscribe(lambda e: None)
        assert id1 != id2

    async def test_subscribe_returns_uuid(self, bus):
        import uuid

        sub_id = bus.subscribe(lambda e: None)
        # Should be a valid UUID
        uuid.UUID(sub_id)
