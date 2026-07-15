"""
Voice Service — orchestrate voice interactions with session persistence.

Routes voice transcripts through the orchestrator pipeline: create session,
send to agent via pi_session_service.stream_chat, collect response, append
to agent profile memory, record activity. Returns formatted response for
TTS playback.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from .. import database as db

logger = logging.getLogger(__name__)


async def process_voice_transcript(
    agent_id: str,
    transcript: str,
    session_id: Optional[str] = None,
    model: Optional[str] = None,
) -> dict:
    """Process a voice transcript through the full orchestration pipeline.

    1. Creates or resumes a session entry
    2. Sends transcript to the agent via pi session service
    3. Collects the complete streaming response
    4. Appends to agent profile memory
    5. Returns structured response for TTS playback
    """
    agent = db.get_agent(agent_id)
    if not agent:
        return {"error": f"Agent not found: {agent_id}"}

    agent_name = agent.get("name", agent_id)

    # ── 1. Session management ──────────────────────────────────
    if session_id:
        existing = db.get_session(session_id)
        if not existing or existing.get("status") not in ("running", "completed"):
            session_id = None

    if not session_id:
        session = db.create_session(
            agent_id=agent_id,
            agent_name=agent_name,
            session_file=f"voice-{db._new_id()[:8]}.jsonl",
            model=model or agent.get("model", ""),
        )
        session_id = session["id"]
        logger.info(f"Voice session created: {session_id[:12]} for {agent_name}")

    # ── 2. Send to agent via pi_session_service ─────────────────
    try:
        from ..services.pi_session_service import stream_chat

        response_text = ""
        tool_calls: list[dict] = []
        tokens_used = 0

        async for chunk in stream_chat(agent_id, transcript, model=model or agent.get("model", "")):
            if chunk.get("type") == "text_delta":
                response_text += chunk.get("content", "")
            elif chunk.get("type") == "tool_call":
                tool_calls.append({
                    "name": chunk.get("tool_name", ""),
                    "input": chunk.get("tool_input", {}),
                })
            elif chunk.get("type") == "turn_end":
                tokens_used = chunk.get("tokens_used", 0)

    except Exception as e:
        logger.exception(f"Voice chat failed for {agent_id}")
        db.update_session(session_id, status="error")
        return {"error": str(e), "session_id": session_id}

    # ── 3. Update session stats ────────────────────────────────
    db.update_session(session_id, turns=1, tokens_out=tokens_used, status="completed")
    db.update_agent_tokens(agent_id, tokens_used)
    db.increment_session_count(agent_id)

    # ── 4. Append to agent profile memory ──────────────────────
    memory_fact = (
        f"[voice] {transcript[:100]}{'...' if len(transcript) > 100 else ''} "
        f"→ {response_text[:120]}{'...' if len(response_text) > 120 else ''}"
    )
    db.append_agent_memory(agent_id, memory_fact, fact_type="dynamic")

    return {
        "response": response_text,
        "session_id": session_id,
        "tool_calls": tool_calls,
        "tokens_used": tokens_used,
    }
