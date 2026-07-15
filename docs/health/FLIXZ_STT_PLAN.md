# Flixz STT / Parakeet plan

**Date:** 2026-07-15  
**Context:** Operator ran YouTube through Flixz with `transcript=native` (VoiceKit / Apple SFSpeechRecognizer). Result: **4 segments, 117 chars** on a **~624s** video — not usable.

## Why VoiceKit failed quality bar

- Flixz uses `~/prismakit` → `voicekit-transcribe` → Apple **SFSpeechRecognizer** on-device.
- That path is fine for short clips / dictation; it is **not** reliable for long video audio (10+ minutes). Sparse output is expected without chunking.
- **Not a download bug** — frames (60) and descriptions (30) completed; STT layer is the weak link.

## What you already have on this Mac

| Asset | Path | Role |
|-------|------|------|
| **Handy.app** | `/Applications/Handy.app` (com.pais.handy 0.8.3) | Dictation app using Parakeet |
| **Parakeet ONNX** | `~/Library/Application Support/com.pais.handy/models/parakeet-tdt-0.6b-v3-int8/` | encoder + decoder_joint + nemo128 + vocab |
| **mlx_whisper** | `/opt/homebrew/bin/mlx_whisper` | Local Whisper (recommended now) |
| **Cached Whisper** | `~/.cache/huggingface/hub/models--mlx-community--whisper-large-v3-turbo-asr-fp16` | Model weights |
| **VoiceKit** | `~/prismakit/.build/release/voicekit-transcribe` | Apple STT CLI (legacy option) |

Handy is a closed GUI app (hotkey dictation). There is **no public CLI** to shell out to Handy’s Parakeet runtime. The ONNX files are reusable if we wire our own runner.

## Shipped in Slice of Pi

| Provider | ID | When to use |
|----------|-----|-------------|
| **Auto** | `auto` | YouTube → captions first; else mlx; else native — **never Parakeet** |
| **MLX Whisper** | `mlx` / `whisper` | Primary local STT for long video |
| **Parakeet ONNX** | `parakeet` | **Secondary explicit** — Handy model dir; verify vs MLX |
| **Compare** | `compare` | Runs **mlx + parakeet** side-by-side (not a fallback chain) |
| **YouTube captions** | `captions` | Fastest transcript-only for YouTube (yt-dlp auto-subs) |
| **Native VoiceKit** | `native` | Short clips only; kept for offline/no-mlx |

### Parakeet implementation (done)

- Module: `pi_orchestrator/services/parakeet_asr.py`
- Weights: Handy dir `…/com.pais.handy/models/parakeet-tdt-0.6b-v3-int8/` (same layout as `istupakov/parakeet-tdt-0.6b-v3-onnx`)
- Engine: [`onnx-asr`](https://github.com/istupakov/onnx-asr) `nemo-parakeet-tdt-0.6b-v3` + `quantization=int8`
- Runtime: in-process if `onnx_asr` importable; else subprocess via `PI_PARAKEET_PYTHON` (e.g. `/opt/homebrew/bin/python3.11`)
- Long audio: ~25s chunks with overlap (override `PI_PARAKEET_CHUNK_SECONDS`)
- **Not** in `auto` chain — only when operator chooses `parakeet` or `compare`
- Status: `GET /api/flixz/stt-status`
- Optional dep: `pip install 'pi-orchestrator[parakeet]'` or `python3.11 -m pip install 'onnx-asr[cpu]'`

Env:

```bash
export PI_PARAKEET_MODEL_DIR="~/Library/Application Support/com.pais.handy/models/parakeet-tdt-0.6b-v3-int8"
export PI_PARAKEET_PYTHON=/opt/homebrew/bin/python3.11
export PI_PARAKEET_CHUNK_SECONDS=25
```

Also:

- **Mode `transcript_only`** — no frames, just transcript  
- **Trash source MP4** after frames extract (default on)  
- **Trash frames / whole run** API  
- **Discuss with agent** — brief + SSE chat into a local pi agent  

Env override for Whisper model:

```bash
export PI_FLIXZ_WHISPER_MODEL=mlx-community/whisper-large-v3-turbo
```

## Operator recommendations (today)

1. **YouTube + need words fast:** mode = **Transcript only**, transcript = **YouTube captions**.  
2. **Primary quality STT:** transcript = **MLX Whisper**.  
3. **Secondary verify:** transcript = **Parakeet** (Handy ONNX) or **Compare** (both).  
4. **Full analysis:** mode = **Full**, transcript = **auto** or **compare**, describe = vision OAuth.  
5. **Then:** **Discuss with agent** on the run.  
6. **Disk:** source MP4 → Trash after frames; **Trash frames** when done.

## Acceptance (Parakeet secondary)

- [x] `transcript=parakeet` uses Handy model dir (no re-download if Handy already has it)  
- [x] **Not** in auto fallback chain  
- [x] `transcript=compare` runs mlx + parakeet and stores both for verification  
- [x] `GET /api/flixz/stt-status` reports readiness  
- [x] Chunked long audio; works offline once onnx-asr is installed on a ≥3.10 Python
