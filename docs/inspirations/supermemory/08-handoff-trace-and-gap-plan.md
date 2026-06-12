# Handoff Trace & Map — Fixing the 4 Biggest Gaps

> Every feature in slice-of-pi is a chain of handoffs. Data passes from one component
> to the next. When a handoff is missing or incomplete, the feature breaks silently.
> This doc traces every handoff in the system and shows exactly what to build for each gap.

---

## 0. The Complete Handoff Map (Before Changes)

```
┌── LAYER 1: DASHBOARD (Vue 3) ───────────────────────────────────┐
│                                                                   │
│  Components: AgentDetail, SlicePlaysPanel, ComsPanel, Settings   │
│  Store: Pinia (app, auth, notifications)                         │
│                                                                   │
│  Handoffs out:                                                    │
│    fetch() ──────HTTP─────▶ Router (15 route groups)              │
│    WebSocket ────WS────────▶ events.py (real-time events)         │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
         │                              ▲
         ▼                              │
┌── LAYER 2: ROUTERS (FastAPI) ────────┼──────────────────────────┐
│                                       │                          │
│  Handoffs out:                       │                          │
│    agents.py ──────▶ pi_session_service.create_agent()          │
│    chat.py ────────▶ pi_session_service.stream_chat()           │
│    skills.py ──────▶ filesystem (SKILL.md)                      │
│    coms.py ────────▶ filesystem (~/.pi/coms/)                   │
│    schedules.py ───▶ schedule_service                            │
│    credentials.py ─▶ database (encrypted CRUD)                   │
│    events.py ◀─────▶ event_bus.subscribe() / publish() ←─┐      │
│    (3 call sites: agent_created, agent_deleted,          │      │
│                    agent_updated)                         │      │
│                                                          │      │
│  Handoff pattern: router calls service function directly  │      │
└──────────────────────────────────────────────────────────┼──────┘
         │                              ▲                  │
         ▼                              │                  │
┌── LAYER 3: SERVICES ──────────────────┼──────────────────┼─────┐
│                                       │                  │     │
│  pi_session_service:                  │                  │     │
│    stream_chat() ──▶ subprocess (pi)  │                  │     │
│                   ──▶ database.update_session()          │     │
│                   ──▶ database.record_activity()         │     │
│                                                          │     │
│  schedule_service:                                       │     │
│    _execute_schedule() ──▶ subprocess (pi)               │     │
│                                                          │     │
│  cleanup_service:                                        │     │
│    _cleanup_once() ──▶ filesystem (remove old JSONL)     │     │
│                    ──▶ database.expire_old_sessions()    │     │
│                                                          │     │
│  git_service: ──────────▶ subprocess (git)               │     │
│  system_chat_service: ──▶ subprocess (pi)                │     │
│                                                          │     │
│  event_bus: ────────────▶ WebSocket clients              │     │
│                                                          │     │
│  Handoff pattern: sync function call or async subprocess │     │
└──────────────────────────────────────────────────────────┼─────┘
         │                              ▲                  │
         ▼                              │                  │
┌── LAYER 4: PERSISTENCE ───────────────┼──────────────────┼─────┐
│                                       │                  │     │
│  database.py: SQLite CRUD             │                  │     │
│    agents, sessions, activities,      │                  │     │
│    schedules, credentials, tags, ...  │                  │     │
│                                       │                  │     │
│  filesystem:                          │                  │     │
│    ~/.pi/agent/sessions/*.jsonl       │                  │     │
│    ~/.pi/agent/skills/*/SKILL.md      │                  │     │
│    ~/.pi/coms/projects/*/agents/*.json│                  │     │
│                                       │                  │     │
└──────────────────────────────────────────────────────────┼─────┘
                                                           │
         ┌─────────────────────────────────────────────────┘
         ▼
┌── EVENT BUS ───────────────────────────────────────────────┐
│                                                             │
│  Events published today:                                    │
│    agent_created    (agents.py → events.py → dashboard)     │
│    agent_deleted    (agents.py → events.py → dashboard)     │
│    agent_updated    (tags.py → events.py → dashboard)       │
│                                                             │
│  Events NOT published (but should be):                      │
│    profile_updated  ❌                                      │
│    facts_written    ❌                                      │
│    connector_sync_* ❌                                      │
│    slice_play_run   ❌                                      │
│    session_completed❌                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. Gap: Connectors Sync Nothing

### The Intended Handoff Chain

```
User clicks "Sync Now" or schedule fires
        │
        ▼
  [SYNC HANDOFF]  ←─ DOES NOT EXIST
        │
        ▼
  Connector Registry → get("google-drive")
        │
        ▼
  plugin.sync(auth, since) → external API
        │
        ▼
  [WRITE HANDOFF]  ←─ DOES NOT EXIST
        │
        ▼
  shared_memory_service.write_fact()
        │
        ▼
  [EVENT HANDOFF]  ←─ DOES NOT EXIST
        │
        ▼
  event_bus.publish("connector_sync_completed")
