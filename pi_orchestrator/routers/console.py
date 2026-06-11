"""
System Console router — live orchestrator log streaming.

Provides:
  - GET /api/logs/tail?lines=N    Fetch the last N lines from the log file
  - WS /ws/logs                    Stream new log lines in real-time via tail -F

The WebSocket uses `tail -F` (follow by name, handles log rotation) and
buffers recent lines in memory so late joiners get a recent snapshot.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from ..logging_config import setup_logging
from ..services.ws_ticket_service import ws_ticket_service

logger = logging.getLogger(__name__)

router = APIRouter()

LOG_FILE = Path.home() / ".pi" / "agent" / "orchestrator.log"
_MAX_LINES_SEND = 50_000  # safety cap


# ── REST: tail ─────────────────────────────────────────────────────


@router.get("/api/logs/tail")
async def tail_logs(lines: int = Query(100, ge=1, le=5000)):
    """Return the last N lines from the orchestrator log file."""
    if not LOG_FILE.exists():
        return {"lines": [], "path": str(LOG_FILE), "exists": False}

    raw = LOG_FILE.read_text(encoding="utf-8", errors="replace")
    all_lines = raw.splitlines()
    tail = all_lines[-min(lines, len(all_lines)):]

    return {
        "lines": tail,
        "path": str(LOG_FILE),
        "exists": True,
        "total_lines": len(all_lines),
        "returned": len(tail),
    }


# ── WebSocket: live stream ─────────────────────────────────────────


@router.websocket("/ws/logs")
async def ws_log_stream(websocket: WebSocket, ticket: str = ""):
    """Stream new log entries live via tail -F.

    1. Sends the last 100 lines immediately as a snapshot.
    2. Spawns `tail -F` to follow the log file and pipes output.
    3. Handles log rotation transparently (tail -F follows by name).
    """
    # Validate ticket
    user_id = ws_ticket_service.consume_ticket(ticket)
    if user_id is None:
        await websocket.close(code=4001, reason="Invalid or expired ticket")
        return
    await websocket.accept()
    logger.info("System console WebSocket connected")

    proc: asyncio.subprocess.Process | None = None

    try:
        # ── 1. Send recent snapshot ──────────────────────────────
        if LOG_FILE.exists():
            try:
                raw = LOG_FILE.read_text(encoding="utf-8", errors="replace")
                recent = raw.splitlines()[-100:]
                await websocket.send_json({
                    "type": "snapshot",
                    "lines": recent,
                    "path": str(LOG_FILE),
                })
            except Exception as e:
                await websocket.send_json({
                    "type": "snapshot",
                    "lines": [f"[console] Error reading log: {e}"],
                    "path": str(LOG_FILE),
                })
        else:
            await websocket.send_json({
                "type": "snapshot",
                "lines": [],
                "path": str(LOG_FILE),
                "note": "Log file does not exist yet",
            })

        # ── 2. Spawn tail -F ─────────────────────────────────────
        # tail -F (capital F) follows by filename, not inode,
        # so it survives RotatingFileHandler renaming the file.
        proc = await asyncio.create_subprocess_exec(
            "tail",
            "-F",
            "-n", "0",
            str(LOG_FILE),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # ── 3. Stream output line by line ────────────────────────
        async def stream_stdout():
            """Read tail's stdout line by line and send as JSON."""
            assert proc is not None and proc.stdout is not None
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").rstrip("\n")
                try:
                    await websocket.send_json({"type": "line", "text": text})
                except Exception:
                    break

        async def stream_stderr():
            """Log tail's stderr (helpful for debugging)."""
            assert proc is not None and proc.stderr is not None
            while True:
                line = await proc.stderr.readline()
                if not line:
                    break
                logger.warning(f"[tail-F] {line.decode().strip()}")

        # ── 4. Wait for either end ───────────────────────────────
        stdout_task = asyncio.create_task(stream_stdout())
        stderr_task = asyncio.create_task(stream_stderr())

        # Also listen for client disconnect
        try:
            while True:
                msg = await websocket.receive()
                if "text" in msg:
                    text = msg["text"]
                    if text == "ping":
                        await websocket.send_json({"type": "pong"})
        except (WebSocketDisconnect, RuntimeError):
            pass

    except Exception as e:
        logger.error(f"System console error: {e}")
    finally:
        # Kill tail process
        if proc and proc.returncode is None:
            try:
                proc.terminate()
                await asyncio.wait_for(proc.wait(), timeout=2)
            except (asyncio.TimeoutError, ProcessLookupError):
                if proc and proc.returncode is None:
                    try:
                        proc.kill()
                        await proc.wait()
                    except ProcessLookupError:
                        pass
        logger.info("System console WebSocket closed")
