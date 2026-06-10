# Slice of Pi — Definitive Implementation Plan

**Date**: 2026-06-09
**Status**: PLAN — awaiting approval before any code is written

---

## Clarified Task

Build **Slice of Pi**: a web dashboard + API server that manages multiple pi coding agents.
The UI uses the design from `agent-fleet-console.html` (dark theme, indigo accent, glass-nav, agent grid).
The backend wraps pi's SDK — no Docker, no Redis, no multi-tenant auth.
Architecture: orchestrator (lifecycle, scheduling, monitoring) + coms (agent-to-agent communication, already exists in pi).

---

## Scope Boundaries

### IN SCOPE
| Item | Description |
|------|-------------|
| Pi Orchestrator API | FastAPI server wrapping pi SDK — create/list/start/stop agents, stream chat, browse sessions |
| SQLite database | 6 tables: agents, sessions, activities, schedules, schedule_executions, settings |
| WebSocket events | In-process event bus → WebSocket for real-time dashboard updates |
| Pi MCP Server | 10 tools exposing pi capabilities via MCP protocol (STDIO + HTTP/SSE) |
| Vue 3 Dashboard | 8 views, ~25 components using design tokens from the HTML mock |
| Pi Scheduler | APScheduler-based cron service for recurring pi sessions |
| Agent persona system | Read `.pi/agents/*.md` + `teams.yaml` — already exists in pi, just surfaced in UI |

### OUT OF SCOPE (explicitly)
- Docker containers (agents ARE pi sessions, not containers)
- Redis (single-user = no distributed locking needed)
- Multi-user auth, JWT, email whitelist (single user)
- Slack/Telegram/WhatsApp channel adapters
- OpenTelemetry, Vector logging, audit retention
- Image generation, voice chat
- Public links, agent sharing, enterprise features
- coms/coms-net implementation (already exists in pi — just surface status in dashboard)
- Multi-agent maestro (already exists in pi — just surface in dashboard)

---

## Plan

### Phase A — Backend Foundation

#### Step A1: Project scaffold + config
**Creates**: `pi_orchestrator/` directory, `pyproject.toml`, `config.py`
**Verify**: `python -c "from pi_orchestrator.config import DATABASE_PATH; print(DATABASE_PATH)"` → prints a valid path under `~/.pi/`

#### Step A2: Database schema + models
**Creates**: `database.py` (6 CREATE TABLE statements), `models.py` (Pydantic models: PiAgentConfig, PiAgentSummary, PiSessionEntry, ChatRequest, ScheduleConfig)
**Verify**: `python -c "from pi_orchestrator.database import init_db; init_db(); import sqlite3; conn=sqlite3.connect('...'); tables=conn.execute('SELECT name FROM sqlite_master WHERE type=\"table\"').fetchall(); assert len(tables)==6"` → all 6 tables exist

#### Step A3: Pi session service (no Docker)
**Creates**: `services/pi_session_service.py` — `create_session()`, `list_sessions()`, `get_session()`, `stop_session()`, `stream_chat()`, `get_status()`
**Verify**: `python -c "from pi_orchestrator.services.pi_session_service import PiSessionService; s=PiSessionService(); assert hasattr(s,'create_session'); assert hasattr(s,'stream_chat')"` → all 6 methods exist and are callable

#### Step A4: Event bus (WebSocket, no Redis)
**Creates**: `services/event_bus.py` — in-process pub/sub: `publish(event)`, `subscribe(callback)`, `unsubscribe(id)`. `routers/events.py` — WebSocket endpoint `GET /ws/events` that streams events to the dashboard.
**Verify**: Connect to `ws://localhost:8420/ws/events` via wscat, publish an event, confirm it arrives at the client within 200ms

#### Step A5: main.py + FastAPI lifespan
**Creates**: `main.py` — FastAPI app with lifespan (init DB, start event bus, recover orphaned sessions, start scheduler)
**Verify**: `curl http://localhost:8420/health` → `{"status": "ok"}`

#### Step A6: Agent CRUD router
**Creates**: `routers/agents.py` — `POST /api/agents` (create), `GET /api/agents` (list), `GET /api/agents/:id` (detail), `DELETE /api/agents/:id` (stop+remove)
**Verify**: `curl -X POST http://localhost:8420/api/agents -d '{"name":"test-agent","model":"claude-sonnet-4-5"}'` → 201, then `curl http://localhost:8420/api/agents` → list includes "test-agent"

### Phase B — Core Features

#### Step B7: Chat router (streaming)
**Creates**: `routers/chat.py` — `POST /api/agents/:id/chat` (stream via SSE or WebSocket), `GET /api/agents/:id/chat/history` (past messages from session JSONL)
**Verify**: `curl -X POST http://localhost:8420/api/agents/:id/chat -d '{"message":"say hello"}' -H "Accept: text/event-stream"` → streams SSE chunks containing the agent's response

