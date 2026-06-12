# Implementation Roadmap — From Inspiration to Code

> Concrete, ordered steps. Each step is self-contained and independently useful.
> Estimated total: ~3-4 focused coding sessions.

---

## Session 1: Agent Profiles (~2 hours)

This is the highest-ROI change. It makes every agent session smarter trivially.

### Step 1.1 — Add `profile_json` to the agents table

**File:** `pi_orchestrator/database.py`

```sql
ALTER TABLE agents ADD COLUMN profile_json TEXT DEFAULT '{"static": {}, "dynamic": []}';
```

Also add CRUD helpers:
- `get_agent_profile(agent_id) → dict`
- `update_agent_profile(agent_id, profile) → None`
- `append_agent_memory(agent_id, fact, type="dynamic") → None`

### Step 1.2 — Create the profile service

**New file:** `pi_orchestrator/services/agent_profile_service.py`

```python
def format_profile_as_prompt(profile: dict) -> str:
    """Convert a profile dict into markdown for system prompt injection.
    Same pattern as supermemory's convertProfileToMarkdown()."""
    parts = []
    if profile.get("static"):
        parts.append("## Agent Profile")
        for k, v in profile["static"].items():
            parts.append(f"- {k}: {v}")
    if profile.get("dynamic"):
        parts.append("\n## Recent Context")
        for fact in profile["dynamic"][-5:]:  # last 5
            parts.append(f"- {fact}")
    return "\n".join(parts) if parts else ""
```

### Step 1.3 — Inject at session start

**File:** `pi_orchestrator/services/pi_session_service.py`

In `stream_chat()`, right after `session = db.create_session(...)` and before building the cmd:

```python
# Load agent profile and inject into system prompt
profile = db.get_agent_profile(agent_id)
if profile and (profile.get("static") or profile.get("dynamic")):
    profile_prompt = format_profile_as_prompt(profile)
    system_prompt = f"{system_prompt}\n\n{profile_prompt}" if system_prompt else profile_prompt
```

**Done.** From this point on, every agent session starts with context from all previous sessions.

### Step 1.4 — Append to profile after session

**File:** `pi_orchestrator/services/pi_session_service.py`

After `stream_chat()` completes (before the `finally` block), summarize what happened and append:

```python
# Extract key facts from the session and store them
# For now, just store: "Session: worked on [summary of task]"
# This is where supermemory's profile pattern pays off
session_summary = f"Session #{session_num}: {prompt[:100]}..."
append_agent_memory(agent_id, session_summary, type="dynamic")
```

---

## Session 2: Shared Knowledge Pool (~3 hours)

This enables agent-to-agent context sharing without direct messaging.

### Step 2.1 — Create the shared memory service

**New file:** `pi_orchestrator/services/shared_memory_service.py`

Implement three functions:

1. `write_fact(agent_id, tag, fact, fact_type)` — append to `~/.pi/agent/shared-memory/{tag}/knowledge.jsonl`
2. `deduplicate_memories(static, dynamic, search)` — exact copy of supermemory's `deduplicateMemories()` from `00-shared/src/utils.ts` (priority: static > dynamic > search)
3. `read_context(tags, max_age_hours)` — read all facts for the agent's tags, deduplicate, return as markdown

### Step 2.2 — Inject shared context into sessions

**File:** `pi_orchestrator/services/pi_session_service.py`

Add alongside Step 1.3:

```python
# Load shared context from the knowledge pool
agent_tags = json.loads(agent.get("tags", "[]")) if agent.get("tags") else []
if agent_tags:
    shared_context = read_context(agent_tags)
    if shared_context:
        system_prompt = f"{system_prompt}\n\n{shared_context}" if system_prompt else shared_context
```

### Step 2.3 — Expose shared context in the coms API

**File:** `pi_orchestrator/routers/coms.py`

Extend the peer response to include:
```python
{
    "name": "agent-foo",
    "project": "default",
    ...
    "recent_facts": [
        "Mapped users table schema",
        "Found null pointer in auth service",
    ],
    "fact_count": 14,
    "last_active_fact": "2026-06-12T..."
}
```

---

## Session 3: Rich Slice Plays (~3 hours)

This turns Slice Plays from blind `/trigger` buttons into parameterized, chainable steps.

### Step 3.1 — Richer SKILL.md parsing

**File:** `pi_orchestrator/routers/skills.py`

Replace the regex frontmatter parser with proper `yaml.safe_load`:

