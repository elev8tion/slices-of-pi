"""
Settings router — read ~/.pi/agent/settings.json.

Provides a single GET endpoint that returns the parsed JSON contents
of the pi agent settings file. Returns 404 if the file doesn't exist.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..services.audit_service import log_settings_changed

router = APIRouter(prefix="/api/settings", tags=["settings"])

SETTINGS_PATH = Path.home() / ".pi" / "agent" / "settings.json"


class SettingsUpdate(BaseModel):
    """Request body for updating settings."""
    settings: dict


@router.get("")
async def get_settings():
    """Return the contents of ~/.pi/agent/settings.json as parsed JSON."""
    if not SETTINGS_PATH.exists():
        raise HTTPException(status_code=404, detail="Settings file not found")

    try:
        import json
        text = SETTINGS_PATH.read_text(encoding="utf-8")
        data = json.loads(text)
        return {"settings": data, "path": str(SETTINGS_PATH)}
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Settings file contains invalid JSON")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Error reading settings file: {e}")


@router.put("")
async def update_settings(body: SettingsUpdate):
    """Write the settings object to ~/.pi/agent/settings.json."""
    import json

    try:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(body.settings, indent=2, ensure_ascii=False)
        SETTINGS_PATH.write_text(text, encoding="utf-8")
        log_settings_changed(list(body.settings.keys()))
        return {"status": "saved", "path": str(SETTINGS_PATH)}
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Error writing settings file: {e}")
