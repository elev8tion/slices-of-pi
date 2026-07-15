"""
Parakeet ONNX ASR — secondary STT using Handy's local model directory.

Uses NVIDIA Parakeet TDT 0.6B v3 INT8 ONNX weights already downloaded by
Handy.app (com.pais.handy). This is an **explicit** secondary provider for
cross-checking MLX Whisper / captions — it is never part of transcript=auto.

Model dir (default):
  ~/Library/Application Support/com.pais.handy/models/parakeet-tdt-0.6b-v3-int8/

  encoder-model.int8.onnx
  decoder_joint-model.int8.onnx
  nemo128.onnx
  vocab.txt
  config.json  (model_type: nemo-conformer-tdt)

Runtime:
  Prefer in-process onnx_asr (Python ≥3.10 + onnxruntime).
  Else subprocess via PI_PARAKEET_PYTHON (default: python3.11 / python3).

Long audio is chunked (~25s windows with small overlap) because Parakeet ONNX
is most reliable on short-to-medium segments without VAD.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_HANDY_DIR = (
    Path.home()
    / "Library/Application Support/com.pais.handy/models/parakeet-tdt-0.6b-v3-int8"
)

# Required files for Handy / istupakov layout
REQUIRED_FILES = (
    "encoder-model.int8.onnx",
    "decoder_joint-model.int8.onnx",
    "nemo128.onnx",
    "vocab.txt",
    "config.json",
)

CHUNK_SECONDS = float(os.getenv("PI_PARAKEET_CHUNK_SECONDS", "25"))
CHUNK_OVERLAP = float(os.getenv("PI_PARAKEET_CHUNK_OVERLAP", "0.5"))
FFMPEG_BINARY = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
FFPROBE_BINARY = shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"


def resolve_parakeet_model_dir() -> Path:
    """Resolve model directory from env or Handy default."""
    env = os.getenv("PI_PARAKEET_MODEL_DIR", "").strip()
    if env:
        return Path(os.path.expanduser(env)).expanduser().resolve()
    return DEFAULT_HANDY_DIR


def parakeet_available() -> tuple[bool, str]:
    """Return (ok, detail) — model dir present and a runnable onnx_asr path exists."""
    model_dir = resolve_parakeet_model_dir()
    if not model_dir.is_dir():
        return False, f"Model dir missing: {model_dir}"
    missing = [f for f in REQUIRED_FILES if not (model_dir / f).is_file()]
    if missing:
        return False, f"Model incomplete (missing {', '.join(missing)}) in {model_dir}"

    if _import_onnx_asr() is not None:
        return True, f"onnx_asr in-process · {model_dir}"

    py = _find_parakeet_python()
    if py:
        return True, f"onnx_asr via {py} · {model_dir}"

    return (
        False,
        "onnx-asr not installed. Install on Python ≥3.10: "
        "python3.11 -m pip install 'onnx-asr[cpu]'  "
        f"(model dir OK: {model_dir})",
    )


def _import_onnx_asr():
    try:
        import onnx_asr  # type: ignore
        return onnx_asr
    except ImportError:
        return None


def _find_parakeet_python() -> Optional[str]:
    """Find a Python that can import onnx_asr."""
    env = os.getenv("PI_PARAKEET_PYTHON", "").strip()
    candidates = []
    if env:
        candidates.append(env)
    candidates.extend(
        [
            "/opt/homebrew/bin/python3.11",
            "/opt/homebrew/bin/python3.12",
            "/opt/homebrew/bin/python3.13",
            "/opt/homebrew/bin/python3.10",
            shutil.which("python3.11") or "",
            shutil.which("python3.12") or "",
            shutil.which("python3") or "",
        ]
    )
    seen: set[str] = set()
    for c in candidates:
        if not c or c in seen:
            continue
        seen.add(c)
        if not os.path.isfile(c) and not shutil.which(c):
            continue
        try:
            r = subprocess.run(
                [c, "-c", "import onnx_asr"],
                capture_output=True,
                timeout=15,
            )
            if r.returncode == 0:
                return c
        except Exception:
            continue
    return None


def _audio_duration_seconds(path: str) -> float:
    try:
        r = subprocess.run(
            [
                FFPROBE_BINARY, "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return float((r.stdout or "0").strip() or 0)
    except Exception:
        return 0.0


def _extract_wav_chunk(
    audio_path: str,
    wav_out: str,
    start: float,
    duration: float,
) -> bool:
    """Extract mono 16 kHz PCM WAV chunk via ffmpeg."""
    cmd = [
        FFMPEG_BINARY, "-y",
        "-ss", str(max(0.0, start)),
        "-t", str(duration),
        "-i", audio_path,
        "-ar", "16000",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        wav_out,
    ]
    r = subprocess.run(cmd, capture_output=True, timeout=120)
    return r.returncode == 0 and os.path.isfile(wav_out) and os.path.getsize(wav_out) > 44


def _recognize_wav_inprocess(wav_path: str, model_dir: Path) -> str:
    onnx_asr = _import_onnx_asr()
    if onnx_asr is None:
        raise RuntimeError("onnx_asr not importable in this process")
    # Cache model on module for repeated chunks
    cache = getattr(_recognize_wav_inprocess, "_cache", None)
    key = str(model_dir)
    if not cache or cache.get("key") != key:
        model = onnx_asr.load_model(
            "nemo-parakeet-tdt-0.6b-v3",
            str(model_dir),
            quantization="int8",
        )
        _recognize_wav_inprocess._cache = {"key": key, "model": model}  # type: ignore[attr-defined]
    else:
        model = cache["model"]
    result = model.recognize(wav_path)
    if isinstance(result, str):
        return result.strip()
    # list of results
    if isinstance(result, (list, tuple)):
        return " ".join(str(x).strip() for x in result if x).strip()
    return str(result).strip()


def _recognize_wav_subprocess(wav_path: str, model_dir: Path, python_bin: str) -> str:
    """Run recognition in a child Python that has onnx-asr (e.g. 3.11)."""
    script = r"""
