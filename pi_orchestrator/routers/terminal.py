"""
Terminal WebSocket router — live pi session with pseudo-terminal.

Spawns a persistent pi process with a pty, bridges stdin/stdout
to a WebSocket. The browser xterm.js renders the ANSI stream.

Compared to the reference pyxtermjs approach, this avoids pty.fork()
(which blocks the asyncio event loop) in favour of os.openpty() +
asyncio.create_subprocess_exec(), keeping everything async-native.
"""

from __future__ import annotations

import asyncio
import fcntl
import logging
import os
import secrets
import shutil
import signal
import struct
import termios
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from ..config import PI_BINARY, PI_MANAGED_SESSIONS_DIR
from .. import database as db
from ..services.ws_ticket_service import ws_ticket_service
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

router = APIRouter()

_terminals: dict[str, int] = {}


def _agent_workspace(agent_id: str) -> Path:
    """Session/workspace root for an agent — always by agent *name* (matches chat/files)."""
    agent = db.get_agent(agent_id)
    if not agent:
        # Fallback keeps old id-based dir only when agent missing mid-session
        return PI_MANAGED_SESSIONS_DIR / agent_id
    return PI_MANAGED_SESSIONS_DIR / agent["name"]


def _set_winsize(fd: int, rows: int, cols: int) -> None:
    """Tell the pty its window size so line wrapping and cursor work correctly."""
    winsize = struct.pack("HHHH", rows, cols, 0, 0)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)


def _read_pty_worker(fd: int) -> bytes | None:
    """Worker function — select + read, runs entirely in executor thread.

    Returns:
        bytes read, empty bytes on timeout, None on EOF/error.
    """
    import select as _select

    try:
        r, _, _ = _select.select([fd], [], [], 0.5)
        if r:
            data = os.read(fd, 4096)
            return data if data else None  # None = EOF
        return b""  # timeout, no data yet
    except OSError:
        return None


