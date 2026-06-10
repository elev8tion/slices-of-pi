"""
Coms router — read pi peer-to-peer agent pool from ~/.pi/coms/.

coms uses file-based discovery: each agent writes a JSON registry file
to ~/.pi/coms/projects/<project>/agents/<name>.json with status info.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/api/coms", tags=["coms"])

COMS_DIR = Path.home() / ".pi" / "coms"


def _discover_peers() -> list[dict]:
    """Walk the coms registry and return all discovered peers."""
    peers = []
    projects_dir = COMS_DIR / "projects"
    if not projects_dir.exists():
        return peers

    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        agents_dir = project_dir / "agents"
        if not agents_dir.exists():
            continue
        for agent_file in agents_dir.glob("*.json"):
            try:
                data = json.loads(agent_file.read_text())
                peers.append({
                    "name": agent_file.stem,
                    "project": project_dir.name,
                    "model": data.get("model", ""),
                    "status": data.get("status", "unknown"),
                    "context_used": data.get("contextUsed", 0),
                    "queue_depth": data.get("queueDepth", 0),
                })
            except Exception:
                peers.append({
                    "name": agent_file.stem,
                    "project": project_dir.name,
                    "status": "error",
                })
    return peers


@router.get("")
async def list_peers():
    """List all discovered pi coms peer agents."""
    peers = _discover_peers()
    return {"peers": peers, "count": len(peers)}
