"""
File Manager router — browse, upload, download, preview, and delete
files in the agent workspace directory.

All paths are restricted to:
  ~/.pi/agent/sessions/managed/<agent_name>/
Path traversal attempts are rejected with 403.
"""

from __future__ import annotations

import logging
import mimetypes
import os
import shutil
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.params import File, Form, Query
from fastapi.responses import Response

from .. import database as db
from ..config import PI_MANAGED_SESSIONS_DIR

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents/{agent_id}/files", tags=["files"])

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB
PREVIEW_MAX_LINES = 100
PREVIEW_MAX_BYTES = 256 * 1024  # 256 KB


def _get_agent(agent_id: str) -> dict:
    agent = db.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


def _safe_resolve(base: Path, requested: str) -> Path:
    """Resolve a path relative to base, rejecting traversal."""
    # Normalise — strip leading / or ./
    clean = requested.lstrip("/").lstrip("./")
    if not clean:
        return base
    target = (base / clean).resolve()
    if not str(target).startswith(str(base.resolve())):
        raise HTTPException(status_code=403, detail="Path traversal denied")
    return target


def _format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024*1024):.1f} MB"
    return f"{size / (1024*1024*1024):.1f} GB"


def _entry_dict(path: Path, base: Path) -> dict:
    """Build a file/dir entry dict."""
    rel = str(path.relative_to(base))
    stat = path.stat()
    is_dir = path.is_dir()
    return {
        "name": path.name,
        "path": rel,
        "type": "dir" if is_dir else "file",
        "size": stat.st_size if not is_dir else 0,
        "size_formatted": "" if is_dir else _format_size(stat.st_size),
        "modified_at": time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)
        ),
    }


def _list_recursive(path: Path, base: Path, max_depth: int = 3) -> list[dict]:
    """Recursively list directory contents up to max_depth."""
    if max_depth <= 0:
        return []
    entries = []
    try:
        for child in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            entry = _entry_dict(child, base)
            if child.is_dir():
                entry["children"] = _list_recursive(child, base, max_depth - 1)
            entries.append(entry)
    except PermissionError:
        pass
    return entries


# ── GET /api/agents/{id}/files?path=...  List directory ──────────


@router.get("")
async def list_files(
    agent_id: str,
    path: str = Query("", description="Relative path within agent workspace"),
):
    """List files and directories at the given path."""
    agent = _get_agent(agent_id)
    agent_name = agent["name"]
    base = PI_MANAGED_SESSIONS_DIR / agent_name

    if not base.exists():
        return {
            "path": path or "/",
            "name": agent_name,
            "type": "dir",
            "children": [],
            "base": str(base),
        }

    target = _safe_resolve(base, path)

    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    if target.is_file():
        entry = _entry_dict(target, base)
        entry["children"] = []
        return entry

    # Directory — list contents
    entries = _list_recursive(target, base)
    return {
        "path": path or "/",
        "name": target.name,
        "type": "dir",
        "children": entries,
        "base": str(base),
    }


# ── GET /api/agents/{id}/files/download?path=...  Download file ──


@router.get("/download")
async def download_file(
    agent_id: str,
    path: str = Query(..., description="Relative path to file"),
):
    """Download a file (raw bytes)."""
    agent = _get_agent(agent_id)
    base = PI_MANAGED_SESSIONS_DIR / agent["name"]
    target = _safe_resolve(base, path)

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    content_type, _ = mimetypes.guess_type(str(target))
    return Response(
        content=target.read_bytes(),
        media_type=content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{target.name}"',
            "Content-Length": str(target.stat().st_size),
        },
    )


# ── GET /api/agents/{id}/files/preview?path=...  Text preview ────


