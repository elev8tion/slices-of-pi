"""
Tests for extensions API endpoint.

GET /api/extensions — discovers and lists pi extensions.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from pi_orchestrator.config import PI_EXTENSIONS_DIR


class TestListExtensions:
    """GET /api/extensions — list all extensions."""

    async def test_list_extensions_empty(self, async_client):
        resp = await async_client.get("/api/extensions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["extensions"] == []
        assert data["count"] == 0

    async def test_list_global_extensions(self, async_client):
        """Extensions from ~/.pi/agent/extensions/."""
        PI_EXTENSIONS_DIR.mkdir(parents=True, exist_ok=True)
        (PI_EXTENSIONS_DIR / "my-ext.ts").write_text("export default {};")
        (PI_EXTENSIONS_DIR / "other.js").write_text("module.exports = {};")

        resp = await async_client.get("/api/extensions")
        data = resp.json()
        assert data["count"] >= 2
        names = [e["name"] for e in data["extensions"]]
        assert "my-ext" in names
        assert "other" in names

    async def test_list_extensions_with_subdirectory(self, async_client):
        """Extensions can be in subdirectories with index files."""
        ext_dir = PI_EXTENSIONS_DIR / "complex-ext"
        ext_dir.mkdir(parents=True, exist_ok=True)
        (ext_dir / "index.ts").write_text("export default {};")

        resp = await async_client.get("/api/extensions")
        data = resp.json()
        names = [e["name"] for e in data["extensions"]]
        assert "complex-ext" in names

    async def test_list_extensions_filters_file_types(self, async_client):
        """Only .ts, .js, .mjs files should be listed."""
        PI_EXTENSIONS_DIR.mkdir(parents=True, exist_ok=True)
        (PI_EXTENSIONS_DIR / "good.ts").write_text("")
        (PI_EXTENSIONS_DIR / "bad.py").write_text("")
        (PI_EXTENSIONS_DIR / "notes.txt").write_text("")

        resp = await async_client.get("/api/extensions")
        data = resp.json()
        names = [e["name"] for e in data["extensions"]]
        assert "good" in names
        assert "bad" not in names

    async def test_list_extensions_has_source_field(self, async_client):
        """Extensions should have a 'source' field (global/project)."""
        PI_EXTENSIONS_DIR.mkdir(parents=True, exist_ok=True)
        (PI_EXTENSIONS_DIR / "global-ext.ts").write_text("")

        resp = await async_client.get("/api/extensions")
        data = resp.json()
        for ext in data["extensions"]:
            assert ext["source"] in ("global", "project")

    async def test_extensions_endpoint_methods(self, async_client):
        """Non-GET methods should not be allowed."""
        resp = await async_client.post("/api/extensions")
        assert resp.status_code == 405
        resp = await async_client.delete("/api/extensions")
        assert resp.status_code == 405
