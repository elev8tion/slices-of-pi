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
_PRISMAKIT_ROOT = Path(os.getenv("PRISMAKIT_ROOT", str(Path.home() / "prismakit")))
VOICEKIT_CLI = str(_PRISMAKIT_ROOT / ".build" / "release" / "voicekit-transcribe")


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


async def _transcribe_audio_native(
    audio_path: str,
    language: str = "en-US",
    timeout_seconds: int = 300,
) -> list[dict]:
    """Transcribe an audio file using Apple's on-device SFSpeechRecognizer via VoiceKit CLI.

    Requires the voicekit-transcribe binary from prismakit (already built).
    No API keys, no network — runs entirely on-device.

    Args:
        audio_path: Path to audio file (.m4a, .mp3, .wav, .caf, .aiff).
        language: BCP-47 language tag (default: en-US).
        timeout_seconds: Max wait for transcription.

    Returns:
        List of dicts with 'index', 'start', 'end', 'text' (SRT segments).
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
        # Check for common error: no speech detected
        if "No speech detected" in stderr_text:
            logger.info(f"No speech detected in {audio_path}")
            return []
        raise RuntimeError(f"VoiceKit transcription failed (code {proc.returncode}): {stderr_text}")

    srt_text = stdout.decode("utf-8", errors="replace")
    return _parse_srt(srt_text)


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
    transcript: str = "none",
    describe: str = "none",
    describe_model: Optional[str] = None,
    agent_id: Optional[str] = None,
    timeout_seconds: Optional[int] = None,
) -> dict:
    """Run frame extraction on a video file using ffmpeg.

    Args:
        video_path: Local path or URL (YouTube, direct video link). 
            URLs are auto-downloaded via yt-dlp before processing.
        max_frames: Maximum frames to extract.
        fps: Frames per second (0 = auto/scene detect).
        scene_detect: Use scene-change detection.
        transcript: Transcription provider ('none', 'native'). 'native' uses Apple on-device SFSpeechRecognizer via VoiceKit CLI.
        describe: Frame description provider ('none', 'gemini', 'claude').
        agent_id: Optional agent scope.
        timeout_seconds: Override default timeout.

    Returns:
        dict with status, frame_count, duration_seconds, resolution, frames (as base64),
        transcript, frame_descriptions, output_dir, error_message.
    """
    run_id = db._new_id()
    output_dir = FLIXZ_OUTPUT_DIR / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    timeout = timeout_seconds or FLIXZ_DEFAULT_TIMEOUT
    config = {
        "max_frames": max_frames,
        "fps": fps,
        "scene_detect": scene_detect,
        "transcript": transcript,
        "describe": describe,
        "describe_model": describe_model,
    }

    run = db.create_flixz_run(
        run_id=run_id,
        agent_id=agent_id,
        video_path=video_path,
        config=config,
        output_dir=str(output_dir),
    )

    try:
        # ── 0. Resolve path (download URL if needed; local path allowlist) ──
        resolved_path = await _resolve_video_path(
            video_path, output_dir,
            timeout_seconds=min(timeout, 600),
            agent_id=agent_id,
        )

        # ── 1. Get video metadata ──────────────────────────────
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

        # ── 2. Extract frames via ffmpeg ───────────────────────
        frame_paths = await _extract_frames_ffmpeg(
            resolved_path, output_dir,
            max_frames=max_frames, fps=fps,
            scene_detect=scene_detect, timeout_seconds=timeout,
        )

        # Convert frames to base64 for API response
        frames_b64: list[str] = []
        for fp in frame_paths[:30]:  # Max 30 in response
            with open(fp, "rb") as f:
                frames_b64.append(base64.b64encode(f.read()).decode())

        # ── 3. Frame descriptions (Gemini or Claude Vision) ────
        frame_descriptions: list[dict] = []
        _VISION = {
            "gemini", "claude", "openai", "openai-codex", "grok", "xai", "xai-auth",
        }
        if describe in _VISION:
            frame_descriptions = await _describe_frames(
                frame_paths,
                provider=describe,
                max_frames=min(max_frames, 30),
                model=describe_model,
            )
        elif describe != "none":
            logger.info(f"Frame description provider '{describe}' — using gemini as default")
            frame_descriptions = await _describe_frames(
                frame_paths,
                provider="gemini",
                max_frames=min(max_frames, 30),
                model=describe_model,
            )

        # ── 4. Audio transcription (Apple SFSpeechRecognizer) ──
        transcript_segments: list[dict] = []
        transcript_full = ""
        if transcript == "native":
            try:
                audio_ext = "m4a"  # SFSpeechRecognizer handles m4a well
                audio_out = str(output_dir / "audio.m4a")
                await _extract_audio_ffmpeg(
                    resolved_path, audio_out, format=audio_ext,
                    timeout_seconds=min(timeout, 300),
                )
                transcript_segments = await _transcribe_audio_native(
                    audio_out, language="en-US",
                    timeout_seconds=min(timeout, 300),
                )
                if transcript_segments:
                    transcript_full = " ".join(s.get("text", "") for s in transcript_segments)
                logger.info(
                    f"Transcription complete: {len(transcript_segments)} segments, "
                    f"{len(transcript_full)} chars"
                )
            except Exception as e:
                logger.warning(f"Transcription failed (non-fatal): {e}")
                transcript_segments = []
                transcript_full = ""

        # ── 5. Persist results ─────────────────────────────────
        transcript_json = json.dumps(transcript_segments) if transcript_segments else None

        db.update_flixz_run(
            run_id,
            status="completed",
            frame_count=len(frame_paths),
            duration_seconds=duration,
            resolution=resolution,
            transcript_text=transcript_full or None,
            sink_results=json.dumps(frame_descriptions) if frame_descriptions else None,
        )

        if agent_id:
            desc_count = len(frame_descriptions)
            seg_count = len(transcript_segments)
            memory = f"Flixz run {run_id[:8]}: extracted {len(frame_paths)} frames"
            if desc_count:
                memory += f", {desc_count} described by Gemini"
            if seg_count:
                memory += f", {seg_count} transcript segments (native)"
            db.append_agent_memory(agent_id, memory, fact_type="dynamic")
            db.record_activity(
                agent_id, "flixz_extraction_completed", None,
                {
                    "run_id": run_id,
                    "frames": len(frame_paths),
                    "descriptions": desc_count,
                    "transcript_segments": seg_count,
                },
            )

        logger.info(
            f"Flixz run {run_id[:12]} complete: {len(frame_paths)} frames, "
            f"{duration:.1f}s, {resolution}, {len(frame_descriptions)} descriptions, "
            f"{len(transcript_segments)} transcript segments"
        )

        return {
            "status": "completed",
            "run_id": run_id,
            "video": {"durationSeconds": duration, "width": width, "height": height},
            "frame_count": len(frame_paths),
            "frames": frames_b64,
            "duration_seconds": duration,
            "resolution": resolution,
            "transcript": transcript_full,
            "transcript_segments": transcript_segments,
            "frame_descriptions": frame_descriptions,
            "output_dir": str(output_dir),
        }

    except Exception as e:
        error = str(e)
        logger.exception(f"Flixz run {run_id} error")
        db.update_flixz_run(run_id, status="failed", error_message=error)
        return {"status": "failed", "error_message": error, "run_id": run_id}
