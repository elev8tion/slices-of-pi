"""
Skills router — discover and list pi skills from ~/.pi/agent/skills/.

Each skill is a directory with a SKILL.md file containing YAML frontmatter.
We parse the frontmatter to extract name, description, and trigger phrases.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from fastapi import APIRouter

from ..config import PI_SKILLS_DIR

router = APIRouter(prefix="/api/skills", tags=["skills"])


def _parse_frontmatter(path: Path) -> dict | None:
    """Extract YAML frontmatter from a SKILL.md file using real YAML parser.

    Returns full frontmatter dict including inputs, outputs, triggers, etc.
    """
    try:
        text = path.read_text()
        match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
        if not match:
            return None
        return yaml.safe_load(match.group(1))
    except Exception:
        return None


def _discover_skills(base_dir: Path) -> list[dict]:
    """Walk a directory and discover all skills."""
    skills = []
    if not base_dir.exists():
        return skills

    for entry in sorted(base_dir.iterdir()):
        if entry.is_dir():
            skill_md = entry / "SKILL.md"
            if skill_md.exists():
                meta = _parse_frontmatter(skill_md) or {}
                skills.append({
                    "name": meta.get("name", entry.name),
                    "description": meta.get("description", ""),
                    "location": str(entry),
                    "inputs": meta.get("inputs", {}),
                    "outputs": meta.get("outputs", {}),
                    "triggers": meta.get("triggers", meta.get("trigger", [])),
                })
        elif entry.suffix == ".md":
            meta = _parse_frontmatter(entry) or {}
            skills.append({
                "name": meta.get("name", entry.stem),
                "description": meta.get("description", ""),
                "location": str(entry),
                "inputs": meta.get("inputs", {}),
                "outputs": meta.get("outputs", {}),
                "triggers": meta.get("triggers", meta.get("trigger", [])),
            })
    return skills


@router.get("")
async def list_skills():
    """List all installed pi skills with frontmatter metadata."""
    skills = _discover_skills(PI_SKILLS_DIR)
    return {"skills": skills, "count": len(skills)}