@router.websocket("/ws/terminal/{agent_id}")
async def terminal_websocket(websocket: WebSocket, agent_id: str, ticket: str = "", mode: str = Query("pi")):
    """Spawn a pi session with a pty and bridge to xterm.js via WebSocket."""
    # Validate inputs BEFORE accepting — close at HTTP level rejects the upgrade
    if mode not in ("pi", "bash"):
        await websocket.close(code=4004, reason=f"Invalid mode '{mode}'. Must be 'pi' or 'bash'")
        return

    # Validate ticket
    user_id = ws_ticket_service.consume_ticket(ticket)
    if user_id is None:
        await websocket.close(code=4001, reason="Invalid or expired ticket")
        return
    await websocket.accept()

    session_start = datetime.now(timezone.utc)

    pi_path = shutil.which(PI_BINARY)
    if mode == "pi" and not pi_path:
        await websocket.send_text("\r\n\x1b[31mError: pi binary not found\x1b[0m\r\n")
        await websocket.close(code=4004, reason="pi binary not found")
        return

    session_dir = _agent_workspace(agent_id)
    session_dir.mkdir(parents=True, exist_ok=True)
    session_file = session_dir / f"terminal-{secrets.token_hex(6)}.jsonl"

    env = os.environ.copy()
    env["TERM"] = "xterm-256color"

    master_fd = -1
    slave_fd = -1
    proc: asyncio.subprocess.Process | None = None

    try:
        # ── Open PTY pair ────────────────────────────────────────────
        # os.openpty() is fast and does not block the event loop
        master_fd, slave_fd = os.openpty()

        # ── Start pi as an async subprocess ──────────────────────────
        # We pass the slave (child) side of the pty as stdin/stdout/stderr.
        # The master (parent) side is used to bridge with the WebSocket.
        if mode == "bash":
            proc = await asyncio.create_subprocess_exec(
                "/bin/bash",
                "--login",
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                env=env,
                pass_fds=(slave_fd,),
            )
        else:
            proc = await asyncio.create_subprocess_exec(
                pi_path,
                "--session",
                str(session_file),
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                env=env,
                pass_fds=(slave_fd,),
            )

        # Close the slave side in the parent — only the child needs it.
        # If we don't close it here, select() on the master will never
        # see EOF (because the parent still holds the slave open).
        os.close(slave_fd)
        slave_fd = -1

        _terminals[agent_id] = proc.pid
        logger.info(f"Terminal started for {agent_id} (pid={proc.pid})")

        # ── Set initial window size ─────────────────────────────────
        cols, rows = 120, 40
        _set_winsize(master_fd, rows, cols)

        await websocket.send_bytes(
            f"\x1b[2J\x1b[H\x1b[36m  Slice of Pi Terminal — {agent_id}\x1b[0m\r\n\r\n".encode()
        )

        # ── Async I/O ───────────────────────────────────────────────
        loop = asyncio.get_event_loop()
        queue: asyncio.Queue = asyncio.Queue()

        async def read_pty() -> None:
            """Read pty output via executor (BOTH select + os.read
            run in the executor thread, never blocking the event loop)."""
            while True:
                try:
                    data = await loop.run_in_executor(
                        None, _read_pty_worker, master_fd
                    )
                    if data is None:  # EOF / error
                        break
                    if data:  # non-empty = actual output
                        await queue.put(("out", data))
                except (OSError, asyncio.CancelledError):
                    break
            # Signal dispatch that the pty has closed
            await queue.put(("pty_closed", None))

        async def read_ws() -> None:
            """Read WebSocket messages (keystrokes or resize)."""
            while True:
                try:
                    msg = await websocket.receive()
                except (WebSocketDisconnect, RuntimeError):
                    # RuntimeError: Starlette raises this instead of
                    # WebSocketDisconnect when receive() is called
                    # after a disconnect has already been processed.
                    await queue.put(("stop", None))
                    break

                if "text" in msg:
                    text = msg["text"]
                    # Resize: xterm.js sends ESC[8;<rows>;<cols>t
                    if text.startswith("\x1b[8;") and text.endswith("t"):
                        try:
                            parts = text[4:-1].split(";")
                            r, c = int(parts[0]), int(parts[1])
                            _set_winsize(master_fd, r, c)
                            if proc and proc.returncode is None:
                                proc.send_signal(signal.SIGWINCH)
                        except (ValueError, IndexError, ProcessLookupError):
                            pass
                        continue
                    # Regular input — forward to pty
                    os.write(master_fd, text.encode())
                elif "bytes" in msg:
                    os.write(master_fd, msg["bytes"])

        async def dispatch() -> None:
            """Read from queue, send to WebSocket."""
            while True:
                item = await queue.get()
                typ, data = item
                if typ in ("stop", "pty_closed"):
                    break
                elif typ == "out":
                    try:
                        await websocket.send_bytes(data)
                    except Exception:
                        break

        # ── Run all three tasks concurrently ───────────────────────
        read_pty_task = asyncio.create_task(read_pty())
        read_ws_task = asyncio.create_task(read_ws())
        dispatch_task = asyncio.create_task(dispatch())

        done, pending = await asyncio.wait(
            [read_pty_task, read_ws_task, dispatch_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

    except Exception as e:
        logger.exception(f"Terminal error for {agent_id}")
        try:
            await websocket.send_bytes(
                f"\r\n\x1b[31mError: {e}\x1b[0m\r\n".encode()
            )
            reason = str(e)[:123]  # WebSocket close reason limit
            await websocket.close(code=4000, reason=reason)
        except Exception:
            pass
    finally:
        _terminals.pop(agent_id, None)

        # Kill the pi subprocess
        if proc and proc.returncode is None:
            try:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=3)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
            except ProcessLookupError:
                pass

        # Close the master fd
        if master_fd >= 0:
            try:
                os.close(master_fd)
            except OSError:
                pass

        # Close slave fd if it wasn't transferred to the child
        if slave_fd >= 0:
            try:
                os.close(slave_fd)
            except OSError:
                pass

        duration = (datetime.now(timezone.utc) - session_start).total_seconds() if session_start else 0
        logger.info(f"Terminal session for {agent_id} ended (duration: {duration:.1f}s)")
