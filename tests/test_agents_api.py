"""
Tests for agents API endpoints (/api/agents/*).

Uses httpx.AsyncClient against the test FastAPI app.
Pi binary calls are mocked — no real subprocesses.
"""

from __future__ import annotations

import asyncio
import json
import pytest
from unittest.mock import patch, AsyncMock

from pi_orchestrator import database as db


class TestCreateAgent:
    """POST /api/agents — create a new agent."""

    async def test_create_agent(self, async_client, mock_pi_binary):
        payload = {
            "name": "my-agent",
            "model": "sonnet",
            "persona": "developer",
            "tools": ["read", "bash", "write"],
            "skills": ["python"],
            "extensions": ["my-ext"],
            "system_prompt": "You are a coding assistant.",
            "git_repo": "https://github.com/user/repo.git",
            "schedule": "0 9 * * *",
        }
        resp = await async_client.post("/api/agents", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "my-agent"
        assert data["model"] == "sonnet"
        assert data["persona"] == "developer"
        assert data["status"] in ("idle", "created")
        assert "id" in data
        assert "created_at" in data

    async def test_create_agent_minimal(self, async_client, mock_pi_binary):
        resp = await async_client.post("/api/agents", json={"name": "minimal"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "minimal"
        assert data["model"] == ""
        assert data["persona"] is None
        assert data["tokens_used"] == 0
        assert data["session_count"] == 0

    async def test_create_agent_empty_name_fails(self, async_client):
        resp = await async_client.post("/api/agents", json={"name": ""})
        assert resp.status_code == 422

    async def test_create_agent_invalid_name_fails(self, async_client):
        resp = await async_client.post("/api/agents", json={"name": "bad name!"})
        assert resp.status_code == 422

    async def test_create_agent_duplicate_fails(self, async_client, mock_pi_binary):
        await async_client.post("/api/agents", json={"name": "dupe"})
        resp = await async_client.post("/api/agents", json={"name": "dupe"})
        assert resp.status_code == 400

    async def test_create_agent_emits_event(self, async_client, mock_pi_binary):
        events = []
        from pi_orchestrator.services.event_bus import event_bus

        async def collector(event):
            events.append(event)

        event_bus.subscribe(collector)
        await async_client.post("/api/agents", json={"name": "event-test"})
        await asyncio.sleep(0.05)
        assert len(events) >= 1
        assert events[0]["type"] == "agent_created"
        assert events[0]["data"]["name"] == "event-test"

    async def test_create_agent_records_activity(self, async_client, mock_pi_binary):
        await async_client.post("/api/agents", json={"name": "activity-check"})
        activities = db.list_activities()
        assert len(activities) >= 1
        assert activities[0]["event_type"] == "agent_created"


class TestListAgents:
    """GET /api/agents — list all agents."""

    async def test_list_agents_empty(self, async_client):
        resp = await async_client.get("/api/agents")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_agents(self, async_client, mock_pi_binary):
        await async_client.post("/api/agents", json={"name": "alpha"})
        await async_client.post("/api/agents", json={"name": "beta"})

        resp = await async_client.get("/api/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        names = {a["name"] for a in data}
        assert names == {"alpha", "beta"}

    async def test_list_agents_filter_by_status(self, async_client, mock_pi_binary):
        await async_client.post("/api/agents", json={"name": "running-agent"})
        # Manually set status to running
        agents = db.list_agents()
        db.update_agent_status(agents[0]["id"], "running")

        resp = await async_client.get("/api/agents?status=running")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "running-agent"

        resp = await async_client.get("/api/agents?status=idle")
        assert len(resp.json()) == 0


class TestGetAgent:
    """GET /api/agents/{id} — get agent details."""

    async def test_get_agent(self, async_client, mock_pi_binary):
        create_resp = await async_client.post("/api/agents", json={
            "name": "detail-agent",
            "model": "sonnet",
            "tools": ["read", "bash"],
            "skills": ["python"],
            "system_prompt": "Be helpful.",
        })
        agent_id = create_resp.json()["id"]

        resp = await async_client.get(f"/api/agents/{agent_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "detail-agent"
        assert data["model"] == "sonnet"
        assert data["tools"] == ["read", "bash"]
        assert data["skills"] == ["python"]
        assert data["system_prompt"] == "Be helpful."
        assert "tokens_used" in data
        assert "session_count" in data

    async def test_get_agent_not_found(self, async_client):
        resp = await async_client.get("/api/agents/nonexistent")
        assert resp.status_code == 404
        assert "not found" in resp.text.lower()

    async def test_get_agent_with_schedule(self, async_client, mock_pi_binary):
        create_resp = await async_client.post("/api/agents", json={
            "name": "scheduled-agent",
            "schedule": "0 9 * * *",
        })
        agent_id = create_resp.json()["id"]

        resp = await async_client.get(f"/api/agents/{agent_id}")
        data = resp.json()
        assert data["schedule"] == "0 9 * * *"


class TestDeleteAgent:
    """DELETE /api/agents/{id} — delete an agent."""

    async def test_delete_agent(self, async_client, mock_pi_binary):
        create_resp = await async_client.post("/api/agents", json={"name": "delete-me"})
        agent_id = create_resp.json()["id"]

        resp = await async_client.delete(f"/api/agents/{agent_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

        # Verify it's gone
        get_resp = await async_client.get(f"/api/agents/{agent_id}")
        assert get_resp.status_code == 404

    async def test_delete_agent_not_found(self, async_client):
        resp = await async_client.delete("/api/agents/nonexistent")
        assert resp.status_code == 404

    async def test_delete_agent_emits_event(self, async_client, mock_pi_binary):
        events = []
        from pi_orchestrator.services.event_bus import event_bus

        async def collector(event):
            events.append(event)

        create_resp = await async_client.post("/api/agents", json={"name": "event-delete"})
        agent_id = create_resp.json()["id"]

        event_bus.subscribe(collector)
        await async_client.delete(f"/api/agents/{agent_id}")
        await asyncio.sleep(0.05)
        assert any(e["type"] == "agent_deleted" for e in events)

    async def test_delete_agent_records_activity(self, async_client, mock_pi_binary):
        create_resp = await async_client.post("/api/agents", json={"name": "activity-delete"})
        agent_id = create_resp.json()["id"]

        await async_client.delete(f"/api/agents/{agent_id}")
        activities = db.list_activities()
        assert any(a["event_type"] == "agent_deleted" for a in activities)