import json, sys
from pathlib import Path
import onnx_asr

model_dir, wav_path = sys.argv[1], sys.argv[2]
model = onnx_asr.load_model("nemo-parakeet-tdt-0.6b-v3", model_dir, quantization="int8")
text = model.recognize(wav_path)
if not isinstance(text, str):
    if isinstance(text, (list, tuple)):
        text = " ".join(str(x) for x in text if x)
    else:
        text = str(text)
print(json.dumps({"text": text.strip()}))
"""
    r = subprocess.run(
        [python_bin, "-c", script, str(model_dir), wav_path],
        capture_output=True,
        text=True,
        timeout=600,
    )
    if r.returncode != 0:
        err = (r.stderr or r.stdout or "")[-800:]
        raise RuntimeError(f"Parakeet subprocess failed: {err}")
    # last non-empty line is JSON (warnings may precede)
    lines = [ln for ln in (r.stdout or "").splitlines() if ln.strip().startswith("{")]
    if not lines:
        raise RuntimeError(f"Parakeet produced no JSON output: {(r.stdout or '')[:300]}")
    data = json.loads(lines[-1])
    return (data.get("text") or "").strip()


def _recognize_wav(wav_path: str, model_dir: Path) -> str:
    if _import_onnx_asr() is not None:
        return _recognize_wav_inprocess(wav_path, model_dir)
    py = _find_parakeet_python()
    if not py:
        ok, detail = parakeet_available()
        raise RuntimeError(detail if not ok else "Parakeet Python not found")
    return _recognize_wav_subprocess(wav_path, model_dir, py)


def transcribe_file_sync(
    audio_path: str,
    *,
    chunk_seconds: float = CHUNK_SECONDS,
    overlap: float = CHUNK_OVERLAP,
) -> list[dict]:
    """Transcribe audio file → list of {index, start, end, text} segments.

    Long files are split into chunks. Short files run as one segment.
    """
    ok, detail = parakeet_available()
    if not ok:
        raise RuntimeError(detail)

    model_dir = resolve_parakeet_model_dir()
    audio_path = str(Path(audio_path).expanduser().resolve())
    if not os.path.isfile(audio_path):
        raise RuntimeError(f"Audio not found: {audio_path}")

    duration = _audio_duration_seconds(audio_path)
    if duration <= 0:
        # still try single-shot
        duration = chunk_seconds

    segments: list[dict] = []
    idx = 0

    # Single shot if short enough
    if duration <= chunk_seconds + 1.0:
        with tempfile.TemporaryDirectory(prefix="parakeet_") as td:
            wav = os.path.join(td, "full.wav")
            if not _extract_wav_chunk(audio_path, wav, 0.0, duration + 0.5):
                # already wav?
                wav = audio_path
            text = _recognize_wav(wav, model_dir)
            if text:
                segments.append({
                    "index": 1,
                    "start": 0.0,
                    "end": round(duration, 3),
                    "text": text,
                })
        return segments

    # Chunked
    start = 0.0
    step = max(1.0, chunk_seconds - overlap)
    with tempfile.TemporaryDirectory(prefix="parakeet_") as td:
        while start < duration:
            chunk_dur = min(chunk_seconds, duration - start + 0.05)
            if chunk_dur < 0.4:
                break
            wav = os.path.join(td, f"chunk_{idx:04d}.wav")
            if not _extract_wav_chunk(audio_path, wav, start, chunk_dur):
                logger.warning("Parakeet: failed to extract chunk at %.1fs", start)
                start += step
                continue
            try:
                text = _recognize_wav(wav, model_dir)
            except Exception as e:
                logger.warning("Parakeet chunk @%.1fs failed: %s", start, e)
                text = ""
            if text:
                idx += 1
                segments.append({
                    "index": idx,
                    "start": round(start, 3),
                    "end": round(min(duration, start + chunk_dur), 3),
                    "text": text,
                })
            start += step

    logger.info(
        "Parakeet: %d segments, %d chars over %.1fs audio (model=%s)",
        len(segments),
        sum(len(s["text"]) for s in segments),
        duration,
        model_dir.name,
    )
    return segments


async def transcribe_file(
    audio_path: str,
    *,
    timeout_seconds: int = 1800,
) -> list[dict]:
    """Async wrapper — runs blocking ONNX work in a thread."""
    return await asyncio.wait_for(
        asyncio.to_thread(transcribe_file_sync, audio_path),
        timeout=timeout_seconds,
    )
