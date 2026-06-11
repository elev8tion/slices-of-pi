"""
System Chat Service — understands voice intents and executes Slice of Pi actions.
Uses direct database/service calls instead of self-HTTP to avoid deadlocks.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import secrets
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .. import database as db
from ..config import PI_BINARY

logger = logging.getLogger(__name__)


async def handle_system_message(message: str) -> dict:
    """Parse a voice command and execute the appropriate action.

    Returns {"response": str, "action": dict|None, "navigate": str|None}
    """
    msg_lower = message.lower().strip()

    # ── Intent: Create agent ──────────────────────────────────────────
    m = re.search(r"create (?:a |an )?agent (?:called |named )?([a-zA-Z0-9_-]+)", msg_lower)
    if m:
        name = m.group(1)
        return _create_agent(name)

    # ── Intent: Delete agent ──────────────────────────────────────────
    m = re.search(r"(?:delete|remove) (?:the |agent )?([a-zA-Z0-9_-]+)", msg_lower)
    if m:
        name = m.group(1)
        return _delete_agent(name)

    # ── Intent: List / count agents ──────────────────────────────────
    if any(p in msg_lower for p in ["list agents", "show agents", "my agents", "all agents"]):
        return _list_agents()

    if any(p in msg_lower for p in ["how many agents", "agent count", "count agents"]):
        return _agent_count()

    # ── Intent: Status / health ──────────────────────────────────────
    if any(p in msg_lower for p in ["system status", "how are you", "whats up", "status"]):
        return _system_status()

    if "health" in msg_lower:
        return _system_health()

    # ── Intent: Stop all agents ──────────────────────────────────────
    if any(p in msg_lower for p in ["stop all", "stop everything", "kill all"]):
        return _stop_all_agents()

    # ── Intent: Open agent / page ────────────────────────────────────
    m = re.search(r"(?:open|show|go to) (?:the |)(\w[\w-]*)", msg_lower)
    if m:
        name = m.group(1)
        page_map = {
            "dashboard": "/", "home": "/", "agents": "/agents",
            "sessions": "/sessions", "console": "/console", "replay": "/replay",
            "settings": "/settings", "audit": "/audit", "ops": "/ops",
        }
        if name in page_map:
            return {"response": f"Opening {name}.", "navigate": page_map[name]}
        # Check if it's an agent name
        agents = db.list_agents()
        match = next((a for a in agents if a["name"].lower() == name), None)
        if match:
            return {"response": f"Found agent {name}.", "navigate": "/"}
        return {"response": f"Page or agent '{name}' not found."}

    # ── Fallback: use pi for a conversational response ───────────────
    return await _pi_fallback(message)


def _create_agent(name: str) -> dict:
    """Create a new agent."""
    import secrets
    agent_id = secrets.token_hex(16)
    now = datetime.now(timezone.utc).isoformat()
    try:
        db.create_agent(agent_id, name, tools=["read", "bash", "web_search"])
        return {"response": f"Created agent {name}. It's ready to use."}
    except Exception as e:
        return {"response": f"Failed to create agent: {e}"}


def _delete_agent(name: str) -> dict:
    """Find and delete an agent by name."""
    try:
        agents = db.list_agents()
        match = next((a for a in agents if a["name"].lower() == name.lower()), None)
        if not match:
            return {"response": f"No agent named {name} found."}
        db.delete_agent(match["id"])
        return {"response": f"Deleted agent {name}."}
    except Exception as e:
        return {"response": f"Failed to delete agent: {e}"}


def _list_agents() -> dict:
    """List all agents with their status."""
    try:
        agents = db.list_agents()
        if not agents:
            return {"response": "No agents yet. Say 'create an agent named test' to make one."}
        names = ", ".join(f"{a['name']} ({a['status']})" for a in agents[:10])
        return {"response": f"You have {len(agents)} agents: {names}"}
    except Exception as e:
        return {"response": f"Failed to list agents: {e}"}


def _agent_count() -> dict:
    """Return the number of agents."""
    try:
        agents = db.list_agents()
        return {"response": f"Slice of Pi has {len(agents)} agents."}
    except Exception as e:
        return {"response": f"Failed to get agent count: {e}"}


def _system_status() -> dict:
    """Return system status from the database."""
    try:
        agents = db.list_agents()
        total = len(agents)
        running = sum(1 for a in agents if a.get("status") in ("idle", "busy"))
        return {"response": f"Slice of Pi is running. {total} agents, {running} active."}
    except Exception:
        return {"response": "Slice of Pi is running."}


def _system_health() -> dict:
    """Return health info from the database."""
    try:
        agents = db.list_agents()
        return {"response": f"System healthy. {len(agents)} agents configured."}
    except Exception:
        return {"response": "System is running."}


def _stop_all_agents() -> dict:
    """Mark all agents as stopped."""
    try:
        agents = db.list_agents()
        count = 0
        for a in agents:
            if a.get("status") in ("idle", "busy"):
                db.update_agent_status(a["id"], "stopped")
                count += 1
        return {"response": f"Stopped {count} agents."}
    except Exception as e:
        return {"response": f"Failed to stop agents: {e}"}


async def _pi_fallback(message: str) -> dict:
    """Fallback: use pi for a conversational response."""
    try:
        agents = db.list_agents()
        agent_count = len(agents)
        running = sum(1 for a in agents if a.get("status") in ("idle", "busy"))

        system_prompt = (
            "You are the system assistant for Slice of Pi, a pi agent management dashboard. "
            "Keep responses concise. Current state: "
            f"{agent_count} agents ({running} active)."
        )

        pi_path = shutil.which(PI_BINARY) or PI_BINARY
        if pi_path and Path(pi_path).exists():
            proc = await asyncio.create_subprocess_exec(
                pi_path, "--mode", "json",
                "--system", system_prompt,
                message,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
            response_text = ""
            for line in stdout.decode().strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                    if event.get("type") == "text_delta":
                        response_text += event.get("content", "")
                except json.JSONDecodeError:
                    continue
            if response_text:
                return {"response": response_text}

        return {"response": f"I heard you say: {message}. Try 'create an agent', 'list agents', or 'system status'."}
    except Exception:
        return {"response": "Sorry, I couldn't process that. Try 'create an agent' or 'system status'."}
