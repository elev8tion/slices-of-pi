# Workflow Overview — All Areas That Need Addressing

> This maps every workflow the new features enable, traces how data flows through the system,
> and identifies gaps the PLAN doesn't cover. Use this alongside `PLAN-maestro-execution.md`.

---

## How I Read This Document

Each section follows this structure:

```
┌─ Workflow ─────────────────────────────────────┐
│  Step-by-step story of what happens             │
│                                                 │
│  Data flow: input → transform → store → output  │
│                                                 │
│  GAPS: things the PLAN doesn't address yet      │
└─────────────────────────────────────────────────┘
```

---

## 1. Agent Session with Profile Injection

### The Workflow

```
User opens AgentDetail → clicks Chat → types "review this PR"
        │
        ▼
POST /api/agents/{id}/chat { message: "review this PR" }
        │
        ▼
pi_session_service.stream_chat()
        │
        ├── 1. Load agent record (has profile_json, tags, system_prompt)
        │
        ├── 2. Format profile → markdown string  ← NEW
        │       Static: "Specialist: code review, Strengths: TypeScript"
        │       Dynamic: "Session #42: reviewed auth middleware"
        │
        ├── 3. Read shared knowledge pool → markdown string  ← NEW
        │       Tag-matching context from other agents
        │
        ├── 4. Append both to system_prompt
        │       Existing prompt + "\n\n[profile]\n\n[shared context]"
        │
        ├── 5. Spawn pi subprocess with enriched system_prompt
        │
        ├── 6. Stream response back to dashboard
        │
        └── 7. Session ends → extract summary → append to profile ← NEW
                "Session #43: reviewed PR #89 (user auth)"
```

### Data Flow

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Agent Chat   │────▶│  profile_json    │────▶│  System Prompt   │
│  (user input) │     │  (SQLite column) │     │  (injected text) │
└──────────────┘     └──────────────────┘     └────────┬─────────┘
                                                       │
                              ┌──────────────────┐     │
                              │  Shared Knowledge │────▶│
                              │  (JSONL files)   │     │
                              └──────────────────┘     │
                                                       ▼
                                              ┌──────────────────┐
                                              │  pi subprocess   │
                                              │  (agent session) │
                                              └────────┬─────────┘
                                                       │
                                              ┌────────▼─────────┐
                                              │  Session summary │
                                              │  → appended to   │
                                              │  profile.dynamic │
                                              └──────────────────┘
```

### Gaps

| Gap | What's Missing | Impact |
|-----|---------------|--------|
| **Profile caps silently** | Dynamic memory caps at 50 entries, oldest dropped. User has no visibility. | Facts disappear without warning |
| **No forget API** | User can't delete a specific memory from the profile | Annoying if a bad fact gets stored |
| **No promote to static** | User can't elevate a dynamic fact to permanent | Agent forgets important context when cap rotates |
| **Token budget unknown** | Profile + shared context adds tokens. No warning if it pushes over model limit. | Truncation, broken prompts |
| **First session is empty** | Profile has no facts. System prompt has no injection. | Works, but user sees no difference — feels like nothing happened |
| **No profile preview** | No way to see "what my agent currently knows" in the dashboard | User can't audit what the agent remembers |

---

## 2. Cross-Agent Shared Knowledge

### The Workflow

```
Agent A finishes a session about DB schema
        │
        ▼
write_fact("agent-a", "infra", "Database users table has: id, name, email")
        │
        ▼
JSONL appended to ~/.pi/agent/shared-memory/infra/knowledge.jsonl
        │
        │   ... 3 hours later ...
        │
        ▼
Agent B (tagged "infra") starts a session
        │
        ▼
read_context(["infra"]) → returns markdown with Agent A's fact
        │
        ▼
Agent B's system prompt now includes: "Database users table has: id, name, email"
        │
        ▼
Agent B doesn't need to rediscover the schema
```

### Data Flow

```
┌──────────────┐     ┌──────────────────────┐     ┌──────────────────┐
│  Agent A     │────▶│  write_fact()         │────▶│  knowledge.jsonl │
│  (session)   │     │  (tag: "infra")      │     │  ~/.pi/agent/    │
└──────────────┘     └──────────────────────┘     │  shared-memory/  │
                                                   │  infra/          │
