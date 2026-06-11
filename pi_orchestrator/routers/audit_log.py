"""
Audit Log router — full event trail across Slice of Pi.

Provides queryable access to the audit_log table with filtering,
pagination, CSV export, and stats.
"""

from __future__ import annotations

import csv
import io
import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Response

from .. import database as db
from ..services.audit_service import *

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audit-log", tags=["audit-log"])

# Known event types for filter UI
KNOWN_EVENT_TYPES = [
    "agent_created",
    "agent_updated",
    "agent_deleted",
    "session_started",
    "session_ended",
    "credential_set",
    "credential_deleted",
    "queue_resolved",
    "settings_changed",
]


@router.get("")
async def list_audit_events(
    event_type: Optional[str] = None,
    agent_id: Optional[str] = None,
    user_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List audit events with optional filters. Paginated."""
    events = db.query_audit_events(
        event_type=event_type,
        agent_id=agent_id,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    total = db.get_total_audit_event_count(
        event_type=event_type,
        agent_id=agent_id,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
    )

    # Parse metadata JSON for each event
    result = []
    for e in events:
        row = dict(e)
        if isinstance(row.get("metadata"), str):
            try:
                row["metadata"] = json.loads(row["metadata"])
            except (json.JSONDecodeError, TypeError):
                pass
        result.append(row)

    return {
        "events": result,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/export")
async def export_audit_events(
    event_type: Optional[str] = None,
    agent_id: Optional[str] = None,
    user_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    """Export audit events as CSV."""
    events = db.query_audit_events(
        event_type=event_type,
        agent_id=agent_id,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        limit=10000,
        offset=0,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "event_type", "agent_id", "agent_name", "username", "metadata", "created_at"])
    for e in events:
        meta = e.get("metadata")
        if isinstance(meta, str):
            meta = meta[:200]  # Truncate long metadata for CSV
        writer.writerow([
            e["id"],
            e["event_type"],
            e.get("agent_id", ""),
            e.get("agent_name", ""),
            e.get("username", ""),
            meta or "",
            e["created_at"],
        ])

    csv_content = output.getvalue()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="audit-log.csv"',
            "Content-Type": "text/csv; charset=utf-8",
        },
    )


@router.get("/stats")
async def get_audit_stats():
    """Get event counts by type for the last 30 days."""
    return db.get_audit_event_stats()


@router.get("/types")
async def get_event_types():
    """Return known event types for filter UI."""
    return {"event_types": KNOWN_EVENT_TYPES}
