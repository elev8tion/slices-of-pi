"""
Extensions router — discover and list pi extensions.

Scans:
  1. ~/.pi/agent/extensions/          — local .ts/.js files
  2. .pi/extensions/                  — project-local .ts/.js files
  3. ~/.pi/agent/npm/node_modules/    — pi extension packages
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter

from ..config import PI_EXTENSIONS_DIR, PI_AGENT_DIR

router = APIRouter(prefix="/api/extensions", tags=["extensions"])

# Packages that are actual pi extensions (not transitive dependencies)
PI_EXTENSION_PACKAGES = {
    "graphify-pi", "pi-scraper", "pi-subagents", "pi-web-access",
    "rpiv-todo", "rpiv-config", "pi-extension-author",
    "pi-nvidia-nim", "pi-bowser-browser",
}


def _discover_extensions(base_dir: Path, source: str) -> list[dict]:
    """Walk a directory and discover .ts/.js extension files."""
    extensions = []
    if not base_dir.exists():
        return extensions
    for entry in sorted(base_dir.iterdir()):
        if entry.is_file() and entry.suffix in (".ts", ".js", ".mjs"):
            extensions.append({"name": entry.stem, "path": str(entry), "source": source})
        elif entry.is_dir():
            for idx_name in ("index.ts", "index.js", "extension.ts", "extension.js"):
                idx = entry / idx_name
                if idx.exists():
                    extensions.append({"name": entry.name, "path": str(idx), "source": source})
                    break
    return extensions


def _discover_npm_extensions() -> list[dict]:
    """Scan npm node_modules for pi extension packages only."""
    npm_dir = PI_AGENT_DIR / "npm" / "node_modules"
    extensions = []
    if not npm_dir.exists():
        return extensions
    for scope_dir in npm_dir.iterdir():
        if scope_dir.name.startswith("@"):
            for pkg_dir in scope_dir.iterdir():
                _check_and_add(pkg_dir, extensions)
        else:
            _check_and_add(scope_dir, extensions)
    return extensions


def _check_and_add(pkg_dir: Path, extensions: list[dict]) -> None:
    """Check if a package is a pi extension and add it if so."""
    pkg_json = pkg_dir / "package.json"
    if not pkg_json.exists():
        return
    try:
        with open(pkg_json) as f:
            data = json.load(f)
        name = data.get("name", pkg_dir.name)
        # Only include known pi extension packages or packages with "pi" prefix
        if pkg_dir.name not in PI_EXTENSION_PACKAGES:
            return
        # Find the entry point
        main = data.get("main") or data.get("module") or ""
        exports = data.get("exports", {})
        if isinstance(exports, dict):
            export_entry = exports.get(".", {})
            if isinstance(export_entry, dict):
                main = export_entry.get("import", export_entry.get("require", main))
        if main:
            main_path = pkg_dir / main
            if main_path.exists():
                extensions.append({"name": name.split("/")[-1], "path": str(main_path), "source": "npm"})
                return
        # Fallback: show the package directory
        extensions.append({"name": name.split("/")[-1], "path": str(pkg_json), "source": "npm"})
    except (json.JSONDecodeError, Exception):
        pass


@router.get("")
async def list_extensions():
    """List all installed pi extensions."""
    global_exts = _discover_extensions(PI_EXTENSIONS_DIR, "global")
    project_dir = PI_AGENT_DIR.parent / ".pi" / "extensions"
    project_exts = _discover_extensions(project_dir, "project") if project_dir.exists() else []
    npm_exts = _discover_npm_extensions()

    seen = set()
    all_exts = []
    for ext in global_exts + project_exts + npm_exts:
        if ext["name"] not in seen:
            seen.add(ext["name"])
            all_exts.append(ext)
    return {"extensions": all_exts, "count": len(all_exts)}
