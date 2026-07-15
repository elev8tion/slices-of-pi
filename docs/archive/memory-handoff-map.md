# Remaining Work — Memory System & Handoff Map

> Every feature flows through the same architecture: **Store → Inject → Sync → Cleanup**.
> This map traces each remaining feature through the existing handoff points,
> showing exactly where new handoffs need to be inserted to make them native.

---

## The Core Loop (Already Built)

```
┌────────────────────────────────────────────────────────┐
│                    THE MEMORY LOOP                      │
│                                                        │
│  1. STORE                                              │
│     agent session ends → append_agent_memory()        │
│     connector syncs    → write_fact()                 │
│     webhook fires      → write_fact()                 │
│                                                        │
│  2. INJECT                                             │
│     agent session starts → format_profile_as_prompt() │
│                            read_context()              │
│                            → appended to system_prompt │
│                                                        │
│  3. SYNC (MISSING)                                     │
│     connector engine → plugin.sync() → write_fact()   │
│                                                        │
│  4. CLEANUP (MISSING)                                   │
│     cleanup_service → cleanup_expired_facts()          │
│                      → delete_agent_facts()            │
└────────────────────────────────────────────────────────┘
```

---

## Feature 1: Connector Sync Engine

**The problem:** Connectors are configured and stored, but nothing calls `plugin.sync()`.
They're decorative — they exist in the DB but never produce data.

### The intended handoff chain

```
Time-based trigger (every N minutes)
         │
         ▼
  SyncEngine._auto_sync_loop()       ← NEW: background loop
         │
         ├── db.list_connectors(enabled_only=True)
         │       ↓
         │   For each connector:
         │       │
         │       ├── registry.get(connector.provider)
         │       │       ↓
         │       │   plugin = WebhookConnector / GoogleDriveConnector / etc.
         │       │
         │       ├── db.get_connector(connector.id)
         │       │       ↓
         │       │   auth_state = decrypted Fernet token
         │       │
         │       ├── plugin.sync(auth_state, since=last_sync_at)
         │       │       ↓
         │       │   docs = [{id, title, content, url, type, updated_at}, ...]
         │       │
         │       ├── write_fact(agent_id, tag, doc.title, "document", {url, type})
         │       │       ↓
         │       │   Each doc → fact in shared knowledge pool ← NATIVE
         │       │
         │       ├── db.update_connector(last_sync_at, last_sync_status)
         │       │
         │       └── event_bus.publish("connector_sync_completed", {
         │               connector_id, provider, status: "success", items: len(docs)
         │           })                                          ← NATIVE (event bus pattern)
         │
         └── Sleep 60s, repeat
```

### Handoffs to create (3)

| Handoff | Type | From | To | Code |
|---------|------|------|----|------|
| `H1` | Background loop | `SyncEngine` | `connector` rows in DB | `list_connectors(enabled_only=True)` |
| `H2` | Plugin execution | `SyncEngine` | `registry.get().sync()` | `await plugin.sync(auth, since)` |
| `H3` | Fact persistence | `SyncEngine` | `write_fact()` | `write_fact(agent_id, tag, title, "document", meta)` |
| `H4` | Event notification | `SyncEngine` | `event_bus.publish()` | `event_bus.publish("connector_sync_*", data)` |
| `H5` | Manual trigger | `POST /api/connectors/{id}/sync` | `SyncEngine.sync_one()` | New REST endpoint |

### Why it's native

The sync engine writes through `write_fact()` — the **same function** that agent sessions use to contribute to the shared knowledge pool. Connector data and agent-learned data flow through the same pipeline: `write_fact → knowledge.jsonl → read_context → system prompt injection`. No separate storage, no special handling.

---

## Feature 2: Webhook Receive Endpoint

**The problem:** The `WebhookConnector` is a built-in plugin, but there's no HTTP endpoint
to POST data into. The connector's `sync()` returns `[]` because webhooks are push-based.

### The intended handoff chain

