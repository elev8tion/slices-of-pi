"""
Flixz Service — run frame extraction via ffmpeg + optional Gemini Vision descriptions.

Uses ffmpeg for frame extraction (always available on macOS/Linux).
Optionally sends extracted frames to Gemini API for description.
Requires GEMINI_API_KEY env var or ~/.pi/agent/auth.json config.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Optional

from .. import database as db
from ..config import PI_HOME, PI_AGENT_DIR, PI_MANAGED_SESSIONS_DIR

logger = logging.getLogger(__name__)

FLIXZ_OUTPUT_DIR = PI_HOME / "flixz" / "output"
FLIXZ_INPUT_DIR = PI_HOME / "flixz" / "input"
FLIXZ_DEFAULT_TIMEOUT = int(os.getenv("PI_FLIXZ_TIMEOUT", "600"))  # 10 minutes
FFMPEG_BINARY = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
FFPROBE_BINARY = shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"
YTDLP_BINARY = shutil.which("yt-dlp") or shutil.which("youtube-dl")


def _path_is_within(base: Path, target: Path) -> bool:
    try:
        target.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def _local_video_allowed(expanded: Path, agent_id: Optional[str] = None) -> bool:
    """Local video files must sit under an explicit allowlist (T1 harden B3)."""
    roots: list[Path] = [
        FLIXZ_INPUT_DIR,
        FLIXZ_OUTPUT_DIR,
        PI_HOME / "flixz",
        PI_MANAGED_SESSIONS_DIR,
        PI_AGENT_DIR,
    ]
    # Extra roots from env (colon-separated), for local operator media folders
    extra = os.getenv("PI_FLIXZ_ALLOW_ROOTS", "")
    for part in extra.split(":"):
        part = part.strip()
        if part:
            roots.append(Path(os.path.expanduser(part)))

    if agent_id:
        agent = db.get_agent(agent_id)
        if agent:
            roots.append(PI_MANAGED_SESSIONS_DIR / agent["name"])

    resolved = expanded.resolve()
    return any(_path_is_within(root, resolved) for root in roots if root)

# VoiceKit CLI for native macOS transcription (Apple SFSpeechRecognizer, on-device)
# Note: SFSpeechRecognizer is weak on long video audio (often ~1 min effective / sparse).
_PRISMAKIT_ROOT = Path(os.getenv("PRISMAKIT_ROOT", str(Path.home() / "prismakit")))
VOICEKIT_CLI = str(_PRISMAKIT_ROOT / ".build" / "release" / "voicekit-transcribe")

# MLX Whisper — preferred local STT for long videos (Homebrew mlx_whisper)
MLX_WHISPER_BINARY = shutil.which("mlx_whisper") or "/opt/homebrew/bin/mlx_whisper"
MLX_WHISPER_MODEL = os.getenv(
    "PI_FLIXZ_WHISPER_MODEL",
    "mlx-community/whisper-large-v3-turbo",
)

# Handy.app Parakeet ONNX — secondary explicit STT (never in auto fallback)
# See docs/health/FLIXZ_STT_PLAN.md and services/parakeet_asr.py
HANDY_PARAKEET_DIR = Path.home() / "Library/Application Support/com.pais.handy/models/parakeet-tdt-0.6b-v3-int8"

TRASH_BINARY = shutil.which("trash") or "/usr/bin/trash"


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


async def _run_ffprobe(video_path: str) -> dict:
    """Get video metadata via ffprobe JSON output."""
    proc = await asyncio.create_subprocess_exec(
        FFPROBE_BINARY,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        video_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
    try:
        return json.loads(stdout.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return {}


async def _resolve_video_path(
    video_path: str,
    output_dir: Path,
    timeout_seconds: int = 300,
    agent_id: Optional[str] = None,
) -> str:
    """Resolve a video path that might be a URL, returning a local file path.

    Handles:
    - Local file paths under allowlisted roots (see _local_video_allowed)
    - YouTube / direct video URLs (downloaded via yt-dlp into output_dir)
    """
    # Local file — must be under allowlist (not arbitrary system paths)
    if not video_path.startswith(("http://", "https://")):
        expanded = Path(os.path.expanduser(video_path)).expanduser()
        if not expanded.is_file():
            raise RuntimeError(f"Video file not found: {expanded}")
        if not _local_video_allowed(expanded, agent_id=agent_id):
            raise RuntimeError(
                "Local video path not allowed. Place files under "
                f"~/.pi/flixz/input, agent session dir, or set PI_FLIXZ_ALLOW_ROOTS. "
                f"Got: {expanded}"
            )
        return str(expanded.resolve())

    # URL — try yt-dlp
    if not YTDLP_BINARY:
        raise RuntimeError(
            "Cannot process URLs — yt-dlp is not installed. "
            "Install it with: brew install yt-dlp"
        )

    # Determine if it's a YouTube URL to set format
    is_youtube = any(d in video_path for d in ["youtube.com", "youtu.be", "yt.be"])

    output_template = str(output_dir / "downloaded.%(ext)s")
    cmd = [
        YTDLP_BINARY,
        "-f", "best[height<=1080]" if is_youtube else "best",
        "-o", output_template,
        "--no-playlist",
        "--merge-output-format", "mp4",
        video_path,
    ]

    logger.info("Downloading video: %s", video_path)
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise RuntimeError(f"Video download timed out after {timeout_seconds}s")

    if proc.returncode != 0:
        stderr_text = stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"yt-dlp failed: {stderr_text[-400:]}")

    # Find the downloaded file
    for f in sorted(output_dir.glob("downloaded.*")):
        if f.suffix in (".mp4", ".mkv", ".webm", ".m4a", ".mp3"):
            logger.info("Downloaded: %s (%d bytes)", f.name, f.stat().st_size)
            return str(f)

    raise RuntimeError("yt-dlp completed but no output file found")


async def _extract_frames_ffmpeg(
    video_path: str,
    output_dir: Path,
    max_frames: int = 60,
    fps: int = 0,
    scene_detect: bool = True,
    timeout_seconds: int = 600,
) -> list[str]:
    """Extract frames using ffmpeg. Returns list of output file paths.
    
    If scene_detect=True and fps=0, first tries scene-change detection;
    falls back to fps=1 if 0 frames are produced (common in talking-head videos).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_pattern = str(output_dir / "frame_%04d.png")

    # Resolve effective fps — never pass 0 to ffmpeg
    effective_fps = fps if fps > 0 else 1
    use_scene_detect = scene_detect and fps == 0

    async def _run_ffmpeg(vf_filter: str) -> tuple[int, bytes]:
        """Run a single ffmpeg command, return (returncode, stderr)."""
        cmd = [FFMPEG_BINARY, "-y", "-i", video_path,
               "-vf", vf_filter,
               "-frames:v", str(max_frames),
               output_pattern]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise RuntimeError(f"ffmpeg timed out after {timeout_seconds}s")
        return proc.returncode, stderr

    def _error_tail(stderr: bytes) -> str:
        """Extract the most useful error lines from ffmpeg stderr."""
        text = stderr.decode("utf-8", errors="replace")
        # Find lines starting with "Error" or "Invalid" — those are the actionable ones
        lines = text.split("\n")
        errors = [l.strip() for l in lines if "Error" in l or "Invalid" in l or "No such" in l]
        if errors:
            return "; ".join(errors[-3:])  # last 3 error lines
        # Fall back to tail
        return text[-500:] if len(text) > 500 else text

    if use_scene_detect:
        # Try scene-detect first
        rc, stderr = await _run_ffmpeg("select='gte(scene,0.2)',scale=iw:ih")
        frame_files = sorted(output_dir.glob("frame_*.png"))
        if frame_files:
            return [str(f) for f in frame_files]
        if rc != 0:
            raise RuntimeError(f"ffmpeg exited with code {rc}: {_error_tail(stderr)}")
        # No frames — clean and fall through to fps-based
        logger.info("Scene detection produced 0 frames — using fps=%d", effective_fps)
        for f in output_dir.glob("frame_*.png"):
            f.unlink(missing_ok=True)

    # Standard fps-based extraction (always works)
    rc, stderr = await _run_ffmpeg(f"fps={effective_fps}")
    if rc != 0:
        raise RuntimeError(f"ffmpeg exited with code {rc}: {_error_tail(stderr)}")

    frame_files = sorted(output_dir.glob("frame_*.png"))
    return [str(f) for f in frame_files]


