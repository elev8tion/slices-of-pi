"""Tests for credentials API (Track A1 — write path must not crash)."""

from __future__ import annotations

import pytest


class TestCredentials:
    async def test_set_list_delete_credential(self, async_client, mock_pi_binary):
        create = await async_client.post("/api/agents", json={"name": "cred-agent"})
        assert create.status_code == 201
        agent_id = create.json()["id"]

        set_resp = await async_client.post(
            f"/api/agents/{agent_id}/credentials",
            json={"name": "OPENAI_API_KEY", "value": "sk-test-secret"},
        )
        assert set_resp.status_code == 201
        data = set_resp.json()
        assert data["name"] == "OPENAI_API_KEY"
        assert data["value"] == "••••••••"

        listed = await async_client.get(f"/api/agents/{agent_id}/credentials")
        assert listed.status_code == 200
        creds = listed.json()["credentials"]
        assert any(c["name"] == "OPENAI_API_KEY" for c in creds)

        deleted = await async_client.delete(
            f"/api/agents/{agent_id}/credentials/OPENAI_API_KEY"
        )
        assert deleted.status_code == 200
        assert deleted.json()["status"] == "deleted"

    async def test_set_missing_agent(self, async_client):
        resp = await async_client.post(
            "/api/agents/nope/credentials",
            json={"name": "X", "value": "y"},
        )
        assert resp.status_code == 404

    async def test_values_requires_reveal(self, async_client, mock_pi_binary):
        create = await async_client.post("/api/agents", json={"name": "reveal-agent"})
        agent_id = create.json()["id"]
        await async_client.post(
            f"/api/agents/{agent_id}/credentials",
            json={"name": "SECRET_KEY", "value": "super-secret"},
        )
        # Casual GET without reveal=1
        bare = await async_client.get(f"/api/agents/{agent_id}/credentials/values")
        assert bare.status_code == 400

        # Operator confirm
        revealed = await async_client.get(
            f"/api/agents/{agent_id}/credentials/values?reveal=1"
        )
        assert revealed.status_code == 200
        assert revealed.json()["SECRET_KEY"] == "super-secret"
