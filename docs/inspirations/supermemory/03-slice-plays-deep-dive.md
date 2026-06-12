# Slice Plays — Deep Dive: Current State → Supermemory-Inspired Future

## Current State

SlicePlaysPanel.vue is a **skill launcher** — nothing more:

1. `GET /api/skills` reads `~/.pi/agent/skills/*/SKILL.md` frontmatter
2. Renders a searchable card grid with name, description, trigger
3. "Run" button sends `/<skill-name>` as a chat message to the agent

**Key code points:**

| File | What it does |
|------|-------------|
| `dashboard/src/components/SlicePlaysPanel.vue` | The entire UI — card grid, search, "Run" button → sends `/trigger` as chat message |
| `pi_orchestrator/routers/skills.py` | `GET /api/skills` — parses SKILL.md frontmatter, returns name + description + location |
| `pi_orchestrator/services/pi_session_service.py` | `stream_chat()` — the actual execution path. A "Run" button sends a prompt, this streams JSONL back |

**Limitations:**

- ❌ No input parameters — every play is a blind `/trigger` text
- ❌ No output capture — the streaming response is displayed but never structured
- ❌ No chaining — each play is a one-shot, no way to pipe outputs into inputs
- ❌ No state — the agent has no accumulated memory across plays
- ❌ No schema — SKILL.md frontmatter only has `name` and `description`, nothing typed

## Supermemory-Inspired Future

### Gap 1: SKILL.md Needs Input/Output Schemas

Supermemory's MCP tools declare **typed input schemas** using Zod. Slice Plays need the same.

**What to change in `pi_orchestrator/routers/skills.py`:**

The frontmatter parser currently extracts only `name` and `description`. Extend it to also parse `inputs`, `outputs`, and `side_effects`:

```yaml
# In SKILL.md
name: audio-chop
description: Split audio into equal-length clips
inputs:
  file:
    type: string
    required: true
    description: "Path to audio file"
  clip_length:
    type: number
    default: 30
    description: "Length of each clip in seconds"
outputs:
  clips:
    type: array[string]
    description: "Paths to generated clip files"
```

**Code targets:**

- `pi_orchestrator/routers/skills.py` — `_parse_frontmatter()` function needs richer YAML parsing (use `yaml.safe_load` instead of regex)
- `models.py` — Add `SkillSchema` Pydantic model with optional `inputs`, `outputs`, `side_effects` fields
- `dashboard/src/components/SlicePlaysPanel.vue` — When a card is clicked, show a parameter form instead of immediately sending `/trigger`

### Gap 2: Slice Play Execution Should Capture Outputs

Currently `stream_chat()` returns text that's displayed but not saved as structured data. We need a **Slay Play Session** — like Supermemory's `containerTag` for scoping memory.

**What to add:**

```python
# New concept: SlicePlaySession — accumulates across chained plays
# Storage: ~/.pi/agent/slice-plays/{session_id}.jsonl

{
  "session_id": "sps_abc123",
  "plays": [
    {
      "skill": "audio-chop",
      "inputs": {"file": "song.mp3", "clip_length": 30},
      "outputs": {"clips": ["/tmp/clip1.mp3", "/tmp/clip2.mp3"]},
      "tokens_used": 1500,
      "agent_id": "agent_42"
    }
  ],
  "shared_context": {
    "agent_memories": ["User prefers 30-second clips", "Keep original format"]
  }
}
```

**Code targets:**

- `database.py` — Add `slice_play_sessions` table (or use generic `sessions` with a `type` discriminator)
- `pi_orchestrator/routers/` — Add new `slice_plays.py` router with `POST /api/slice-plays/execute` and `GET /api/slice-plays/{id}`
- `pi_session_service.py` — After `stream_chat()` completes, parse the output for structured results

### Gap 3: Chaining Plays (Pipeline Mode)

Supermemory's `recall` tool returns profile + search results that get fed into the next AI call. Same pattern for Slice Plays: **output of one play becomes context for the next**.

**What to add:**

```python
# In a new slice_plays router:
async def execute_pipeline(agent_id: str, steps: list[dict]):
    """
    steps = [
      {"skill": "audio-chop", "inputs": {"file": "song.mp3"}},
      {"skill": "transcribe", "inputs": {"file": "{steps[0].outputs.clips[0]}"}},
    ]
    """
    shared_context = {"agent_memories": []}
    for i, step in enumerate(steps):
        # Resolve template variables from previous outputs
        resolved = resolve_templates(step["inputs"], shared_context)
        
        # Execute the play
        result = await execute_play(agent_id, step["skill"], resolved)
        
        # Store outputs for subsequent steps
        shared_context[f"steps[{i}].outputs"] = result["outputs"]
        
        # Agent memories accumulate across the pipeline
        shared_context["agent_memories"].extend(result.get("memories", []))
    
    return shared_context
```

**Code targets:**

- New file: `pi_orchestrator/services/slice_play_service.py` — pipeline executor
- `dashboard/src/components/SlicePlaysPanel.vue` — Add "Add Step" button to build multi-play sequences

### Gap 4: Agent Memory Across Plays

Like Supermemory's static/dynamic profile — Slice Plays should remember what they learned.

**What to add to `pi_session_service.py`:**

```python
# Before spawning pi subprocess:
if agent_has_profile(agent_id):
    profile = load_agent_profile(agent_id)
    memory_context = format_profile_as_prompt(profile)
    if system_prompt:
        system_prompt += "\n\n" + memory_context
    else:
        system_prompt = memory_context
```

**Code targets:**

- `pi_orchestrator/services/pi_session_service.py` — `stream_chat()` function, just before the `cmd` building section (~line 100)
- New file: `pi_orchestrator/services/agent_profile_service.py` — read/write profile JSON

## Implementation Order (Cheapest First)

| Order | Change | Effort | Files |
|-------|--------|--------|-------|
| 1 | **Profile JSON** — add `profile_json` column to agents, inject at session start | ~1 hour | `database.py`, `models.py`, `pi_session_service.py` |
| 2 | **SKILL.md schemas** — parse inputs/outputs from frontmatter | ~2 hours | `skills.py`, `models.py` |
| 3 | **Parameter form UI** — show inputs as form fields in SlicePlaysPanel | ~2 hours | `SlicePlaysPanel.vue` |
| 4 | **Slice Play sessions** — capture outputs in structured JSONL | ~3 hours | New `slice_plays.py` router, `slice_play_service.py` |
| 5 | **Pipeline chaining** — chain multiple plays | ~4 hours | `slice_play_service.py`, `SlicePlaysPanel.vue` |