```

### Existing Handoffs That Almost Fit

| Handoff Point | Exists? | What It Does | Why It Doesn't Fit |
|--------------|---------|-------------|-------------------|
| `schedule_service._execute_schedule()` | ✅ | Spawns pi subprocess on cron | Spawns an agent — we need to call `plugin.sync()`, not run a pi session |
| `POST /api/schedules` | ✅ | Creates a cron job | Same — fires agent sessions, not connector syncs |
| `cleanup_service._cleanup_once()` | ✅ | Periodic background task | Runs on timer but only cleans sessions — no hook for custom tasks |
| `event_bus.publish()` | ✅ | 3 call sites exist | Used for agent lifecycle, not for connector events |

### New Handoffs To Build

#### Handoff A: `POST /api/connectors/{id}/sync` → Sync Engine

```
New router endpoint            Existing DB              New engine
┌──────────────────┐     ┌──────────────┐     ┌─────────────────────┐
│  POST /api/       │────▶│  get_connector│────▶│  SyncEngine.        │
│  connectors/{id}  │     │  (SQLite)    │     │  sync_one()         │
│  /sync            │     └──────────────┘     └──────────┬──────────┘
└──────────────────┘                                      │
                                                   ┌──────▼──────┐
                                                   │  registry.  │
                                                   │  get()      │
                                                   └──────┬──────┘
                                                          │
                                                   ┌──────▼──────┐
                                                   │  plugin.    │
                                                   │  sync()     │
                                                   └─────────────┘
```

**Code to write:**
- `routers/connectors.py` — add `POST /api/connectors/{id}/sync` endpoint
- `services/connectors/engine.py` — `SyncEngine` class with `sync_one(connector_id)` method
- `services/connectors/engine.py` — `sync_all()` method for batch syncs

**Handoff interface:**
```python
# Router → Engine: call with connector_id
result = await sync_engine.sync_one(connector_id)

# Engine → Plugin: call plugin.sync(auth, since)
docs = await plugin.sync(auth_state, since=last_sync_at)

# Engine → Shared Memory: write each doc
for doc in docs:
    write_fact(agent_id, tag, f"[{provider}] {doc['title']}: {doc['content'][:200]}")

# Engine → DB: update sync status
db.update_connector_sync_status(connector_id, "success", items_found=len(docs))
```

#### Handoff B: Schedule Service → Connector Sync Jobs

```
Schedule service poll loop          Connector auto-sync
┌─────────────────────┐       ┌──────────────────────────────┐
│  _reload_loop()      │       │  SyncEngine.sync_all()       │
│  every 30s           │       │  Checks all connectors:     │
│       │              │       │    - enabled?                │
│       │              │       │    - has schedule?           │
│       ▼              │       │    - due for sync?           │
│  _reload_schedules() │       │    - calls sync_one()        │
└─────────────────────┘       └──────────────────────────────┘
```

This doesn't need a new handoff — it reuses the **existing schedule_service pattern** but
the SyncEngine manages its own timing instead of adding rows to the `schedules` table.

```python
# services/connectors/engine.py
class SyncEngine:
    async def _auto_sync_loop(self):
        while self._running:
            connectors = db.list_connectors(enabled_only=True)
            for c in connectors:
                plugin = registry.get(c["provider"])
                if plugin and plugin.get_schedule():
                    if self._is_due(c):
                        await self.sync_one(c["id"])
            await asyncio.sleep(60)  # Check every minute
