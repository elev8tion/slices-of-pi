"""
Operator Queue router — items requiring human intervention.

Agents push items here when they need approval, confirmation, or
help with error recovery. The Operator Room view displays them
for human review and resolution.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query

from .. import database as db
from ..services.audit_service import log_queue_resolved

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/operator-queue", tags=["operator-queue"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return secrets.token_urlsafe(16)


def _row_to_dict(row) -> dict:
    return {
        "id": row[0],
        "agent_id": row[1],
        "agent_name": row[2],
        "type": row[3],
        "title": row[4],
        "description": row[5],
        "status": row[6],
        "priority": row[7],
        "created_at": row[8],
        "updated_at": row[9],
        "resolved_at": row[10],
        "resolution_note": row[11],
    }


@router.get("")
async def list_queue(
    status: Optional[str] = Query(None, pattern="^(pending|acknowledged|resolved|rejected)?$"),
    agent_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
):
    """List operator queue items. Optionally filter by status or agent."""
    conn = db._get_conn()
    params = []
    where = []
    if status:
        where.append("status = ?")
        params.append(status)
    if agent_id:
        where.append("agent_id = ?")
        params.append(agent_id)
    sql = "SELECT * FROM operator_queue"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 WHEN 'low' THEN 3 ELSE 4 END, created_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    return [_row_to_dict(r) for r in rows]


@router.get("/stats")
async def queue_stats():
    """Return counts by status."""
    conn = db._get_conn()
    rows = conn.execute(
        "SELECT status, COUNT(*) as cnt FROM operator_queue GROUP BY status"
    ).fetchall()
    stats = {"pending": 0, "acknowledged": 0, "resolved": 0, "rejected": 0, "total": 0}
    for r in rows:
        stats[r[0]] = r[1]
        stats["total"] += r[1]
    return stats


@router.get("/{item_id}")
async def get_queue_item(item_id: str):
    """Get a single queue item."""
    conn = db._get_conn()
    row = conn.execute("SELECT * FROM operator_queue WHERE id = ?", (item_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Queue item not found")
    return _row_to_dict(row)


class PushQueueItemRequest(BaseModel):
    agent_id: str = Field(..., min_length=1)
    agent_name: str = Field(..., min_length=1)
    type: str = Field("info", pattern="^(approval_needed|confirmation|error|info)$")
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    priority: str = Field("normal", pattern="^(low|normal|high|critical)$")


@router.post("")
async def push_queue_item(body: PushQueueItemRequest):
    """Push a new item to the operator queue."""
    conn = db._get_conn()
    item_id = _new_id()
    now = _now_iso()
    conn.execute(
        """INSERT INTO operator_queue (id, agent_id, agent_name, item_type, type, title, description,
           status, priority, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)""",
        (item_id, body.agent_id, body.agent_name, body.type, body.type, body.title, body.description, body.priority, now),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM operator_queue WHERE id = ?", (item_id,)).fetchone()
    return _row_to_dict(row)


class UpdateQueueItemRequest(BaseModel):
    status: str = Field(..., pattern="^(pending|acknowledged|resolved|rejected)$")
    note: Optional[str] = None


@router.patch("/{item_id}")
async def update_queue_item(item_id: str, body: UpdateQueueItemRequest):
    """Update a queue item's status (acknowledge, resolve, reject)."""
    # Validation handled by Pydantic

    conn = db._get_conn()
    existing = conn.execute("SELECT * FROM operator_queue WHERE id = ?", (item_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Queue item not found")

    now = _now_iso()
    if body.status in ("resolved", "rejected"):
        conn.execute(
            "UPDATE operator_queue SET status = ?, updated_at = ?, resolved_at = ?, resolution_note = ? WHERE id = ?",
            (body.status, now, now, body.note, item_id),
        )
    else:
        conn.execute(
            "UPDATE operator_queue SET status = ?, updated_at = ? WHERE id = ?",
            (body.status, now, item_id),
        )
    conn.commit()
    row = conn.execute("SELECT * FROM operator_queue WHERE id = ?", (item_id,)).fetchone()
    # Audit log for resolution
    if body.status in ("resolved", "rejected"):
        log_queue_resolved(item_id, row[1], body.status + (f": {body.note}" if body.note else ""))
    return _row_to_dict(row)


@router.delete("/{item_id}")
async def delete_queue_item(item_id: str):
    """Remove a queue item."""
    conn = db._get_conn()
    cursor = conn.execute("DELETE FROM operator_queue WHERE id = ?", (item_id,))
    conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Queue item not found")
    return {"status": "deleted"}
