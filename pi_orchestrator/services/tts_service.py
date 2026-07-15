"""
TTS Service — bridge to mossy (MOSS-TTS-Nano) for voice synthesis.

Calls the mossy FastAPI backend on localhost:7860. Handles warmup polling,
base64 audio decoding, and timeout control. Falls back gracefully when
mossy is not running.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

MOSSY_URL = os.environ.get("PI_MOSSY_URL", "http://127.0.0.1:7860")
MOSSY_WARMUP_TIMEOUT = int(os.environ.get("PI_MOSSY_WARMUP_TIMEOUT", "120"))
MOSSY_GENERATE_TIMEOUT = int(os.environ.get("PI_MOSSY_GENERATE_TIMEOUT", "60"))

_warmup_checked = False
_warmup_ready = False


async def is_available() -> bool:
    """Check if mossy is reachable and model is loaded."""
    global _warmup_checked, _warmup_ready
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{MOSSY_URL}/api/warmup-status")
            if r.status_code == 200:
                data = r.json()
                _warmup_ready = data.get("ready", False)
                _warmup_checked = True
                return _warmup_ready
    except Exception as e:
        logger.debug(f"mossy not reachable: {e}")
    _warmup_ready = False
    _warmup_checked = True
    return False


async def ensure_warm(ttl: int = MOSSY_WARMUP_TIMEOUT) -> bool:
    """Poll mossy until model is ready, up to ttl seconds."""
    global _warmup_checked, _warmup_ready

    if _warmup_ready:
        return True

    if not await is_available():
        # Not even alive — don't bother polling
        return False

    logger.info(f"Waiting for mossy warmup (timeout={ttl}s)...")
    import httpx
    elapsed = 0
    async with httpx.AsyncClient(timeout=5.0) as client:
        while elapsed < ttl:
            try:
                r = await client.get(f"{MOSSY_URL}/api/warmup-status")
                if r.status_code == 200:
                    data = r.json()
                    if data.get("ready"):
                        _warmup_ready = True
                        _warmup_checked = True
                        logger.info("mossy warmup complete")
                        return True
                    if data.get("failed"):
                        logger.error(f"mossy warmup failed: {data.get('error')}")
                        return False
            except Exception:
                pass
            await asyncio.sleep(2)
            elapsed += 2

    logger.warning(f"mossy warmup timed out after {ttl}s")
    return False


async def synthesize(
    text: str,
    voice_id: Optional[str] = None,
    language: Optional[str] = None,
) -> dict:
    """Generate speech from text using mossy TTS.

    Args:
        text: Text to synthesize.
        voice_id: Optional demo_id for a preset voice (e.g., 'en-female-01').
        language: Target language code (e.g., 'en', 'zh', 'jp').

    Returns:
        dict with:
          - audio_base64: base64-encoded WAV audio
          - sample_rate: audio sample rate
          - status: "ok" | "unavailable" | "error"
          - error: error message if any
    """
    # Check availability
    if not await is_available():
        return {
            "status": "unavailable",
            "error": "mossy TTS backend not reachable. Start mossy: cd /Users/kc/mossy && ./run.sh",
        }

    # Build request
    import httpx

    form_data = {
        "text": text.strip(),
        "enable_text_normalization": "0",
        "enable_normalize_tts_text": "1",
        "max_new_frames": "375",
    }

    if voice_id:
        form_data["demo_id"] = voice_id

    try:
        async with httpx.AsyncClient(timeout=float(MOSSY_GENERATE_TIMEOUT)) as client:
            r = await client.post(
                f"{MOSSY_URL}/api/generate",
                data=form_data,
            )
            if r.status_code != 200:
                error = "Unknown error"
                try:
                    error = r.json().get("error", r.text[:200])
                except Exception:
                    error = r.text[:200]
                logger.error(f"mossy generate failed: {error}")
                return {"status": "error", "error": error}

            data = r.json()
            return {
                "status": "ok",
                "audio_base64": data.get("audio_base64", ""),
                "sample_rate": data.get("sample_rate", 24000),
                "run_status": data.get("run_status", ""),
            }
    except Exception as e:
        logger.exception("mossy synthesize failed")
        return {"status": "error", "error": str(e)}


def wav_base64_to_audio_element_src(audio_base64: str) -> str:
    """Convert mossy's base64 WAV to a browser-playable data URL."""
    return f"data:audio/wav;base64,{audio_base64}"
