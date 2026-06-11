"""
Session File Cleanup Service — periodic garbage collection of old session data.

Design:
  - Async background task that runs every CLEANUP_INTERVAL seconds (default 6 hours).
  - Scans ~/.pi/agent/sessions/managed/ for JSONL files older than RETENTION_DAYS (default 7).
  - Removes stale files and marks corresponding DB rows as 'expired'.
  - Logs cleanup stats (files removed, bytes freed) after every run.
  - Runs staggered (first run after STAGGER_DELAY seconds, not immediately at startup).
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .. import database as db
from ..config import PI_MANAGED_SESSIONS_DIR

logger = logging.getLogger(__name__)

# ── Tunables (overridable via env vars) ───────────────────────────

CLEANUP_INTERVAL = int(os.getenv("PI_CLEANUP_INTERVAL", "21600"))      # 6 hours
RETENTION_DAYS = int(os.getenv("PI_CLEANUP_RETENTION_DAYS", "7"))     # 7 days
STAGGER_DELAY = int(os.getenv("PI_CLEANUP_STAGGER_DELAY", "300"))     # 5 minutes


class CleanupService:
    """Periodic janitor that purges old session files and DB rows."""

    def __init__(self) -> None:
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Launch the cleanup background task with staggered first run."""
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            "Cleanup service scheduled (interval=%ss, retention=%sd, stagger=%ss)",
            CLEANUP_INTERVAL, RETENTION_DAYS, STAGGER_DELAY,
        )

    async def stop(self) -> None:
        """Cancel the cleanup background task."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            logger.info("Cleanup service stopped")

    # ── Internal ──────────────────────────────────────────────────

    async def _run_loop(self) -> None:
        """Run cleanup on a fixed interval, with staggered initial delay."""
        # Stagger the first run so the service doesn't contend with startup
        await asyncio.sleep(STAGGER_DELAY)

        while self._running:
            try:
                await self._cleanup_once()
            except Exception:
                logger.exception("Session cleanup iteration failed")
            await asyncio.sleep(CLEANUP_INTERVAL)

    async def _cleanup_once(self) -> None:
        """One pass of cleanup: remove old JSONL files, expire DB rows."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
        cutoff_iso = cutoff.isoformat()
        cutoff_ts = cutoff.timestamp()

        removed_files = 0
        total_bytes = 0

        managed = Path(PI_MANAGED_SESSIONS_DIR)
        if not managed.is_dir():
            logger.warning("Managed sessions directory %s does not exist", managed)
            return

        # Walk agent-name subdirectories
        for agent_dir in managed.iterdir():
            if not agent_dir.is_dir():
                continue
            for child in agent_dir.iterdir():
                if not child.is_file() or child.suffix not in (".jsonl", ".JSONL"):
                    continue
                try:
                    # Use mtime as the authoritative age
                    mtime = child.stat().st_mtime
                    if mtime < cutoff_ts:
                        file_size = child.stat().st_size
                        child.unlink()
                        removed_files += 1
                        total_bytes += file_size
                        logger.debug("Removed stale session file: %s (%d bytes)", child, file_size)
                except OSError:
                    logger.exception("Failed to remove session file: %s", child)

        # Mark corresponding DB rows as expired (only non-running sessions)
        expired_rows = db.expire_old_sessions(cutoff_iso)

        # Log summary
        if removed_files > 0 or expired_rows > 0:
            logger.info(
                "Cleanup complete: %d file(s) removed (%s freed), %d session(s) expired",
                removed_files,
                _format_bytes(total_bytes),
                expired_rows,
            )
        else:
            logger.debug("Cleanup skipped — no files or sessions to expire")


def _format_bytes(num_bytes: int) -> str:
    """Human-readable byte size."""
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


# Singleton
cleanup = CleanupService()
