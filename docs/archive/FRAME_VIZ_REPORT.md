# Frame Visualization — Claude Vision Integration

## What was built

Three files changed:

| File | Action | Description |
|------|--------|-------------|
| `pi_orchestrator/services/flixz_service.py` | **Rewritten** | Replaced nonexistent `flixz` CLI with ffmpeg subprocess. Added Claude Vision frame description pipeline. |
| `pi_orchestrator/services/frame_description_service.py` | **Created** | Sends frame images to Claude Vision API with OAuth support. |
| `dashboard/src/components/FlixzPanel.vue` | **Updated** | Added "Claude Vision" option to describe dropdown |
| `dashboard/src/components/SystemFlixzPanel.vue` | **Updated** | Added "Claude Vision" option to describe dropdown |
| `pi_orchestrator/routers/flixz.py` | **Updated** | Accepts `describe: "claude"` in validation |
| `install.sh` + `slices` | **Updated** | Added `aiohttp` dependency |

## Architecture

```
User selects "Claude Vision" in FlixzPanel
          ↓
POST /api/flixz/extract  { describe: "claude" }
          ↓
flixz_service.extract_video()
    ├── ffprobe → video metadata (duration, resolution)
    ├── ffmpeg → frame extraction (PNG files in output dir)
    ├── frame_description_service.describe_frame_batch()
    │       ├── Reads ~/.pi/agent/auth.json for Claude OAuth token
    │       ├── Sends each frame as base64 to Claude Vision API
    │       └── Returns descriptions per frame
    └── DB: flixz_runs updated with frame_count + descriptions
```

## How Claude auth works

Same as gotpapi/launch.ts:
1. Reads `~/.pi/agent/auth.json` 
2. Looks for `auth.anthropic.access` (OAuth token from Chrome extension)
3. Checks `sk-ant-oat` prefix to determine OAuth vs API key
4. OAuth: `Authorization: Bearer <token>` header
5. API key: `x-api-key: <token>` header

## Frame extraction via ffmpeg

Replaced the nonexistent `flixz` CLI:
- **Scene detection**: `ffmpeg -vf "select='gt(scene,0.3)'"` 
- **FPS mode**: `ffmpeg -vf fps=N`
- **Default**: `ffmpeg -vf fps=1`
- **Metadata**: `ffprobe -print_format json` for duration/resolution

## Tests

30/30 pass (19 flixz + 11 voice). Full suite: 309 passed.

## What's needed to use it

1. **Restart orchestrator** (`./slices`) to pick up new code
2. **Have ~/.pi/agent/auth.json** populated with Claude OAuth token (from Chrome extension)
3. **ffmpeg** is already installed at `/opt/homebrew/bin/ffmpeg`
4. Select a video, pick "Claude Vision" in the describe dropdown, hit Extract

## What Claude sees

Each frame is sent as:
```json
{
  "model": "claude-sonnet-4-20250514",
  "messages": [{
    "role": "user",
    "content": [
      { "type": "image", "source": { "type": "base64", "media_type": "image/png", "data": "..." } },
      { "type": "text", "text": "Describe this video frame in detail. What do you see?" }
    ]
  }]
}
```

Max 30 frames per run, 3 concurrent API calls (to avoid rate limits).
