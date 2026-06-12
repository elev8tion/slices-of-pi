"""
Agent Profile Service — format agent profiles for system prompt injection.

Converts agent profiles into injectable system prompt context.
"""

from __future__ import annotations

from typing import Optional


def format_profile_as_prompt(agent_id: str) -> str:
    """Format an agent's profile as markdown for system prompt injection.

    Returns empty string if no profile data exists.
    """
    from .. import database as db

    profile = db.get_agent_profile(agent_id)
    if not profile:
        return ""

    parts = []

    static = profile.get("static", {})
    if static:
        parts.append("## Agent Profile")
        for key, value in static.items():
            parts.append(f"- {key}: {value}")

    dynamic = profile.get("dynamic", [])
    if dynamic:
        parts.append("\n## Recent Context")
        for fact in dynamic[-5:]:
            parts.append(f"- {fact}")

    return "\n".join(parts) if parts else ""


def extract_session_summary(agent_id: str, prompt: str, session_id: str) -> str:
    """Create a summary fact from a completed session."""
    truncated = prompt[:80].replace("\n", " ")
    return f"Session {session_id[:8]}: {truncated}..."
