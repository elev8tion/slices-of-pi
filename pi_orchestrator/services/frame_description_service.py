"""
Frame Description Service — multi-backend vision for Flixz frames.

Backends:
  - gemini  — Google Generative Language API
  - claude  — Anthropic Messages API
  - openai  — OpenAI-compatible Chat Completions (openai-codex OAuth / OPENAI_API_KEY)
  - grok    — xAI OpenAI-compatible Chat Completions (xai-auth OAuth / XAI_API_KEY)

Auth is loaded from env vars and ~/.pi/agent/auth.json (same place pi uses).
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
MODELS_PATH = Path.home() / ".pi" / "agent" / "models.json"
DEFAULT_MODEL = os.getenv("PI_FLIXZ_VISION_MODEL", "gemini-2.0-flash")
GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"
OPENAI_DEFAULT_BASE = "https://api.openai.com/v1"
XAI_DEFAULT_BASE = "https://api.x.ai/v1"


def _load_auth() -> dict:
    if not AUTH_PATH.exists():
        return {}
    try:
        return json.loads(AUTH_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _provider_base_url(provider_name: str, default: str) -> str:
    """Read baseUrl from models.json providers if present."""
    if MODELS_PATH.exists():
        try:
            data = json.loads(MODELS_PATH.read_text())
            prov = (data.get("providers") or {}).get(provider_name) or {}
            base = (prov.get("baseUrl") or prov.get("base_url") or "").rstrip("/")
            if base:
                # openai-codex baseUrl is ChatGPT backend (not standard vision chat)
                if "chatgpt.com" in base or "backend-api" in base:
                    return default
                if not base.endswith("/v1"):
                    # Chat completions expect .../v1
                    if base.endswith("/v1/"):
                        return base.rstrip("/")
                return base if base.endswith("/v1") else base + "/v1" if "/v1" not in base else base
        except (json.JSONDecodeError, OSError):
            pass
    return default


def _load_gemini_api_key() -> str:
    """Load Gemini API key from GEMINI_API_KEY env var or ~/.pi/agent/auth.json."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if key:
        return key

    auth = _load_auth()
    key = (
        auth.get("gemini", {}).get("key")
        or auth.get("gemini", {}).get("apiKey")
        or auth.get("google", {}).get("gemini_key")
        or auth.get("GOOGLE_API_KEY")
        or ""
    ).strip()

    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY not set. Set the environment variable or add it to "
            f"{AUTH_PATH} as {{\"gemini\": {{\"key\": \"...\"}}}}"
        )
    return key


def _load_openai_token() -> str:
    """OpenAI / Codex token: OPENAI_API_KEY or openai-codex OAuth access."""
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if key:
        return key
    auth = _load_auth()
    key = (
        auth.get("openai", {}).get("key")
        or auth.get("openai", {}).get("access")
        or auth.get("openai-codex", {}).get("access")
        or auth.get("openai-codex", {}).get("key")
        or ""
    ).strip()
    if not key:
        raise RuntimeError(
            "No OpenAI credentials. Set OPENAI_API_KEY or ensure openai-codex "
            f"OAuth is in {AUTH_PATH}"
        )
    return key


def _load_xai_token() -> str:
    """xAI / Grok token: XAI_API_KEY or xai-auth OAuth access."""
    key = os.getenv("XAI_API_KEY", "").strip() or os.getenv("GROK_API_KEY", "").strip()
    if key:
        return key
    auth = _load_auth()
    key = (
        auth.get("xai-auth", {}).get("access")
        or auth.get("xai", {}).get("access")
        or auth.get("xai", {}).get("key")
        or auth.get("xai-auth", {}).get("key")
        or ""
    ).strip()
    if not key:
        raise RuntimeError(
            "No xAI/Grok credentials. Set XAI_API_KEY or ensure xai-auth "
            f"OAuth is in {AUTH_PATH}"
        )
    return key


async def _http_json_post(url: str, headers: dict, body: dict, timeout: float = 45.0) -> dict:
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=headers,
                json=body,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                text = await resp.text()
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status}: {text[:400]}")
                return json.loads(text)
    except ImportError:
        import httpx
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=body)
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:400]}")
            return resp.json()


