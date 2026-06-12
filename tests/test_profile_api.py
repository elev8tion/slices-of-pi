"""
Tests for agent profile API endpoints.
"""

from __future__ import annotations


class TestGetProfile:
    """GET /api/agents/{id}/profile"""

    async def test_get_profile_returns_profile(self, async_client, test_agent):
        """Profile endpoint returns profile data for existing agent."""
        resp = await async_client.get(f"/api/agents/{test_agent['id']}/profile")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_id"] == test_agent["id"]
        assert "profile" in data
        assert "preview" in data
        assert data["static_count"] >= 0
        assert data["dynamic_count"] >= 0

    async def test_get_profile_not_found(self, async_client):
        """Profile endpoint returns 404 for nonexistent agent."""
        resp = await async_client.get("/api/agents/nonexistent/profile")
        assert resp.status_code == 404

    async def test_get_profile_has_preview(self, async_client, test_agent):
        """Profile preview should be markdown-formatted."""
        from pi_orchestrator import database as db
        db.append_agent_memory(test_agent["id"], "Working on auth module")
        db.append_agent_memory(test_agent["id"], "Fixed SQLite connection")

        resp = await async_client.get(f"/api/agents/{test_agent['id']}/profile")
        data = resp.json()
        assert data["dynamic_count"] >= 1
        assert "Recent Context" in (data.get("preview") or "")


class TestForgetFact:
    """DELETE /api/agents/{id}/profile/fact"""

    async def test_forget_existing_fact(self, async_client, test_agent):
        """Forget a fact that exists in the profile."""
        from pi_orchestrator import database as db
        db.append_agent_memory(test_agent["id"], "Test fact to forget")

        resp = await async_client.post(
            f"/api/agents/{test_agent['id']}/profile/fact/forget",
            json={"fact": "Test fact to forget"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "forgotten"

        # Verify it's gone
        profile = db.get_agent_profile(test_agent["id"])
        assert "Test fact to forget" not in profile.get("dynamic", [])

    async def test_forget_nonexistent_fact_returns_404(self, async_client, test_agent):
        """Forget a fact that doesn't exist."""
        resp = await async_client.post(
            f"/api/agents/{test_agent['id']}/profile/fact/forget",
            json={"fact": "This fact does not exist"},
        )
        assert resp.status_code == 404

    async def test_forget_missing_fact_field_returns_400(self, async_client, test_agent):
        """Forget without fact field returns 400."""
        resp = await async_client.post(
            f"/api/agents/{test_agent['id']}/profile/fact/forget",
            json={},
        )
        assert resp.status_code == 400