```python
import yaml

def _parse_frontmatter(path: Path) -> dict | None:
    try:
        text = path.read_text()
        match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
        if not match:
            return None
        return yaml.safe_load(match.group(1))
    except Exception:
        return None
```

Now frontmatter like this parses correctly:
```yaml
inputs:
  file:
    type: string
    required: true
outputs:
  clips:
    type: array[string]
```

### Step 3.2 — Add SkillSchema to models

**File:** `pi_orchestrator/models.py`

```python
class SkillParameter(BaseModel):
    type: str = "string"
    required: bool = False
    default: Any = None
    description: str = ""

class SkillSchema(BaseModel):
    name: str
    description: str = ""
    location: str = ""
    inputs: dict[str, SkillParameter] = {}
    outputs: dict[str, SkillParameter] = {}
    triggers: list[str] = []
```

### Step 3.3 — Update the skills API response

**File:** `pi_orchestrator/routers/skills.py`

The `_discover_skills()` function should return the full schema including inputs/outputs.

### Step 3.4 — Parameter form UI

**File:** `dashboard/src/components/SlicePlaysPanel.vue`

When a user clicks a skill card that has `inputs`, show a mini-form instead of immediately sending `/trigger`. Each input field renders as the appropriate HTML input based on `type`.

**Types to support initially:** `string`, `number`, `boolean`, `file` (file picker), `array[string]`.

### Step 3.5 — Capture slice play outputs

**New file:** `pi_orchestrator/services/slice_play_service.py`

After a slice play finishes, parse the streaming output for structured results and store them in a slice play session JSONL file:

```python
{
    "skill": "audio-chop",
    "inputs": {"file": "song.mp3", "clip_length": 30},
    "outputs": {"clips": ["/tmp/clip1.mp3", ...]},
    "tokens_used": 1500,
    "duration_ms": 4200
}
```

---

## Session 4: Pipeline Builder & Coms Deepening (~3 hours)

### Step 4.1 — Pipeline builder UI

**File:** `dashboard/src/components/SlicePlaysPanel.vue`

Add a "Build Pipeline" mode where users can:
1. Search and select a skill
2. Fill in its inputs
3. Add another step that references outputs from step 1 (via template syntax like `{steps[0].outputs.clips}`)
4. Run the entire pipeline
5. See results cascade through steps

### Step 4.2 — Pipeline execution backend

**File:** `pi_orchestrator/services/slice_play_service.py`

```python
async def execute_pipeline(agent_id, steps, initial_context=None):
    context = {"agent_memories": [], **(initial_context or {})}
    for i, step in enumerate(steps):
        resolved_inputs = resolve_templates(step["inputs"], context)
        result = await execute_play(agent_id, step["skill"], resolved_inputs)
        context[f"steps[{i}]"] = {"outputs": result["outputs"]}
        context["agent_memories"].extend(result.get("memories", []))
    return context
```

### Step 4.3 — Coms panel shows shared knowledge

**File:** `dashboard/src/components/ComsPanel.vue`

For each peer, show:
- Number of shared facts they've contributed
- Recent facts (last 3)
- Click to see full context
- A "Send this to my agent" button that injects a peer's context into the current chat

---

## Summary: What Each Session Unlocks

| Session | Delivers | User-visible change |
|---------|----------|---------------------|
| **1** Agent Profiles | Agents remember past sessions | Agent says "Last time I was working on X" without being told |
| **2** Shared Knowledge Pool | Agents share context without messaging | Agent B knows what Agent A learned |
| **3** Rich Slice Plays | Parameterized, schema-driven plays | Slice Play cards have form fields, not blind buttons |
| **4** Pipeline + Coms | Chained plays, interactive peer context | Drag-drop skill pipelines, clickable peer knowledge |

## Where to Look for Supermemory's Actual Code

All patterns are in `~/supermemory-toolchest/`:

| What you need | Which file |
|---------------|------------|
| Deduplication algorithm (copy-paste) | `00-shared/src/utils.ts` → `deduplicateMemories()` (20 lines) |
| Profile-to-prompt formatting | `03-sdks-tools/src/shared/prompt-builder.ts` → `convertProfileToMarkdown()` (15 lines) |
| Profile fetch → dedup → format pipeline | `03-sdks-tools/src/shared/memory-client.ts` → `buildMemoriesText()` (40 lines) |
| MCP tool schema pattern (Zod inputs) | `01-mcp-server/src/server.ts` → `memorySchema`, `recallSchema` |
| Container tag scoping pattern | `00-shared/src/core-types.ts` → `CONTAINER_TAG_CONSTANTS` |
