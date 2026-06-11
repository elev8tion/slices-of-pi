"""
Tests for the health endpoint.

GET /health — returns system status, agent/session counts.
"""

from __future__ import annotations

import pytest
from pi_orchestrator import database as db


class TestHealthEndpoint:
    """GET /health — system health check."""

    async def test_health_ok(self, async_client):
        resp = await async_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == "0.1.0"
        assert data["agent_count"] == 0
        assert data["active_session_count"] == 0

    async def test_health_with_agents(self, async_client):
        db.create_agent(name="health-agent-1")
        db.create_agent(name="health-agent-2")

        resp = await async_client.get("/health")
        data = resp.json()
        assert data["agent_count"] == 2

    async def test_health_with_active_sessions(self, async_client):
        agent = db.create_agent(name="health-session")
        db.create_session(agent["id"], agent["name"], "/tmp/s.jsonl", "sonnet")

        resp = await async_client.get("/health")
        data = resp.json()
        assert data["active_session_count"] == 1

    async def test_health_completed_sessions_not_counted(self, async_client):
        agent = db.create_agent(name="health-completed")
        s1 = db.create_session(agent["id"], agent["name"], "/tmp/s1.jsonl", "sonnet")
        db.update_session(s1["id"], status="completed")
        db.create_session(agent["id"], agent["name"], "/tmp/s2.jsonl", "sonnet")

        resp = await async_client.get("/health")
        data = resp.json()
        assert data["active_session_count"] == 1

    async def test_health_method_not_allowed(self, async_client):
        resp = await async_client.post("/health")
        assert resp.status_code == 405
