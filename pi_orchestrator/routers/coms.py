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

        # Add recent facts from the shared knowledge pool
        try:
            from ..services.shared_memory_service import SHARED_MEMORY_DIR
            peer_facts = []
            tag_path = SHARED_MEMORY_DIR / project_dir.name / "knowledge.jsonl"
            if tag_path.exists():
                with open(tag_path) as f:
                    for line in f:
                        try:
                            entry = json.loads(line)
                            if entry.get("agent_id", "") == agent_file.stem or entry.get("agent_name") == agent_file.stem:
                                peer_facts.append(entry.get("fact", ""))
                                if len(peer_facts) >= 5:
                                    break
                        except (json.JSONDecodeError, ValueError):
                            continue
            peers[-1]["recent_facts"] = peer_facts
            peers[-1]["fact_count"] = len(peer_facts)
        except Exception:
            peers[-1]["recent_facts"] = []
            peers[-1]["fact_count"] = 0

    return peers


@router.get("")
async def list_peers():
    """List all discovered pi coms peer agents."""
    peers = _discover_peers()
    return {"peers": peers, "count": len(peers)}
