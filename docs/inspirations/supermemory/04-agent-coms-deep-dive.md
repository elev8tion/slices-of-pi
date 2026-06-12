# Agent-to-Agent Communication — Deep Dive: Current State → Supermemory-Inspired Future

## Current State

### Coms Router (`pi_orchestrator/routers/coms.py`)

A **read-only peer browser**. It reads `~/.pi/coms/projects/*/agents/*.json` and returns:

```python
[
    {
        "name": "agent-foo",
        "project": "default",
        "model": "claude-sonnet-4",
        "status": "online",
        "context_used": 42,
        "queue_depth": 0
    },
    ...
]
```

That's **all it does**. No sending messages. No shared context.

### Teams Router (`pi_orchestrator/routers/teams.py`)

Reads `~/.pi/agents/teams.yaml` and **deploys agents** — creates DB records for each team member. That's also all it does. Once deployed, team members are independent — they don't share context.

### Abstract Interfaces (Unimplemented)

The `slice_of_pi/orchestration/` package defines **three abstract interfaces with zero concrete implementations**:

| Interface | File | Purpose | Implemented? |
|-----------|------|---------|-------------|
| `AgentRuntime` | `_agent_runtime.py` | Abstract agent execution environment | ❌ No impls |
| `WorkflowEngine` | `_workflow_engine.py` | Multi-step agent pipeline orchestration | ❌ No impls |
| `ChannelAdapter` | `_channel_adapter.py` | External platform adapters (Slack, Discord, etc.) | ❌ No impls |

### ComsPanel.vue

A tiny card showing peer name, model, project, status. No interaction — just a list.

## Key Insight: You Don't Need Agent-to-Agent Messaging

Supermemory's entire architecture is built on a **shared memory pool** — agents don't talk to each other, they **both read from and write to the same accumulating context**. This is far more robust than direct messaging:

| Approach | Pros | Cons |
|----------|------|------|
| **Direct messaging** (A→B) | Feels natural | Both agents must be alive, fragile, coupling, race conditions |
| **Shared memory pool** (A↔DB↔B) | Decoupled, survives restarts, queryable, auditable | Slightly more latency (insignificant) |

Supermemory chose the shared pool. Slice of Pi should too.

## Supermemory-Inspired Architecture

```
┌────────────────────────────────────────────────────┐
│              Shared Agent Knowledge Pool           │
│  ~/.pi/agent/shared-memory/{tag}/knowledge.jsonl   │
│                                                     │
│  Each line: { agent_id, tag, fact, type, ts }       │
└────────────────────────────────────────────────────┘
          ▲                          ▲
          │ writes                   │ reads
          │                          │
┌─────────▼─────────┐    ┌──────────▼──────────┐
│   Agent A (pi)    │    │   Agent B (pi)       │
│  (subprocess)     │    │  (subprocess)        │
│                   │    │                      │
│  Session #1:      │    │  Session #5:         │
│  "Learned DB     │    │  "Agent A already    │
│   schema has     │    │   mapped the DB      │
│   users table"   │    │   schema last week"  │
└──────────────────┘    └──────────────────────┘
```

### What This Looks Like in Code

#### A. Shared Knowledge Pool Storage

```python
# New file: pi_orchestrator/services/shared_memory_service.py

SHARED_MEMORY_DIR = Path.home() / ".pi" / "agent" / "shared-memory"


def write_fact(agent_id: str, tag: str, fact: str, fact_type: str = "dynamic"):
    """Write a fact to the shared knowledge pool."""
    path = SHARED_MEMORY_DIR / tag / "knowledge.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps({
            "agent_id": agent_id,
            "tag": tag,
            "fact": fact,
            "type": fact_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }) + "\n")


def read_context(tags: list[str], max_age_hours: int = 24) -> str:
    """Read relevant facts for given tags, deduplicate, return as markdown."""
    facts = {"static": [], "dynamic": []}
    cutoff = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
    
    for tag in tags:
        path = SHARED_MEMORY_DIR / tag / "knowledge.jsonl"
        if not path.exists():
            continue
        with open(path) as f:
            for line in f:
                entry = json.loads(line)
                entry_ts = datetime.fromisoformat(entry["timestamp"]).timestamp()
                if entry_ts < cutoff:
                    continue
                facts[entry.get("type", "dynamic")].append(entry["fact"])
    
    # Deduplicate (static wins over dynamic)
    seen = set()
    parts = []
    for fact_type in ("static", "dynamic"):
        for fact in facts[fact_type]:
            if fact not in seen:
                seen.add(fact)
                parts.append(f"- {fact}")
    
    return "## Shared Workspace Knowledge\n" + "\n".join(parts) if parts else ""
```

#### B. Injection at Session Start

In `pi_session_service.py`, just before building the pi command:

```python
# After creating session record, before spawning pi:
if agent_tags := agent.get("tags", []):
    shared_context = read_context(agent_tags)
    if shared_context:
        if system_prompt:
            system_prompt += "\n\n" + shared_context
        else:
            system_prompt = shared_context
```

