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
    """Prefer openai-codex OAuth (how pi runs Codex), then OPENAI_API_KEY."""
    auth = _load_auth()
    # Prefer working pi OAuth path first (user's long-standing setup)
    key = (
        auth.get("openai-codex", {}).get("access")
        or auth.get("openai-codex", {}).get("key")
        or ""
    ).strip()
    if key:
        return key
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if key:
        return key
    key = (
        auth.get("openai", {}).get("key")
        or auth.get("openai", {}).get("access")
        or ""
    ).strip()
    if not key:
        raise RuntimeError(
            "No OpenAI/Codex credentials. Ensure openai-codex OAuth is in "
            f"{AUTH_PATH} (same as pi) or set OPENAI_API_KEY"
        )
    return key


def _is_jwt(token: str) -> bool:
    return token.count(".") == 2 and not token.startswith("sk-")


def _codex_account_id(token: str) -> str:
    """Extract chatgpt_account_id from openai-codex OAuth JWT (same as pi)."""
    import base64 as b64

    try:
        payload_b64 = token.split(".")[1]
        pad = "=" * (-len(payload_b64) % 4)
        payload = json.loads(b64.urlsafe_b64decode(payload_b64 + pad))
        account_id = (payload.get("https://api.openai.com/auth") or {}).get(
            "chatgpt_account_id"
        )
        if not account_id:
            raise ValueError("no chatgpt_account_id")
        return str(account_id)
    except Exception as e:
        raise RuntimeError(
            f"Failed to read ChatGPT account id from openai-codex OAuth token: {e}"
        ) from e


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
    """OpenAI-compatible chat completions with image input (API keys, xAI Grok, etc.)."""
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


def _extract_codex_text(event: dict) -> str:
    """Pull text from Codex Responses SSE event payloads."""
    # Incremental deltas
    if event.get("type") == "response.output_text.delta":
        return str(event.get("delta") or "")
    if event.get("type") == "response.content_part.delta":
        d = event.get("delta") or {}
        if isinstance(d, dict):
            return str(d.get("text") or d.get("delta") or "")
        return str(d) if d else ""

    # Completed response object
    response = event.get("response") if isinstance(event.get("response"), dict) else None
    if response and event.get("type") in (
        "response.completed",
        "response.done",
        "response.incomplete",
    ):
        parts: list[str] = []
        for item in response.get("output") or []:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "message":
                for c in item.get("content") or []:
                    if isinstance(c, dict) and c.get("type") in ("output_text", "text"):
                        parts.append(str(c.get("text") or ""))
            if item.get("type") == "output_text" and item.get("text"):
                parts.append(str(item.get("text")))
        return "".join(parts)
    return ""