┌──────────────┐     ┌──────────────────────┐     └──────────────────┘
│  Agent B     │◀────│  read_context()       │           │
│  (session)   │     │  (tag: "infra")      │◀──────────┘
└──────────────┘     └──────────────────────┘
```

### Gaps

| Gap | What's Missing | Impact |
|-----|---------------|--------|
| **Facts never expire on disk** | TTL (30 days) is defined but nothing purges old entries | knowledge.jsonl grows unbounded |
| **No cleanup service integration** | The existing `cleanup_service.py` doesn't touch shared memory | Manual cleanup needed |
| **Tag discovery** | User needs to know what tags exist to configure them | Orphan tags, wasted reads |
| **No fact provenance in UI** | Dashboard has no way to show "who learned what" | Opaque — user can't trace where a fact came from |
| **Agent deletion = orphan facts** | Deleting an agent- doesn't clean its facts from shared memory | Stale facts from deleted agents persist |
| **Multi-tag scaling** | 20 tags = 20 file reads every session start | Potential latency if knowledge.jsonl files are large |
| **No fact dedup in read path** | Dedup happens, but if two agents write the exact same fact, only one survives | Correct but wastes writes |

---

## 3. Rich Slice Plays

### The Workflow (Current)

```
User opens AgentDetail → clicks Slice Plays tab
        │
        ▼
GET /api/skills → returns [{name, description, location}]
        │
        ▼
Dashboard renders card grid
        │
        ▼
User clicks "Run" on "/audio-chop"
        │
        ▼
POST /api/agents/{id}/chat { message: "/audio-chop" }
        │
        ▼
Agent receives raw trigger text, processes it
```

### The Workflow (With Plan Changes)

```
User opens AgentDetail → clicks Slice Plays tab
        │
        ▼
GET /api/skills → returns [{name, inputs: {file: {type, required}}, outputs: {...}}]
        │
        ▼
Dashboard renders card grid WITH parameter forms
        │
        ▼
User clicks "audio-chop" card → form opens:
        │  File: [________________]  ← required
        │  Clip length: [30]         ← optional, has default
        │
        ▼
User fills form, clicks "Run"
        │
        ▼
POST /api/agents/{id}/chat { message: "Run audio-chop with file=/tmp/song.mp3, clip_length=30" }
        │
        ▼
Agent receives structured instruction instead of raw /trigger
        │
        ▼
Results captured in slice play session JSONL
```

### Data Flow

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  SKILL.md     │────▶│  skills.py       │────▶│  Dashboard       │
│  (YAML with   │     │  (yaml parser)   │     │  (parameter form)│
│   inputs/     │     └──────────────────┘     └────────┬─────────┘
│   outputs)    │                                       │
└──────────────┘                                        │
                                               ┌────────▼─────────┐
                                               │  POST /api/agents │
                                               │  /chat (structured│
                                               │  instruction)     │
                                               └────────┬─────────┘
                                                        │
                                               ┌────────▼─────────┐
                                               │  slice_play_      │
                                               │  session.jsonl   │
                                               │  (captured       │
                                               │   outputs)       │
                                               └──────────────────┘
```

### Gaps

| Gap | What's Missing | Impact |
|-----|---------------|--------|
| **No pipeline chaining UI** | PLAN mentions it but provides no Vue component changes | Chaining is backend-only, no way to use from dashboard |
| **No slice play session viewer** | Outputs are captured but there's no dashboard view to browse past play results | Opaque — user can't see what a play produced |
| **No template variable syntax** | `{steps[0].outputs.clips}` is described but never implemented | Pipeline chaining can't actually reference previous outputs |
| **Parameter form not built** | `SlicePlaysPanel.vue` is listed as "NO CHANGE" in the PLAN | Forms don't exist — user still gets the blind "Run" button |
| **No output display** | After a play runs, results aren't shown differently than normal chat | No visual distinction between a play result and a chat message |
| **Slice play session not linked to agent** | The session ID is standalone, not connected to the agent | Can't browse "what slice plays did this agent run?" |

