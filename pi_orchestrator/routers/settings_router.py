"""
Settings router — local operator config files only.

- GET/PUT /api/settings — ~/.pi/agent/settings.json
- GET/PUT /api/settings/orchestrator-config — ~/.pi/agent/orchestrator.json

No arbitrary filesystem paths. Local single-operator only (PRODUCT_INTENT).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..config import load_orchestrator_config, save_orchestrator_config, ORCHESTRATOR_CONFIG
from ..services.audit_service import log_settings_changed

router = APIRouter(prefix="/api/settings", tags=["settings"])

SETTINGS_PATH = Path.home() / ".pi" / "agent" / "settings.json"


class SettingsUpdate(BaseModel):
    """Request body for updating settings."""
    settings: dict


class OrchestratorConfigUpdate(BaseModel):
    """Full orchestrator.json document (must be a JSON object)."""
    config: dict[str, Any] = Field(default_factory=dict)


@router.get("")
async def get_settings():
    """Return the contents of ~/.pi/agent/settings.json as parsed JSON."""
    if not SETTINGS_PATH.exists():
        raise HTTPException(status_code=404, detail="Settings file not found")

    try:
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
    try:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(body.settings, indent=2, ensure_ascii=False)
        SETTINGS_PATH.write_text(text, encoding="utf-8")
        log_settings_changed(list(body.settings.keys()))
        return {"status": "saved", "path": str(SETTINGS_PATH)}
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Error writing settings file: {e}")


@router.get("/orchestrator-config")
async def get_orchestrator_config():
    """Return ~/.pi/agent/orchestrator.json (profiles) for local editing."""
    config = load_orchestrator_config()
    return {
        "config": config,
        "path": str(ORCHESTRATOR_CONFIG),
        "text": json.dumps(config, indent=2, ensure_ascii=False) + "\n",
    }


@router.put("/orchestrator-config")
async def put_orchestrator_config(body: OrchestratorConfigUpdate):
    """Replace orchestrator.json. Only this fixed path is writable."""
    if not isinstance(body.config, dict):
        raise HTTPException(status_code=400, detail="config must be a JSON object")
    # Light shape check — keep profiles object if present
    if "profiles" in body.config and not isinstance(body.config["profiles"], dict):
        raise HTTPException(status_code=400, detail="profiles must be an object")
    try:
        save_orchestrator_config(body.config)
        log_settings_changed(["orchestrator.json"])
        return {"status": "saved", "path": str(ORCHESTRATOR_CONFIG)}
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Error writing orchestrator config: {e}")
