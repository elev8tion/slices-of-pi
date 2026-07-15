"""
Tests for Voice service, router endpoint, and session persistence.
Uses conftest fixtures: async_client, test_agent, clear_db.
"""

import pytest
from pi_orchestrator import database as db


class TestVoiceRouter:
    """Voice process endpoint."""

    @pytest.mark.asyncio
    async def test_voice_process_endpoint_registered(self, async_client):
        routes = [r.path for r in async_client._transport.app.routes]
        assert "/api/voice/process" in routes

    @pytest.mark.asyncio
    async def test_voice_process_requires_agent_id(self, async_client):
        r = await async_client.post("/api/voice/process", json={"transcript": "hello"})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_voice_process_requires_transcript(self, async_client):
        r = await async_client.post("/api/voice/process", json={"agent_id": "test"})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_voice_process_missing_agent(self, async_client):
        r = await async_client.post("/api/voice/process", json={
            "agent_id": "nonexistent-agent-12345",
            "transcript": "Hello, can you help me?",
        })
        assert r.status_code == 500
        data = r.json()
        assert "error" in data["detail"].lower() or "not found" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_voice_process_valid_request(self, async_client, test_agent, mock_pi_binary_stream):
        r = await async_client.post("/api/voice/process", json={
            "agent_id": test_agent["id"],
            "transcript": "What is 2+2?",
        })
        assert r.status_code == 200
        data = r.json()
        assert "response" in data
        assert "session_id" in data
        assert len(data["response"]) > 0

    @pytest.mark.asyncio
    async def test_voice_process_accepts_optional_fields(self, async_client, test_agent, mock_pi_binary_stream):
        r = await async_client.post("/api/voice/process", json={
            "agent_id": test_agent["id"],
            "transcript": "Hello",
            "session_id": "nonexistent-session",
            "model": "claude-sonnet-4-5",
        })
        assert r.status_code == 200
        data = r.json()
        assert "response" in data


class TestVoiceService:
    """Voice orchestration service."""

    def test_imports(self):
        from pi_orchestrator.services.voice_service import process_voice_transcript
        import inspect
        assert inspect.iscoroutinefunction(process_voice_transcript)

    def test_process_voice_transcript_missing_agent(self):
        import asyncio
        from pi_orchestrator.services.voice_service import process_voice_transcript

        result = asyncio.run(process_voice_transcript(
            agent_id="nonexistent-agent",
            transcript="Hello",
        ))
        assert "error" in result
        assert "not found" in result["error"].lower()


class TestVoiceSessionPersistence:
    """End-to-end: voice creates session that appears in session list."""

    @pytest.mark.asyncio
    async def test_voice_session_appears_in_list(self, async_client, test_agent, mock_pi_binary_stream):
        r = await async_client.post("/api/voice/process", json={
            "agent_id": test_agent["id"],
            "transcript": "List test",
        })
        assert r.status_code == 200
        data = r.json()
        session_id = data["session_id"]

        sessions = db.list_sessions(agent_id=test_agent["id"])
        ids = [s["id"] for s in sessions]
        assert session_id in ids

    @pytest.mark.asyncio
    async def test_voice_appends_agent_memory(self, async_client, test_agent, mock_pi_binary_stream):
        r = await async_client.post("/api/voice/process", json={
            "agent_id": test_agent["id"],
            "transcript": "Remember this important fact: the sky is blue",
        })
        assert r.status_code == 200

        profile = db.get_agent_profile(test_agent["id"])
        dynamic = profile.get("dynamic", [])
        voice_facts = [f for f in dynamic if "[voice]" in f]
        assert len(voice_facts) >= 1


class TestVoiceWorkspaceFrontend:
    """Frontend integration checks."""

    def test_voice_workspace_calls_orchestration_endpoint(self):
        import os
        path = os.path.join(
            os.path.dirname(__file__), "..", "dashboard", "src", "components", "VoiceWorkspace.vue"
        )
        with open(path) as f:
            content = f.read()
        assert "/api/voice/process" in content
        assert "agent_id: props.agentId" in content
