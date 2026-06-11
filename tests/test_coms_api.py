"""
Tests for coms (peer agent discovery) API endpoint.

GET /api/coms — discovers pi peer agents from ~/.pi/coms/.
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path


class TestListPeers:
    """GET /api/coms — list discovered peer agents."""

    @property
    def coms_base_dir(self):
        return Path.home() / ".pi" / "coms"

    @property
    def coms_agents_dir(self):
        return Path.home() / ".pi" / "coms" / "projects" / "test-project" / "agents"

    async def _cleanup_coms(self):
        """Remove all coms test data between tests."""
        base = self.coms_base_dir
        if base.exists():
            import shutil
            shutil.rmtree(str(base))

    async def _create_peer(self, name: str, data: dict | None = None):
        """Helper to create a peer agent file."""
        agents_dir = self.coms_agents_dir
        agents_dir.mkdir(parents=True, exist_ok=True)
        peer_data = data or {
            "model": "sonnet",
            "status": "available",
            "contextUsed": 1024,
            "queueDepth": 0,
        }
        (agents_dir / f"{name}.json").write_text(json.dumps(peer_data))

    async def test_list_peers_empty(self, async_client):
        await self._cleanup_coms()
        resp = await async_client.get("/api/coms")
        assert resp.status_code == 200
        data = resp.json()
        assert data["peers"] == []
        assert data["count"] == 0

    async def test_list_peers(self, async_client):
        await self._cleanup_coms()
        await self._create_peer("agent-alpha", {
            "model": "sonnet",
            "status": "available",
            "contextUsed": 50,
            "queueDepth": 0,
        })
        await self._create_peer("agent-beta", {
            "model": "haiku",
            "status": "busy",
            "contextUsed": 100,
            "queueDepth": 2,
        })

        resp = await async_client.get("/api/coms")
        data = resp.json()
        assert data["count"] >= 2
        peers_by_name = {p["name"]: p for p in data["peers"]}

        assert peers_by_name["agent-alpha"]["status"] == "available"
        assert peers_by_name["agent-alpha"]["model"] == "sonnet"
        assert peers_by_name["agent-alpha"]["context_used"] == 50
        assert peers_by_name["agent-alpha"]["queue_depth"] == 0

        assert peers_by_name["agent-beta"]["status"] == "busy"
        assert peers_by_name["agent-beta"]["model"] == "haiku"

    async def test_peer_has_project(self, async_client):
        await self._cleanup_coms()
        await self._create_peer("project-peer")

        resp = await async_client.get("/api/coms")
        data = resp.json()
        assert data["peers"][0]["project"] == "test-project"

    async def test_malformed_peer_file(self, async_client):
        await self._cleanup_coms()
        """Corrupted JSON should still be listed with error status."""
        agents_dir = self.coms_agents_dir
        agents_dir.mkdir(parents=True, exist_ok=True)
        (agents_dir / "broken.json").write_text("not valid json{{{")

        resp = await async_client.get("/api/coms")
        data = resp.json()
        peers = [p for p in data["peers"] if p["name"] == "broken"]
        assert len(peers) == 1
        assert peers[0]["status"] == "error"

    async def test_multiple_projects(self, async_client):
        """Peers from different projects should all appear."""
        await self._cleanup_coms()
        proj1 = Path.home() / ".pi" / "coms" / "projects" / "project-a" / "agents"
        proj2 = Path.home() / ".pi" / "coms" / "projects" / "project-b" / "agents"
        proj1.mkdir(parents=True, exist_ok=True)
        proj2.mkdir(parents=True, exist_ok=True)

        (proj1 / "peer1.json").write_text(json.dumps({"status": "available"}))
        (proj2 / "peer2.json").write_text(json.dumps({"status": "busy"}))

        resp = await async_client.get("/api/coms")
        data = resp.json()
        assert data["count"] >= 2
        projects = {p["project"] for p in data["peers"]}
        assert "project-a" in projects
        assert "project-b" in projects

    async def test_coms_methods(self, async_client):
        """Only GET should be allowed."""
        await self._cleanup_coms()
        resp = await async_client.post("/api/coms")
        assert resp.status_code == 405
        resp = await async_client.put("/api/coms")
        assert resp.status_code == 405
        resp = await async_client.delete("/api/coms")
        assert resp.status_code == 405
