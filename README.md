# Slice of Pi

A web dashboard and API server for managing multiple pi coding agents.

Run `./slices` to start everything — a FastAPI backend serves the Vue 3 dashboard on `localhost:8420`, where you can create agents, chat with them, view session history, and control the whole system.

---

## Quick Start

```bash
./slices
```

Opens the dashboard at `http://localhost:8420`. No login required in single-user mode.

## Features

### Core
- **[Dashboard](/)** — agent grid with live status, stats, host telemetry, activity feed
- **[Agents](/agents)** — create, edit, tag, search, delete agents with model/tools/skills config
- **[Chat](/agents)** — SSE streaming chat with markdown, tool calls, file attach, session history
- **[Terminal](/agents)** — live pseudo-terminal to each agent via WebSocket + xterm.js
- **[Sessions](/sessions)** — session history with fork, export, replay timeline

### Productivity
- **[Slice Plays](/agents)** — one-click skill execution from the dashboard
- **[Credentials](/agents)** — encrypted API key storage per agent with env injection
- **[Git](/agents)** — GitHub-backed agent configs with commit/push/pull
- **[Tags](/agents)** — organize and filter agents by custom labels
- **[Model Selector](/agents)** — searchable model dropdown with provider badges

### Observability
- **[Audit Log](/audit)** — full event trail with filters, date range, CSV export
- **[System Console](/console)** — live log stream of the orchestrator
- **[Slice Operations](/settings)** — stop/restart all agents, scheduler controls
- **[Operator Queue](/ops)** — human-in-loop approval for agent requests
- **[Host Telemetry](/)** — CPU/RAM/Disk sparklines in the nav bar

### System
- **[Voice](/)** — system voice with intent parsing (create/delete/list agents, navigate pages)
- **[Voice Workspace](/agents)** — per-agent voice mode with Web Speech API
- **[Replay](/replay)** — zoomable timeline of agent session activity
- **[File Manager](/agents)** — browse/upload/preview agent workspace files
- **[YAML Editor](/settings)** — in-browser config editing with syntax highlighting
- **[MCP Keys](/settings)** — encrypted MCP server key management
- **[Notifications](/)** — real-time toasts on agent lifecycle events

### Collaboration
- **[Sharing](/agents)** — share agents by email with chat/admin permissions
- **[Teams](/teams)** — deploy multi-agent teams from `~/.pi/agents/teams.yaml`
- **[Schedules](/schedules)** — cron-based recurring agent execution
- **[Templates](/templates)** — persona templates and prompt template editing

---

## Architecture

```
Browser (Vue 3 + xterm.js)
    │  WebSocket / HTTP
    ▼
FastAPI (port 8420)
    │
    ├── SQLite (~/.pi/agent/orchestrator.db)
    ├── JSONL session files (~/.pi/agent/sessions/)
    ├── pi binary (subprocess per agent)
    └── Event bus (in-process WebSocket pub/sub)
```

- **Backend**: FastAPI with ~90+ API routes, SQLite, WebSocket event bus
- **Frontend**: Vue 3 + TypeScript + Pinia + Tailwind CSS
- **Design**: Dark theme with lime accent (`#9DD522`), transparent inputs with backdrop blur
- **Auth**: JWT-based with `PI_NO_AUTH=1` for single-user mode

See [DESIGN.md](./DESIGN.md) for the design system.
See [PRODUCTIZATION_PATH.md](./PRODUCTIZATION_PATH.md) for multi-user / SaaS roadmap.
See [FUTURE_TIER4.md](./FUTURE_TIER4.md) for enterprise features (Slack, Telegram, billing, fleet).

---

## Project Structure

```
├── pi_orchestrator/          # FastAPI backend
│   ├── main.py               # App entry, router registration
│   ├── config.py             # Paths, env vars
│   ├── database.py           # SQLite schema + CRUD
│   ├── models.py             # Pydantic models
│   ├── routers/              # 20+ API route modules
│   │   ├── agents.py, chat.py, sessions.py, ...
│   │   ├── tags.py, telemetry.py, console.py
│   │   ├── auth.py, users.py, sharing.py
│   │   ├── credentials.py, git.py, files.py
│   │   ├── operator_queue.py, ops.py, audit_log.py
│   │   ├── voice.py, terminal.py, mcp_keys.py
│   │   └── system.py, settings_router.py, ...
│   └── services/             # Backend services
│       ├── pi_session_service.py
│       ├── system_chat_service.py
│       ├── ws_ticket_service.py
│       ├── git_service.py
│       └── audit_service.py
├── dashboard/                # Vue 3 frontend
│   ├── src/
│   │   ├── components/       # 40+ Vue components
│   │   │   ├── chat/         # ChatBubble, ChatInput, ...
│   │   │   ├── NavIsland.vue # Top navigation bar
│   │   │   └── Sidebar.vue   # Retractable sidebar
│   │   ├── views/            # 15+ page views
│   │   ├── stores/           # Pinia stores
│   │   └── assets/           # CSS, logos
│   └── tailwind.config.js    # Design system tokens
├── tests/                    # 18 pytest test files
├── slices                    # Launch script
└── DESIGN.md                 # Design system documentation
```

---

## Commands

| Command | What it does |
|---------|-------------|
| `./slices` | Build dashboard + start orchestrator on port 8420 |
| `PI_NO_AUTH=1 python3 start-orchestrator.py` | Start without auth (dev mode) |
| `python3 -m pytest tests/ -v` | Run all tests |
| `python3 -m pytest tests/test_e2e_api.py -v` | Run end-to-end API tests |
