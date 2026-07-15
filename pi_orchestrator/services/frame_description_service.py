"""
Frame Description Service — Gemini Vision-powered frame analysis.

Sends extracted video frames to Google Gemini for description.
Uses GEMINI_API_KEY from environment or ~/.pi/agent/auth.json.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import mimetypes
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Prefer env var, fall back to auth.json
AUTH_PATH = Path.home() / ".pi" / "agent" / "auth.json"
DEFAULT_MODEL = os.getenv("PI_FLIXZ_VISION_MODEL", "gemini-2.0-flash")
GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"


def _load_gemini_api_key() -> str:
    """Load Gemini API key from GEMINI_API_KEY env var or ~/.pi/agent/auth.json."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if key:
        return key

    if AUTH_PATH.exists():
        try:
            auth = json.loads(AUTH_PATH.read_text())
            key = (
                auth.get("gemini", {}).get("key")
                or auth.get("gemini", {}).get("apiKey")
                or auth.get("google", {}).get("gemini_key")
                or auth.get("GOOGLE_API_KEY")
                or ""
            ).strip()
        except (json.JSONDecodeError, OSError):
            pass

    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY not set. Set the environment variable or add it to "
            f"{AUTH_PATH} as {{\"gemini\": {{\"key\": \"...\"}}}}"
        )
    return key


async def describe_frame(
    image_path: str,
    prompt: str = "Describe this video frame in detail. What do you see?",
    model: str = DEFAULT_MODEL,
    max_tokens: int = 300,
    api_key: Optional[str] = None,
) -> dict:
    """Send a single frame image to Gemini for description.

    Args:
        image_path: Path to PNG/JPG frame file.
        prompt: Description prompt.
        model: Gemini model ID (default: gemini-2.0-flash).
        max_tokens: Max response tokens.
        api_key: Optional override for the API key.

    Returns:
        dict with filename, description, model, tokens_used.
    """
    key = api_key or _load_gemini_api_key()

    # Read and encode image
    with open(image_path, "rb") as f:
        image_data = f.read()

    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type or not mime_type.startswith("image/"):
        mime_type = "image/png"

    image_b64 = base64.b64encode(image_data).decode()

    # Build Gemini API request
    url = f"{GEMINI_API_ENDPOINT}/{model}:generateContent?key={key}"

    body = {
        "contents": [{
            "parts": [
                {
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": image_b64,
                    }
                },
                {"text": prompt},
            ]
        }],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.4,
        },
    }

    import aiohttp

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=body,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise RuntimeError(
                        f"Gemini API returned {resp.status}: {error_text[:300]}"
                    )
                result = await resp.json()

        # Extract text from Gemini response
        description = ""
        tokens_used = 0
        try:
            candidates = result.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                for part in parts:
                    if "text" in part:
                        description += part["text"]
            tokens_used = (
                result.get("usageMetadata", {}).get("candidatesTokenCount", 0)
                + result.get("usageMetadata", {}).get("promptTokenCount", 0)
            )
        except Exception:
            pass

        return {
            "filename": Path(image_path).name,
            "description": description.strip(),
            "model": model,
            "tokens_used": tokens_used,
            "provider": "gemini",
        }

    except ImportError:
        # Fall back to httpx
        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=body)
                if resp.status_code != 200:
                    raise RuntimeError(
                        f"Gemini API returned {resp.status_code}: {resp.text[:300]}"
                    )
                result = resp.json()

            description = ""
            tokens_used = 0
            try:
                candidates = result.get("candidates", [])
                if candidates:
                    content = candidates[0].get("content", {})
                    parts = content.get("parts", [])
                    for part in parts:
                        if "text" in part:
                            description += part["text"]
                tokens_used = (
                    result.get("usageMetadata", {}).get("candidatesTokenCount", 0)
                    + result.get("usageMetadata", {}).get("promptTokenCount", 0)
                )
            except Exception:
                pass

            return {
                "filename": Path(image_path).name,
                "description": description.strip(),
                "model": model,
                "tokens_used": tokens_used,
                "provider": "gemini",
            }
        except ImportError:
            raise RuntimeError(
                "No HTTP client available. Install aiohttp or httpx: "
                "pip install aiohttp"
            )


async def _describe_frame_claude(
    image_path: str,
    prompt: str = "Describe this video frame in detail. What do you see?",
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 300,
) -> dict:
    """Send a single frame to Claude Vision API for description.

    Auth: reads from ~/.pi/agent/auth.json (anthropic.access or anthropic.key).
    """
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode()

    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type or not mime_type.startswith("image/"):
        mime_type = "image/png"

    # Load Claude auth
    if not AUTH_PATH.exists():
        raise RuntimeError(f"Claude auth not found at {AUTH_PATH}")
    auth = json.loads(AUTH_PATH.read_text())
    token = auth.get("anthropic", {}).get("access") or auth.get("anthropic", {}).get("key")
    if not token:
        raise RuntimeError("No Anthropic auth token in ~/.pi/agent/auth.json")

    is_oauth = str(token).startswith("sk-ant-oat")
    headers = {
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }
    if is_oauth:
        headers["Authorization"] = f"Bearer {token}"
    else:
        headers["x-api-key"] = token

    body = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": mime_type,
                        "data": image_data,
                    },
                },
                {"type": "text", "text": prompt},
            ],
        }],
    }

    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=body,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise RuntimeError(f"Claude API returned {resp.status}: {error_text[:300]}")
                result = await resp.json()
    except ImportError:
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=body,
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Claude API returned {resp.status_code}: {resp.text[:300]}")
            result = resp.json()

    description = ""
    for block in result.get("content", []):
        if block.get("type") == "text":
            description += block.get("text", "")

    return {
        "filename": Path(image_path).name,
        "description": description.strip(),
        "model": model,
        "tokens_used": result.get("usage", {}).get("output_tokens", 0),
        "provider": "claude",
    }


async def describe_frame_batch(
    frame_paths: list[str],
    prompt: str = "Describe this video frame in detail. What do you see?",
    model: str = DEFAULT_MODEL,
    max_concurrent: int = 3,
    provider: str = "gemini",
) -> list[dict]:
    """Describe multiple frames concurrently.

    Args:
        provider: 'gemini' (default) or 'claude'.

    Limits concurrency to avoid rate limiting.
    Returns list of description dicts in the same order as frame_paths.
    """
    sem = asyncio.Semaphore(max_concurrent)
    results: list[Optional[dict]] = [None] * len(frame_paths)

    async def _describe_one(idx: int, path: str) -> None:
        async with sem:
            try:
                if provider == "claude":
                    results[idx] = await _describe_frame_claude(path, prompt)
                else:
                    results[idx] = await describe_frame(path, prompt, model)
            except Exception as e:
                logger.warning(
                    f"Frame {idx} ({Path(path).name}) {provider} description failed: {e}"
                )
                results[idx] = {
                    "filename": Path(path).name,
                    "description": f"[Error: {e}]",
                    "model": "claude-sonnet-4-20250514" if provider == "claude" else model,
                    "tokens_used": 0,
                    "provider": provider,
                }

    tasks = [_describe_one(i, p) for i, p in enumerate(frame_paths)]
    await asyncio.gather(*tasks)

    return [r for r in results if r is not None]
