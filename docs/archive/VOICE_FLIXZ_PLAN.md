# Voice + Flixz Orchestration Plan

## Goal

Make voice and Flixz **first-class Slice of Pi features** — they go through
the orchestrator pipeline, persist results, and can be used both at the
system level and per-agent level.

---

## Current State (what you have)

```
┌─ Voice ───────────────────────────────┐
│  Browser mic → Web Speech API         │
│         ↓                             │
│  transcript text → /api/agents/{id}/chat (SSE)  │
│         ↓                             │
│  response text → SpeechSynthesis      │
│                                        │
│  ❌ No session history                 │
│  ❌ No agent memory/profile writes     │
│  ❌ No orchestrator awareness          │
│  ❌ WebSocket only relays JSON status  │
└────────────────────────────────────────┘

┌─ Flixz ───────────────────────────────┐
│  User types video path                │
│         ↓                             │
│  Sent as chat message to agent        │
│         ↓                             │
│  Agent runs flixz CLI in its session  │
│         ↓                             │
│  Results parsed in browser, not saved │
│                                        │
│  ❌ No dedicated backend               │
│  ❌ No result persistence              │
│  ❌ No system-level panel              │
│  ❌ Lost on page refresh               │
└────────────────────────────────────────┘
```

## Target State (what we're building)

```
┌─ Voice ──────────────────────────────────────────────────────────┐
│  Browser mic → Web Speech API → transcript text                  │
│         ↓                                                        │
│  POST /api/voice/process   (NEW — orchestrator endpoint)         │
│         ↓                                                        │
│  Orchestrator: intent parse → pick agent → run → collect result  │
│         ↓                                                        │
│  Writes to: session JSONL ✓, agent profile ✓, activity log ✓    │
│         ↓                                                        │
│  TTS response back to browser                                    │
└──────────────────────────────────────────────────────────────────┘

┌─ Flixz (System) ─────────────────────┬─ Flixz (Per-Agent) ──────┐
│                                       │                           │
│  Panel in Console/Settings            │  Tab in AgentDetail       │
│  (NEW component)                      │  (existing UI, rewired)   │
│         ↓                             │         ↓                 │
│  POST /api/flixz/extract              │  POST /api/agents/{id}    │
│  (NEW endpoint)                       │       /flixz/extract      │
│         ↓                             │  (NEW endpoint)           │
│  FlixzService runs extraction         │         ↓                 │
│  as subprocess                        │  Same service, scoped     │
│         ↓                             │  to agent workspace       │
│  Frames saved to ~/.pi/flixz/output/  │         ↓                 │
│  Results persisted to DB              │  Frames saved to agent    │
│  Activity logged                      │  workspace                │
│                                       │  Session recorded         │
└───────────────────────────────────────┴───────────────────────────┘
```

---

## Architecture

```
dashboard (Vue)
    │
    ├── POST /api/voice/process      → voice_router.py
    ├── POST /api/flixz/extract      → flixz_router.py
    ├── POST /api/agents/{id}/flixz/extract → flixz_router.py
    │
    ▼
FastAPI orchestrator
    │
    ├── services/flixz_service.py    (runs flixz CLI as subprocess)
    ├── services/voice_service.py    (intent routing + TTS config)
    │
    ├── database.py
    │   ├── flixz_runs table          (NEW)
    │   └── append_agent_memory()     (exists — just needs calling)
    │
    └── services/agent_profile_service.py
        └── append_agent_memory()     (exists — voice will call it)
```

---

## Phase 1 — Flixz Backend (the execution engine)

**Time**: ~1 focused session  
**Files**: 2 new, 2 modified

### 1.1 Flixz Service (`pi_orchestrator/services/flixz_service.py`)

A new service that runs frame extraction as an async subprocess.
Does NOT go through the agent chat API. The orchestrator runs it directly.

```python
# What it does:
extract_video(video_path, config) → runs flixz CLI with args
  - Accepts: path/URL, fps, max_frames, scene_detect, transcript, describe
  - Returns: frames list, transcript text, video metadata, sink results
  - Saves output to ~/.pi/flixz/output/{run_id}/
  - Times out after configurable duration
  - Records result in flixz_runs DB table
```