```
External service POSTs JSON to /api/connectors/webhook/{token}
         │
         ▼
  connectors.py router                                 ← NEW: POST endpoint
         │
         ├── Find connector by matching auth_state.token
         │       ↓
         │   db.get_connector_by_token(token)           ← NEW: DB lookup
         │
         ├── Parse request body
         │
         ├── write_fact(agent_id, tag, body.title || body.snippet, "webhook", {
         │       source: "webhook",
         │       url: body.url,
         │       content_type: body.type
         │   })                                          ← NATIVE: uses write_fact()
         │
         └── Return 200 OK
```

### Handoffs to create (2)

| Handoff | Type | From | To | Code |
|---------|------|------|----|------|
| `H6` | HTTP receive | `POST /webhook/{token}` | DB token lookup | `db.get_connector_by_token()` |
| `H7` | Fact write | Router | `write_fact()` | Direct call — reuses existing |

### Native integration

The webhook writes directly into the **shared knowledge pool** via `write_fact()`. The data then appears in agent sessions automatically via `read_context()`. No separate storage path.

---

## Feature 3: Profile View & Forget API

**The problem:** Agent profiles are stored and injected, but there's no way to
see what an agent knows or delete a specific fact. The data is invisible and
immutable to the user.

### The intended handoff chain

```
GET /api/agents/{id}/profile                            ← NEW: profile endpoint
         │
         ▼
  New profile router                                      ← NEW
         │
         ├── db.get_agent_profile(agent_id)
         │       ↓
         │   Returns {"static": {...}, "dynamic": [...]}
         │
         ├── Format for display
         │       ↓
         │   {static_count, dynamic_count, last_updated, recent_facts[5]}
         │
         └── Return to dashboard

DELETE /api/agents/{id}/profile/fact                     ← NEW: forget endpoint
         │
         ▼
  Profile router
         │
         ├── body = {fact: "Session #42: reviewed PR..."}
         │
         ├── db.get_agent_profile(agent_id)
         ├── Remove matching fact from dynamic[]
         ├── db.update_agent_profile(agent_id, modified_profile)
         │
         ├── event_bus.publish("profile_updated", {
         │       agent_id, action: "fact_removed"
         │   })                                          ← NATIVE: event bus pattern
         │
         └── Return 200 OK
```

### Handoffs to create (2)

| Handoff | Type | From | To | Code |
|---------|------|------|----|------|
| `H8` | Profile read | `GET /api/agents/{id}/profile` | `db.get_agent_profile()` | Route → DB — 3 lines |
| `H9` | Fact deletion | `DELETE /api/agents/{id}/profile/fact` | `db.update_agent_profile()` | Route → DB — 10 lines |

### Native integration

Reuses `get_agent_profile()` / `update_agent_profile()` that already exist. The profile data format is the same one injected into agent prompts — what you see in the API is exactly what the agent sees.

---

## Feature 4: Unified Tags System

**The problem:** Two conflicting tag systems. The code uses `agent.tags` as a JSON
string column (added in the P0 fix), but the DB schema has a proper many-to-many
`tags` + `agent_tags` table that's never written to.

### The intended handoff chain

```
Tags router receives PATCH /api/agents/{id}/tags
         │
         ▼
  Current:  db.update_agent(agent_id, tags=cleaned)     ← JSON column approach
         │
  Should also: write to tags + agent_tags tables         ← NATIVE: use existing schema
         │
         ├── Upsert tag names into tags table
         ├── Replace agent_tags rows for this agent
         ├── Keep agent.tags JSON column in sync (for backward compat)
         │
         └── event_bus.publish("agent_updated", {
                 agent_id, fields: ["tags"]
             })                                          ← Already exists! (tags.py:72)
```

### Handoffs to fix (1)

| Handoff | Type | From | To | Code |
|---------|------|------|----|------|
| `H10` | Tag sync | `db.update_agent(tags=...)` | `tags` + `agent_tags` tables | ~15 lines in `database.py` |

### Native integration

The many-to-many tables already exist in `SCHEMA` — they just need to be populated. Once they are, `db.get_agent()` can join them, and the tags API becomes queryable (e.g. "find all agents tagged 'frontend'") instead of scanning every agent row.