async def _extract_audio_ffmpeg(
    video_path: str,
    output_path: str,
    format: str = "m4a",
    sample_rate: int = 16000,
    timeout_seconds: int = 300,
) -> str:
    """Extract audio track from a video file using ffmpeg.

    Returns the output file path on success.
    """
    args = [
        FFMPEG_BINARY, "-y", "-i", video_path,
        "-vn",  # no video
        "-acodec", "aac" if format == "m4a" else "pcm_s16le",
        "-ar", str(sample_rate),
        "-ac", "1",  # mono for speech recognition
        output_path,
    ]

    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise RuntimeError(f"Audio extraction timed out after {timeout_seconds}s")

    if proc.returncode != 0:
        stderr_text = stderr.decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Audio extraction failed (code {proc.returncode}): {stderr_text}")

    return output_path


def move_to_trash(path: Path | str) -> bool:
    """Move a file or directory to the macOS Trash (or unlink as last resort)."""
    p = Path(path)
    if not p.exists():
        return False
    try:
        if TRASH_BINARY and os.path.isfile(TRASH_BINARY):
            import subprocess
            r = subprocess.run(
                [TRASH_BINARY, str(p)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if r.returncode == 0:
                logger.info("Trashed: %s", p)
                return True
            logger.warning("trash failed for %s: %s", p, (r.stderr or r.stdout)[:200])
        # Fallback: hard delete (still frees disk)
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        else:
            p.unlink(missing_ok=True)
        logger.info("Removed (no trash CLI): %s", p)
        return True
    except Exception as e:
        logger.warning("move_to_trash failed for %s: %s", p, e)
        return False


def trash_source_videos(output_dir: Path) -> list[str]:
    """After frames are extracted, trash downloaded source video files (keep frames/audio)."""
    trashed: list[str] = []
    if not output_dir.is_dir():
        return trashed
    for pattern in ("downloaded.*", "source.*", "input.*"):
        for f in output_dir.glob(pattern):
            if f.suffix.lower() in (".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v"):
                if move_to_trash(f):
                    trashed.append(str(f))
    return trashed


def trash_run_frames(output_dir: Path) -> int:
    """Trash all extracted frame_*.png in a run directory."""
    n = 0
    if not output_dir.is_dir():
        return 0
    for f in sorted(output_dir.glob("frame_*.png")):
        if move_to_trash(f):
            n += 1
    return n


def trash_run_all(output_dir: Path) -> bool:
    """Trash the entire run output directory."""
    return move_to_trash(output_dir)


async def _transcribe_audio_native(
    audio_path: str,
    language: str = "en-US",
    timeout_seconds: int = 300,
) -> list[dict]:
    """Transcribe via Apple SFSpeechRecognizer (VoiceKit).

    Works for short clips; long videos (10+ min) often return sparse/incomplete text.
    Prefer 'mlx' or 'captions' for YouTube / long media.
    """
    if not os.path.isfile(VOICEKIT_CLI):
        raise RuntimeError(
            f"voicekit-transcribe not found at {VOICEKIT_CLI}. "
            "Build it with: cd ~/prismakit && swift build -c release"
        )

    logger.info(f"Transcribing {audio_path} with VoiceKit (language={language})")

    proc = await asyncio.create_subprocess_exec(
        VOICEKIT_CLI,
        audio_path,
        language,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise RuntimeError(f"Transcription timed out after {timeout_seconds}s")

    if proc.returncode != 0:
        stderr_text = stderr.decode("utf-8", errors="replace")[:500]
        if "No speech detected" in stderr_text:
            logger.info(f"No speech detected in {audio_path}")
            return []
        raise RuntimeError(f"VoiceKit transcription failed (code {proc.returncode}): {stderr_text}")

    srt_text = stdout.decode("utf-8", errors="replace")
    return _parse_srt(srt_text)


async def _transcribe_audio_mlx(
    audio_path: str,
    language: str = "en",
    timeout_seconds: int = 900,
    output_dir: Optional[Path] = None,
) -> list[dict]:
    """Transcribe with local mlx_whisper (good quality for long video audio)."""
    if not os.path.isfile(MLX_WHISPER_BINARY):
        raise RuntimeError(
            "mlx_whisper not found. Install with: pip install mlx-whisper  "
            "or brew install mlx-whisper"
        )

    out = Path(output_dir) if output_dir else Path(audio_path).parent
    out.mkdir(parents=True, exist_ok=True)
    # mlx_whisper names output after the audio stem by default
    stem = Path(audio_path).stem

    logger.info(
        "Transcribing %s with mlx_whisper model=%s",
        audio_path, MLX_WHISPER_MODEL,
    )
    proc = await asyncio.create_subprocess_exec(
        MLX_WHISPER_BINARY,
        audio_path,
        "--model", MLX_WHISPER_MODEL,
        "--language", language,
        "--output-format", "srt",
        "--output-dir", str(out),
        "--verbose", "False",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise RuntimeError(f"mlx_whisper timed out after {timeout_seconds}s")

    if proc.returncode != 0:
        err = stderr.decode("utf-8", errors="replace")[-600:]
        raise RuntimeError(f"mlx_whisper failed (code {proc.returncode}): {err}")

    srt_path = out / f"{stem}.srt"
    if not srt_path.is_file():
        # Some versions write differently
        candidates = list(out.glob("*.srt"))
        if candidates:
            srt_path = candidates[0]
        else:
            raise RuntimeError("mlx_whisper completed but no .srt file found")

    srt_text = srt_path.read_text(encoding="utf-8", errors="replace")
    return _parse_srt(srt_text)


async def _fetch_youtube_captions(
    video_url: str,
    output_dir: Path,
    timeout_seconds: int = 120,
) -> list[dict]:
    """Pull auto/manual captions via yt-dlp (no STT model needed). Fast path for YouTube."""
    if not YTDLP_BINARY:
        raise RuntimeError("yt-dlp not installed")

    output_dir.mkdir(parents=True, exist_ok=True)
    # Write subs next to other run artifacts
    outtmpl = str(output_dir / "captions")
    cmd = [
        YTDLP_BINARY,
        "--skip-download",
        "--write-auto-sub",
        "--write-sub",
        "--sub-langs", "en.*,en",
        "--convert-subs", "srt",
        "-o", outtmpl,
        "--no-playlist",
        video_url,
    ]
    logger.info("Fetching YouTube captions for %s", video_url)
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise RuntimeError("Caption fetch timed out")

    # Find any .srt produced
    srt_files = sorted(output_dir.glob("captions*.srt")) + sorted(output_dir.glob("*.en*.srt"))
    if not srt_files:
        err = stderr.decode("utf-8", errors="replace")[-400:]
        raise RuntimeError(f"No captions available for this URL. yt-dlp: {err}")

    # Prefer the largest / first srt
    srt_text = srt_files[0].read_text(encoding="utf-8", errors="replace")
    segments = _parse_srt(srt_text)
    logger.info("Captions: %d segments from %s", len(segments), srt_files[0].name)
    return segments


async def _ensure_audio(resolved_local: str, output_dir: Path, timeout_seconds: int) -> str:
    """Extract mono m4a if missing; return path."""
    audio_out = str(output_dir / "audio.m4a")
    if not Path(audio_out).is_file():
        if not resolved_local:
            raise RuntimeError("No local video/audio to extract for STT")
        await _extract_audio_ffmpeg(
            resolved_local, audio_out, format="m4a",
            timeout_seconds=min(timeout_seconds, 300),
        )
    return audio_out


async def _run_one_transcript(
    method: str,
    *,
    video_path_or_url: str,
    resolved_local: str,
    output_dir: Path,
    timeout_seconds: int,
    is_youtube: bool,
) -> tuple[list[dict], str]:
    """Run a single STT provider. Returns (segments, full_text)."""
    if method == "captions":
        if not is_youtube:
            raise RuntimeError("captions provider only works for YouTube URLs")
        segs = await _fetch_youtube_captions(
            video_path_or_url, output_dir,
            timeout_seconds=min(timeout_seconds, 180),
        )
    elif method == "mlx":
        audio_out = await _ensure_audio(resolved_local, output_dir, timeout_seconds)
        segs = await _transcribe_audio_mlx(
            audio_out,
            language="en",
            timeout_seconds=min(timeout_seconds, 900),
            output_dir=output_dir,
        )
    elif method == "native":
        audio_out = await _ensure_audio(resolved_local, output_dir, timeout_seconds)
        segs = await _transcribe_audio_native(
            audio_out, language="en-US",
            timeout_seconds=min(timeout_seconds, 300),
        )
    elif method == "parakeet":
        # Secondary explicit provider — Handy ONNX via onnx-asr (never auto-fallback)
        from pi_orchestrator.services.parakeet_asr import (
            parakeet_available,
            transcribe_file,
        )
        ok, detail = parakeet_available()
        if not ok:
            raise RuntimeError(detail)
        audio_out = await _ensure_audio(resolved_local, output_dir, timeout_seconds)
        segs = await transcribe_file(
            audio_out,
            timeout_seconds=min(timeout_seconds, 1800),
        )
    else:
        raise RuntimeError(f"Unknown transcript provider: {method}")

    full = " ".join(s.get("text", "") for s in segs).strip()
    return segs, full


async def _resolve_transcript(
    provider: str,
    *,
    video_path_or_url: str,
    resolved_local: str,
    output_dir: Path,
    timeout_seconds: int,
) -> tuple[list[dict], str, str, dict]:
    """Run the chosen STT/captions provider.

    Returns (segments, full_text, provider_used, extras).
    extras may include compare transcripts: { "compare": { "mlx": {...}, "parakeet": {...} } }

    Providers:
      none | auto | native | mlx | captions | whisper | parakeet | compare

    auto = captions (YT) → mlx → native  — **never includes parakeet**
    parakeet = Handy ONNX only (secondary explicit)
    compare = run mlx + parakeet side-by-side for verification (primary = mlx if ok else parakeet)
    """
    p = (provider or "none").lower().strip()
    if p in ("whisper", "mlx_whisper"):
        p = "mlx"
    if p == "none":
        return [], "", "none", {}

    is_url = video_path_or_url.startswith(("http://", "https://"))
    is_youtube = is_url and any(
        d in video_path_or_url for d in ("youtube.com", "youtu.be", "yt.be")
    )

    # ── Compare: secondary verification path (mlx + parakeet, both kept) ──
    if p == "compare":
        compare: dict = {}
        primary_segs: list[dict] = []
        primary_full = ""
        primary_name = "none"

        for method in ("mlx", "parakeet"):
            try:
                segs, full = await _run_one_transcript(
                    method,
                    video_path_or_url=video_path_or_url,
                    resolved_local=resolved_local,
                    output_dir=output_dir,
                    timeout_seconds=timeout_seconds,
                    is_youtube=is_youtube,
                )
                compare[method] = {
                    "segments": segs,
                    "text": full,
                    "chars": len(full),
                    "segment_count": len(segs),
                    "ok": bool(full),
                }
                # Write side-by-side files for operator / agent discuss
                (output_dir / f"transcript_{method}.txt").write_text(full or "", encoding="utf-8")
                if full and not primary_full:
                    primary_segs, primary_full, primary_name = segs, full, method
                elif method == "mlx" and full:
                    # Prefer mlx as primary when both succeed
                    primary_segs, primary_full, primary_name = segs, full, method
                logger.info(
                    "Compare STT %s: %d segs, %d chars",
                    method, len(segs), len(full),
                )
            except Exception as e:
                logger.warning("Compare STT %s failed: %s", method, e)
                compare[method] = {
                    "segments": [],
                    "text": "",
                    "chars": 0,
                    "segment_count": 0,
                    "ok": False,
                    "error": str(e),
                }

        # Summary file for discuss / human review
        summary_lines = ["# STT compare (mlx vs parakeet)", ""]
        for name, data in compare.items():
            summary_lines.append(f"## {name}")
            if data.get("error"):
                summary_lines.append(f"ERROR: {data['error']}")
            else:
                summary_lines.append(
                    f"{data.get('segment_count', 0)} segments · {data.get('chars', 0)} chars"
                )
                summary_lines.append("")
                summary_lines.append(data.get("text") or "_(empty)_")
            summary_lines.append("")
        (output_dir / "transcript_compare.md").write_text(
            "\n".join(summary_lines), encoding="utf-8",
        )

        return primary_segs, primary_full, f"compare:{primary_name}", {"compare": compare}

    # ── auto chain — never includes parakeet (secondary only) ──
    chain: list[str]
    if p == "auto":
        chain = []
        if is_youtube:
            chain.append("captions")
        if os.path.isfile(MLX_WHISPER_BINARY):
            chain.append("mlx")
        chain.append("native")
    else:
        chain = [p]

    last_err: Optional[Exception] = None
    for method in chain:
        try:
            segs, full = await _run_one_transcript(
                method,
                video_path_or_url=video_path_or_url,
                resolved_local=resolved_local,
                output_dir=output_dir,
                timeout_seconds=timeout_seconds,
                is_youtube=is_youtube,
            )
            logger.info(
                "Transcription complete via %s: %d segments, %d chars",
                method, len(segs), len(full),
            )
            return segs, full, method, {}
        except Exception as e:
            last_err = e
            logger.warning("Transcript provider %s failed: %s", method, e)
            continue

    if last_err:
        logger.warning("All transcript providers failed: %s", last_err)
    return [], "", "none", {}


def build_flixz_brief(run: dict, extra_message: str = "") -> str:
    """Markdown brief for agent discussion of a Flixz run."""
    run_id = run.get("id") or run.get("run_id") or "?"
    lines = [
        "# Flixz run context (local operator)",
        "",
        f"- **Run ID:** `{run_id}`",
        f"- **Source:** `{run.get('video_path', '')}`",
        f"- **Status:** {run.get('status', '')}",
        f"- **Frames:** {run.get('frame_count') or 0}",
        f"- **Duration:** {run.get('duration_seconds') or '?'}s",
        f"- **Resolution:** {run.get('resolution') or '?'}",
        f"- **Output dir:** `{run.get('output_dir') or ''}`",
        "",
        "Frame PNGs (if still on disk) are under the output dir as `frame_*.png`.",
        "You can `read` those paths if the operator asks about visual content.",
        "",
    ]
    transcript = (run.get("transcript_text") or "").strip()
    if transcript:
        lines += ["## Transcript", "", transcript[:12000], ""]
        if len(transcript) > 12000:
            lines.append(f"_(truncated truncated to 12k chars; full text in DB / output dir)_")
            lines.append("")
    else:
        lines += ["## Transcript", "", "_(no transcript stored for this run)_", ""]

    # Frame descriptions live in sink_results JSON
    descs_raw = run.get("sink_results")
    if descs_raw:
        try:
            descs = json.loads(descs_raw) if isinstance(descs_raw, str) else descs_raw
            if isinstance(descs, list) and descs:
                lines += ["## Frame descriptions", ""]
                for i, d in enumerate(descs[:40]):
                    if isinstance(d, dict):
                        text = d.get("description") or d.get("text") or json.dumps(d)[:300]
                        idx = d.get("frame") or d.get("index") or i
                        lines.append(f"- **Frame {idx}:** {text}")
                    else:
                        lines.append(f"- {str(d)[:300]}")
                lines.append("")
        except Exception:
            pass

    if extra_message.strip():
        lines += ["## Operator request", "", extra_message.strip(), ""]
    else:
        lines += [
            "## Operator request",
            "",
            "Review this Flixz extraction. Summarize what the video is about from the "
            "transcript and frame descriptions, and ask what I want to do next with this material.",
            "",
        ]
    return "\n".join(lines)


def _parse_srt(srt_text: str) -> list[dict]:
    """Parse SRT text into a list of segment dicts."""
    segments: list[dict] = []
    blocks = srt_text.strip().split("\n\n")
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue
        try:
            index = int(lines[0].strip())
        except ValueError:
            continue

        # Parse timestamp line: "00:00:01,000 --> 00:00:04,500"
        times = lines[1].strip()
        parts = times.split("-->")
        if len(parts) != 2:
            continue

        start = _srt_time_to_seconds(parts[0].strip())
        end = _srt_time_to_seconds(parts[1].strip())
        text = " ".join(lines[2:]).strip()

        if text:
            segments.append({
                "index": index,
                "start": start,
                "end": end,
                "text": text,
            })

    return segments


def _srt_time_to_seconds(timestamp: str) -> float:
    """Convert SRT timestamp 'HH:MM:SS,mmm' to seconds."""
    # Handle both comma and period as millisecond separator
    ts = timestamp.replace(",", ".")
    parts = ts.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    return 0.0


async def _describe_frames(
    frame_paths: list[str],
    provider: str = "gemini",
    prompt: str = "Describe this video frame in detail. What do you see?",
    max_frames: int = 30,
    model: Optional[str] = None,
) -> list[dict]:
    """Send frames for description via the specified provider.

    Args:
        provider: 'gemini' (uses GEMINI_API_KEY) or 'claude' (uses ~/.pi/agent/auth.json).
        model: Optional model id from the operator's pi list (within that backend).
    """
    try:
        from pi_orchestrator.services.frame_description_service import describe_frame_batch
        kwargs: dict = {"provider": provider}
        if model:
            kwargs["model"] = model
        return await describe_frame_batch(frame_paths[:max_frames], prompt, **kwargs)
    except ImportError:
        logger.warning("frame_description_service not available — skipping descriptions")
        return []
    except Exception as e:
        logger.warning(f"{provider} frame description failed: {e}")
        return []


async def extract_video(
    video_path: str,
    max_frames: int = 60,
    fps: int = 0,
    scene_detect: bool = True,
    transcript: str = "auto",
    describe: str = "none",
    describe_model: Optional[str] = None,
    agent_id: Optional[str] = None,
    timeout_seconds: Optional[int] = None,
    mode: str = "full",
    trash_source_video: bool = True,
) -> dict:
    """Run frame extraction and/or transcription on a video.

    Args:
        video_path: Local path or URL (YouTube, direct video link).
        max_frames: Maximum frames to extract (ignored in transcript_only).
        fps: Frames per second (0 = auto/scene detect).
        scene_detect: Use scene-change detection.
        transcript: none | auto | native | mlx | captions | whisper | parakeet | compare.
            auto = YouTube captions → mlx → native (**never** parakeet).
            native = Apple SFSpeechRecognizer (poor on long audio).
            mlx = local mlx_whisper (primary quality path).
            captions = yt-dlp auto-subs only (YouTube, fastest).
            parakeet = Handy ONNX Parakeet TDT (secondary explicit — verify vs mlx).
            compare = run mlx + parakeet side-by-side for verification.
        describe: Frame description provider ('none', 'claude', 'openai', 'grok', …).
        mode: full | frames_only | transcript_only.
        trash_source_video: After frames extracted, move downloaded.mp4 to Trash.
        agent_id: Optional agent scope.
        timeout_seconds: Override default timeout.
    """
    run_id = db._new_id()
    output_dir = FLIXZ_OUTPUT_DIR / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    mode = (mode or "full").lower().strip()
    if mode not in ("full", "frames_only", "transcript_only"):
        mode = "full"

    # Normalize transcript defaults per mode
    if mode == "transcript_only" and transcript in ("none", ""):
        transcript = "auto"
    if mode == "frames_only":
        transcript = "none"
        describe = "none"

    timeout = timeout_seconds or FLIXZ_DEFAULT_TIMEOUT
    config = {
        "max_frames": max_frames,
        "fps": fps,
        "scene_detect": scene_detect,
        "transcript": transcript,
        "describe": describe,
        "describe_model": describe_model,
        "mode": mode,
        "trash_source_video": trash_source_video,
    }

    db.create_flixz_run(
        run_id=run_id,
        agent_id=agent_id,
        video_path=video_path,
        config=config,
        output_dir=str(output_dir),
    )

    try:
        # ── 0. Resolve path (download URL if needed) ───────────
        # transcript_only + captions-only can skip full download for YouTube
        is_url = video_path.startswith(("http://", "https://"))
        is_youtube = is_url and any(
            d in video_path for d in ("youtube.com", "youtu.be", "yt.be")
        )
        want_captions_only = (
            mode == "transcript_only"
            and (transcript in ("captions", "auto") and is_youtube)
        )

        resolved_path = ""
        width = height = 0
        duration = 0.0
        resolution = "unknown"

        if want_captions_only and transcript == "captions":
            # Skip video download entirely
            resolved_path = ""
        else:
            resolved_path = await _resolve_video_path(
                video_path, output_dir,
                timeout_seconds=min(timeout, 600),
                agent_id=agent_id,
            )
            metadata = await _run_ffprobe(resolved_path)
            video_stream = None
            for s in metadata.get("streams", []):
                if s.get("codec_type") == "video":
                    video_stream = s
                    break
            width = video_stream.get("width", 0) if video_stream else 0
            height = video_stream.get("height", 0) if video_stream else 0
            resolution = f"{width}×{height}" if width and height else "unknown"
            duration_str = metadata.get("format", {}).get("duration", "0")
            duration = float(duration_str) if duration_str else 0

        # ── 1. Frames (unless transcript_only) ─────────────────
        frame_paths: list[str] = []
        frames_b64: list[str] = []
        if mode != "transcript_only":
            if not resolved_path:
                raise RuntimeError("Video path required for frame extraction")
            frame_paths = await _extract_frames_ffmpeg(
                resolved_path, output_dir,
                max_frames=max_frames, fps=fps,
                scene_detect=scene_detect, timeout_seconds=timeout,
            )
            for fp in frame_paths[:30]:
                with open(fp, "rb") as f:
                    frames_b64.append(base64.b64encode(f.read()).decode())

        # ── 2. Frame descriptions ──────────────────────────────
        frame_descriptions: list[dict] = []
        _VISION = {
            "claude", "openai", "openai-codex", "grok", "xai", "xai-auth",
        }
        if mode != "transcript_only" and frame_paths and describe != "none":
            provider = describe if describe in _VISION else "claude"
            if describe not in _VISION and describe != "none":
                logger.info("Frame description provider %r unknown — using claude", describe)
            frame_descriptions = await _describe_frames(
                frame_paths,
                provider=provider,
                max_frames=min(max_frames, 30),
                model=describe_model,
            )

        # ── 3. Transcription ───────────────────────────────────
        transcript_segments: list[dict] = []
        transcript_full = ""
        transcript_provider_used = "none"
        transcript_extras: dict = {}
        if transcript != "none":
            # For captions-only without download, resolved may be empty
            local_for_stt = resolved_path
            if not local_for_stt and transcript in ("auto", "captions") and is_youtube:
                # captions don't need local file
                local_for_stt = ""
            elif not local_for_stt:
                local_for_stt = await _resolve_video_path(
                    video_path, output_dir,
                    timeout_seconds=min(timeout, 600),
                    agent_id=agent_id,
                )
                if duration <= 0:
                    metadata = await _run_ffprobe(local_for_stt)
                    duration_str = metadata.get("format", {}).get("duration", "0")
                    duration = float(duration_str) if duration_str else 0

            transcript_segments, transcript_full, transcript_provider_used, transcript_extras = (
                await _resolve_transcript(
                    transcript,
                    video_path_or_url=video_path,
                    resolved_local=local_for_stt or resolved_path or "",
                    output_dir=output_dir,
                    timeout_seconds=timeout,
                )
            )
            # Persist SRT / full text for agent discuss
            if transcript_full:
                (output_dir / "transcript.txt").write_text(transcript_full, encoding="utf-8")

        # ── 4. Trash source MP4 after successful frame extract ──
        trashed_videos: list[str] = []
        if trash_source_video and mode != "transcript_only" and frame_paths:
            trashed_videos = trash_source_videos(output_dir)

        # ── 5. Persist results ─────────────────────────────────
        db.update_flixz_run(
            run_id,
            status="completed",
            frame_count=len(frame_paths),
            duration_seconds=duration,
            resolution=resolution,
            transcript_text=transcript_full or None,
            sink_results=json.dumps(frame_descriptions) if frame_descriptions else None,
        )

        # Write brief for later discuss
        run_row = db.get_flixz_run(run_id) or {}
        brief = build_flixz_brief(run_row)
        (output_dir / "flixz_brief.md").write_text(brief, encoding="utf-8")

        if agent_id:
            desc_count = len(frame_descriptions)
            seg_count = len(transcript_segments)
            memory = f"Flixz run {run_id[:8]}: mode={mode}, {len(frame_paths)} frames"
            if desc_count:
                memory += f", {desc_count} frame descriptions"
            if seg_count:
                memory += f", {seg_count} transcript segments via {transcript_provider_used}"
            db.append_agent_memory(agent_id, memory, fact_type="dynamic")
            db.record_activity(
                agent_id, "flixz_extraction_completed", None,
                {
                    "run_id": run_id,
                    "mode": mode,
                    "frames": len(frame_paths),
                    "descriptions": desc_count,
                    "transcript_segments": seg_count,
                    "transcript_provider": transcript_provider_used,
                },
            )

        logger.info(
            "Flixz run %s complete: mode=%s frames=%d duration=%.1fs %s "
            "descs=%d transcript=%s(%d segs) trashed_video=%s",
            run_id[:12], mode, len(frame_paths), duration, resolution,
            len(frame_descriptions), transcript_provider_used,
            len(transcript_segments), bool(trashed_videos),
        )

        return {
            "status": "completed",
            "run_id": run_id,
            "mode": mode,
            "video": {"durationSeconds": duration, "width": width, "height": height},
            "frame_count": len(frame_paths),
            "frames": frames_b64,
            "duration_seconds": duration,
            "resolution": resolution,
            "transcript": transcript_full,
            "transcript_segments": transcript_segments,
            "transcript_provider": transcript_provider_used,
            "transcript_compare": (transcript_extras or {}).get("compare"),
            "frame_descriptions": frame_descriptions,
            "output_dir": str(output_dir),
            "trashed_videos": trashed_videos,
            "brief_path": str(output_dir / "flixz_brief.md"),
        }

    except Exception as e:
        error = str(e)
        logger.exception(f"Flixz run {run_id} error")
        db.update_flixz_run(run_id, status="failed", error_message=error)
        return {"status": "failed", "error_message": error, "run_id": run_id}


async def delete_flixz_run_with_files(
    run_id: str,
    *,
    what: str = "all",
) -> dict:
    """Trash run artifacts and/or DB row.

    what: 'video' | 'frames' | 'all' (entire dir + DB) | 'db_only'
    """
    run = db.get_flixz_run(run_id)
    if not run:
        return {"status": "not_found"}

    out = Path(run["output_dir"]) if run.get("output_dir") else None
    result: dict = {"status": "ok", "run_id": run_id, "what": what, "trashed": []}

    if what == "video" and out:
        result["trashed"] = trash_source_videos(out)
    elif what == "frames" and out:
        n = trash_run_frames(out)
        result["trashed"] = [f"{n} frames"]
        result["frame_count_trashed"] = n
    elif what == "all":
        if out and out.exists():
            trash_run_all(out)
            result["trashed"] = [str(out)]
        db.delete_flixz_run(run_id)
        result["db_deleted"] = True
    elif what == "db_only":
        db.delete_flixz_run(run_id)
        result["db_deleted"] = True
    else:
        result["status"] = "error"
        result["error"] = f"Unknown what={what}"
    return result
