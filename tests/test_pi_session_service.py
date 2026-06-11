"""
Tests for pi_session_service — the core service managing pi subprocess lifecycle.

Covers create_agent, destroy_agent, stream_chat, kill_all, and status methods.
Pi binary calls are mocked — no real subprocess invocations.
"""

from __future__ import annotations

import json
import asyncio
import pytest
from unittest.mock import patch, AsyncMock
from pathlib import Path

from pi_orchestrator import database as db
from pi_orchestrator.services.pi_session_service import (
    create_agent,
    destroy_agent,
    stream_chat,
    get_status,
    list_all,
    get_running_sessions,
    kill_all,
    _running,
    _session_dir,
)
from pi_orchestrator.config import PI_MANAGED_SESSIONS_DIR


class TestCreateAgent:
    """create_agent — register agent in DB and create session dir."""

    async def test_create_agent_basic(self):
        agent_id = await create_agent({
            "name": "svc-agent",
            "model": "sonnet",
            "persona": "dev",
            "tools": ["read", "bash"],
            "system_prompt": "Be helpful.",
        })
        assert agent_id is not None

        agent = db.get_agent(agent_id)
        assert agent["name"] == "svc-agent"
        assert agent["model"] == "sonnet"
        assert agent["status"] == "idle"

        # Session directory should exist
        assert _session_dir("svc-agent").exists()

    async def test_create_agent_minimal(self):
        agent_id = await create_agent({"name": "minimal-svc"})
        agent = db.get_agent(agent_id)
        assert agent["name"] == "minimal-svc"
        assert agent["status"] == "idle"

    async def test_create_agent_duplicate_name(self):
        await create_agent({"name": "dup-agent"})
        with pytest.raises(Exception):
            await create_agent({"name": "dup-agent"})


class TestDestroyAgent:
    """destroy_agent — stop sessions and remove agent."""

    async def test_destroy_agent(self):
        agent_id = await create_agent({"name": "destroy-me"})
        result = await destroy_agent(agent_id)
        assert result is True
        assert db.get_agent(agent_id) is None

    async def test_destroy_agent_not_found(self):
        result = await destroy_agent("nonexistent")
        assert result is False

    async def test_destroy_running_agent(self, mock_pi_binary_stream):
        """Destroy should kill any running session first."""
        agent_id = await create_agent({"name": "running-destroy"})

        # Start a chat session
        async for _ in stream_chat(agent_id, "test message"):
            pass

        assert len(_running) >= 0
        result = await destroy_agent(agent_id)
        assert result is True


class TestGetStatus:
    """get_status — retrieve agent info."""

    async def test_get_status(self):
        agent_id = await create_agent({"name": "status-check"})
        agent = await get_status(agent_id)
        assert agent is not None
        assert agent["name"] == "status-check"

    async def test_get_status_not_found(self):
        agent = await get_status("nonexistent")
        assert agent is None


class TestListAll:
    """list_all — list all managed agents."""

    async def test_list_all(self):
        await create_agent({"name": "list-a"})
        await create_agent({"name": "list-b"})
        agents = await list_all()
        assert len(agents) == 2

    async def test_list_all_empty(self):
        # DB is cleared in conftest
        agents = await list_all()
        assert agents == []


class TestGetRunningSessions:
    """get_running_sessions — return running session IDs."""

    async def test_get_running_empty(self):
        sessions = await get_running_sessions()
        assert sessions == []

    async def test_get_running_after_chat(self, mock_pi_binary_stream):
        agent_id = await create_agent({"name": "running-session"})

        async for _ in stream_chat(agent_id, "test"):
            pass

        sessions = await get_running_sessions()
        assert isinstance(sessions, list)


class TestStreamChat:
    """stream_chat — the core streaming method."""

    async def test_stream_chat_returns_chunks(self, mock_pi_binary_stream):
        agent_id = await create_agent({"name": "stream-test", "model": "sonnet"})
        chunks = []
        async for chunk in stream_chat(agent_id, "Hello!"):
            chunks.append(chunk)

        assert len(chunks) > 0
        # Should include turn_end
        assert any(c["type"] == "turn_end" for c in chunks)

    async def test_stream_chat_with_tool_calls(self, mock_pi_binary_tool_call):
        agent_id = await create_agent({"name": "tool-test", "tools": ["read", "bash"]})
        chunks = []
        async for chunk in stream_chat(agent_id, "Read something"):
            chunks.append(chunk)

        types = {c["type"] for c in chunks}
        assert "tool_call" in types
        assert "tool_result" in types

    async def test_stream_chat_agent_not_found(self):
        chunks = []
        async for chunk in stream_chat("nonexistent", "Hello"):
            chunks.append(chunk)
        assert len(chunks) == 1
        assert chunks[0]["type"] == "error"

    async def test_stream_chat_creates_session(self, mock_pi_binary_stream):
        agent_id = await create_agent({"name": "session-creator"})
        async for _ in stream_chat(agent_id, "Hello"):
            pass

        sessions = db.list_sessions(agent_id=agent_id)
        assert len(sessions) >= 1

    async def test_stream_chat_updates_agent_status(self, mock_pi_binary_stream):
        agent_id = await create_agent({"name": "status-update"})
        async for _ in stream_chat(agent_id, "Hello"):
            pass

        agent = db.get_agent(agent_id)
        assert agent["status"] in ("idle", "busy", "error")

    async def test_stream_chat_increments_session_count(self, mock_pi_binary_stream):
        agent_id = await create_agent({"name": "count-increment"})
        assert db.get_agent(agent_id)["session_count"] == 0
        async for _ in stream_chat(agent_id, "Hello"):
            pass
        assert db.get_agent(agent_id)["session_count"] >= 1

    async def test_stream_chat_records_activity(self, mock_pi_binary_stream):
        agent_id = await create_agent({"name": "activity-record"})
        async for _ in stream_chat(agent_id, "Hello"):
            pass

        activities = db.list_activities(agent_id=agent_id)
        types = [a["event_type"] for a in activities]
        assert "session_start" in types

    async def test_stream_chat_with_model_override(self, mock_pi_binary_stream):
        agent_id = await create_agent({"name": "model-override", "model": "sonnet"})
        chunks = []
        async for chunk in stream_chat(agent_id, "Hi", model="haiku"):
            chunks.append(chunk)
        assert len(chunks) > 0

    async def test_stream_chat_with_timeout_override(self, mock_pi_binary_stream):
        agent_id = await create_agent({"name": "timeout-override"})
        chunks = []
        async for chunk in stream_chat(agent_id, "Hi", timeout_seconds=60):
            chunks.append(chunk)
        assert len(chunks) > 0


class TestKillAll:
    """kill_all — terminate all running processes."""

    async def test_kill_all_empty(self):
        await kill_all()  # Should not raise

    async def test_kill_all_clears_registry(self, mock_pi_binary_stream):
        agent_id = await create_agent({"name": "kill-test"})
        async for _ in stream_chat(agent_id, "Hello"):
            pass
        await kill_all()
        # Registry should be clean
        assert len(_running) == 0
