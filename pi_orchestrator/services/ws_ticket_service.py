"""
WebSocket ticket service — single-use 30-second TTL tickets for WS auth.

Mints cryptographically random tickets that are consumed immediately
when a WebSocket connection is established. Expired tickets are
periodically swept from memory.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

_TICKET_TTL = 30  # seconds


class WsTicketService:
    """In-memory ticket store with expiry and periodic cleanup."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tickets: dict[str, dict] = {}  # ticket -> {"user_id": str, "expires_at": float}
        self._cleanup_task: Optional[asyncio.Task] = None

    # ── Public API ───────────────────────────────────────────────

    def mint_ticket(self, user_id: str = "admin", ttl_seconds: int = _TICKET_TTL) -> str:
        """Generate a single-use ticket valid for ttl_seconds.

        Returns the ticket string (64 hex chars).
        """
        ticket = secrets.token_hex(32)
        expires_at = time.monotonic() + ttl_seconds

        with self._lock:
            self._tickets[ticket] = {"user_id": user_id, "expires_at": expires_at}
            removed = self._cleanup_expired_locked()

        return ticket

    def consume_ticket(self, ticket: str) -> Optional[str]:
        """Consume a ticket, returning user_id if valid, None otherwise.

        The ticket is removed from the store on first consume, making
        it single-use even if the connection later fails.
        """
        with self._lock:
            entry = self._tickets.pop(ticket, None)
            removed = self._cleanup_expired_locked()

        if entry is None:
            return None

        if time.monotonic() > entry["expires_at"]:
            return None  # expired

        return entry["user_id"]

    # ── Cleanup ──────────────────────────────────────────────────

    def _cleanup_expired_locked(self) -> int:
        """Remove expired tickets (caller must hold _lock)."""
        now = time.monotonic()
        expired = [k for k, v in self._tickets.items() if v["expires_at"] <= now]
        for k in expired:
            del self._tickets[k]
        return len(expired)

    # ── Periodic sweep (asyncio) ─────────────────────────────────

    async def start_periodic_cleanup(self) -> None:
        """Start a background task that sweeps expired tickets every 60s."""
        if self._cleanup_task is not None:
            return

        async def _sweep() -> None:
            while True:
                await asyncio.sleep(60)
                with self._lock:
                    removed = self._cleanup_expired_locked()
                if removed:
                    logger.debug(f"Cleaned up {removed} expired WS tickets")

        self._cleanup_task = asyncio.create_task(_sweep())
        logger.debug("WS ticket cleanup task started")

    async def stop_periodic_cleanup(self) -> None:
        """Stop the background cleanup task."""
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.debug("WS ticket cleanup task stopped")


# Singleton
ws_ticket_service = WsTicketService()
