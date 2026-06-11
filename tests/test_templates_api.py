"""
Tests for templates/persona API endpoints.

GET /api/templates       — list all agent persona templates
GET /api/templates/{name} — get single persona template with content
"""

from __future__ import annotations

import pytest
from pathlib import Path

from pi_orchestrator.config import PI_AGENTS_CONFIG_DIR


@pytest.fixture(autouse=True)
def _clean_templates():
    """Clean up persona files between tests."""
    yield
    if PI_AGENTS_CONFIG_DIR.exists():
        for child in list(PI_AGENTS_CONFIG_DIR.iterdir()):
            if child.is_file():
                child.unlink()


class TestListTemplates:
    """GET /api/templates — list personas."""

    async def test_list_templates_empty(self, async_client):
        resp = await async_client.get("/api/templates")
        assert resp.status_code == 200
        data = resp.json()
        assert data["templates"] == []
        assert data["count"] == 0

    async def test_list_templates(self, async_client):
        PI_AGENTS_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        (PI_AGENTS_CONFIG_DIR / "developer.md").write_text(
            "---\nname: Developer\ndescription: A coding agent\n"
            "tools:\n  - read\n  - bash\n  - write\nmodel: sonnet\n---\n\n"
            "Full markdown content here."
        )
        (PI_AGENTS_CONFIG_DIR / "writer.md").write_text(
            "---\nname: Writer\ndescription: A writing agent\n"
            "skills:\n  - prose\n  - editing\nextensions:\n  - grammar\n---\n\n"
            "Writer content."
        )

        resp = await async_client.get("/api/templates")
        data = resp.json()
        assert data["count"] >= 2
        names = [t["name"] for t in data["templates"]]
        assert "Developer" in names
        assert "Writer" in names

    async def test_list_templates_with_all_fields(self, async_client):
        PI_AGENTS_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        (PI_AGENTS_CONFIG_DIR / "full.md").write_text(
            "---\nname: Full Agent\ndescription: Has everything\n"
            "tools:\n  - read\n  - bash\nmodel: sonnet\n"
            "skills:\n  - python\nextensions:\n  - my-ext\nschedule: 0 9 * * *\n---\n"
        )

        resp = await async_client.get("/api/templates")
        data = resp.json()
        full = [t for t in data["templates"] if t["name"] == "Full Agent"][0]
        assert full["description"] == "Has everything"
        assert full["tools"] == ["read", "bash"]
        assert full["model"] == "sonnet"
        assert full["skills"] == ["python"]
        assert full["extensions"] == ["my-ext"]
        assert full["schedule"] == "0 9 * * *"
        assert "path" in full

    async def test_list_templates_skips_non_md_files(self, async_client):
        PI_AGENTS_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        (PI_AGENTS_CONFIG_DIR / "persona.md").write_text("---\nname: Valid\n---")
        (PI_AGENTS_CONFIG_DIR / "notes.txt").write_text("Not a persona")
        (PI_AGENTS_CONFIG_DIR / "script.py").write_text("# not a persona")

        resp = await async_client.get("/api/templates")
        data = resp.json()
        names = [t["name"] for t in data["templates"]]
        assert "Valid" in names
        assert len(names) == 1


class TestGetTemplate:
    """GET /api/templates/{name} — get single persona."""

    async def test_get_template(self, async_client):
        PI_AGENTS_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        content = (
            "---\nname: Designer\ndescription: A design agent\n"
            "tools:\n  - read\n  - bash\nmodel: sonnet\n---\n\n"
            "Full designer markdown content."
        )
        (PI_AGENTS_CONFIG_DIR / "designer.md").write_text(content)

        resp = await async_client.get("/api/templates/designer")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Designer"
        assert data["description"] == "A design agent"
        assert data["tools"] == ["read", "bash"]
        assert data["model"] == "sonnet"
        assert data["content"] == content

    async def test_get_template_not_found(self, async_client):
        resp = await async_client.get("/api/templates/nonexistent")
        assert resp.status_code == 404

    async def test_get_template_without_frontmatter(self, async_client):
        PI_AGENTS_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        (PI_AGENTS_CONFIG_DIR / "simple.md").write_text("Just content, no frontmatter.")

        resp = await async_client.get("/api/templates/simple")
        assert resp.status_code == 200
        data = resp.json()
        # Without frontmatter, only 'content' field is returned
        assert data["content"] == "Just content, no frontmatter."
