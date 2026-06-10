"""
Teams router — multi-agent maestro integration.

Reads ~/.pi/agents/teams.yaml and agent persona files.
Supports deploying an entire team at once.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from fastapi import APIRouter, HTTPException

from ..config import PI_AGENTS_CONFIG_DIR

router = APIRouter(prefix="/api/teams", tags=["teams"])

TEAMS_FILE = PI_AGENTS_CONFIG_DIR / "teams.yaml"


def _parse_persona(path: Path) -> dict | None:
    """Parse a .pi/agents/<name>.md persona file for frontmatter."""
    try:
        text = path.read_text()
        match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
        if not match:
            return None
        result: dict = {}
        current_key = None
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
            "model": result.get("model", ""),
            "skills": result.get("skills", []),
            "extensions": result.get("extensions", []),
        }
    except Exception:
        return None


def _load_teams() -> dict:
    """Load teams.yaml, return {team_name: [agent_names]}."""
    if not TEAMS_FILE.exists():
        return {}
    try:
        with open(TEAMS_FILE) as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _load_personas() -> dict[str, dict]:
    """Load all persona files, return {name: {...}}."""
    personas = {}
    if not PI_AGENTS_CONFIG_DIR.exists():
        return personas
    for entry in PI_AGENTS_CONFIG_DIR.iterdir():
        if entry.suffix == ".md":
            parsed = _parse_persona(entry)
            if parsed:
                personas[parsed["name"]] = parsed
    return personas


@router.get("")
async def list_teams():
    """List all team rosters with member details."""
    teams = _load_teams()
    personas = _load_personas()

    result = []
    for team_name, members in teams.items():
        member_details = []
        for name in members:
            persona = personas.get(name, {"name": name, "description": ""})
            member_details.append({
                "name": name,
                "description": persona.get("description", ""),
                "tools": persona.get("tools", []),
                "model": persona.get("model", ""),
            })
        result.append({
            "name": team_name,
            "members": member_details,
            "count": len(member_details),
        })

    return {"teams": result, "count": len(result)}


@router.post("/{team_name}/deploy", status_code=201)
async def deploy_team(team_name: str):
    """Deploy all agents in a team. Creates agents from persona files."""
    teams = _load_teams()
    if team_name not in teams:
        raise HTTPException(status_code=404, detail=f"Team '{team_name}' not found")

    personas = _load_personas()
    from .. import database as db

    created = []
    for member_name in teams[team_name]:
        persona = personas.get(member_name, {})
        try:
            agent = db.create_agent(
                name=member_name,
                model=persona.get("model", ""),
                tools=persona.get("tools"),
                skills=persona.get("skills"),
                persona=member_name,
            )
            created.append({"name": member_name, "id": agent["id"]})
        except Exception as e:
            created.append({"name": member_name, "error": str(e)})

    return {"team": team_name, "deployed": created, "count": len(created)}