@router.get("/preview")
async def preview_file(
    agent_id: str,
    path: str = Query(..., description="Relative path to file"),
):
    """Return first 100 lines for text file preview."""
    agent = _get_agent(agent_id)
    base = PI_MANAGED_SESSIONS_DIR / agent["name"]
    target = _safe_resolve(base, path)

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    # Only text-like files
    text_extensions = {
        ".txt", ".md", ".json", ".jsonl", ".yaml", ".yml", ".toml", ".ini",
        ".py", ".js", ".ts", ".jsx", ".tsx", ".vue", ".css", ".scss", ".html",
        ".sh", ".bash", ".zsh", ".env", ".cfg", ".conf", ".xml", ".svg",
        ".log", ".csv", ".tsv", ".sql", ".lock", ".gitignore",
    }
    ext = target.suffix.lower()
    is_text = ext in text_extensions

    # Also check mime
    if not is_text:
        mime, _ = mimetypes.guess_type(str(target))
        if mime and mime.startswith("text/"):
            is_text = True

    if not is_text:
        # For images, return base64
        img_mime, _ = mimetypes.guess_type(str(target))
        if img_mime and img_mime.startswith("image/"):
            import base64
            data = target.read_bytes()
            return {
                "type": "image",
                "mime": img_mime,
                "content": base64.b64encode(data).decode(),
                "size": len(data),
                "size_formatted": _format_size(len(data)),
            }
        raise HTTPException(
            status_code=400,
            detail="Not a previewable file type. Use download instead.",
        )

    # Read preview
    total_size = target.stat().st_size
    if total_size > PREVIEW_MAX_BYTES:
        # Read first PREVIEW_MAX_BYTES
        with open(target, "rb") as f:
            raw = f.read(PREVIEW_MAX_BYTES)
        text = raw.decode("utf-8", errors="replace")
        lines = text.splitlines()
        truncated = total_size > PREVIEW_MAX_BYTES
        remaining_bytes = total_size - PREVIEW_MAX_BYTES if truncated else 0
    else:
        text = target.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        truncated = False
        remaining_bytes = 0

    shown = lines[:PREVIEW_MAX_LINES]
    more = len(lines) - PREVIEW_MAX_LINES if len(lines) > PREVIEW_MAX_LINES else 0

    return {
        "type": "text",
        "filename": target.name,
        "content": "\n".join(shown),
        "total_lines": len(lines),
        "shown_lines": len(shown),
        "truncated_lines": more,
        "truncated_bytes": remaining_bytes,
        "total_bytes": total_size,
        "size_formatted": _format_size(total_size),
    }


# ── POST /api/agents/{id}/files/upload?path=...  Upload file ─────


@router.post("/upload")
async def upload_file(
    agent_id: str,
    file: UploadFile = File(...),
    path: str = Form("", description="Relative directory to upload into"),
):
    """Upload a file to the agent workspace."""
    agent = _get_agent(agent_id)
    base = PI_MANAGED_SESSIONS_DIR / agent["name"]
    target_dir = _safe_resolve(base, path)

    if not target_dir.exists():
        target_dir.mkdir(parents=True, exist_ok=True)

    if not target_dir.is_dir():
        raise HTTPException(status_code=400, detail="Upload path must be a directory")

    # Check file size
    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max {_format_size(MAX_UPLOAD_BYTES)}",
        )

    dest = target_dir / (file.filename or "uploaded_file")
    # Prevent path traversal in filename
    dest = _safe_resolve(base, str(dest.relative_to(base)))

    with open(dest, "wb") as f:
        f.write(contents)

    logger.info(f"Uploaded {dest} ({_format_size(len(contents))})")
    return {
        "status": "uploaded",
        "path": str(dest.relative_to(base)),
        "size": len(contents),
        "size_formatted": _format_size(len(contents)),
    }


# ── POST /api/agents/{id}/files/mkdir?path=...  Create directory ─


@router.post("/mkdir")
async def create_directory(
    agent_id: str,
    path: str = Query(..., description="Relative path for new directory"),
):
    """Create a new directory."""
    agent = _get_agent(agent_id)
    base = PI_MANAGED_SESSIONS_DIR / agent["name"]
    target = _safe_resolve(base, path)

    if target.exists():
        raise HTTPException(status_code=409, detail="Path already exists")

    target.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created directory {target}")
    return {"status": "created", "path": str(target.relative_to(base))}


# ── DELETE /api/agents/{id}/files?path=...  Delete file/dir ──────


@router.delete("")
async def delete_file(
    agent_id: str,
    path: str = Query(..., description="Relative path to file or empty directory"),
):
    """Delete a file or empty directory."""
    agent = _get_agent(agent_id)
    base = PI_MANAGED_SESSIONS_DIR / agent["name"]
    target = _safe_resolve(base, path)

    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    # Safety: don't allow deleting the base directory itself
    if str(target.resolve()) == str(base.resolve()):
        raise HTTPException(status_code=403, detail="Cannot delete root workspace")

    if target.is_file():
        target.unlink()
        logger.info(f"Deleted file {target}")
        return {"status": "deleted", "path": str(target.relative_to(base))}

    if target.is_dir():
        try:
            target.rmdir()  # Only removes empty dirs
            logger.info(f"Deleted directory {target}")
            return {"status": "deleted", "path": str(target.relative_to(base))}
        except OSError:
            raise HTTPException(
                status_code=400,
                detail="Directory not empty. Delete files inside first.",
            )

    raise HTTPException(status_code=400, detail="Not a file or directory")