#### C. Agents Can Write Facts During a Session

In the `stream_chat()` function, after each turn completes, scan the agent's output for memory-worthy facts and write them to the shared pool:

```python
# After parsing a turn's output:
memories = extract_memory_patterns(turn_text)  # e.g. "I learned that..."
for memory in memories:
    write_fact(agent_id, tag, memory, fact_type="dynamic")
```

## Code Points Map

### Files to Create

| New File | Purpose | Key Functions |
|----------|---------|---------------|
| `pi_orchestrator/services/shared_memory_service.py` | Shared knowledge pool read/write | `write_fact()`, `read_context()`, `deduplicate_memories()` |
| `pi_orchestrator/services/agent_profile_service.py` | Per-agent profile management | `load_profile()`, `save_profile()`, `append_dynamic()`, `format_profile_as_prompt()` |
| `pi_orchestrator/services/slice_play_service.py` | Slice play pipeline executor | `execute_play()`, `execute_pipeline()`, `resolve_templates()` |
| `pi_orchestrator/routers/slice_plays.py` | Slice plays API endpoints | `POST /api/slice-plays/execute`, `GET /api/slice-plays/{id}` |

### Files to Modify

| File | What to Change | Why |
|------|---------------|-----|
| `pi_orchestrator/database.py` | Add `profile_json` column to agents table, add `slice_play_sessions` table | Persist accumulated knowledge |
| `pi_orchestrator/models.py` | Add `SkillSchema` (with inputs/outputs), `SlicePlaySession` Pydantic models | Schema for typed plays |
| `pi_orchestrator/routers/skills.py` | Replace regex frontmatter parser with proper YAML, parse `inputs`/`outputs` fields | Richer skill metadata |
| `pi_orchestrator/services/pi_session_service.py` | Inject profile + shared context before spawning pi, capture post-session memories | The core "memory injection" point |
| `pi_orchestrator/routers/coms.py` | Return peer profiles with shared context summary, not just basic status | Make coms useful |
| `dashboard/src/components/SlicePlaysPanel.vue` | Add parameter forms, pipeline builder UI | User-facing slice play editor |
| `dashboard/src/components/ComsPanel.vue` | Show peer profiles and shared knowledge, not just a list | Make coms interactive |

### Key Injection Points in `pi_session_service.py`

The file `pi_orchestrator/services/pi_session_service.py` is the single most important file. Here's exactly where to inject things:

```
Line ~80:  session = db.create_session(...)
           ─────────────────────────────────────
           AFTER this, BEFORE building cmd:

           INJECTION POINT #1 — Load agent profile
           profile = load_agent_profile(agent_id)
           profile_context = format_profile_as_prompt(profile)

           INJECTION POINT #2 — Load shared context
           tags = json.loads(agent.get("tags", "[]"))
           shared = read_context(tags)

           INJECTION POINT #3 — Append to system prompt
           if profile_context or shared:
               extra = "\n\n".join(filter(None, [profile_context, shared]))
               system_prompt = (system_prompt + "\n\n" + extra) if system_prompt else extra

Line ~100: cmd = [PI_BINARY, "--mode", "json", "--session", ...]
```

### After Session Completion

```
Line ~220: After streaming loop, before finally:

           INJECTION POINT #4 — Extract and save memories
           memories = extract_memories_from_turns(session_id)
           for m in memories:
               write_fact(agent_id, tag, m)

           INJECTION POINT #5 — Update agent profile
           append_to_dynamic_profile(agent_id, memories)
```

## Inspiration Sources in the Supermemory Toolchest

The actual supermemory code at `~/supermemory-toolchest/` has these specific files to reference:

| Supermemory File | Pattern | What to Steal |
|-----------------|---------|---------------|
| `00-shared/src/utils.ts` | `deduplicateMemories()` (priority: static > dynamic > search) | The exact dedup logic — copy-paste to `shared_memory_service.py` |
| `02-mcp-client/src/client.ts` | The client API (create, forget, search, profile, projects) | API design pattern for shared memory |
| `03-sdks-tools/src/shared/memory-client.ts` | `supermemoryProfileSearch()` + `buildMemoriesText()` | The profile fetch → dedup → format → inject pipeline |
| `03-sdks-tools/src/shared/prompt-builder.ts` | `convertProfileToMarkdown()` | Profile-to-prompt formatting |
| `00-shared/src/core-types.ts` | MemoryMode, ProfileStructure, PromptTemplate | Type definitions for memory model |

## The One-Liner

> Slice of Pi's agent-to-agent "coms" is currently a **read-only list of peer names**. Supermemory shows a better path: a **shared knowledge pool** where every agent writes what it learns and reads what others learned — no direct messaging needed. Same 3-line dedup function. Same profile-to-prompt inject pattern. The orchestrator mediates, agents stay simple, knowledge accumulates.
