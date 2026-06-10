"""
Extensions router — discover and list pi extensions.

Extensions are .ts or .js files in ~/.pi/agent/extensions/ (global)
or .pi/extensions/ (project-local). Each file exports a default
function that registers tools, commands, and event hooks.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from ..config import PI_EXTENSIONS_DIR, PI_AGENT_DIR

router = APIRouter(prefix="/api/extensions", tags=["extensions"])


def _discover_extensions(base_dir: Path, source: str) -> list[dict]:
    """Walk a directory and discover .ts/.js extension files."""
    extensions = []
    if not base_dir.exists():
        return extensions

    for entry in sorted(base_dir.iterdir()):
        if entry.is_file() and entry.suffix in (".ts", ".js", ".mjs"):
            extensions.append({
                "name": entry.stem,
                "path": str(entry),
                "source": source,
            })
        elif entry.is_dir():
            # Check for index files inside subdirectories
            for idx_name in ("index.ts", "index.js", "extension.ts", "extension.js"):
                idx = entry / idx_name
                if idx.exists():
                    extensions.append({
                        "name": entry.name,
                        "path": str(idx),
                        "source": source,
                    })
                    break
    return extensions


@router.get("")
async def list_extensions():
    """List all installed pi extensions (global + project-local)."""
    global_exts = _discover_extensions(PI_EXTENSIONS_DIR, "global")
    project_exts = _discover_extensions(
        PI_AGENT_DIR.parent / ".pi" / "extensions", "project"
    ) if (PI_AGENT_DIR.parent / ".pi" / "extensions").exists() else []

    all_exts = global_exts + project_exts
    return {"extensions": all_exts, "count": len(all_exts)}
