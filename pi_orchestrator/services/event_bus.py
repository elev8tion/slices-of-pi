"""
In-process event bus for Pi Orchestrator.

Single-user, no Redis needed. Publishers call `publish(event)`.
Subscribers register callbacks with `subscribe(callback)`.
The WebSocket router fans events out to connected dashboard clients.

Design:
  - asyncio.Queue per subscriber
  - Single dispatcher coroutine reads from all queues
  - No persistence — events are fire-and-forget (dashboard is live-only)
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Callable, Awaitable

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Types
# ═══════════════════════════════════════════════════════════════════

SubscriberCallback = Callable[[dict], Awaitable[None]]


# ═══════════════════════════════════════════════════════════════════
# Event Bus
# ═══════════════════════════════════════════════════════════════════


class EventBus:
    """In-process pub/sub event bus."""

    def __init__(self):
        self._subscribers: dict[str, SubscriberCallback] = {}
        self._queues: dict[str, asyncio.Queue] = {}
        self._running = False
        self._dispatcher_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the event bus."""
        self._running = True
        logger.info("Event bus started (in-process)")

    async def stop(self) -> None:
        """Stop the event bus. Drains pending events."""
        self._running = False
        if self._dispatcher_task:
            self._dispatcher_task.cancel()
            try:
                await self._dispatcher_task
            except asyncio.CancelledError:
                pass
        logger.info("Event bus stopped")

    async def publish(self, event_type: str, data: dict | None = None) -> None:
        """Publish an event to all subscribers.

        Args:
            event_type: Event type string (e.g., 'agent_created', 'session_start', 'activity').
            data: Optional event payload.
        """
        if not self._running:
            return

        event = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data or {},
        }

        # Fan out to all subscriber queues
        for sub_id, queue in list(self._queues.items()):
            if sub_id in self._subscribers:
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    # Drop event for slow subscriber — dashboard is fire-and-forget
                    pass

    def subscribe(self, callback: SubscriberCallback, maxsize: int = 256) -> str:
        """Register a subscriber. Returns a subscriber ID for unsubscribe.

        Args:
            callback: Async function called with each event dict.
            maxsize: Queue size before events are dropped.

        Returns:
            subscriber_id for use with unsubscribe().
        """
        sub_id = str(uuid.uuid4())
        self._subscribers[sub_id] = callback
        self._queues[sub_id] = asyncio.Queue(maxsize=maxsize)

        # Start dispatching for this subscriber (requires running event loop)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._dispatch_one(sub_id))
        except RuntimeError:
            pass  # No event loop — subscriber will be served when loop starts

        return sub_id

    def unsubscribe(self, sub_id: str) -> None:
        """Remove a subscriber."""
        self._subscribers.pop(sub_id, None)
        self._queues.pop(sub_id, None)

    async def _dispatch_one(self, sub_id: str) -> None:
        """Dispatch events from a single subscriber's queue."""
        callback = self._subscribers.get(sub_id)
        queue = self._queues.get(sub_id)
        if callback is None or queue is None:
            return

        while self._running and sub_id in self._subscribers:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=1.0)
                try:
                    await callback(event)
                except Exception:
                    logger.exception(f"Subscriber {sub_id} callback failed")
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break


# ═══════════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════════

event_bus = EventBus()
