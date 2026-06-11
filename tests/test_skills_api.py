"""
Tests for skills API endpoint.

GET /api/skills — discovers and lists pi skills from ~/.pi/agent/skills/.
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from pi_orchestrator.config import PI_SKILLS_DIR


class TestListSkills:
    """GET /api/skills — list all skills."""

    async def test_list_skills_empty(self, async_client):
        resp = await async_client.get("/api/skills")
        assert resp.status_code == 200
        data = resp.json()
        assert data["skills"] == []
        assert data["count"] == 0

    async def test_list_skills_with_directory_skill(self, async_client):
        """Skill defined by a directory with SKILL.md."""
        skill_dir = PI_SKILLS_DIR / "my-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: My Custom Skill\ndescription: A custom skill for testing\n---\n\nSkill content here."
        )

        resp = await async_client.get("/api/skills")
        data = resp.json()
        assert data["count"] >= 1
        names = [s["name"] for s in data["skills"]]
        assert "My Custom Skill" in names

    async def test_list_skills_with_md_file(self, async_client):
        """Skill defined by a standalone .md file."""
        PI_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        (PI_SKILLS_DIR / "standalone.md").write_text(
            "---\nname: Standalone Skill\ndescription: A standalone skill file\n---\n\nContent."
        )

        resp = await async_client.get("/api/skills")
        data = resp.json()
        assert data["count"] >= 1
        names = [s["name"] for s in data["skills"]]
        assert "Standalone Skill" in names

    async def test_list_skills_no_frontmatter(self, async_client):
        """Files without frontmatter should still be listed."""
        skill_dir = PI_SKILLS_DIR / "no-frontmatter"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("Just content, no frontmatter.")

        resp = await async_client.get("/api/skills")
        data = resp.json()
        names = [s["name"] for s in data["skills"]]
        assert "no-frontmatter" in names

    async def test_list_skills_returns_location(self, async_client):
        skill_dir = PI_SKILLS_DIR / "locatable"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("---\nname: Locatable\n---")

        resp = await async_client.get("/api/skills")
        data = resp.json()
        skills = [s for s in data["skills"] if s["name"] == "Locatable"]
        assert len(skills) == 1
        assert "locatable" in skills[0]["location"]

    async def test_skills_endpoint_methods(self, async_client):
        """POST/PUT/DELETE should not be allowed."""
        resp = await async_client.post("/api/skills")
        assert resp.status_code == 405
        resp = await async_client.put("/api/skills")
        assert resp.status_code == 405
        resp = await async_client.delete("/api/skills")
        assert resp.status_code == 405
