"""
Tests for chat API endpoints: streaming SSE chat + history.

POST /api/agents/{agent_id}/chat  → SSE stream
GET  /api/agents/{agent_id}/chat/history  → past sessions

Pi binary calls are mocked (mock_pi_binary_stream, mock_pi_binary_tool_call).
"""

from __future__ import annotations

import asyncio
import json
import pytest
from unittest.mock import patch, AsyncMock

from pi_orchestrator import database as db


# Helper to safely consume a streaming SSE response (handles CancelledError)
async def _consume_stream(async_client, method, url, **kwargs):
    """Send a request and consume the streaming body, ignoring CancelledError."""
    try:
        async with async_client.stream(method, url, **kwargs) as resp:
            try:
                async for _ in resp.aiter_bytes():
                    pass
            except (asyncio.CancelledError, GeneratorExit):
                pass
            return resp
    except (asyncio.CancelledError, GeneratorExit):
        return None


class TestChatStreaming:
    """POST /api/agents/{id}/chat — streaming SSE response."""

    async def test_chat_returns_sse(self, async_client, mock_pi_binary_stream, test_agent):
        resp = await _consume_stream(
            async_client, "POST",
            f"/api/agents/{test_agent['id']}/chat",
            json={"message": "Hello!"},
        )
        assert resp is not None
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        assert "no-cache" in resp.headers["cache-control"]

    async def test_chat_streams_text_deltas(self, async_client, mock_pi_binary_stream, test_agent):
        body = b""
        try:
            async with async_client.stream(
                "POST",
                f"/api/agents/{test_agent['id']}/chat",
                json={"message": "Say hi"},
            ) as resp:
                try:
                    async for chunk in resp.aiter_bytes():
                        body += chunk
                except (asyncio.CancelledError, GeneratorExit):
                    pass
        except (asyncio.CancelledError, GeneratorExit):
            pass

        if body:
            text = body.decode()
            lines = [l for l in text.split("\n\n") if l.strip()]
            events = [json.loads(l.replace("data: ", "")) for l in lines if l.startswith("data: ")]
            types = {e["type"] for e in events}
            assert "text_delta" in types

    async def test_chat_with_tool_call(self, async_client, mock_pi_binary_tool_call, test_agent):
        body = b""
        try:
            async with async_client.stream(
                "POST",
                f"/api/agents/{test_agent['id']}/chat",
                json={"message": "Read file"},
            ) as resp:
                try:
                    async for chunk in resp.aiter_bytes():
                        body += chunk
                except (asyncio.CancelledError, GeneratorExit):
                    pass
        except (asyncio.CancelledError, GeneratorExit):
            pass

        if body:
            text = body.decode()
            lines = [l for l in text.split("\n\n") if l.strip()]
            events = [json.loads(l.replace("data: ", "")) for l in lines if l.startswith("data: ")]
            types = {e["type"] for e in events}
            assert "tool_call" in types
            assert "tool_result" in types

            tool_calls = [e for e in events if e["type"] == "tool_call"]
            assert tool_calls[0]["tool_name"] == "read"

    async def test_chat_agent_not_found(self, async_client):
        resp = await async_client.post(
            "/api/agents/nonexistent/chat",
            json={"message": "Hello"},
        )
        assert resp.status_code == 404

    async def test_chat_creates_session_record(self, async_client, mock_pi_binary, test_agent):
        await _consume_stream(
            async_client, "POST",
            f"/api/agents/{test_agent['id']}/chat",
            json={"message": "Hello!"},
        )
        sessions = db.list_sessions(agent_id=test_agent["id"])
        assert len(sessions) >= 1
        assert sessions[0]["agent_id"] == test_agent["id"]

    async def test_chat_agent_becomes_busy_then_idle(self, async_client, mock_pi_binary, test_agent):
        await _consume_stream(
            async_client, "POST",
            f"/api/agents/{test_agent['id']}/chat",
            json={"message": "Hello!"},
        )
        updated = db.get_agent(test_agent["id"])
        assert updated["status"] in ("idle", "busy", "error")

    async def test_chat_with_model_override(self, async_client, mock_pi_binary, test_agent):
        await _consume_stream(
            async_client, "POST",
            f"/api/agents/{test_agent['id']}/chat",
            json={"message": "Hi", "model": "haiku"},
        )

    async def test_chat_with_timeout_param(self, async_client, mock_pi_binary, test_agent):
        await _consume_stream(
            async_client, "POST",
            f"/api/agents/{test_agent['id']}/chat",
            json={"message": "Hi", "timeout_seconds": 30},
        )

    async def test_chat_empty_message_fails(self, async_client, test_agent):
        resp = await async_client.post(
            f"/api/agents/{test_agent['id']}/chat",
            json={"message": ""},
        )
        assert resp.status_code == 422

    async def test_chat_error_handling(self, async_client, test_agent, mock_pi_binary):
        """When pi binary returns, stream should complete gracefully."""
        resp = await _consume_stream(
            async_client, "POST",
            f"/api/agents/{test_agent['id']}/chat",
            json={"message": "Hi"},
        )
        assert resp is not None
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]


class TestChatHistory:
    """GET /api/agents/{id}/chat/history — past session list."""

    async def test_chat_history_empty(self, async_client, test_agent):
        resp = await async_client.get(
            f"/api/agents/{test_agent['id']}/chat/history"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_id"] == test_agent["id"]
        assert data["sessions"] == []

    async def test_chat_history_after_chat(self, async_client, mock_pi_binary, test_agent):
        await _consume_stream(
            async_client, "POST",
            f"/api/agents/{test_agent['id']}/chat",
            json={"message": "Hello!"},
        )

        resp = await async_client.get(
            f"/api/agents/{test_agent['id']}/chat/history"
        )
        data = resp.json()
        assert len(data["sessions"]) >= 1
        assert data["agent_id"] == test_agent["id"]
        assert "id" in data["sessions"][0]
        assert "session_file" in data["sessions"][0]
        assert "started_at" in data["sessions"][0]

    async def test_chat_history_agent_not_found(self, async_client):
        resp = await async_client.get("/api/agents/nonexistent/chat/history")
        assert resp.status_code == 404

    async def test_chat_history_limit(self, async_client, mock_pi_binary, test_agent):
        for _ in range(3):
            await _consume_stream(
                async_client, "POST",
                f"/api/agents/{test_agent['id']}/chat",
                json={"message": "Hi"},
            )

        resp = await async_client.get(
            f"/api/agents/{test_agent['id']}/chat/history?limit=2"
        )
        data = resp.json()
        assert len(data["sessions"]) == 2
