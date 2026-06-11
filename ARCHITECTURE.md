# Slice of Pi — Architecture

## System Overview

Slice of Pi is a single-user web dashboard for managing multiple pi coding agents.
All services run on localhost, bound to port 8420.

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

- **Router**: 14 routes (dashboard, agents, sessions, console, replay, audit, ops, settings, login, etc.)
- **State**: Pinia stores (`app`, `auth`, `notifications`)
- **Styling**: Tailwind CSS with custom design tokens in `tailwind.config.js`
- **Navigation**: Sticky top nav bar with primary links + "More" dropdown. Retractable sidebar with logo, saved views, and system info. Mobile hamburger menu.

### Component Architecture

```
App.vue
├── NavIsland.vue           # Top nav (primary links, More dropdown, telemetry, voice, user menu)
├── Sidebar.vue             # Retractable sidebar (logo, saved views, system info)
├── Router views            # 14 page views
│   ├── Dashboard.vue       # Stats, agent grid, activity feed, ops queue
│   ├── Agents.vue          # Agent CRUD, search, filters
│   ├── Sessions.vue        # Session history + replay timeline toggle
│   ├── Console.vue         # Live orchestrator log stream
│   ├── ...                 # Settings, Audit, Ops, Replay, etc.
└── AgentDetail.vue         # Agent overlay (chat, terminal, files, git, credentials, etc.)
    ├── ChatPanel.vue       # SSE chat with rich markdown bubbles
    ├── TerminalPanel.vue   # xterm.js PTY terminal via WebSocket
    ├── VoiceWorkspace.vue  # Browser speech-to-text + text-to-speech
    ├── InfoPanel.vue       # Read-only agent info
    ├── GitPanel.vue        # GitHub push/pull/commit
    ├── FileManager.vue     # Browse/upload/preview files
    └── ...
```

## Backend (FastAPI + SQLite)

### API Routes (~90+)

| Prefix | Modules | Purpose |
|--------|---------|---------|
| `/api/agents` | agents, chat, credentials, files, git, sharing, tags | Agent CRUD + per-agent features |
| `/api/sessions` | sessions | Session history, export, fork |
| `/api/schedules` | schedules | Cron-based execution |
| `/api/auth` | auth | JWT login/register |
| `/api/audit-log` | audit_log | Event trail |
| `/api/ops` | ops | Fleet operations (stop-all, scheduler pause) |
| `/api/telemetry` | telemetry | Host CPU/RAM/disk |
| `/api/console` | console | Live log tail |
| `/api/operator-queue` | operator_queue | Human-in-loop items |
| `/api/system` | system | Version, models, chat, extensions |
| `/api/*` | mcp_keys, tags, coms, teams, templates, skills, extensions, settings, users | Miscellaneous |
| `/ws/*` | events, logs, terminal, voice | WebSocket endpoints |

### WebSocket Architecture

4 WebSocket endpoints, all authenticated via single-use 30-second tickets:

- `/ws/events` — Real-time agent lifecycle events (created, deleted, updated, session forked)
- `/ws/logs` — Live orchestrator log stream (tail -F)
- `/ws/terminal/{agent_id}` — PTY bridge to pi session (xterm.js)
- `/ws/voice/{agent_id}` — Voice session state sync

### Database

SQLite stored at `~/.pi/agent/orchestrator.db` with tables:
- `agents`, `sessions`, `activities` — Core agent/session tracking
- `schedules`, `schedule_executions` — Cron execution
- `credentials` — Encrypted API keys (Fernet AES-128)
- `mcp_keys` — MCP server keys
- `audit_log` — Event trail
- `operator_queue` — Human-in-loop items
- `users`, `agent_shares`, `access_requests` — Multi-user auth
- `tags`, `agent_tags` — Agent tagging
- `settings` — Key-value config

### Services

- `pi_session_service.py` — Spawns pi as subprocess (`pi --mode json --session <file>`)
- `system_chat_service.py` — Voice intent parser (create/delete/list agents, navigate)
- `ws_ticket_service.py` — Single-use 30-second WebSocket auth tickets
- `git_service.py` — Git init/status/commit/push/pull via subprocess
- `audit_service.py` — Structured event logging
- `cleanup_service.py` — Periodic session/event pruning

## Launch Flow

```
./slices
  │
  ├── Check Python dependencies (fastapi, uvicorn, etc.)
  ├── npm install (if needed)
  ├── vite build (production bundle)
  │
  └── PI_NO_AUTH=1 python3 start-orchestrator.py --serve-dashboard
        │
        ├── SQLite init (auto-creates tables)
        ├── FastAPI app starts on port 8420
        ├── Serves static dashboard at /
        └── API at /api/*, WebSocket at /ws/*
```

## Design System

See [DESIGN.md](./DESIGN.md) for brand colors, typography, spacing, input styles, and glass/blur effects.

## Productization

See [PRODUCTIZATION_PATH.md](./PRODUCTIZATION_PATH.md) for the roadmap to multi-user, open source, and commercial deployment.