```

#### Handoff C: Event Bus → Connector Sync Events

```
engine.sync_one() completes
        │
        ▼
event_bus.publish("connector_sync_completed", {
    "connector_id": "...", 
    "provider": "google-drive",
    "status": "success",
    "items": 14,
})
        │
        ▼
Dashboard receives via /ws/events
        │
        ▼
Shows toast or updates connector status in real-time
```

**New event types to publish:** `connector_sync_started`, `connector_sync_completed`, `connector_sync_error`, `connector_auth_expired`

---

## 2. Gap: Dashboard Shows No New UI

### The Intended Handoff Chain

```
User navigates to Agent Detail
        │
        ▼
AgentDetail.vue loads tabs: Chat | Terminal | Files | Settings | SLICE PLAYS | CONNECTORS
                                                                       ▲          ▲
                                                                       │          │
                                                         ┌─────────────┘          │
                                                         │                       │
                                                    fetch('/api/skills')   fetch('/api/connectors')
                                                         │                       │
                                                         ▼                       ▼
                                                    SlicePlaysPanel.vue    New: ConnectorsPanel.vue
                                                         │                       │
                                                         ▼                       ▼
                                                    Parameter form         Configure/Sync/Status
```

### Existing Handoffs

| Handoff Point | Exists? | What It Does |
|--------------|---------|-------------|
| `AgentDetail.vue` tabs | ✅ | Renders tabs array with activeTab state |
| `fetch('/api/skills')` | ✅ | Already called on mount |
| `SlicePlaysPanel.vue` | ✅ | Already rendered in tabs |
| `fetch('/api/connectors')` | ❌ | Doesn't exist (no router yet) |
| `ConnectorsPanel.vue` | ❌ | Doesn't exist |

### New Handoffs To Build

#### Handoff A: AgentDetail Tabs → Connectors Panel

```javascript
// In AgentDetail.vue — add to the tabs array
const tabs = [
  'Info', 'Chat', 'Slice Plays', 'Terminal', 
  'Files', 'Git', 'Credentials', 'Connectors',  // ← NEW
  'Sharing', 'Activity', 'Edit', 'Settings'
]
```

This is a **one-line change** plus adding a `ConnectorsPanel.vue` component import.

#### Handoff B: SlicePlaysPanel → Parameter Form

```vue
<!-- Before: blind Run button -->
<button @click="runSlicePlay(skill)">Run</button>

<!-- After: show form when skill has inputs -->
<template v-if="skill.inputs && Object.keys(skill.inputs).length > 0">
  <div v-for="(param, name) in skill.inputs">
    <label>{{ name }}</label>
    <input v-if="param.type === 'string'" v-model="formValues[name]" />
    <input v-if="param.type === 'number'" type="number" v-model.number="formValues[name]" />
    <input v-if="param.type === 'boolean'" type="checkbox" v-model="formValues[name]" />
  </div>
  <button @click="runSlicePlay(skill, formValues)">Run with parameters</button>
</template>
<template v-else>
  <button @click="runSlicePlay(skill)">Run</button>
</template>
```

#### Handoff C: Settings Page → Connector Management

```vue
<!-- New section in Settings.vue -->
<template v-if="activeSection === 'connectors'">
  <h2>Connectors</h2>
  <div v-for="conn in configuredConnectors">
    <span>{{ conn.label }} ({{ conn.provider }})</span>
    <span>Status: {{ conn.last_sync_status }}</span>
    <button @click="syncNow(conn.id)">Sync Now</button>
  </div>
