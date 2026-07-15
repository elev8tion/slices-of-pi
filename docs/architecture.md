# Slice of Pi — Architecture

Living architecture doc.  
**Product direction (binding):** [PRODUCT_INTENT.md](./PRODUCT_INTENT.md) — local single-operator; **not** SaaS/multi-tenant.  
**Codebase inventory:** [PROJECT_STATE.md](../PROJECT_STATE.md).

## System Overview

Slice of Pi is a **local, single-operator** web dashboard for managing multiple **pi** coding agents on one machine.
Services bind to localhost (default port **8420**). No Docker, no Redis as core infrastructure.

```
┌──────────────┐     WebSocket / HTTP      ┌──────────────────┐
│   Browser    │ ◄──────────────────────►  │   FastAPI Server  │
│  (Vue 3 +    │                           │   (port 8420)    │
│   xterm.js)  │                           │                  │
└──────────────┘                           │  ┌────────────┐  │
                                           │  │  Event Bus │  │
                                           │  │  (in-proc) │  │
                                           │  └────────────┘  │
                                           │         │        │
                                           │  ┌────────────┐  │
                                           │  │   SQLite    │  │
                                           │  │  (agents,   │  │
                                           │  │  sessions,  │  │
                                           │  │  audit, …)  │  │
                                           │  └────────────┘  │
                                           │         │        │
                                           │  ┌────────────┐  │
                                           │  │ pi binary   │  │
                                           │  │ (subprocess │  │
                                           │  │ per agent) │  │
                                           │  └────────────┘  │
                                           └──────────────────┘
```

## Frontend (Vue 3 + TypeScript)

- **Router**: 14 routes (`/`, `/agents`, `/sessions`, `/schedules`, `/skills`, `/extensions`, `/templates`, `/teams`, `/console`, `/ops`, `/replay`, `/audit`, `/settings`, `/login`)
- **State**: Pinia stores (`app`, `auth`, `notifications`)
- **Styling**: Tailwind CSS — tokens in `dashboard/tailwind.config.js` and [design.md](./design.md)
- **Auth guard**: Skips login when backend reports `PI_NO_AUTH` mode

### Component Architecture

```
App.vue
├── ToastContainer, OnboardingChecklist, EditorHelpPanel
└── Router views
    ├── Dashboard.vue
    ├── Agents.vue → AgentDetail (chat, terminal, files, git, voice, flixz, …)
    ├── Sessions, Schedules, Skills, Extensions, Templates, Teams
    ├── Console, OperatorRoom (/ops), Replay, AuditLog, Settings, Login
```

## Backend (FastAPI + SQLite)

### API surface (router modules in `pi_orchestrator/routers/`)

| Prefix / path | Modules | Purpose |
|---------------|---------|---------|
| `/api/agents` | agents, chat, profile, credentials, files, git, sharing, tags, flixz | Agent CRUD + per-agent features |
| `/api/sessions` | sessions | History, detail, export |
| `/api/schedules` | schedules | Cron CRUD |
| `/api/skills`, `/api/extensions`, `/api/templates` | skills, extensions, templates | Discovery / personas |
| `/api/teams`, `/api/coms`, `/api/connectors` | teams, coms, connectors | Multi-agent + peers + sync |
| `/api/auth`, `/api/users` | auth, users | JWT register/login; user list/search |
| `/api/audit-log`, `/api/ops`, `/api/operator-queue` | audit_log, ops, operator_queue | Trail, fleet ops, HITL |
| `/api/telemetry`, `/api/settings`, `/api/mcp-keys`, `/api/system` | telemetry, settings, mcp_keys, system | Host metrics, config, keys, system chat |
| `/api/activities`, `/api/flixz/*`, `/api/voice/*` | activities, flixz, voice | Feed, video frames, voice/TTS |
| `/api/ws/ticket` | ws_tickets | Single-use WS tickets |
| `/health` | main | Liveness + counts |
| `/ws/events`, `/ws/logs`, `/ws/terminal/{id}`, `/ws/voice/{id}` | events, console, terminal, voice | Real-time channels |

### WebSocket endpoints

- `/ws/events` — agent lifecycle / activity fan-out (in-process event bus)
- `/ws/logs` — live orchestrator logs
- `/ws/terminal/{agent_id}` — PTY bridge (xterm.js)
- `/ws/voice/{agent_id}` — voice session channel

Tickets: `POST /api/ws/ticket` (short-lived, single-use).

### Database

SQLite at `~/.pi/agent/orchestrator.db` (WAL). Tables include:

- Core: `agents`, `sessions`, `activities`
- Schedules: `schedules`, `schedule_executions`
- Auth/sharing: `users`, `agent_shares`, `access_requests`
- Security: `credentials`, `mcp_keys`, `audit_log`
- Ops: `operator_queue`, `tags`, `agent_tags`, `settings`
- Connectors: `connectors`, `connector_sync_log`
- Media: `flixz_runs`

### Services (`pi_orchestrator/services/`)

| Service | Role |
|---------|------|
| `pi_session_service` | Spawn `pi --mode json`, stream JSONL chat, process registry |
| `event_bus` | In-process pub/sub for dashboard clients |
| `schedule_service` | APScheduler cron → pi sessions |
| `cleanup_service` | GC old managed session files |
| `git_service` | Per-agent repos under `~/.pi/agent/repos/` |
| `audit_service` | Structured audit logging |
| `agent_profile_service` | Profile → system prompt injection |
| `shared_memory_service` | Cross-agent knowledge pool |
| `system_chat_service` | System/voice intents without self-HTTP |
| `voice_service` / `tts_service` | Voice pipeline; optional mossy TTS |
| `ws_ticket_service` | In-memory WS tickets |
| `flixz_service` / `frame_description_service` | ffmpeg frames; optional Gemini vision |
| `connectors/` | Plugin engine + webhook builtin |

### Related packages (not the main process)

| Path | Role |
|------|------|
| `slice_of_pi/` | Abstract ABCs — **not imported** by the orchestrator |
| `pi-mcp-server/` | Optional MCP STDIO bridge to this API |
| `pi-coding-agent/` | Extracted pi agent docs (reference only) |

## Launch Flow

```
./slices
  │
  ├── Check Python dependencies
  ├── npm install (if needed)
  ├── vite build → dashboard/dist
  │
  └── PI_NO_AUTH=1 python3 start-orchestrator.py --serve-dashboard
        │
        ├── ensure_directories + init_db
        ├── event_bus, connector sync_engine, scheduler, cleanup
        ├── FastAPI on 127.0.0.1:8420
        ├── Static dashboard at /
        └── API at /api/*, WebSocket at /ws/*
```

Alternate: `install.sh` runs API without forcing static dashboard and starts Vite on 5173.

## Design System

See [design.md](./design.md) for brand colors, typography, and UI tokens.

## Product boundaries

| This architecture | Not this architecture |
|-------------------|------------------------|
| One host, one operator (default) | Multi-tenant SaaS cloud |
| SQLite + in-process bus | Redis/cluster control plane as requirement |
| `pi` subprocesses | Docker/K8s agent fleet as the core model |
| Optional local auth/sharing | Commercial multi-tenant / billing product |

Rejected historical sketches (SaaS, Tier-4 enterprise): [archive/rejected/](./archive/rejected/).  
Do not treat them as roadmap.