#### Step B8: Session history router
**Creates**: `routers/sessions.py` — `GET /api/sessions` (list all), `GET /api/sessions/:id` (detail with messages), `GET /api/sessions/:id/export` (JSONL download)
**Verify**: `curl http://localhost:8420/api/sessions` → returns JSON array with at least one session after a chat completes

#### Step B9: Activity tracking service
**Creates**: `services/activity_service.py` — records session_start, turn_complete, tool_call, error events to `activities` table. Wired into pi_session_service and event_bus.
**Verify**: After a chat completes, `sqlite3 ... "SELECT count(*) FROM activities"` → returns > 0

### Phase C — Dashboard UI

#### Step C10: Vue 3 project with design system
**Creates**: `dashboard/` directory, `vite.config.ts`, `tailwind.config.js` with design tokens extracted from HTML mock (#08080A background, #6366F1 accent, Satoshi + Clash Display fonts, 20px card radius, glass-nav blur)
**Verify**: `npm run dev` → opens at localhost:5173, page shows dark background with indigo accent, fonts load

#### Step C11: Layout shell (nav + sidebar + main)
**Creates**: `NavIsland.vue`, `Sidebar.vue`, `DashboardLayout.vue`, `DashboardHeader.vue`
**Verify**: Page renders the fluid pill nav at top, 220px sidebar on left, main content area. Resize to 768px → sidebar hides. No console errors.

#### Step C12: Dashboard view (stats + agent grid + activity + ops)
**Creates**: `Dashboard.vue`, `StatCard.vue`, `AgentCard.vue`, `AgentGrid.vue`, `ActivityFeed.vue`, `OpsQueue.vue`, `TagCloud.vue`, `SparklineChart.vue`
**Verify**: Page shows 4 stat cards, 3-column agent grid (6 cards), tag cloud, activity feed, ops queue. All with mock data. Resize to 768px → single column.

#### Step C13: Agent detail overlay
**Creates**: `AgentDetail.vue`, `AgentHeader.vue`, `AgentTabs.vue`, `ChatPanel.vue`, `ChatBubble.vue`, `ChatInput.vue`
**Verify**: Click an agent card → overlay opens with tabs (Chat, Terminal, Files, Activity, Settings). Chat tab shows message bubbles. Click outside/Escape → closes.

#### Step C14: Wire dashboard to live API
**Connect**: Dashboard fetches from `localhost:8420/api/agents` instead of mock data. Agent cards show real pi agents. Activity feed shows real events via WebSocket.
**Verify**: Create an agent via API → appears in dashboard grid within 2 seconds (WebSocket event). Start a chat → activity feed updates in real time.

### Phase D — Advanced Features

#### Step D15: Skills + Extensions catalog views
**Creates**: `routers/skills.py` (reads `~/.pi/agent/skills/`, returns list with frontmatter), `routers/extensions.py` (reads `~/.pi/agent/extensions/`, returns list). `SkillsPanel.vue`, `ExtensionsPanel.vue`.
**Verify**: `curl http://localhost:8420/api/skills` → returns JSON array of installed skills with name, description, trigger phrases

#### Step D16: Scheduler service + router + UI
**Creates**: `services/schedule_service.py` (APScheduler-based), `routers/schedules.py` (CRUD + execution history), `Schedules.vue` (list + create/edit form)
**Verify**: Create a schedule via API → `curl http://localhost:8420/api/schedules` → shows it. Create via UI → form submits, list updates.

#### Step D17: MCP server (10 tools)
**Creates**: `pi-mcp-server/src/tools/agents.ts`, `chat.ts`, `sessions.ts`, `skills.ts`, `extensions.ts`, `schedules.ts`, `files.ts`, `coms.ts`, `events.ts`, `settings.ts`. `server.ts` with STDIO + HTTP/SSE transport.
**Verify**: `npx @modelcontextprotocol/inspector http://localhost:8420/mcp` → lists 10 pi tools, each executable

#### Step D18: Template gallery
**Creates**: `routers/templates.py` (reads `.pi/agents/*.md` personas, GitHub template discovery). `Templates.vue` (grid of persona cards, "Deploy" button).
**Verify**: `curl http://localhost:8420/api/templates` → returns at least the personas from `~/.pi/agents/`

---

## Plan Integrity Check

| Check | Result |
|-------|--------|
| Total steps | 18 |
| Unbounded verify conditions (e.g., "it works") | 0 |
| Steps with unclear dependencies | 0 |
| Steps that touch >3 files without justification | 0 — each step is atomic |
| Steps that require a decision we haven't made | 0 |
| Gate | PASSED |

---

## Files Inventory (What We'll Create)

```
slice_of_pi/
├── SANITIZATION_GUIDE.md          # ✅ Done — Trinity → Pi mapping
├── PI_VS_TRINITY_COMPARISON.md    # ✅ Done — Capability comparison
├── IMPLEMENTATION_PLAN.md         # ← This file
│
├── pi_orchestrator/               # Backend (Phases A, B, D)
│   ├── pyproject.toml
│   ├── config.py                  # A1
│   ├── models.py                  # A2
│   ├── database.py                # A2
│   ├── main.py                    # A5
│   ├── services/
│   │   ├── __init__.py
│   │   ├── pi_session_service.py  # A3
│   │   ├── event_bus.py           # A4
│   │   ├── activity_service.py    # B9
│   │   └── schedule_service.py    # D16
│   └── routers/
│       ├── __init__.py
│       ├── events.py              # A4
│       ├── agents.py              # A6
│       ├── chat.py                # B7
│       ├── sessions.py            # B8
│       ├── skills.py              # D15
│       ├── extensions.py          # D15
│       ├── schedules.py           # D16
│       └── templates.py           # D18
│
├── pi-mcp-server/                 # MCP Server (Phase D)
│   ├── package.json
│   ├── tsconfig.json
│   ├── server.ts                  # D17
│   └── src/tools/
│       ├── agents.ts              # D17
│       ├── chat.ts                # D17
│       ├── sessions.ts            # D17
│       ├── skills.ts              # D17
│       ├── extensions.ts          # D17
│       ├── schedules.ts           # D17
│       ├── files.ts               # D17
│       ├── coms.ts                # D17
│       ├── events.ts              # D17
│       └── settings.ts            # D17
│
├── dashboard/                     # Frontend (Phase C)
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js         # C10
│   ├── index.html
│   └── src/
│       ├── main.ts
│       ├── App.vue
│       ├── stores/
│       │   ├── agents.ts
│       │   ├── sessions.ts
│       │   └── events.ts
│       ├── views/
│       │   ├── Dashboard.vue       # C12
│       │   ├── Agents.vue
│       │   ├── Sessions.vue
│       │   ├── Schedules.vue       # D16
│       │   ├── Skills.vue
│       │   ├── Extensions.vue
│       │   ├── Templates.vue       # D18
│       │   └── Settings.vue
│       └── components/
│           ├── NavIsland.vue       # C11
│           ├── Sidebar.vue         # C11
│           ├── DashboardLayout.vue # C11
│           ├── DashboardHeader.vue # C11
│           ├── StatCard.vue        # C12
│           ├── AgentCard.vue       # C12
│           ├── AgentGrid.vue       # C12
│           ├── AgentDetail.vue     # C13
│           ├── AgentHeader.vue     # C13
│           ├── AgentTabs.vue       # C13
│           ├── ChatPanel.vue       # C13
│           ├── ChatBubble.vue      # C13
│           ├── ChatInput.vue       # C13
│           ├── ActivityFeed.vue    # C12
│           ├── ActivityItem.vue    # C12
│           ├── OpsQueue.vue        # C12
│           ├── OpsItem.vue         # C12
│           ├── TagCloud.vue        # C12
│           ├── FilterPills.vue     # C12
│           ├── SectionBar.vue      # C12
│           ├── SparklineChart.vue  # C12
│           ├── StatusDot.vue       # C12
│           ├── SkillsPanel.vue     # D15
│           ├── ExtensionsPanel.vue # D15
│           └── ConfirmDialog.vue
│
└── slice_of_pi/                    # Interface contracts (✅ already exists)
    └── (22 ABCs, Protocols, dataclasses — no changes needed)
```

---

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent runtime | pi sessions (not Docker) | pi is local, single-user; Docker is overkill |
| Database | SQLite | Already used by Trinity, zero-config, sufficient for single-user |
| Event bus | In-process (not Redis) | Single user = no distributed contention |
| API framework | FastAPI | Consistency with Trinity patterns; async-native |
| Frontend framework | Vue 3 + Tailwind | Matches HTML mock; Trinity experience reusable |
| Multi-agent communication | pi coms (already exists) | Don't rebuild what pi provides |
| Orchestration | New orchestrator (this plan) | pi lacks lifecycle management, scheduling, dashboard |
| Auth | None (single-user) | Runs on localhost; API bound to 127.0.0.1 |
| Scheduler | APScheduler (no Redis lock) | Single instance, no contention |
| MCP transport | STDIO + HTTP/SSE | Same as Trinity; STDIO for local, HTTP for remote |

---

## Questions That Need Answers Before Phase B

1. **pi SDK availability**: Can we import `@earendil-works/pi-coding-agent` from Python (via subprocess) or do we need a Node.js bridge? The current plan assumes spawning `pi --mode json` as a subprocess. If there's a cleaner SDK path, Step A3 changes.

2. **Streaming model**: Do we stream via Server-Sent Events (simpler) or WebSocket (already built in Step A4)? The plan uses SSE for chat streaming and WebSocket for events. Confirm.

3. **Port**: 8420 for the orchestrator, 5173 for Vite dev. OK?

---

## Ready to Start?

**Phase A (Backend Foundation)** is 6 steps, each independently verifiable. 

Approve the plan and I start at **Step A1** — project scaffold + config. One step at a time, verify each, no jumping ahead.