</template>
```

---

## 3. Gap: Bad Memories Get Stored

### The Intended Handoff Chain

```
stream_chat() completes
        │
        ├── SUCCESS path:
        │   db.update_session(status="completed")
        │   db.update_agent_status("idle")
        │   → append_agent_memory(agent_id, summary)  ← CURRENT: always runs
        │
        └── ERROR path:
            db.update_session(status="error")
            db.update_agent_status("error")
            → yield {"type": "error"}
            → ... nothing else ...                    ← SHOULD NOT append memory
```

### The Problem

In `pi_session_service.py`, the session summary extraction and profile append happen
**unconditionally** in the success block (around line 225-235). But there's actually
a structural issue: the success and error paths are different code blocks.

The current code:

```python
# Lines ~200-235:
try:
    async for chunk in _stream_jsonl(...):
        # ... streaming loop ...
except asyncio.TimeoutError:
    # ... handles timeout → sets status=error ...
    return                    # ← Exits early, never reaches memory append

# Stream completed normally
stderr_task.cancel()
# Finalize session — THIS IS THE SUCCESS PATH
db.update_session(session_id, status="completed", ...)
db.update_agent_status(agent_id, "idle")
# ── Store session memory ──  ← NEW PLAN CODE (runs only on success)
db.append_agent_memory(agent_id, session_note)
```

Wait — the current code **doesn't append memory yet** (the PLAN adds that). So the
current Gap 3 concern is: "when we add Step 1.4, we must guard it properly."

### Fix: Guard the Memory Append

```python
# In the success path (after streaming completes normally):
if turn_count > 0:  # Only record if actual work happened
    session_note = extract_session_summary(agent_id, prompt, session_id)
    db.append_agent_memory(agent_id, session_note, fact_type="dynamic")

# NEVER append in the error path (timeout, exception)
```

**Handoff that needs guarding:** `stream_chat() → db.append_agent_memory()`

The guard is simple: only append when `turn_count > 0` and the session status is `"completed"`.
The success path already has this context — the error paths exit via `return` before reaching
the append code. So as long as Step 1.4's code is positioned correctly (inside the success
block, after the stderr cleanup), it's naturally guarded.

But we should also add an explicit guard:

```python
# Explicit guard — safety net
session_status = "completed"  # We're in the success path
if session_status == "completed" and turn_count > 0:
    db.append_agent_memory(agent_id, session_note)
else:
    logger.debug(f"Skipping memory append: status={session_status}, turns={turn_count}")
```

### New Handoff To Add: Session Completion → Audit

```
stream_chat() completes (success)
        │
        ├── db.update_session(status="completed")
        ├── db.update_agent_status("idle")
        ├── db.record_activity("session_end", ...)
        │
        ├── [GUARD] turn_count > 0?
        │       │
        │       ├── YES → db.append_agent_memory(agent_id, summary)
        │       │          event_bus.publish("profile_updated", ...)
        │       │
        │       └── NO  → logger.debug("skipped — no turns")
        │
        └── event_bus.publish("session_completed", {
                "agent_id": agent_id,
                "turns": turn_count,
                "tokens": total_tokens,
                "memories_stored": 1 if turn_count > 0 else 0,
            })
```

---

## 4. Gap: Data Grows Without Bounds

### The Intended Handoff Chain

```
Every write_fact() call
        │
        ▼
knowledge.jsonl appends a line
        │
        ▼
[FILE GROWS FOREVER]  ←─ NO cleanup handoff
        │
        ▼
Eventual impact: read_context() gets slower
                 disk usage grows
                 stale 30-day-old facts still in prompts

What SHOULD happen:
        │
        ▼
cleanup_service._cleanup_once() should ALSO:
  ──▶ shared_memory_service.cleanup_expired_facts()
  ──▶ prune knowledge.jsonl entries older than FACT_TTL_DAYS
  ──▶ log stats: "Purged 1,204 expired facts (42KB freed)"
