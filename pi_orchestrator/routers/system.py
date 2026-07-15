"""
System router — pi version, updates, and package installation.
"""

from __future__ import annotations

import asyncio
import subprocess

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import PI_BINARY

router = APIRouter(prefix="/api/system", tags=["system"])


class InstallRequest(BaseModel):
    source: str  # npm:@foo/bar, git:github.com/user/repo, etc.


@router.get("/models")
async def list_models(images_only: bool = False):
    """Return models from `pi --list-models` (your configured .pi providers).

    Returns:
      models: groups by provider
      flat: all models as a single list (for selectors)
      count: number of models

    Query images_only=true filters to vision-capable models (images=yes).
    """
    try:
        import re

        proc = await asyncio.create_subprocess_exec(
            PI_BINARY, "--list-models",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=20)
        output = stdout.decode().strip()
        if not output:
            return {"models": [], "flat": [], "count": 0, "error": "No output from pi --list-models"}

        PROVIDER_COLORS = {
            "anthropic": "#8B5CF6",
            "openai-codex": "#22C55E",
            "openai": "#22C55E",
            "deepseek-openai": "#F59E0B",
            "g0dm0d3-deepseek-openai": "#F59E0B",
            "fairy-tales-deepseek-openai": "#F59E0B",
            "google-gla": "#3B82F6",
            "google": "#3B82F6",
            "nvidia-nim": "#76B900",
            "kimi-coding": "#EC4899",
            "mlx-local": "#6B7280",
            "cloudflare-ai-gateway": "#F6821F",
            "cloudflare-workers-ai": "#F6821F",
            "glm": "#0EA5E9",
            "g0dm0d3-glm": "#0EA5E9",
            "agua": "#F59E0B",
            "fugu": "#EC4899",
        }

        PROVIDER_LABELS = {
            "anthropic": "Anthropic",
            "openai-codex": "OpenAI",
            "openai": "OpenAI",
            "deepseek-openai": "DeepSeek",
            "g0dm0d3-deepseek-openai": "DeepSeek (g0dm0d3)",
            "fairy-tales-deepseek-openai": "DeepSeek (fairy-tales)",
            "google-gla": "Google",
            "google": "Google",
            "nvidia-nim": "NVIDIA NIM",
            "kimi-coding": "Kimi",
            "mlx-local": "Local (MLX)",
            "cloudflare-ai-gateway": "Cloudflare",
            "cloudflare-workers-ai": "Cloudflare Workers",
            "glm": "GLM",
            "g0dm0d3-glm": "GLM (g0dm0d3)",
            "agua": "Agua",
            "fugu": "Fugu",
        }

        # Format: provider model context max-out thinking images
        lines = output.split("\n")
        groups: dict[str, dict] = {}
        flat: list[dict] = []

        for line in lines:
            if not line.strip() or line.startswith("-"):
                continue

            cols = re.split(r"\s{2,}", line.strip())
            if len(cols) < 2:
                continue

            provider = cols[0].strip()
            model_id = cols[1].strip()

            if provider.lower() == "provider" or model_id.lower() == "model":
                continue

            context = cols[2].strip() if len(cols) >= 3 else ""
            thinking = False
            images = False
            if len(cols) >= 6:
                thinking = cols[4].strip().lower() in ("yes", "true", "1")
                images = cols[5].strip().lower() in ("yes", "true", "1")
            elif len(cols) >= 5:
                thinking = cols[4].strip().lower() in ("yes", "true", "1")

            if images_only and not images:
                continue

            color = PROVIDER_COLORS.get(provider, "#6B7280")
            provider_label = PROVIDER_LABELS.get(provider, provider)

            if provider not in groups:
                groups[provider] = {
                    "provider": provider,
                    "label": provider_label,
                    "color": color,
                    "models": [],
                }

            short_label = model_id.split("/")[-1] if "/" in model_id else model_id
            entry = {
                "id": model_id,
                "label": short_label,
                "provider": provider,
                "providerLabel": provider_label,
                "color": color,
                "context": context,
                "thinking": thinking,
                "images": images,
            }
            groups[provider]["models"].append(entry)
            flat.append(entry)

        result = sorted(
            groups.values(),
            key=lambda g: (g.get("label") or "").lower(),
        )
        for g in result:
            g["models"] = sorted(g["models"], key=lambda m: m["id"])

        flat_sorted = sorted(
            flat,
            key=lambda m: (m["providerLabel"].lower(), m["label"].lower()),
        )

        return {
            "models": result,
            "flat": flat_sorted,
            "count": len(flat_sorted),
            "source": "pi --list-models",
        }

    except asyncio.TimeoutError:
        return {"models": [], "flat": [], "count": 0, "error": "pi --list-models timed out"}
    except FileNotFoundError:
        return {"models": [], "flat": [], "count": 0, "error": "pi binary not found"}
    except Exception as e:
        return {"models": [], "flat": [], "count": 0, "error": str(e)}


@router.get("/version")
async def get_version():
    """Get the current pi version."""
    try:
        proc = await asyncio.create_subprocess_exec(
            PI_BINARY, "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
        version = (stderr.decode() or stdout.decode()).strip() if proc.returncode == 0 else "unknown"
        return {"version": version}
    except Exception as e:
        return {"version": "unknown", "error": str(e)}


@router.post("/update")
async def run_update():
    """Run pi update and return the output."""
    try:
        proc = await asyncio.create_subprocess_exec(
            PI_BINARY, "update",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        return {
            "success": proc.returncode == 0,
            "output": stdout.decode(),
            "errors": stderr.decode(),
        }
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Update timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extensions/install")
async def install_extension(request: InstallRequest):
    """Install a pi extension or package via pi install."""
    if not request.source.strip():
        raise HTTPException(status_code=400, detail="Source is required")

    try:
        proc = await asyncio.create_subprocess_exec(
            PI_BINARY, "install", request.source,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        return {
            "success": proc.returncode == 0,
            "output": stdout.decode(),
            "errors": stderr.decode(),
        }
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Install timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
async def system_chat(body: dict):
    """System-level chat for voice mode — understands intents and executes API calls."""
    from ..services.system_chat_service import handle_system_message

    message = body.get("message", "")
    result = await handle_system_message(message)
    return result
