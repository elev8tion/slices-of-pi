"""
Pi Session Service — manage pi agent sessions.

Manages pi agents as subprocess sessions. Instead of Docker containers,
agents are pi sessions managed via asyncio subprocess and JSONL parsing.

Each agent has a session file at:
  ~/.pi/agent/sessions/managed/<agent_name>/<session_id>.jsonl

The pi binary is invoked as:
  pi --mode json --session-file <path> [--model <model>] [--tools <tools>] "<prompt>"

Output is JSONL — one JSON object per line — which we parse and stream.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator, Optional

from ..config import (
    PI_BINARY,
    PI_MANAGED_SESSIONS_DIR,
    DEFAULT_MODEL,
    DEFAULT_TOOLS,
    SESSION_TIMEOUT_SECONDS,
)
from .. import database as db

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Process Registry
# ═══════════════════════════════════════════════════════════════════

# Maps session_id → running asyncio subprocess
_running: dict[str, asyncio.subprocess.Process] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ═══════════════════════════════════════════════════════════════════
# Session File Paths
# ═══════════════════════════════════════════════════════════════════


def _session_dir(agent_name: str) -> Path:
    return PI_MANAGED_SESSIONS_DIR / agent_name


def _session_path(agent_name: str, session_id: str) -> Path:
    return _session_dir(agent_name) / f"{session_id}.jsonl"


# ═══════════════════════════════════════════════════════════════════
# Create / Destroy
# ═══════════════════════════════════════════════════════════════════


async def create_agent(config: dict) -> str:
    """Create a new managed pi agent.

    Registers the agent in the database and creates its session directory.
    Does NOT start a pi process — that happens on first chat.

    Args:
        config: Agent configuration dict (name, model, tools, skills, etc.)

    Returns:
        agent_id
    """
    import sqlite3
    try:
        agent = db.create_agent(
            name=config["name"],
            model=config.get("model", DEFAULT_MODEL),
            persona=config.get("persona"),
            tools=config.get("tools"),
            skills=config.get("skills"),
            extensions=config.get("extensions"),
            system_prompt=config.get("system_prompt"),
            git_repo=config.get("git_repo"),
            schedule_cron=config.get("schedule"),
        )
    except sqlite3.IntegrityError as e:
        raise ValueError(str(e))

    _session_dir(config["name"]).mkdir(parents=True, exist_ok=True)

    db.update_agent_status(agent["id"], "idle")
    return agent["id"]


async def destroy_agent(agent_id: str) -> bool:
    """Stop any running session and remove the agent from the database."""
    agent = db.get_agent(agent_id)
    if not agent:
        return False

    running_sessions = db.list_sessions(agent_id=agent_id)
    for session in running_sessions:
        if session["id"] in _running:
            await _kill_process(session["id"])

    return db.delete_agent(agent_id)


# ═══════════════════════════════════════════════════════════════════
# Chat / Execute
# ═══════════════════════════════════════════════════════════════════


async def stream_chat(
    agent_id: str,
    prompt: str,
    model: Optional[str] = None,
    timeout_seconds: Optional[int] = None,
) -> AsyncIterator[dict]:
    """Send a prompt to an agent and stream JSONL chunks back.

    Each yielded dict has:
      - type: "text_delta" | "tool_call" | "tool_result" | "turn_end" | "error"
      - plus type-specific fields

    Uses asyncio.create_subprocess_exec for non-blocking I/O.
    Stderr is read concurrently to prevent pipe-buffer deadlocks.
    Timeout is measured from process start, not end-of-stream.
    """
    agent = db.get_agent(agent_id)
    if not agent:
        yield {"type": "error", "content": f"Agent {agent_id} not found"}
        return

    agent_name = agent["name"]
    tools = json.loads(agent["tools"]) if isinstance(agent["tools"], str) else agent["tools"]
    used_model = model or agent["model"]
    timeout = timeout_seconds or SESSION_TIMEOUT_SECONDS

    # ── Create session record ─────────────────────────────────
    session_dir = _session_dir(agent_name)
    session_dir.mkdir(parents=True, exist_ok=True)

    session = db.create_session(
        agent_id=agent_id,
        agent_name=agent_name,
        session_file="",
        model=used_model,
    )
    session_id = session["id"]
    session_file = _session_path(agent_name, session_id)

    db.update_session_file(session_id, str(session_file))

    db.update_agent_status(agent_id, "busy")
    db.increment_session_count(agent_id)
    db.record_activity(agent_id, "session_start", agent_name)

    # ── Build pi command ──────────────────────────────────────
    cmd = [PI_BINARY, "--mode", "json", "--session", str(session_file)]
    if agent.get("system_prompt"):
        cmd.extend(["--system-prompt", agent["system_prompt"]])
    # Only pass --model when it differs from pi's default (avoids breaking streaming)
    if used_model != DEFAULT_MODEL:
        cmd.extend(["--model", used_model])
    cmd.extend(["--tools", ",".join(tools), "--print", prompt])

    logger.info(f"Starting pi session {session_id[:12]}...: {' '.join(cmd[:6])}...")

    try:
        # Use asyncio subprocess — non-blocking, event-loop-friendly
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _running[session_id] = proc
        start_time = time.monotonic()

        # Read stderr concurrently to prevent pipe-buffer deadlock
        stderr_task = asyncio.create_task(_read_stderr(proc, session_id))

        turn_count = 0
        total_tokens = 0

        try:
            # Wrap the entire streaming block in a timeout from process start
            async for chunk in _stream_jsonl(proc, session_id, timeout - (time.monotonic() - start_time)):
                if chunk["type"] == "turn_end_marker":
                    turn_count += 1
                elif chunk["type"] == "token_accumulate":
                    total_tokens += chunk["tokens"]
                else:
                    yield chunk
        except asyncio.TimeoutError:
            logger.warning(f"Session {session_id[:12]} timed out after {time.monotonic() - start_time:.0f}s")
            await _kill_process(session_id)
            db.update_session(session_id, status="error", ended_at=_now_iso())
            db.update_agent_status(agent_id, "error")
            db.record_activity(agent_id, "session_timeout", agent_name)
            yield {"type": "error", "content": f"Session timed out after {timeout}s"}
            # Cancel stderr reader
            stderr_task.cancel()
            try:
                await stderr_task
            except asyncio.CancelledError:
                pass
            return

        # Wait for stderr to finish
        stderr_task.cancel()
        try:
            await stderr_task
        except asyncio.CancelledError:
            pass

        # Finalize session
        db.update_session(
            session_id, status="completed", turns=turn_count,
            tokens_out=total_tokens, ended_at=_now_iso(),
        )
        db.update_agent_tokens(agent_id, total_tokens)
        db.update_agent_status(agent_id, "idle")
        db.record_activity(
            agent_id, "session_end", agent_name,
            {"turns": turn_count, "tokens": total_tokens},
        )

        yield {
            "type": "turn_end",
            "content": f"Session complete — {turn_count} turns, {total_tokens} tokens",
            "tokens_used": total_tokens,
            "turns": turn_count,
        }

    except Exception as e:
        logger.exception(f"Error in pi session {session_id[:12]}")
        db.update_session(session_id, status="error", ended_at=_now_iso())
        db.update_agent_status(agent_id, "error")
        db.record_activity(agent_id, "session_error", agent_name, {"error": str(e)})
        yield {"type": "error", "content": str(e)}

    finally:
        _running.pop(session_id, None)


# ═══════════════════════════════════════════════════════════════════
# JSONL Streaming (internal)
# ═══════════════════════════════════════════════════════════════════


async def _stream_jsonl(
    proc: asyncio.subprocess.Process,
    session_id: str,
    timeout: float,
) -> AsyncIterator[dict]:
    """Read JSONL from proc stdout, yield mapped chunks.

    pi JSONL event types (v0.79):
      session, agent_start, turn_start, turn_end, agent_end
      message_start.{user,assistant}
      message_update.{text_start,text_delta,text_end,thinking_start,thinking_delta,thinking_end}
      message_end.{user,assistant}
      tool_call, tool_result
    """

    async def read_line() -> str:
        """Read one line with timeout, returns empty string on EOF/timeout."""
        if proc.stdout is None:
            return ""
        try:
            line = await asyncio.wait_for(
                proc.stdout.readline(),
                timeout=max(timeout, 1.0),  # At least 1s between reads
            )
            return line.decode() if isinstance(line, bytes) else (line or "")
        except asyncio.TimeoutError:
            raise  # Propagate to outer handler

    while True:
        line = (await read_line()).strip()
        if not line:
            if proc.stdout is not None and proc.stdout.at_eof():
                break
            continue

        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        event_type = event.get("type", "")

        # ── User message (skip) ──
        if event_type == "message_start":
            msg = event.get("message", {})
            if msg.get("role") == "assistant":
                for block in msg.get("content", []):
                    if block.get("type") == "text":
                        yield {"type": "text_delta", "content": block.get("text", "")}
                    elif block.get("type") == "thinking":
                        pass  # Skip thinking blocks in full message
                # If no streaming updates follow, extract token usage from this message too
                usage = msg.get("usage", {})
                tokens = usage.get("input", 0) + usage.get("output", 0)
                if not tokens:
                    tokens = usage.get("totalTokens", 0)
                if tokens > 0:
                    yield {"type": "token_accumulate", "tokens": tokens}
            continue

        # ── Streaming text deltas ──
        if event_type == "message_update":
            update = event.get("assistantMessageEvent", {})
            update_type = update.get("type", "")
            if update_type == "text_delta":
                yield {"type": "text_delta", "content": update.get("delta", "")}
            elif update_type == "text_start":
                yield {"type": "text_start"}
            elif update_type == "text_end":
                yield {"type": "text_end"}
            # Skip thinking_delta/thinking_start/thinking_end
            continue

        # ── Tool calls ──
        if event_type == "tool_call":
            yield {
                "type": "tool_call",
                "tool_name": event.get("tool_name", event.get("name", "")),
                "tool_input": event.get("input", event.get("arguments", {})),
            }
            continue

        if event_type == "tool_result":
            yield {
                "type": "tool_result",
                "tool_name": event.get("tool_name", event.get("name", "")),
                "content": str(event.get("result", event.get("output", "")))[:2000],
            }
            continue

        # ── Turn marker ──
        if event_type == "turn_end":
            yield {"type": "turn_end_marker"}
            continue

        # ── Message end — extract tokens ──
        if event_type == "message_end":
            msg = event.get("message", {})
            if msg.get("role") == "assistant":
                usage = msg.get("usage", {})
                tokens = usage.get("input", 0) + usage.get("output", 0)
                if not tokens:
                    tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                if not tokens:
                    tokens = usage.get("totalTokens", 0)
                if tokens > 0:
                    yield {"type": "token_accumulate", "tokens": tokens}
            continue


async def _read_stderr(proc: asyncio.subprocess.Process, session_id: str) -> None:
    """Read stderr from the pi process to prevent pipe-buffer deadlock."""
    if proc.stderr is None:
        return
    try:
        while True:
            line = await proc.stderr.readline()
            if not line:
                break
            text = line.decode() if isinstance(line, bytes) else line
            if text.strip():
                logger.warning(f"pi stderr [{session_id[:12]}]: {text.strip()}")
    except asyncio.CancelledError:
        pass
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════
# Status
# ═══════════════════════════════════════════════════════════════════


async def get_status(agent_id: str) -> Optional[dict]:
    """Get detailed status of an agent."""
    return db.get_agent(agent_id)


async def list_all() -> list[dict]:
    """List all managed agents."""
    return db.list_agents()


async def get_running_sessions() -> list[str]:
    """Return list of currently running session IDs."""
    return list(_running.keys())


# ═══════════════════════════════════════════════════════════════════
# Internal Helpers
# ═══════════════════════════════════════════════════════════════════


async def _kill_process(session_id: str) -> None:
    """Kill a running pi process."""
    proc = _running.get(session_id)
    if proc is None:
        return
    try:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
    except Exception:
        pass


async def kill_all() -> None:
    """Kill all running pi processes. Called at shutdown."""
    for session_id in list(_running.keys()):
        await _kill_process(session_id)