---

## 4. Connector Plugin System

### The Workflow

```
User navigates to AgentDetail → clicks "Connectors" tab
        │
        ▼
GET /api/connectors/available → lists installed plugins
        │  webhook (WebhookConnector)
        │  google-drive (GoogleDriveConnector) — if installed
        │  my-notes (MyNotesConnector) — user's custom plugin from ~/.pi/connectors/
        │
        ▼
User clicks "Configure" on "Google Drive"
        │
        ▼
Modal opens: auth fields, tag scope selector, auto-sync toggle
        │
        ▼
User authorizes → POST /api/connectors { provider, auth_state, container_tags }
        │
        ▼
Connector plugin runs authorize() → stores encrypted auth_state
        │
        ▼
Sync engine kicks off first sync → plugin.sync(auth) → returns documents
        │
        ▼
Documents written to shared knowledge pool under specified tags
        │
        ▼
Dashboard shows: ✅ Last sync: 2m ago (14 items imported)
```

### Data Flow

```
┌──────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│  ~/.pi/       │────▶│  Connector Registry │────▶│  GET /api/       │
│  connectors/  │     │  (discovery)        │     │  connectors/     │
│  *.py         │     └─────────────────────┘     │  available       │
└──────────────┘                                   └────────┬─────────┘
                                                            │
┌──────────────┐     ┌─────────────────────┐               │
│  User Config  │────▶│  POST /api/         │◀──────────────┘
│  (dashboard)  │     │  connectors         │
└──────────────┘     └──────────┬──────────┘
                                │
                       ┌────────▼─────────┐     ┌──────────────────┐
                       │  connector.auth   │────▶│  SQLite          │
                       │  State (encrypted)│     │  (connectors     │
                       └──────────────────┘     │   table)         │
                                                └──────────────────┘
                                │
                       ┌────────▼─────────┐     ┌──────────────────┐
                       │  plugin.sync()   │────▶│  Shared Knowledge│
                       │  (external API)  │     │  Pool (JSONL)    │
                       └──────────────────┘     └──────────────────┘
```

### Gaps

| Gap | What's Missing | Impact |
|-----|---------------|--------|
| **No connectors tab in AgentDetail** | Listed as "NO CHANGE" — no Vue component added | Connectors have no dashboard UI |
| **No connector form in Settings** | Listed as "NO CHANGE" in the PLAN | User can't configure connectors |
| **No sync engine** | `engine.py` is described in the doc but not in the PLAN | The connector exists but nothing drives its sync() method |
| **No schedule integration** | `get_schedule()` exists but `schedule_service.py` doesn't fire it | Auto-sync is a no-op |
| **No webhook endpoint** | Webhook connector needs a POST endpoint but none is created | The simplest connector has no way to receive data |
| **No manual sync button API** | No `POST /api/connectors/{id}/sync` endpoint | User can't trigger a sync on demand |
| **No connector sync status in UI** | `connector_sync_log` table exists but no dashboard view | User can't see if syncs succeeded or failed |
| **No plugin error surface** | If a plugin crashes during sync, error is logged but nowhere visible | Silent failures |
| **Auth token refresh** | No mechanism to handle expired OAuth tokens | Connectors break silently after token expiry |
| **Plugin hot-reload** | Registry caches on first call; no way to reload after installing a new plugin | User has to restart the orchestrator to pick up a new connector |

---

## 5. Agent and Fact Lifecycle

### The Workflow (Creation → Use → Cleanup)

```
Agent created
        │
        ▼
profile_json initialized: {"static": {}, "dynamic": []}
shared-memory dirs created (if agent has tags)
        │
        ▼
Session runs → facts flow in:
  - session summary → profile.dynamic
  - learned facts → shared knowledge pool (if agent has tags)
        │
        ▼
Over time:
  - profile.dynamic grows → caps at 50
  - knowledge.jsonl grows → 30-day TTL
  - connectors sync → more facts
        │
        ▼
Agent deleted → what happens to its facts?
  - profile_json goes away (cascade from agents table)
  - shared memory facts remain (no cascade — the file system doesn't know about SQLite)
```