---

## Feature 5: Cleanup Service Hooks

**The problem:** `cleanup_service._cleanup_once()` runs every 6 hours but only
cleans session JSONL files. The shared knowledge pool grows unbounded.

### The intended handoff chain

```
cleanup_service._cleanup_once()     ← Already runs every 6h
         │
         ├── ... existing session cleanup ...
         │
         ├── NEW: shared_memory_service.cleanup_expired_facts()    ← Already exists
         │       ↓
         │   Scans all tags/*/knowledge.jsonl
         │   Removes entries > 30 days old
         │   Rewrites each file in-place
         │   Returns count of purged facts
         │
         ├── NEW: db.prune_connector_sync_logs()                   ← Already exists
         │       ↓
         │   Removes sync log entries > 30 days old
         │
         └── Log: "Cleanup: purged N expired facts, M sync log entries"
```

### Handoffs to create (1)

| Handoff | Type | From | To | Code |
|---------|------|------|----|------|
| `H11` | Cleanup hook | `_cleanup_once()` | `cleanup_expired_facts()` | 3 lines — call existing function |

### Native integration

The function `cleanup_expired_facts()` already exists in `shared_memory_service.py` (line 140). The cleanup loop already exists in `cleanup_service.py` (line 74). They just need to be connected — a 3-line handoff.

---

## Feature 6: Connector Sync Events

**The problem:** The event bus publishes `agent_created`, `agent_deleted`,
`agent_updated` — but nothing for connector sync lifecycle. The dashboard
can't show real-time sync status.

### The intended handoff chain

```
SyncEngine completes a sync
         │
         ▼
  event_bus.publish("connector_sync_started", {
      connector_id, provider, timestamp
  })
         │
         ▼
  ... sync runs ...
         │
         ▼
  event_bus.publish("connector_sync_completed", {
      connector_id, provider, status: "success",
      items: 14, duration_ms: 3200
  })
         │
         ▼
  Dashboard receives via /ws/events     ← Already exists
         │
         ▼
  Updates connector status in real-time  ← NEW: frontend handler
```

### Handoffs to create (1)

| Handoff | Type | From | To | Code |
|---------|------|------|----|------|
| `H12` | Sync events | `SyncEngine` | `event_bus.publish()` | 3 lines — same pattern as agents.py:106 |

### Native integration

Reuses the exact same `event_bus.publish()` / `/ws/events` WebSocket pipeline
that already streams `agent_created` and `agent_deleted` events to the dashboard.

---

## Summary: All Remaining Handoffs

| # | Feature | New Code | Lines | Reuses |
|---|---------|----------|-------|--------|
| **H1-H5** | Connector sync engine | ~120 lines | `engine.py`, modify `routers/connectors.py` | `write_fact()`, `event_bus.publish()`, existing DB CRUD |
| **H6-H7** | Webhook endpoint | ~30 lines | Add to `routers/connectors.py` | `write_fact()`, existing token lookup pattern |
| **H8-H9** | Profile view & forget | ~40 lines | New router `routers/profile.py` | `get_agent_profile()`, `update_agent_profile()` |
| **H10** | Unified tags | ~15 lines | Modify `database.py` | Existing `tags` + `agent_tags` tables |
| **H11** | Cleanup hook | ~3 lines | Modify `cleanup_service.py` | `cleanup_expired_facts()` already exists |
| **H12** | Sync events | ~3 lines | Add to `engine.py` | `event_bus.publish()` pattern from `agents.py` |
| **Tests** | Coverage for all new services | ~200 lines | New test files | Existing pytest fixtures and patterns |

### The pattern

Every remaining feature **reuses existing infrastructure**:

```
All data → write_fact() → shared knowledge pool → read_context() → agent prompts
All events → event_bus.publish() → /ws/events → dashboard
All cleanup → cleanup_service._cleanup_once() → one more function call
```

Nothing needs a new storage system, a new event pipeline, or a new worker framework.
They're all handoffs into the loop that already exists.
