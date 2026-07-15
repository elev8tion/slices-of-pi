"""
Tests for session history API endpoints.

GET  /api/sessions          — list sessions (optional agent_id, status filters)
GET  /api/sessions/{id}     — session metadata + message history from JSONL
GET  /api/sessions/{id}/export  — download raw JSONL file
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from pi_orchestrator import database as db
from pi_orchestrator.config import PI_MANAGED_SESSIONS_DIR


class TestListSessions:
    """GET /api/sessions — list sessions."""

    async def test_list_sessions_empty(self, async_client):
        resp = await async_client.get("/api/sessions")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_sessions(self, async_client, test_agent, test_session):
        resp = await async_client.get("/api/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["agent_id"] == test_agent["id"]
        assert data[0]["agent_name"] == test_agent["name"]
        assert data[0]["status"] == "running"
        assert data[0]["model"] == "sonnet"

    async def test_list_sessions_filter_by_agent(self, async_client, test_agent, test_session):
        # Create another agent with no sessions
        other = db.create_agent(name="other-agent")

        resp = await async_client.get(f"/api/sessions?agent_id={test_agent['id']}")
        data = resp.json()
        assert len(data) == 1

        resp = await async_client.get(f"/api/sessions?agent_id={other['id']}")
        assert resp.json() == []

    async def test_list_sessions_filter_by_status(self, async_client, test_agent, test_session):
        resp = await async_client.get("/api/sessions?status=running")
        assert len(resp.json()) == 1

        resp = await async_client.get("/api/sessions?status=completed")
        assert resp.json() == []

    async def test_list_sessions_limit(self, async_client, test_agent):
        for i in range(3):
            db.create_session(
                agent_id=test_agent["id"],
                agent_name=test_agent["name"],
                session_file=f"/tmp/s{i}.jsonl",
                model="sonnet",
            )

        resp = await async_client.get("/api/sessions?limit=2")
        data = resp.json()
        assert len(data) == 2

    async def test_list_sessions_returns_sorted(self, async_client, test_agent):
        db.create_session(test_agent["id"], test_agent["name"], "/tmp/old.jsonl", "sonnet")
        db.create_session(test_agent["id"], test_agent["name"], "/tmp/new.jsonl", "sonnet")

        resp = await async_client.get("/api/sessions")
        data = resp.json()
        # Most recent first
        assert len(data) >= 2


class TestGetSession:
    """GET /api/sessions/{id} — session with messages."""

    async def test_get_session(self, async_client, test_session):
        resp = await async_client.get(f"/api/sessions/{test_session['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == test_session["id"]
        assert data["agent_id"] == test_session["agent_id"]
        assert data["agent_name"] == test_session["agent_name"]
        assert data["status"] == "running"
        assert data["model"] == "sonnet"
        assert "messages" in data

    async def test_get_session_not_found(self, async_client):
        resp = await async_client.get("/api/sessions/nonexistent")
        assert resp.status_code == 404

    async def test_get_session_with_messages(self, async_client, test_agent):
        # Create a session with a real JSONL file
        session_dir = PI_MANAGED_SESSIONS_DIR / test_agent["name"]
        session_dir.mkdir(parents=True, exist_ok=True)
        session_file = session_dir / "test_messages.jsonl"

        with open(session_file, "w") as f:
            f.write(json.dumps({"type": "message_start", "message": {"role": "assistant", "content": []}}) + "\n")
            f.write(json.dumps({"type": "message_update", "assistantMessageEvent": {"type": "text_delta", "delta": "Hello"}}) + "\n")
            f.write(json.dumps({"type": "tool_call", "tool_name": "read", "input": {"path": "/tmp/x"}}) + "\n")

        session = db.create_session(
            agent_id=test_agent["id"],
            agent_name=test_agent["name"],
            session_file=str(session_file),
            model="sonnet",
        )

        resp = await async_client.get(f"/api/sessions/{session['id']}")
        data = resp.json()
        # C2: message_update included for chat hydration (text deltas)
        assert len(data["messages"]) == 3
        assert data["messages"][0]["type"] == "message_start"
        assert data["messages"][1]["type"] == "message_update"
        assert data["messages"][-1]["type"] == "tool_call"

    async def test_get_session_missing_file(self, async_client, test_session):
        """If session file doesn't exist, should still return metadata."""
        resp = await async_client.get(f"/api/sessions/{test_session['id']}")
        data = resp.json()
        assert data["messages"] == []


class TestExportSession:
    """GET /api/sessions/{id}/export — download JSONL."""

    async def test_export_session(self, async_client, test_agent):
        # Create a session with a real file
        session_dir = PI_MANAGED_SESSIONS_DIR / test_agent["name"]
        session_dir.mkdir(parents=True, exist_ok=True)
        session_file = session_dir / "export_test.jsonl"
        session_file.write_text(
            json.dumps({"type": "test", "msg": "hello"}) + "\n" +
            json.dumps({"type": "test", "msg": "world"}) + "\n"
        )

        session = db.create_session(
            agent_id=test_agent["id"],
            agent_name=test_agent["name"],
            session_file=str(session_file),
            model="sonnet",
        )

        resp = await async_client.get(f"/api/sessions/{session['id']}/export")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/x-ndjson"
        lines = resp.text.strip().split("\n")
        assert len(lines) >= 2

    async def test_export_session_not_found(self, async_client):
        resp = await async_client.get("/api/sessions/nonexistent/export")
        assert resp.status_code == 404

    async def test_export_session_file_missing(self, async_client, test_session):
        """Session record exists but file is missing."""
        resp = await async_client.get(f"/api/sessions/{test_session['id']}/export")
        assert resp.status_code == 404