async def _describe_frame_openai_compatible(
    image_path: str,
    prompt: str,
    model: str,
    token: str,
    base_url: str,
    provider_label: str,
    max_tokens: int = 300,
) -> dict:
    """OpenAI-compatible chat completions with image input (OpenAI, xAI Grok, etc.)."""
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type or not mime_type.startswith("image/"):
        mime_type = "image/png"

    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{image_b64}",
                    },
                },
                {"type": "text", "text": prompt},
            ],
        }],
    }

    result = await _http_json_post(url, headers, body)
    description = ""
    try:
        choices = result.get("choices") or []
        if choices:
            msg = choices[0].get("message") or {}
            content = msg.get("content")
            if isinstance(content, str):
                description = content
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        description += part.get("text") or ""
                    elif isinstance(part, str):
                        description += part
    except Exception:
        pass

    usage = result.get("usage") or {}
    tokens = int(usage.get("total_tokens") or usage.get("completion_tokens") or 0)

    return {
        "filename": Path(image_path).name,
        "description": description.strip(),
        "model": model,
        "tokens_used": tokens,
        "provider": provider_label,
    }


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
        provider: 'gemini' | 'claude' | 'openai' | 'grok' (aliases: openai-codex, xai, xai-auth).

    Limits concurrency to avoid rate limiting.
    Returns list of description dicts in the same order as frame_paths.
    """
    provider = (provider or "gemini").lower().strip()
    # Normalize aliases from UI / pi provider ids
    if provider in ("openai-codex", "openai_codex", "codex"):
        provider = "openai"
    if provider in ("xai", "xai-auth", "x_ai", "xai_auth"):
        provider = "grok"

    # Resolve auth + base + default model once
    openai_token = ""
    openai_base = OPENAI_DEFAULT_BASE
    xai_token = ""
    xai_base = XAI_DEFAULT_BASE

    if provider == "openai":
        openai_token = _load_openai_token()
        openai_base = _provider_base_url("openai-codex", OPENAI_DEFAULT_BASE)
        if not model or model == DEFAULT_MODEL:
            model = os.getenv("PI_FLIXZ_OPENAI_MODEL", "gpt-5.4")
    elif provider == "grok":
        xai_token = _load_xai_token()
        xai_base = _provider_base_url("xai-auth", XAI_DEFAULT_BASE)
        # models.json may not define xai base; force api.x.ai
        if "chatgpt.com" in xai_base:
            xai_base = XAI_DEFAULT_BASE
        if not model or model == DEFAULT_MODEL:
            model = os.getenv("PI_FLIXZ_GROK_MODEL", "grok-4.3")

    sem = asyncio.Semaphore(max_concurrent)
    results: list[Optional[dict]] = [None] * len(frame_paths)

    async def _describe_one(idx: int, path: str) -> None:
        async with sem:
            try:
                if provider == "claude":
                    results[idx] = await _describe_frame_claude(
                        path, prompt, model=model or "claude-sonnet-4-5"
                    )
                elif provider == "openai":
                    results[idx] = await _describe_frame_openai_compatible(
                        path,
                        prompt,
                        model=model,
                        token=openai_token,
                        base_url=openai_base,
                        provider_label="openai",
                    )
                elif provider == "grok":
                    results[idx] = await _describe_frame_openai_compatible(
                        path,
                        prompt,
                        model=model,
                        token=xai_token,
                        base_url=xai_base,
                        provider_label="grok",
                    )
                else:
                    results[idx] = await describe_frame(path, prompt, model)
            except Exception as e:
                logger.warning(
                    f"Frame {idx} ({Path(path).name}) {provider} description failed: {e}"
                )
                results[idx] = {
                    "filename": Path(path).name,
                    "description": f"[Error: {e}]",
                    "model": model or DEFAULT_MODEL,
                    "tokens_used": 0,
                    "provider": provider,
                }

    tasks = [_describe_one(i, p) for i, p in enumerate(frame_paths)]
    await asyncio.gather(*tasks)

    return [r for r in results if r is not None]
