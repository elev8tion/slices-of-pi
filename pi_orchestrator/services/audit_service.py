"""
Audit service — structured logging of all significant operations.

Provides convenience wrappers around database.log_audit_event() with
consistent metadata formatting. Every call records who did what to
which agent and when.
"""

from __future__ import annotations

import json
from typing import Optional

from .. import database as db


def log_agent_created(
    agent_id: str,
    agent_name: str,
    username: str = "system",
    user_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> str:
    """Record agent creation."""
    meta = {"name": agent_name}
    if metadata:
        meta.update(metadata)
    return db.log_audit_event(
        event_type="agent_created",
        agent_id=agent_id,
        agent_name=agent_name,
        user_id=user_id,
        username=username,
        metadata=meta,
    )


def log_agent_updated(
    agent_id: str,
    agent_name: str,
    fields_changed: list[str],
    username: str = "system",
    user_id: Optional[str] = None,
) -> str:
    """Record agent config update."""
    return db.log_audit_event(
        event_type="agent_updated",
        agent_id=agent_id,
        agent_name=agent_name,
        user_id=user_id,
        username=username,
        metadata={"fields_changed": fields_changed},
    )


def log_agent_deleted(
    agent_id: str,
    agent_name: str,
    username: str = "system",
    user_id: Optional[str] = None,
) -> str:
    """Record agent deletion."""
    return db.log_audit_event(
        event_type="agent_deleted",
        agent_id=agent_id,
        agent_name=agent_name,
        user_id=user_id,
        username=username,
        metadata={"name": agent_name},
    )


def log_session_started(
    session_id: str,
    agent_id: str,
    agent_name: str,
    username: str = "system",
    user_id: Optional[str] = None,
) -> str:
    """Record session start."""
    return db.log_audit_event(
        event_type="session_started",
        agent_id=agent_id,
        agent_name=agent_name,
        user_id=user_id,
        username=username,
        metadata={"session_id": session_id},
    )


def log_session_ended(
    session_id: str,
    agent_id: str,
    agent_name: str,
    turns: int = 0,
    tokens: int = 0,
    username: str = "system",
    user_id: Optional[str] = None,
) -> str:
    """Record session end with usage stats."""
    return db.log_audit_event(
        event_type="session_ended",
        agent_id=agent_id,
        agent_name=agent_name,
        user_id=user_id,
        username=username,
        metadata={
            "session_id": session_id,
            "turns": turns,
            "tokens": tokens,
        },
    )


def log_credential_set(
    agent_id: str,
    credential_name: str,
    username: str = "system",
    user_id: Optional[str] = None,
) -> str:
    """Record credential creation or update."""
    return db.log_audit_event(
        event_type="credential_set",
        agent_id=agent_id,
        user_id=user_id,
        username=username,
        metadata={"credential_name": credential_name},
    )


def log_credential_deleted(
    agent_id: str,
    credential_name: str,
    username: str = "system",
    user_id: Optional[str] = None,
) -> str:
    """Record credential deletion."""
    return db.log_audit_event(
        event_type="credential_deleted",
        agent_id=agent_id,
        user_id=user_id,
        username=username,
        metadata={"credential_name": credential_name},
    )


def log_queue_resolved(
    item_id: str,
    agent_id: str,
    resolution: str,
    username: str = "system",
    user_id: Optional[str] = None,
) -> str:
    """Record operator queue item resolution."""
    return db.log_audit_event(
        event_type="queue_resolved",
        agent_id=agent_id,
        user_id=user_id,
        username=username,
        metadata={"item_id": item_id, "resolution": resolution},
    )


def log_settings_changed(
    fields_changed: list[str],
    username: str = "system",
    user_id: Optional[str] = None,
) -> str:
    """Record settings change."""
    return db.log_audit_event(
        event_type="settings_changed",
        user_id=user_id,
        username=username,
        metadata={"fields_changed": fields_changed},
    )