### Data Flow

```
Time →  Agent A creates facts → profile_json (SQLite) → survives
                          → knowledge.jsonl (filesystem) → NO cascade on delete

Time →  Cleanup service runs → ? → should purge expired knowledge.jsonl entries
                                     → should trim profile.dynamic
                                     → should warn on profile nearing cap
```

### Gaps

| Gap | What's Missing | Impact |
|-----|---------------|--------|
| **No cleanup for shared memory** | `cleanup_service.py` exists but doesn't touch JSONL | knowledge.jsonl grows forever |
| **No cascade on agent delete** | Deleting an agent from SQLite doesn't remove its facts from JSONL | Phantom facts from deleted agents persist in shared context |
| **No profile_updated_at** | No timestamp tracking when a profile was last modified | Can't sort or filter by recency |
| **No fact staleness detection** | A fact like "Working on auth middleware" never ages out automatically | Stale context pollutes prompts |
| **No capacity warning** | No alert when an agent approaches the 50-fact dynamic cap | Users surprised when old facts vanish |
| **Profile not deletable independently** | Deleting an agent also deletes its profile, but there's no way to WIPE a profile without deleting the agent | If bad data gets in, the only fix is nuke the agent |

---

## 6. Monitoring & Observability

### What Exists Today

```
Activity feed:     session_start, session_end, session_error, credential events
Audit log:         agent CRUD, credential changes, user actions
Event bus:         WebSocket events (agent created/deleted/updated)
Health endpoint:   agent_count, active_session_count
```

### What the New Features Add (But Don't Surface)

```
Profile:           ─ no events for profile updates
                   ─ no profile_size metric
                   ─ no endpoint to view raw profile

Shared knowledge:  ─ no fact_count metric
                   ─ no most_active_agents metric
                   ─ no tag_usage metric

Connectors:        ─ sync events not emitted on event bus
                   ─ no connector health dashboard
                   ─ no sync latency metric

Slice plays:        ─ no play execution events
                   ─ no most_used_plays metric
                   ─ no play_success_rate metric
```

### Gaps

| Gap | What's Missing | Impact |
|-----|---------------|--------|
| **No profile audit events** | `record_activity()` isn't called when memories are appended | Can't trace "when did this fact get added?" |
| **No connector sync events** | Event bus doesn't emit connector_sync_start/completed/failed | Real-time dashboard won't show sync activity |
| **No profile endpoint** | No `GET /api/agents/{id}/profile` to let users or other services inspect current memory | Dashboard can't render a "what my agent knows" view |
| **No shared memory metrics** | No way to answer "how many facts in the pool?" or "which tag is most used?" | Ops visibility blind spot |
| **Health endpoint stale** | Health returns `agent_count` and `active_session_count` but not `fact_count`, `connector_count`, `pending_syncs` | Can't monitor system health at a glance |

---

## 7. Error and Edge Case Catalog

### What Happens When...

| Scenario | Current Behavior | Desired Behavior | Addressed? |
|----------|-----------------|------------------|------------|
| **profile.jsonl is malformed** | SQLite stores TEXT; json.loads could throw | Default to empty profile, log warning | ✅ Plan Step 1.1 handles this |
| **knowledge.jsonl is corrupted** | `read_context` hits JSONDecodeError on a line | Skip bad line, continue, log warning | ❌ Not in PLAN |
| **prompt + profile > model limit** | pi rejects or truncates silently | Warn in dashboard, truncate profile context first | ❌ Not in PLAN |
| **tag doesn't exist yet** | `read_context(["unknown-tag"])` → empty | Works correctly (empty result) | ✅ Implicitly handled |
| **two agents write same fact** | Dedup in read_context filters it out | Correct | ✅ Plan Step 3.1 dedup |
| **connector plugin imports fail** | `registry.py` catches exception and skips | Logs error, continues, remaining plugins load | ✅ Plan Step 4.2 has try/except |
| **agent deleted with 500 profile facts** | SQLite cascade removes profile_json | Correct | ✅ Partially — but facts in shared pool remain |
| **sync engine running when app restarts** | No sync state persisted mid-sync | Completed syncs logged, in-progress syncs are lost but retry on next cycle | ❌ Not in PLAN |
| **OAuth token expires mid-sync** | Connector plugin's API call fails | Mark sync as "error" with "auth_expired", disable connector, notify user | ❌ Not in PLAN |
| **user runs same slice play 2x** | Agent processes it again (duplicate work) | Dedup based on input hash, or warn "already run" | ❌ Not in PLAN |
| **profile summarizes a failed session** | session_summary is always appended even if agent returned an error | Only append on successful session completion | ❌ Not in PLAN — Step 1.4 appends unconditionally |