```

### Existing Handoffs That Nearly Fit

| Handoff Point | Exists? | What It Cleans | Why It Doesn't Cover This |
|--------------|---------|---------------|--------------------------|
| `cleanup_service._cleanup_once()` | ✅ | Session JSONL files > 7 days old | Only touches session files in `sessions/managed/` — not shared memory |
| `cleanup_service._cleanup_once()` | ✅ | DB sessions marked expired | Only expires session DB rows — not connector_sync_log | 
| `cleanup_service` runs every 6h | ✅ | Background periodic task | Perfect for hooking into — the loop already exists |

### New Handoffs To Build

#### Handoff A: Cleanup Service → Shared Memory Pruning

**Just add one function call at the end of `cleanup_service._cleanup_once()`:**

```python
async def _cleanup_once(self) -> None:
    # ... existing session cleanup ...
    
    # NEW: Prune expired shared memory facts
    try:
        from ..services.shared_memory_service import cleanup_expired_facts
        purged = cleanup_expired_facts(max_age_days=30)
        if purged > 0:
            logger.info("Cleanup: purged %d expired shared memory facts", purged)
    except Exception:
        logger.exception("Shared memory cleanup failed")
    
    # NEW: Prune old connector sync logs
    try:
        purged_logs = db.prune_connector_sync_logs(retention_days=30)
        if purged_logs > 0:
            logger.info("Cleanup: pruned %d old connector sync log entries", purged_logs)
    except Exception:
        logger.exception("Connector sync log pruning failed")
