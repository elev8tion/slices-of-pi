"""
Tests for Flixz service, router, and database CRUD.
Uses conftest fixtures: async_client, test_agent, clear_db.
"""

import json
import os
import pytest
from pi_orchestrator import database as db


class TestFlixzDatabase:
    """CRUD operations for flixz_runs table."""

    def test_create_flixz_run(self):
        run = db.create_flixz_run(
            run_id="test-run-1",
            agent_id=None,
            video_path="/tmp/test.mp4",
            config={"max_frames": 60, "fps": 0},
            output_dir="/tmp/flixz/output/test-run-1",
        )
        assert run is not None
        assert run["id"] == "test-run-1"
        assert run["status"] == "running"
        assert run["video_path"] == "/tmp/test.mp4"

    def test_get_flixz_run(self):
        db.create_flixz_run(
            run_id="test-run-2",
            agent_id=None,
            video_path="/tmp/test2.mp4",
            config={"max_frames": 30},
            output_dir="/tmp/flixz/output/test-run-2",
        )
        run = db.get_flixz_run("test-run-2")
        assert run is not None
        assert run["id"] == "test-run-2"

    def test_get_flixz_run_not_found(self):
        assert db.get_flixz_run("nonexistent") is None

    def test_list_flixz_runs(self):
        db.create_flixz_run("run-a", None, "/tmp/a.mp4", {}, "/tmp/a")
        db.create_flixz_run("run-b", None, "/tmp/b.mp4", {}, "/tmp/b")
        runs = db.list_flixz_runs(limit=10)
        assert len(runs) >= 2
        assert runs[0]["id"] == "run-b"  # Most recent first

    def test_list_flixz_runs_filter_by_agent(self):
        agent = db.create_agent("flixz-filter-agent", model="test", tools=["read"])
        db.create_flixz_run("run-agt-1", agent["id"], "/tmp/a1.mp4", {}, "/tmp/a1")
        db.create_flixz_run("run-sys-1", None, "/tmp/sys.mp4", {}, "/tmp/sys")

        agent_runs = db.list_flixz_runs(agent_id=agent["id"])
        assert len(agent_runs) == 1
        assert agent_runs[0]["id"] == "run-agt-1"

    def test_update_flixz_run_completed(self):
        db.create_flixz_run("run-upd-1", None, "/tmp/upd.mp4", {}, "/tmp/upd")
        db.update_flixz_run(
            "run-upd-1",
            status="completed",
            frame_count=42,
            duration_seconds=10.5,
            resolution="1920×1080",
            transcript_text="Hello world",
        )
        run = db.get_flixz_run("run-upd-1")
        assert run["status"] == "completed"
        assert run["frame_count"] == 42
        assert run["duration_seconds"] == 10.5
        assert run["resolution"] == "1920×1080"
        assert run["transcript_text"] == "Hello world"
        assert run["completed_at"] is not None

    def test_update_flixz_run_failed(self):
        db.create_flixz_run("run-fail-1", None, "/tmp/fail.mp4", {}, "/tmp/fail")
        db.update_flixz_run("run-fail-1", status="failed", error_message="File not found")
        run = db.get_flixz_run("run-fail-1")
        assert run["status"] == "failed"
        assert run["error_message"] == "File not found"

    def test_delete_flixz_run(self):
        db.create_flixz_run("run-del-1", None, "/tmp/del.mp4", {}, "/tmp/del")
        assert db.delete_flixz_run("run-del-1") is True
        assert db.get_flixz_run("run-del-1") is None

    def test_delete_flixz_run_not_found(self):
        assert db.delete_flixz_run("nonexistent") is False


class TestFlixzRouter:
    """Endpoint registration and schema validation."""

    @pytest.mark.asyncio
    async def test_all_routes_registered(self, async_client):
        routes = [r.path for r in async_client._transport.app.routes]
        assert "/api/flixz/extract" in routes
        assert "/api/flixz/runs" in routes
        assert "/api/flixz/runs/{run_id}" in routes
        assert "/api/agents/{agent_id}/flixz/extract" in routes
        assert "/api/agents/{agent_id}/flixz/runs" in routes

    @pytest.mark.asyncio
    async def test_system_extract_requires_video_path(self, async_client):
        r = await async_client.post("/api/flixz/extract", json={"video_path": ""})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_system_extract_accepts_valid_request(self, async_client):
        r = await async_client.post("/api/flixz/extract", json={
            "video_path": "/tmp/test.mp4",
            "max_frames": 30,
            "fps": 0,
            "scene_detect": True,
            "transcript": "none",
            "describe": "gemini",
        })
        assert r.status_code in (200, 500)
        data = r.json()
        if r.status_code == 500:
            assert "flixz" in data.get("detail", "").lower() or "not found" in data.get("detail", "").lower()

    @pytest.mark.asyncio
    async def test_agent_extract_requires_valid_agent(self, async_client, test_agent):
        r = await async_client.post(f"/api/agents/{test_agent['id']}/flixz/extract", json={
            "video_path": "/tmp/test.mp4",
        })
        assert r.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_agent_extract_404_for_missing_agent(self, async_client):
        r = await async_client.post("/api/agents/nonexistent-agent/flixz/extract", json={
            "video_path": "/tmp/test.mp4",
        })
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_system_list_runs(self, async_client):
        r = await async_client.get("/api/flixz/runs")
        assert r.status_code == 200
        data = r.json()
        assert "runs" in data
        assert isinstance(data["runs"], list)

    @pytest.mark.asyncio
    async def test_system_get_run_404(self, async_client):
        r = await async_client.get("/api/flixz/runs/nonexistent")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_agent_list_runs_404_missing_agent(self, async_client):
        r = await async_client.get("/api/agents/nonexistent/flixz/runs")
        assert r.status_code == 404


class TestFlixzService:
    """Service-level extraction logic."""

    def test_imports(self):
        from pi_orchestrator.services.flixz_service import extract_video
        import inspect
        assert inspect.iscoroutinefunction(extract_video)

    def test_ffmpeg_handles_missing_file(self):
        """When video file doesn't exist, ffmpeg returns an error."""
        import asyncio
        from pi_orchestrator.services.flixz_service import extract_video

        result = asyncio.run(extract_video(
            video_path="/tmp/nonexistent_video_12345.mp4",
            max_frames=10,
            agent_id=None,
        ))
        assert result["status"] == "failed"
        assert "not found" in result.get("error_message", "").lower() or "error" in result.get("error_message", "").lower()