async def _describe_frame_openai_codex(
    image_path: str,
    prompt: str,
    model: str,
    token: str,
    max_tokens: int = 300,
) -> dict:
    """Vision via ChatGPT Codex Responses API + OAuth (same path pi uses).

    POST https://chatgpt.com/backend-api/codex/responses
    Headers: Authorization Bearer <oauth>, chatgpt-account-id from JWT claim.
    """
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type or not mime_type.startswith("image/"):
        mime_type = "image/png"

    account_id = _codex_account_id(token)
    # Prefer models.json baseUrl when it's the chatgpt backend
    base = "https://chatgpt.com/backend-api"
    if MODELS_PATH.exists():
        try:
            data = json.loads(MODELS_PATH.read_text())
            prov = (data.get("providers") or {}).get("openai-codex") or {}
            bu = (prov.get("baseUrl") or "").rstrip("/")
            if bu and "chatgpt.com" in bu:
                base = bu
        except (json.JSONDecodeError, OSError):
            pass
    url = f"{base}/codex/responses" if not base.endswith("/codex/responses") else base
    if base.endswith("/codex"):
        url = f"{base}/responses"

    import time as _time
    session_id = f"flixz-{os.getpid()}-{int(_time.time() * 1000)}"
    headers = {
        "Authorization": f"Bearer {token}",
        "chatgpt-account-id": account_id,
        "OpenAI-Beta": "responses=experimental",
        "accept": "text/event-stream",
        "content-type": "application/json",
        "originator": "slice-of-pi",
        "User-Agent": "slice-of-pi (macos; flixz)",
        "session-id": session_id,
        "x-client-request-id": session_id,
    }

    body = {
        "model": model,
        "store": False,
        "stream": True,
        "instructions": "You describe images accurately and briefly.",
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_image",
                        "image_url": f"data:{mime_type};base64,{image_b64}",
                    },
                    {
                        "type": "input_text",
                        "text": prompt,
                    },
                ],
            }
        ],
        "text": {"verbosity": "low"},
        "include": ["reasoning.encrypted_content"],
        "tool_choice": "auto",
        "parallel_tool_calls": False,
    }

    description_parts: list[str] = []
    tokens_used = 0

    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=headers,
                json=body,
                timeout=aiohttp.ClientTimeout(total=90),
            ) as resp:
                if resp.status != 200:
                    err = await resp.text()
                    raise RuntimeError(f"Codex HTTP {resp.status}: {err[:500]}")
                # Parse SSE
                buffer = ""
                async for raw in resp.content:
                    buffer += raw.decode("utf-8", errors="replace")
                    while "\n\n" in buffer:
                        chunk, buffer = buffer.split("\n\n", 1)
                        data_lines = [
                            ln[5:].strip()
                            for ln in chunk.split("\n")
                            if ln.startswith("data:")
                        ]
                        if not data_lines:
                            continue
                        data = "\n".join(data_lines).strip()
                        if not data or data == "[DONE]":
                            continue
                        try:
                            event = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        et = event.get("type") or ""
                        if et in ("error", "response.failed"):
                            msg = (
                                (event.get("response") or {}).get("error", {}).get("message")
                                or event.get("message")
                                or json.dumps(event)[:300]
                            )
                            raise RuntimeError(f"Codex error: {msg}")
                        piece = _extract_codex_text(event)
                        if piece and et.endswith(".delta"):
                            description_parts.append(piece)
                        elif piece and et in (
                            "response.completed",
                            "response.done",
                            "response.incomplete",
                        ):
                            # Prefer full completed text if we only got fragments
                            if not description_parts:
                                description_parts.append(piece)
                            elif len(piece) > len("".join(description_parts)):
                                description_parts = [piece]
                        # usage if present
                        resp_obj = event.get("response") if isinstance(event.get("response"), dict) else {}
                        usage = resp_obj.get("usage") or event.get("usage") or {}
                        if usage:
                            tokens_used = int(
                                usage.get("total_tokens")
                                or usage.get("output_tokens")
                                or usage.get("completion_tokens")
                                or tokens_used
                                or 0
                            )
    except ImportError:
        raise RuntimeError("aiohttp required for openai-codex OAuth streaming") from None

    description = "".join(description_parts).strip()
    if not description:
        raise RuntimeError("Codex returned empty description (check model vision support)")

    return {
        "filename": Path(image_path).name,
        "description": description,
        "model": model,
        "tokens_used": tokens_used,
        "provider": "openai-codex",
    }


async def _describe_frame_openai(
    image_path: str,
    prompt: str,
    model: str,
    max_tokens: int = 300,
) -> dict:
    """Route OpenAI: Codex OAuth JWT → ChatGPT backend; sk- keys → api.openai.com."""
    token = _load_openai_token()
    if _is_jwt(token):
        return await _describe_frame_openai_codex(
            image_path, prompt, model=model, token=token, max_tokens=max_tokens
        )
    return await _describe_frame_openai_compatible(
        image_path,
        prompt,
        model=model,
        token=token,
        base_url=OPENAI_DEFAULT_BASE,
        provider_label="openai",
        max_tokens=max_tokens,
    )


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

    if provider == "openai":
        if not model or model == DEFAULT_MODEL:
            model = os.getenv("PI_FLIXZ_OPENAI_MODEL", "gpt-5.4")
    elif provider == "grok":
        if not model or model == DEFAULT_MODEL:
            model = os.getenv("PI_FLIXZ_GROK_MODEL", "grok-4.3")
    elif provider == "gemini":
        # Kept for API compatibility; UI no longer exposes Gemini.
        pass

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
                    results[idx] = await _describe_frame_openai(
                        path, prompt, model=model
                    )
                elif provider == "grok":
                    xai_token = _load_xai_token()
                    xai_base = _provider_base_url("xai-auth", XAI_DEFAULT_BASE)
                    if "chatgpt.com" in xai_base:
                        xai_base = XAI_DEFAULT_BASE
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