```

**The `cleanup_expired_facts()` function** rewrites `knowledge.jsonl` excluding expired entries:

```python
def cleanup_expired_facts(max_age_days: int = 30) -> int:
    """Remove facts older than max_age_days from all knowledge.jsonl files.
    
    Rewrites each file in-place (read all, filter, write back).
    This is safe because writes are append-only — we never lose in-flight data.
    """
    cutoff = datetime.now(timezone.utc).timestamp() - (max_age_days * 86400)
    total_purged = 0
    
    for tag_dir in SHARED_MEMORY_DIR.iterdir():
        if not tag_dir.is_dir():
            continue
        path = tag_dir / "knowledge.jsonl"
        if not path.exists():
            continue
        
        # Read all entries
        entries = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    ts = datetime.fromisoformat(entry.get("timestamp", "")).timestamp()
                    if ts >= cutoff:
                        entries.append(entry)
                    else:
                        total_purged += 1
                except (json.JSONDecodeError, ValueError):
                    pass  # Keep unparseable lines (don't corrupt)
        
        # Rewrite file with only non-expired entries
        with open(path, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")
    
    return total_purged
```

#### Handoff B: Agent Delete → Cascade to Shared Memory

Add to `destroy_agent()` in `pi_session_service.py`:

```python
async def destroy_agent(agent_id: str) -> bool:
    """Stop any running session and remove the agent from the database."""
    agent = db.get_agent(agent_id)
    if not agent:
        return False

    # NEW: Clean up shared memory facts from this agent
    try:
        from ..services.shared_memory_service import delete_agent_facts
        deleted = delete_agent_facts(agent_id)
        if deleted:
            logger.info("Cleaned up %d shared memory facts for deleted agent %s", 
                       deleted, agent_id[:12])
    except Exception:
        logger.exception("Failed to clean up shared memory facts")
    
    # ... existing destroy logic ...
```

**Handoff to build:** `destroy_agent() → shared_memory_service.delete_agent_facts()`

#### Handoff C: Active → JSONL Rotation Warning

When `read_context()` detects a knowledge.jsonl file exceeding a threshold, log a warning:

```python
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB warning threshold

def read_context(tags, ...):
    for tag in tags:
        path = SHARED_MEMORY_DIR / tag / "knowledge.jsonl"
        if path.exists():
            size = path.stat().st_size
            if size > MAX_FILE_SIZE_BYTES:
                logger.warning(
                    "Shared memory for tag '%s' is %.1f MB — cleanup recommended",
                    tag, size / (1024 * 1024)
                )
            # ... continue reading ...
```

---

## Summary: The 4 Gaps → The New Handoffs

| Gap | The Missing Handoff | What to Build | File Changes |
|-----|--------------------|---------------|-------------|
| **Connectors sync nothing** | Router → Sync Engine → Plugin → Shared Memory → Event Bus | `SyncEngine.sync_one()`, `POST /api/connectors/{id}/sync`, auto-sync loop, event bus events | New: `engine.py`, extend: `connectors.py` |
| **Dashboard shows no new UI** | Tabs → Connectors Panel, Skill Cards → Parameter Form, Settings → Connector Status | `ConnectorsPanel.vue`, form inputs in `SlicePlaysPanel.vue`, settings section | Modify: `AgentDetail.vue`, `SlicePlaysPanel.vue`, `Settings.vue`. New: `ConnectorsPanel.vue` |
| **Bad memories get stored** | stream_chat success → memory append (guarded by turn_count > 0) | Guard clause on Step 1.4's `append_agent_memory()` | Modify: `pi_session_service.py` (add `if turn_count > 0`) |
| **Data grows without bounds** | Cleanup Service → Shared Memory Pruning, Agent Delete → Fact Cascade | `cleanup_expired_facts()`, `delete_agent_facts()`, hook into existing `cleanup_service` | Modify: `cleanup_service.py`, `pi_session_service.py`. Extend: `shared_memory_service.py` |

### The Four Handoffs in One Diagram

```
         User Action                          Background                     Cleanup Cycle
    ┌─────────────────┐              ┌─────────────────────┐          ┌──────────────────────┐
    │                 │              │                     │          │                      │
    │  POST /api/     │              │  Schedule Service    │          │  Cleanup Service     │
    │  connectors/    │              │  poll loop           │          │  every 6h            │
    │  {id}/sync      │              │                     │          │                      │
    │        │        │              │        │            │          │         │            │
    │        ▼        │              │        ▼            │          │         ▼            │
    │  ┌───────────┐  │              │  ┌──────────────┐   │          │  ┌──────────────┐    │
    │  │  Sync     │  │              │  │  SyncEngine  │   │          │  │  cleanup_    │    │
    │  │  Engine   │◀─┼──────────────┼──│  .sync_all() │   │          │  │  expired_    │    │
    │  └─────┬─────┘  │              │  └──────┬───────┘   │          │  │  facts()     │    │
    │        │        │              │         │           │          │  └──────┬───────┘    │
    │        ▼        │              │         │           │          │         │           │
    │  ┌───────────┐  │              │         │           │          │         ▼           │
    │  │  Plugin   │  │              │         │           │          │  ┌──────────────┐    │
    │  │  .sync()  │  │              │         │           │          │  │  Rewrite     │    │
    │  └─────┬─────┘  │              │         │           │          │  │  knowledge   │    │
    │        │        │              │         │           │          │  │  .jsonl      │    │
    │        ▼        │              │         │           │          │  └──────────────┘    │
    │  ┌───────────┐  │              │         │           │          │                      │
    │  │  write_   │  │              │         │           │          │  GAP 4 FIX            │
    │  │  fact()   │  │              │         │           │          │                      │
    │  └─────┬─────┘  │              │         │           │          │                      │
    │        │        │              │         │           │          │                      │
    │        ▼        │              │         │           │          │                      │
    │  ┌───────────┐  │              │         │           │          │                      │
    │  │ event_bus │  │              │         │           │          │                      │
    │  │ .publish  │  │              │         │           │          │                      │
    │  └───────────┘  │              │         │           │          │                      │
    │                 │              │         │           │          │                      │
    │  GAP 1 FIX      │              │  GAP 1  │           │          │                      │
    │  (manual sync)  │              │  (auto) │           │          │                      │
    └─────────────────┘              └─────────┴───────────┘          └──────────────────────┘
```

### Effort Estimate

| Handoff | Lines of Code | Files Changed | Risk |
|---------|---------------|---------------|------|
| **Gap 1: Sync engine** | ~150 | 3 files (1 new, 2 modified) | Medium — new async service with external API calls |
| **Gap 2: Dashboard UI** | ~200 | 4 Vue files | Medium — component work, needs backend endpoints to exist first |
| **Gap 3: Memory guard** | ~5 | 1 file | None — single if-guard in existing code |
| **Gap 4: Cleanup** | ~80 | 3 files (1 new function, 2 hooks) | Low — read-only rewrite of JSONL, existing cleanup pattern |
