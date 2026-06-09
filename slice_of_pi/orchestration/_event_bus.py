"""
Event Bus Interface

Abstract pub/sub event system for real-time platform updates.

Events are published by backend services (agent status changes,
chat messages, schedule completions, etc.) and delivered to
subscribed clients (WebSocket frontend, webhook endpoints,
MCP clients).

Design:
  - Publishers call publish(channel, event) — fire-and-forget
  - Subscribers register callbacks for specific channels
  - The bus handles fan-out, backpressure, and reconnection

Channel naming convention:
  agent:<id>        — Events for a specific agent
  system:<name>     — Events for a multi-agent system
  platform          — Platform-wide events
  operator          — Operator queue events
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Awaitable, Union

# Event handler type: async callable receiving an event dict
EventHandler = Callable[[dict[str, Any]], Awaitable[None]]


class EventBus(ABC):
    """Abstract pub/sub event system.

    One bus instance per process. Thread-safe if the underlying
    transport supports it (Redis Streams, NATS, etc.).
    """

    @abstractmethod
    async def publish(
        self,
        channel: str,
        event: dict[str, Any],
    ) -> None:
        """Publish an event to a channel.

        Non-blocking. Implementations should enqueue and return
        immediately, not wait for delivery to all subscribers.

        Args:
            channel: The topic/channel name.
            event:   Arbitrary JSON-serializable dict.
        """
        ...

    @abstractmethod
    async def subscribe(
        self,
        channel: str,
        handler: EventHandler,
    ) -> str:
        """Register a handler for a channel.

        Returns:
            subscription_id — opaque string for later unsubscribe.
        """
        ...

    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> None:
        """Remove a subscription.

        Must be idempotent — unsubscribing an already-removed
        subscription is a no-op.
        """
        ...

    # ------------------------------------------------------------------ optional

    async def start(self) -> None:
        """Start the event bus (connect to transport, start loops).

        Optional. Default no-op. Call before publish/subscribe.
        """
        return None

    async def stop(self) -> None:
        """Stop the event bus (drain pending, close transport).

        Optional. Default no-op.
        """
        return None

    async def stats(self) -> dict[str, Any]:
        """Return operational statistics.

        Optional. Default returns empty dict.
        """
        return {}
