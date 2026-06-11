"""
Tests for activities/event feed API endpoint.

GET /api/activities — list recent activity events.
"""

from __future__ import annotations

import json
import pytest

from pi_orchestrator import database as db


class TestListActivities:
    """GET /api/activities — list recent activities."""

    async def test_list_activities_empty(self, async_client):
        resp = await async_client.get("/api/activities")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_activities(self, async_client):
        agent = db.create_agent(name="activity-agent")
        db.record_activity(agent["id"], "session_start", agent["name"])
        db.record_activity(agent["id"], "session_end", agent["name"], {"turns": 5})

        resp = await async_client.get("/api/activities")
        data = resp.json()
        assert len(data) == 2
        assert len(data) == 2
        types = {d["event_type"] for d in data}
        assert types == {"session_start", "session_end"}

    async def test_list_activities_filter_by_agent(self, async_client):
        a1 = db.create_agent(name="act-a")
        a2 = db.create_agent(name="act-b")
        db.record_activity(a1["id"], "event_a1")
        db.record_activity(a1["id"], "event_a2")
        db.record_activity(a2["id"], "event_b1")

        resp = await async_client.get(f"/api/activities?agent_id={a1['id']}")
        data = resp.json()
        assert len(data) == 2
        assert all(a["agent_id"] == a1["id"] for a in data)

    async def test_list_activities_limit(self, async_client):
        agent = db.create_agent(name="limit-agent")
        for i in range(5):
            db.record_activity(agent["id"], f"event_{i}")

        resp = await async_client.get("/api/activities?limit=3")
        data = resp.json()
        assert len(data) == 3

    async def test_activity_event_data(self, async_client):
        agent = db.create_agent(name="data-agent")
        db.record_activity(agent["id"], "custom_event", agent["name"], {"key": "value", "count": 42})

        resp = await async_client.get("/api/activities")
        data = resp.json()
        entry = data[0]
        assert entry["agent_id"] == agent["id"]
        assert entry["agent_name"] == "data-agent"
        assert entry["event_type"] == "custom_event"
        assert json.loads(entry["event_data"]) == {"key": "value", "count": 42}
