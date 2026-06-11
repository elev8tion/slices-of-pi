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
async def list_models():
    """Return available models grouped by provider.

    Parses the output of `pi --list-models` to build a structured
    list of models organized by provider with metadata.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            PI_BINARY, "--list-models",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,  # pi outputs models on stderr
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
        output = stdout.decode().strip()
        if not output:
            return {"models": [], "error": "No output from pi --list-models"}

        PROVIDER_COLORS = {
            "anthropic": "#8B5CF6",
            "openai-codex": "#22C55E",
            "deepseek-openai": "#F59E0B",
            "g0dm0d3-deepseek-openai": "#F59E0B",
            "google-gla": "#3B82F6",
            "nvidia-nim": "#76B900",
            "kimi-coding": "#EC4899",
            "mlx-local": "#6B7280",
            "cloudflare-ai-gateway": "#F6821F",
            "cloudflare-workers-ai": "#F6821F",
        }

        PROVIDER_LABELS = {
            "anthropic": "Anthropic",
            "openai-codex": "OpenAI",
            "deepseek-openai": "DeepSeek",
            "g0dm0d3-deepseek-openai": "DeepSeek",
            "google-gla": "Google",
            "nvidia-nim": "NVIDIA NIM",
            "kimi-coding": "Kimi",
            "mlx-local": "Local (MLX)",
            "cloudflare-ai-gateway": "Cloudflare",
            "cloudflare-workers-ai": "Cloudflare Workers",
        }

        PROVIDER_ORDER = {
            k: i for i, k in enumerate([
                "anthropic", "openai-codex", "deepseek-openai",
                "g0dm0d3-deepseek-openai", "google-gla", "nvidia-nim",
                "kimi-coding", "mlx-local", "cloudflare-ai-gateway",
                "cloudflare-workers-ai",
            ])
        }

        # Parse the tabular output
        # pi --list-models uses space-separated columns with variable widths
        # Format: provider model context max-out thinking images
        lines = output.split("\n")
        groups: dict[str, dict] = {}

        for line in lines:
            if not line.strip() or line.startswith("-"):
                continue

            # Split on 2+ spaces to get columns (handles variable-width columns)
            import re
            cols = re.split(r"\s{2,}", line.strip())
            if len(cols) < 2:
                continue

            provider = cols[0].strip()
            model_id = cols[1].strip()

            # Skip header rows
            if provider == "provider" or model_id == "model":
                continue

            # Extract context and thinking from remaining columns
            context = cols[2].strip() if len(cols) >= 3 else ""
            thinking_col = cols[4].strip().lower() if len(cols) >= 5 else "no"
            thinking = thinking_col == "yes"

            if provider not in groups:
                groups[provider] = {
                    "label": PROVIDER_LABELS.get(provider, provider),
                    "color": PROVIDER_COLORS.get(provider, "#6B7280"),
                    "models": [],
                }

            # Build a clean label
            label = model_id
            short_label = label.split("/")[-1] if "/" in label else label

            groups[provider]["models"].append({
                "id": label,
                "label": short_label,
                "provider": provider,
                "providerLabel": PROVIDER_LABELS.get(provider, provider),
                "context": context,
                "thinking": thinking,
            })

        # Convert to sorted array
        result = sorted(
            groups.values(),
            key=lambda g: (PROVIDER_ORDER.get(g["label"], 99), g["label"]),
        )
        # Sort models within each group
        for g in result:
            g["models"] = sorted(g["models"], key=lambda m: m["id"])

        return {"models": result}

    except asyncio.TimeoutError:
        return {"models": [], "error": "pi --list-models timed out"}
    except FileNotFoundError:
        return {"models": [], "error": "pi binary not found"}
    except Exception as e:
        return {"models": [], "error": str(e)}


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