### 1.2 Flixz Router (`pi_orchestrator/routers/flixz.py`)

```python
# System-level
POST   /api/flixz/extract           — run extraction (system scope)
GET    /api/flixz/runs               — list past extractions
GET    /api/flixz/runs/{id}          — get single run details + frames
DELETE /api/flixz/runs/{id}          — delete a run and its files

# Per-agent
POST   /api/agents/{id}/flixz/extract — run extraction (agent scope)
GET    /api/agents/{id}/flixz/runs    — list agent's extractions
```

### 1.3 Database (`pi_orchestrator/database.py`)

New table:

```sql
CREATE TABLE IF NOT EXISTS flixz_runs (
    id TEXT PRIMARY KEY,
    agent_id TEXT,              -- NULL = system-level run
    video_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',  -- running|completed|failed
    config TEXT NOT NULL,       -- JSON: fps, maxFrames, transcript, describe
    output_dir TEXT,            -- path to extracted frames
    frame_count INTEGER DEFAULT 0,
    duration_seconds REAL,
    resolution TEXT,            -- "1920×1080"
    transcript_text TEXT,
    sink_results TEXT,          -- JSON array of sink outputs
    error_message TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT
);
```

New DB functions: `create_flixz_run`, `get_flixz_run`, `list_flixz_runs`, `update_flixz_run`, `delete_flixz_run`

### 1.4 Registration in main.py

```python
from .routers.flixz import router as flixz_router
app.include_router(flixz_router)
```

### 1.5 install.sh / slices — check for flixz CLI

Add a check: warn if `flixz` binary not found in PATH (non-fatal — just a warning).

---

## Phase 2 — Flixz System Panel (orchestrator-level UI)

**Time**: ~1 focused session  
**Files**: 1 new component, 2 modified

### 2.1 System Flixz Panel (`dashboard/src/components/SystemFlixzPanel.vue`)

A standalone panel for orchestrator-level video processing.
Lives in the Console view or as its own section.

```
┌──────────────────────────────────────┐
│  🎞 Frame Extraction                  │
│                                       │
│  Video Path: [____________________]   │
│                                       │
│  Max Frames: [60]    FPS: [0=auto]   │
│  ☑ Scene Detect    Transcription: [↓]│
│  Frame Desc: [↓]                      │
│                                       │
│  [ Extract Frames ]                   │
│                                       │
│  ── Recent Runs ──────────────────   │
│  video1.mp4  · 45 frames · 2m ago    │
│  video2.mp4  · 30 frames · 1h ago    │
└──────────────────────────────────────┘
```

This is essentially the same UI as the per-agent FlixzPanel but:
- No agent dependency — standalone orchestrator feature
- Results go to system-level storage
- Shows ALL runs across all agents
- Placed in the Console view (new tab or section)

### 2.2 Place it

Add a "Flixz" tab to `Console.vue` (the System Console view).
This is the natural home since Console is already the orchestrator overview.

### 2.3 Re-wire per-agent FlixzPanel

The existing `FlixzPanel.vue` already has a full UI with config, results display,
etc. Just change its `processVideo()` function to call:

```
POST /api/agents/{id}/flixz/extract
```

Instead of:

```
POST /api/agents/{id}/chat  (with "Run flixz..." message)
```

The backend endpoint returns JSON directly (no SSE streaming needed for
video extraction). This means the parsing logic in FlixzPanel simplifies —
no more reading SSE chunks, just `await res.json()`.

**Line changes**: ~5 lines in `FlixzPanel.vue`

---

## Phase 3 — Voice Orchestration + Persistence

**Time**: ~1 focused session  
**Files**: 1 new service, 1 modified router, 2 modified components

### 3.1 Voice Service (`pi_orchestrator/services/voice_service.py`)

```python
# What it does:
process_voice_transcript(agent_id, text) → dict
  1. Creates a session entry (so voice turns appear in history)
  2. Routes to agent chat API
  3. Collects response
  4. Appends to agent profile memory via append_agent_memory()
  5. Records activity event
  6. Returns full response

# Configurable:
- TTS provider (default: browser SpeechSynthesis, future: ElevenLabs)
- Whether to auto-continue listening after response
- Max turns per voice session
```

