"""
Tests for teams API endpoints.

GET  /api/teams               — list all teams with member details
POST /api/teams/{name}/deploy — deploy all agents in a team
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from pi_orchestrator.config import PI_AGENTS_CONFIG_DIR


@pytest.fixture(autouse=True)
def setup_teams():
    """Create teams.yaml and persona files for team tests."""
    PI_AGENTS_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Personas
    (PI_AGENTS_CONFIG_DIR / "frontend-dev.md").write_text(
        "---\nname: Frontend Dev\ndescription: Builds UI components\n"
        "tools:\n  - read\n  - bash\nmodel: sonnet\n---\n"
    )
    (PI_AGENTS_CONFIG_DIR / "backend-dev.md").write_text(
        "---\nname: Backend Dev\ndescription: Builds API services\n"
        "tools:\n  - read\n  - bash\n  - write\nmodel: haiku\n---\n"
    )
    (PI_AGENTS_CONFIG_DIR / "qa-engineer.md").write_text(
        "---\nname: QA Engineer\ndescription: Writes and runs tests\n"
        "tools:\n  - read\n  - bash\nmodel: sonnet\nskills:\n  - pytest\n---\n"
    )

    # Teams config
    teams = {
        "web-app-team": ["Frontend Dev", "Backend Dev"],
        "qa-team": ["QA Engineer"],
    }
    (PI_AGENTS_CONFIG_DIR / "teams.yaml").write_text(
        "web-app-team:\n  - Frontend Dev\n  - Backend Dev\n"
        "qa-team:\n  - QA Engineer\n"
    )
    yield


class TestListTeams:
    """GET /api/teams — list teams with member details."""

    async def test_list_teams(self, async_client):
        resp = await async_client.get("/api/teams")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        names = {t["name"] for t in data["teams"]}
        assert names == {"web-app-team", "qa-team"}

    async def test_team_member_details(self, async_client):
        resp = await async_client.get("/api/teams")
        data = resp.json()
        web_app = [t for t in data["teams"] if t["name"] == "web-app-team"][0]
        assert web_app["count"] == 2
        members = {m["name"] for m in web_app["members"]}
        assert members == {"Frontend Dev", "Backend Dev"}

        # Check member details are populated from persona files
        frontend = [m for m in web_app["members"] if m["name"] == "Frontend Dev"][0]
        assert frontend["model"] == "sonnet"
        assert frontend["tools"] == ["read", "bash"]
        assert frontend["description"] == "Builds UI components"

    async def test_list_teams_without_teams_file(self, async_client, setup_teams):
        """If teams.yaml doesn't exist, return empty."""
        # Remove teams.yaml temporarily
        teams_file = PI_AGENTS_CONFIG_DIR / "teams.yaml"
        teams_file.unlink()

        resp = await async_client.get("/api/teams")
        data = resp.json()
        assert data["teams"] == []
        assert data["count"] == 0

    async def test_team_methods(self, async_client):
        """DELETE/PUT should not be allowed."""
        resp = await async_client.delete("/api/teams")
        assert resp.status_code == 405


class TestDeployTeam:
    """POST /api/teams/{name}/deploy — create agents from team."""

    async def test_deploy_team(self, async_client):
        """Deploy creates agents in the database."""
        resp = await async_client.post("/api/teams/web-app-team/deploy")
        assert resp.status_code == 201
        data = resp.json()
        assert data["team"] == "web-app-team"
        assert data["count"] == 2
        names = {d["name"] for d in data["deployed"]}
        assert names == {"Frontend Dev", "Backend Dev"}
        for d in data["deployed"]:
            assert "id" in d
            assert "error" not in d

    async def test_deploy_team_not_found(self, async_client):
        resp = await async_client.post("/api/teams/nonexistent-team/deploy")
        assert resp.status_code == 404

    async def test_deploy_qa_team(self, async_client):
        """Deploy the QA team with skill info."""
        resp = await async_client.post("/api/teams/qa-team/deploy")
        assert resp.status_code == 201
        data = resp.json()
        assert data["count"] == 1
        assert data["deployed"][0]["name"] == "QA Engineer"
        assert "id" in data["deployed"][0]
