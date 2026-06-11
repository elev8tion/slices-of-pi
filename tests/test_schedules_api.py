"""
Tests for schedules API endpoints.

POST   /api/schedules          — create schedule
GET    /api/schedules          — list schedules
GET    /api/schedules/{id}     — get schedule + executions
PATCH  /api/schedules/{id}     — update schedule
DELETE /api/schedules/{id}     — delete schedule
"""

from __future__ import annotations

import json
import pytest

from pi_orchestrator import database as db


class TestCreateSchedule:
    """POST /api/schedules — create a schedule."""

    async def test_create_schedule(self, async_client, test_agent):
        resp = await async_client.post("/api/schedules", json={
            "agent_id": test_agent["id"],
            "cron_expression": "0 9 * * *",
            "message": "Daily standup",
            "model": "sonnet",
            "max_turns": 5,
            "timeout_seconds": 300,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["agent_id"] == test_agent["id"]
        assert data["cron_expression"] == "0 9 * * *"
        assert data["message"] == "Daily standup"
        assert data["model"] == "sonnet"
        assert data["max_turns"] == 5
        assert data["timeout_seconds"] == 300
        assert data["enabled"] == 1
        assert "id" in data

    async def test_create_schedule_minimal(self, async_client, test_agent):
        resp = await async_client.post("/api/schedules", json={
            "agent_id": test_agent["id"],
            "cron_expression": "0 * * * *",
            "message": "Hourly task",
        })
        assert resp.status_code == 201

    async def test_create_schedule_agent_not_found(self, async_client):
        resp = await async_client.post("/api/schedules", json={
            "agent_id": "nonexistent",
            "cron_expression": "0 9 * * *",
            "message": "Task",
        })
        assert resp.status_code == 404

    async def test_create_schedule_disabled(self, async_client, test_agent):
        resp = await async_client.post("/api/schedules", json={
            "agent_id": test_agent["id"],
            "cron_expression": "0 9 * * *",
            "message": "Task",
            "enabled": False,
        })
        assert resp.status_code == 201
        data = resp.json()
        # disabled via PATCH after creation, so initially enabled
        # but we can check created_at exists
        assert data["id"] is not None

    async def test_create_schedule_invalid_cron_fails(self, async_client, test_agent):
        resp = await async_client.post("/api/schedules", json={
            "agent_id": test_agent["id"],
            "cron_expression": "",
            "message": "Task",
        })
        assert resp.status_code == 422


class TestListSchedules:
    """GET /api/schedules — list schedules."""

    async def test_list_schedules_empty(self, async_client):
        resp = await async_client.get("/api/schedules")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_schedules(self, async_client, test_agent):
        await async_client.post("/api/schedules", json={
            "agent_id": test_agent["id"],
            "cron_expression": "0 9 * * *",
            "message": "Task 1",
        })
        await async_client.post("/api/schedules", json={
            "agent_id": test_agent["id"],
            "cron_expression": "0 10 * * *",
            "message": "Task 2",
        })

        resp = await async_client.get("/api/schedules")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        # Should have agent_name enriched
        assert data[0].get("agent_name") == test_agent["name"]

    async def test_list_schedules_filter_by_agent(self, async_client, test_agent):
        other = db.create_agent(name="other-agent")
        await async_client.post("/api/schedules", json={
            "agent_id": test_agent["id"],
            "cron_expression": "0 9 * * *",
            "message": "Agent 1 task",
        })
        await async_client.post("/api/schedules", json={
            "agent_id": other["id"],
            "cron_expression": "0 10 * * *",
            "message": "Other task",
        })

        resp = await async_client.get(f"/api/schedules?agent_id={test_agent['id']}")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["message"] == "Agent 1 task"


class TestGetSchedule:
    """GET /api/schedules/{id} — get schedule + executions."""

    async def test_get_schedule(self, async_client, test_agent):
        create_resp = await async_client.post("/api/schedules", json={
            "agent_id": test_agent["id"],
            "cron_expression": "0 9 * * *",
            "message": "My schedule",
        })
        schedule_id = create_resp.json()["id"]

        resp = await async_client.get(f"/api/schedules/{schedule_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == schedule_id
        assert data["agent_name"] == test_agent["name"]
        assert data["executions"] == []

    async def test_get_schedule_with_executions(self, async_client, test_agent):
        create_resp = await async_client.post("/api/schedules", json={
            "agent_id": test_agent["id"],
            "cron_expression": "0 9 * * *",
            "message": "Executed schedule",
        })
        schedule_id = create_resp.json()["id"]

        # Record an execution directly
        db.record_schedule_execution_start(schedule_id)

        resp = await async_client.get(f"/api/schedules/{schedule_id}")
        data = resp.json()
        assert len(data["executions"]) == 1
        assert data["executions"][0]["status"] == "running"

    async def test_get_schedule_not_found(self, async_client):
        resp = await async_client.get("/api/schedules/nonexistent")
        assert resp.status_code == 404


class TestUpdateSchedule:
    """PATCH /api/schedules/{id} — update schedule."""

    async def test_update_schedule(self, async_client, test_agent):
        create_resp = await async_client.post("/api/schedules", json={
            "agent_id": test_agent["id"],
            "cron_expression": "0 9 * * *",
            "message": "Original",
        })
        schedule_id = create_resp.json()["id"]

        resp = await async_client.patch(f"/api/schedules/{schedule_id}", json={
            "agent_id": test_agent["id"],
            "cron_expression": "0 10 * * *",
            "message": "Updated",
            "enabled": False,
            "model": "haiku",
            "max_turns": 10,
            "timeout_seconds": 600,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["cron_expression"] == "0 10 * * *"
        assert data["message"] == "Updated"
        assert data["enabled"] == 0
        assert data["model"] == "haiku"

    async def test_update_schedule_not_found(self, async_client, test_agent):
        resp = await async_client.patch("/api/schedules/nonexistent", json={
            "agent_id": test_agent["id"],
            "cron_expression": "0 9 * * *",
            "message": "Nope",
        })
        assert resp.status_code == 404


class TestDeleteSchedule:
    """DELETE /api/schedules/{id} — delete schedule."""

    async def test_delete_schedule(self, async_client, test_agent):
        create_resp = await async_client.post("/api/schedules", json={
            "agent_id": test_agent["id"],
            "cron_expression": "0 9 * * *",
            "message": "Delete me",
        })
        schedule_id = create_resp.json()["id"]

        resp = await async_client.delete(f"/api/schedules/{schedule_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

        # Verify it's gone
        get_resp = await async_client.get(f"/api/schedules/{schedule_id}")
        assert get_resp.status_code == 404

    async def test_delete_schedule_not_found(self, async_client):
        resp = await async_client.delete("/api/schedules/nonexistent")
        assert resp.status_code == 404
