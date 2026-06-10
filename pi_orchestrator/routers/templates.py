"""
Templates router — discover agent persona templates from ~/.pi/agents/.

Each persona is a .md file with YAML frontmatter defining:
  name, description, tools, model, skills, extensions, schedule
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..config import PI_AGENTS_CONFIG_DIR

router = APIRouter(prefix="/api/templates", tags=["templates"])


def _parse_persona(path: Path) -> dict | None:
    """Parse a .pi/agents/<name>.md persona file."""
    try:
        text = path.read_text()
        match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
        if not match:
            return None

        result: dict = {}
        current_key = None
        # Parse list items
        for line in match.group(1).split("\n"):
            line = line.strip()
            if not line:
                continue
            if ":" in line and not line.startswith("-"):
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if value:
                    result[key] = value
                else:
                    current_key = key
                    result[key] = []
            elif line.startswith("-") and current_key:
                result[current_key].append(line[1:].strip().strip('"').strip("'"))

        return {
            "name": result.get("name", path.stem),
            "description": result.get("description", ""),
            "tools": result.get("tools", []),
            "model": result.get("model"),
            "skills": result.get("skills", []),
            "extensions": result.get("extensions", []),
            "schedule": result.get("schedule"),
            "path": str(path),
        }
    except Exception:
        return None


@router.get("")
async def list_templates():
    """List all available agent persona templates."""
    personas = []
    if PI_AGENTS_CONFIG_DIR.exists():
        for entry in sorted(PI_AGENTS_CONFIG_DIR.iterdir()):
            if entry.suffix == ".md":
                parsed = _parse_persona(entry)
                if parsed:
                    personas.append(parsed)
    return {"templates": personas, "count": len(personas)}


@router.get("/{name}")
async def get_template(name: str):
    """Get a single persona template with full markdown content."""
    path = PI_AGENTS_CONFIG_DIR / f"{name}.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Template not found")

    text = path.read_text()
    parsed = _parse_persona(path) or {}
    parsed["content"] = text
    return parsed