---

## 8. Summary: Work That's NOT in the PLAN

This is the list of work you'll need to do on top of `PLAN-maestro-execution.md`.

### High Priority (Blockers for basic usability)

| # | Area | What's Missing | Why It Matters |
|---|------|---------------|----------------|
| 1 | **Connector sync engine** | Plan creates plugins but no scheduler drives them. No `POST /api/connectors/{id}/sync`. | Connectors exist but never sync data |
| 2 | **Slice Plays dashboard UI** | Plan adds backend parsing but `SlicePlaysPanel.vue` is marked "NO CHANGE" | Users still see the blind "Run" button — parameter forms don't exist |
| 3 | **Connectors dashboard UI** | `AgentDetail.vue` and `Settings.vue` are marked "NO CHANGE" | Connectors have no UI — can't configure, see status, or trigger syncs |
| 4 | **Session summary only on success** | Step 1.4 appends memory unconditionally | Failed/error sessions pollute the profile with useless summaries |

### Medium Priority (Quality of life)

| # | Area | What's Missing |
|---|------|---------------|
| 5 | **Shared memory cleanup** | No integration with `cleanup_service.py` for TTL-based pruning |
| 6 | **Profile preview API** | No `GET /api/agents/{id}/profile` endpoint |
| 7 | **Forget API** | No way to delete a specific memory from an agent's profile |
| 8 | **Token budget estimation** | No check that profile + shared context fits within model limits |
| 9 | **Connector sync events** | No events emitted on the event bus for sync lifecycle |
| 10 | **Webhook receive endpoint** | The webhook connector needs a `POST /api/connectors/webhook/{token}` endpoint |

### Low Priority (Polish, future)

| # | Area | What's Missing |
|---|------|---------------|
| 11 | **Pipeline chaining UI** | Multi-step slice play builder in the dashboard |
| 12 | **Slice play session viewer** | Browse past play results |
| 13 | **Promote dynamic → static** | Elevate a fact so it doesn't get rotated out |
| 14 | **Profile and fact audit events** | `record_activity()` calls for profile mutations |
| 15 | **Plugin hot-reload API** | `POST /api/connectors/reload` |
| 16 | **Cascade facts on agent delete** | Clean up shared memory when an agent is removed |
| 17 | **Fact provenance in dashboard** | Show "agent A learned this fact on June 12" |

---

## 9. The Complete File Change Map (PLAN + Gaps)

This merges what the PLAN covers with what's missing.