### 3.2 Voice Router updates (`pi_orchestrator/routers/voice.py`)

Add a new REST endpoint (the WebSocket already exists):

```python
POST /api/voice/process
  Body: {"agent_id": "...", "transcript": "...", "session_id": "..."}
  Returns: {"response": "...", "session_id": "...", "tool_calls": [...]}
```

The existing WebSocket `/ws/voice/{agent_id}` stays as-is for state sync.
The new REST endpoint is where the actual orchestration happens.

### 3.3 VoiceWorkspace.vue — hook into persistence

`VoiceWorkspace.vue` already sends transcripts to the chat API.
Change `sendToPi()` to call the new orchestrator endpoint instead:

```
POST /api/voice/process  (instead of POST /api/agents/{id}/chat)
```

The response now includes `session_id` which gets tracked in the UI.

**Line changes**: ~10 lines in `VoiceWorkspace.vue`

### 3.4 Memory integration

The voice service calls `db.append_agent_memory()` after each turn:

```
After agent responds:
  → db.append_agent_memory(agent_id, "Voice session: user asked about X")
  → Shows up in InfoPanel's "Agent Memory" section
  → Inject into system prompt on next session for context
```

This already works end-to-end — the `append_agent_memory` function exists in
`database.py`, and the `InfoPanel.vue` now reads profile data reactively.
We just need to call it from the voice flow.

---

## Phase 4 — Polish + Test

**Time**: ~30 min  
**Files**: 0 new, verification only

### 4.1 Verify full flows

| Flow | What to check |
|------|---------------|
| System Flixz | Open Console → Flixz tab → paste video → extract → see frames → run persists across refresh |
| Per-agent Flixz | Open agent → Flixz tab → extract → results in agent workspace → session recorded |
| Voice + memory | Open agent → voice mode → speak → agent responds → check Sessions: voice turn appears → check Info: memory updated |
| Voice + session history | Voice session appears in Sessions view and Replay timeline |

### 4.2 Build check

```bash
cd dashboard && npx vite build
cd .. && PI_NO_AUTH=1 python3 -c "from pi_orchestrator.main import app; print('OK')"
```

---

## File Change Summary

| Phase | File | Action |
|-------|------|--------|
| 1 | `pi_orchestrator/services/flixz_service.py` | **CREATE** — flixz CLI runner |
| 1 | `pi_orchestrator/routers/flixz.py` | **CREATE** — system + per-agent endpoints |
| 1 | `pi_orchestrator/database.py` | **MODIFY** — flixz_runs table + CRUD functions |
| 1 | `pi_orchestrator/main.py` | **MODIFY** — register flixz_router |
| 2 | `dashboard/src/components/SystemFlixzPanel.vue` | **CREATE** — orchestrator-level UI |
| 2 | `dashboard/src/views/Console.vue` | **MODIFY** — add Flixz tab |
| 2 | `dashboard/src/components/FlixzPanel.vue` | **MODIFY** — point to real backend (~5 lines) |
| 3 | `pi_orchestrator/services/voice_service.py` | **CREATE** — voice orchestration |
| 3 | `pi_orchestrator/routers/voice.py` | **MODIFY** — add POST /api/voice/process |
| 3 | `dashboard/src/components/VoiceWorkspace.vue` | **MODIFY** — call orchestrator endpoint (~10 lines) |
| 4 | `install.sh` + `slices` | **MODIFY** — warn if flixz CLI missing |

**Total**: 3 new files, 8 modified files. No breaking changes.

---

## What does NOT change

- Browser Web Speech API stays for STT/TTS (works today, good enough)
- Existing chat flow stays completely untouched
- AgentDetail.vue tabs stay the same
- WebSocket voice relay stays as-is
- All existing features continue working

---

## Execution order

```
Phase 1 (Flixz backend)
    ↓
Phase 2 (Flixz UI — both panels)
    ↓
Phase 3 (Voice orchestration + persistence)
    ↓
Phase 4 (Verify + build)
```

Phases are sequential because Phase 2 needs Phase 1's endpoints to exist,
and Phase 3 is independent but we do Flixz first since it's the bigger
gap (no backend at all vs voice which has partial backend).
