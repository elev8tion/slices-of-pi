"""
Sync Engine — drives connector plugin sync on schedule and on demand.

Handoff chain:
  Timer → list_connectors(enabled=True) → get_connector(id) → plugin.sync() → write_fact()
                                                                              → event_bus.publish()
                                                                              → db.update_connector_status()
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from ... import database as db
from ..shared_memory_service import write_fact
from .registry import get as get_plugin

logger = logging.getLogger(__name__)

SYNC_INTERVAL_SECONDS = 60  # Check for due connectors every 60s


class SyncEngine:
    """Background sync engine for connector plugins.

    Manages two sync triggers:
      1. Manual: sync_one(connector_id) — called from API
      2. Auto: _auto_sync_loop() — background loop for scheduled connectors
    """

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the auto-sync background loop."""
        self._running = True
        self._task = asyncio.create_task(self._auto_sync_loop())
        logger.info("Sync engine started (interval=%ss)", SYNC_INTERVAL_SECONDS)

    async def stop(self) -> None:
        """Stop the auto-sync background loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            logger.info("Sync engine stopped")

    async def sync_one(self, connector_id: str) -> dict:
        """Sync a single connector by ID. Returns result dict.

        Handoff: router → sync_one() → get_connector() → registry.get() → plugin.sync()
                 → write_fact() → event_bus.publish()
        """
        connector = db.get_connector(connector_id)
        if not connector:
            return {"error": "Connector not found"}

        plugin = get_plugin(connector["provider"])
        if not plugin:
            return {"error": f"Unknown provider: {connector['provider']}"}

        auth_state = connector.get("auth_state", {})
        if isinstance(auth_state, str):
            import json
            try:
                auth_state = json.loads(auth_state)
            except (json.JSONDecodeError, TypeError):
                auth_state = {}

        # Verify auth
        try:
            if not await plugin.verify(auth_state):
                return {"error": "Auth expired — re-authorize"}
        except Exception as e:
            return {"error": f"Auth verification failed: {e}"}

        # Publish start event
        try:
            from ...routers.events import event_bus
            await event_bus.publish("connector_sync_started", {
                "connector_id": connector_id,
                "provider": connector["provider"],
                "label": connector["label"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        except Exception:
            pass

        # Run sync
        start_time = datetime.now(timezone.utc)
        try:
            since = connector.get("last_sync_at")
            docs = await plugin.sync(auth_state, since=since)
            items = len(docs)
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()

            # Write each doc to shared knowledge pool
            import json
            tags = json.loads(connector.get("container_tags", "[]")) if isinstance(connector.get("container_tags"), str) else (connector.get("container_tags") or [])
            for doc in docs:
                snippet = (doc.get("content") or doc.get("title") or "")[:200]
                write_fact(
                    agent_id=connector["agent_id"],
                    tag=tags[0] if tags else "default",
                    fact=f"[{connector['provider']}] {doc.get('title', 'untitled')}: {snippet}",
                    fact_type="dynamic",
                    metadata={"url": doc.get("url"), "source": connector["provider"]},
                )

            # Update connector status
            db._get_conn().execute(
                """UPDATE connectors SET last_sync_at = ?, last_sync_status = ?,
                   updated_at = ? WHERE id = ?""",
                (start_time.isoformat(), "success", start_time.isoformat(), connector_id)
            )
            db._get_conn().commit()

            # Publish completion event
            try:
                await event_bus.publish("connector_sync_completed", {
                    "connector_id": connector_id,
                    "provider": connector["provider"],
                    "status": "success",
                    "items": items,
                    "duration_ms": round(elapsed * 1000),
                })
            except Exception:
                pass

            return {"status": "success", "items": items}

        except Exception as e:
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            error_msg = str(e)

            # Update connector with error
            db._get_conn().execute(
                """UPDATE connectors SET last_sync_at = ?, last_sync_status = ?,
                   last_error = ?, updated_at = ? WHERE id = ?""",
                (start_time.isoformat(), "error", error_msg[:500], start_time.isoformat(), connector_id)
            )
            db._get_conn().commit()

            # Publish error event
            try:
                await event_bus.publish("connector_sync_error", {
                    "connector_id": connector_id,
                    "provider": connector["provider"],
                    "status": "error",
                    "error": error_msg[:200],
                    "duration_ms": round(elapsed * 1000),
                })
            except Exception:
                pass

            logger.error(f"Sync failed for connector {connector_id[:12]}: {error_msg}")
            return {"error": error_msg}

    async def sync_all(self) -> list[dict]:
        """Sync all enabled connectors. Returns list of results."""
        connectors = db.list_connectors(enabled_only=True)
        results = []
        for c in connectors:
            result = await self.sync_one(c["id"])
            results.append({"connector_id": c["id"], "provider": c["provider"], **result})
        return results

    async def _auto_sync_loop(self) -> None:
        """Background loop: check for due connectors every SYNC_INTERVAL_SECONDS.

        Only syncs connectors whose plugin has a schedule defined.
        """
        await asyncio.sleep(30)  # Stagger first run

        while self._running:
            try:
                connectors = db.list_connectors(enabled_only=True)
                for c in connectors:
                    plugin = get_plugin(c["provider"])
                    if plugin and plugin.get_schedule():
                        # Simple: just sync if never synced or last sync was > 1h ago
                        import json
                        from datetime import datetime, timezone
                        last = c.get("last_sync_at")
                        needs_sync = False
                        if not last:
                            needs_sync = True
                        else:
                            try:
                                last_dt = datetime.fromisoformat(last)
                                if (datetime.now(timezone.utc) - last_dt).total_seconds() > 3600:
                                    needs_sync = True
                            except (ValueError, TypeError):
                                needs_sync = True
                        if needs_sync:
                            await self.sync_one(c["id"])
            except Exception as e:
                logger.error(f"Auto-sync loop error: {e}")
            await asyncio.sleep(SYNC_INTERVAL_SECONDS)


# Singleton
sync_engine = SyncEngine()