```
LEGEND:
  ✅  = Covered in PLAN
  ⚠️  = Mentioned but incomplete
  ❌  = Not in PLAN at all

BACKEND — Python

  pi_orchestrator/database.py
    ✅  Add profile_json column + CRUD
    ✅  Add connectors + connector_sync_log tables + CRUD
    ❌  Add get_agent_profile_audit() — track when facts added
    ❌  Add connector CRUD for delete_connector
    ❌  Add connector update method

  pi_orchestrator/models.py
    ✅  Add SkillParameter, SkillSchema
    ❌  Add ConnectorCreate, ConnectorSummary, ConnectorDetail models
    ❌  Add AgentProfileResponse model
    ❌  Add SlicePlaySession model

  pi_orchestrator/services/agent_profile_service.py
    ✅  Create file with format_profile_as_prompt(), extract_session_summary()
    ❌  Add profile_to_json() — direct JSON access for GET API
    ❌  Add forget_profile_fact() — remove specific memory

  pi_orchestrator/services/shared_memory_service.py
    ✅  Create file with write_fact(), read_context(), deduplicate_facts()
    ❌  Add cleanup_expired_facts() — TTL-based pruning
    ❌  Add get_fact_count(tag) — metrics
    ❌  Add delete_agent_facts(agent_id) — cascade on agent delete
    ❌  Add list_tags() — discover which tags have facts

  pi_orchestrator/services/pi_session_service.py
    ✅  Inject profile context at session start
    ✅  Inject shared context at session start
    ✅  Append session summary on completion
    ❌  Guard: only append summary if session completed successfully
    ❌  Guard: truncate context if approaching token limit
    ❌  Emit event_bus event for profile update

  pi_orchestrator/routers/skills.py
    ✅  Replace regex parser with yaml.safe_load
    ✅  Return inputs, outputs, triggers in response
    ❌  Add GET /api/skills/{skill_name} — single skill detail with full schema

  pi_orchestrator/routers/coms.py
    ✅  Add recent_facts, fact_count to peer response
    ❌  Add tag-based filtering: GET /api/coms?tag=infra

  pi_orchestrator/services/connectors/
    ✅  Create _base.py, registry.py, builtins/__init__.py, builtins/webhook.py
    ❌  Create engine.py — sync engine that drives plugin.sync() on schedule
    ❌  Create engine.py — POST /api/connectors/{id}/sync handler

  pi_orchestrator/routers/connectors.py
    ⚠️  Create file with CRUD endpoints
    ❌  Add POST /api/connectors/{id}/sync — trigger manual sync
    ❌  Add POST /api/connectors/webhook/{token} — webhook receive endpoint
    ❌  Add POST /api/connectors/reload — hot-reload plugins

  pi_orchestrator/main.py
    ✅  Register connectors router
    ❌  Initialize sync engine on startup

  pi_orchestrator/services/schedule_service.py
    ❌  Hook connector get_schedule() into cron system
    ❌  Register auto-sync jobs for connectors that have schedules

  pi_orchestrator/services/cleanup_service.py
    ❌  Add shared memory TTL pruning
    ❌  Add connector_sync_log retention

FRONTEND — Vue 3

  dashboard/src/components/AgentDetail.vue
    ❌  Add "Connectors" tab
    ❌  Add "Profile" section in Info tab (show fact count, recent memories)

  dashboard/src/components/SlicePlaysPanel.vue
    ❌  Parameter form renders from SKILL.md inputs
    ❌  Pipeline builder UI (add step, chain steps)
    ❌  Output display (show structured results, not raw chat)
    ❌  Session history for past plays

  dashboard/src/components/ComsPanel.vue
    ❌  Show recent facts per peer
    ❌  Click peer → show full shared context
    ❌  "Inject this context" button

  dashboard/src/views/Settings.vue
    ❌  Add Connectors section (list configured connectors, status, sync now)

INFRASTRUCTURE

  Tests
    ❌  Test shared_memory_service.py — write, read, dedup, cleanup
    ❌  Test connector plugin discovery + registry
    ❌  Test profile injection in pi_session_service
    ❌  Test skills.py with rich YAML frontmatter
    ❌  Test knowledge.jsonl corruption recovery
    ❌  Test connector CRUD API endpoints
    ❌  Test profile CRUD API endpoints
```

---

## 10. What This Means for the Plan

The PLAN-maestro-execution.md is correct as a **Phase 1 backend foundation**. It builds the storage layer, the injection mechanism, and the plugin framework. But it's about **60% of the total work** needed for these features to be usable from the dashboard.

| Layer | PLAN Coverage | Remaining |
|-------|---------------|-----------|
| Storage (DB, files, models) | ✅ 80% | Connector delete/update, profile audit |
| Backend services | ✅ 60% | Sync engine, cleanup, forget API, webhook endpoint |
| Backend API routes | ✅ 50% | Connector sync, profile GET, webhook receive |
| Frontend components | ❌ 0% | All of it — forms, tabs, panels, settings page |
| Infrastructure (tests, events) | ❌ 5% | Tests for everything new, event bus integration |
| Monitoring & Ops | ❌ 0% | Metrics, alerts, health endpoint extensions |
