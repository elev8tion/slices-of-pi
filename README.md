# Slice of Pi

A web dashboard and API server for managing multiple **pi** coding agents on a single machine.

Run `./slices` to start everything — a FastAPI backend serves the Vue 3 dashboard on `localhost:8420`, where you can create agents, chat with them, view session history, and control the system.

---

## Quick Start

```bash
./slices
```

Opens the dashboard at `http://localhost:8420`. No login required in single-user mode (`PI_NO_AUTH=1`).

**Requirements:** Python 3.11+, Node.js (for the dashboard build), and the `pi` binary on your `PATH` (or set `PI_BINARY`).

---

## Features

### Core
- **[Dashboard](/)** — agent grid with live status, stats, host telemetry, activity feed
- **[Agents](/agents)** — create, tag, search, delete agents with model/tools/skills config
- **[Chat](/agents)** — SSE streaming chat with markdown, tool calls, session history
- **[Terminal](/agents)** — live pseudo-terminal via WebSocket + xterm.js
- **[Sessions](/sessions)** — session history, export, replay timeline

### Productivity
- **[Slice Plays](/agents)** — one-click skill execution from the dashboard
- **[Credentials](/agents)** — encrypted API key storage per agent
- **[Git](/agents)** — per-agent git repos (status, commit, push, pull)
- **[Tags](/agents)** — organize and filter agents by labels
- **[Connectors](/agents)** — connector plugins (webhook builtin) and sync
- **[Model Selector](/agents)** — searchable model dropdown with provider badges

### Observability
- **[Audit Log](/audit)** — event trail with filters, export, stats
- **[System Console](/console)** — live orchestrator log stream
- **[Slice Operations](/ops)** — stop/restart all agents, scheduler controls
- **[Operator Queue](/ops)** — human-in-loop approval items
- **[Host Telemetry](/)** — CPU/RAM/Disk sparklines

### System
- **[Voice](/)** — system voice with intent parsing; per-agent voice workspace
- **[Flixz](/agents)** — video frame extraction (ffmpeg) + optional vision descriptions
- **[Replay](/replay)** — zoomable timeline of session activity
- **[File Manager](/agents)** — browse/upload/preview agent workspace files
- **[YAML Editor](/settings)** — in-browser config editing
- **[MCP Keys](/settings)** — encrypted MCP key management

### Collaboration
- **[Sharing](/agents)** — share agents with chat/admin permissions
- **[Teams](/teams)** — deploy multi-agent teams
- **[Schedules](/schedules)** — cron-based recurring agent execution
- **[Templates](/templates)** — persona templates

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

- **Backend**: FastAPI, SQLite, in-process event bus, APScheduler for cron
- **Frontend**: Vue 3 + TypeScript + Pinia + Tailwind CSS
- **Design**: Dark theme with lime accent (`#9DD522`)
- **Auth**: JWT-based; `PI_NO_AUTH=1` for single-user mode (default via `./slices`)
- **Scope**: Single-user localhost — no Docker, no Redis in the running design

**Living docs**

| Doc | Purpose |
|-----|---------|
| [PROJECT_STATE.md](./PROJECT_STATE.md) | Codebase truth — packages, routes, services, doc disposition |
| [docs/architecture.md](./docs/architecture.md) | System architecture |
| [docs/design.md](./docs/design.md) | Design system tokens |
| [docs/ops/CLAUDE_OAUTH_SETUP.md](./docs/ops/CLAUDE_OAUTH_SETUP.md) | Pi / Claude OAuth ops notes |
| [docs/archive/](./docs/archive/) | Superseded plans, reports, future roadmaps |

---

## Project Structure

```
├── slices                      # Primary launcher (build dashboard + serve on 8420)
├── start-orchestrator.py       # Uvicorn entry
├── install.sh                  # Alternate: API + Vite dev server
├── pi_orchestrator/            # FastAPI backend
│   ├── main.py                 # App entry, lifespan, router registration
│   ├── config.py               # Paths, env vars
│   ├── database.py             # SQLite schema + CRUD
│   ├── models.py               # Pydantic models
│   ├── routers/                # 32 route modules (agents, chat, sessions, …)
│   └── services/               # Session, event bus, schedule, git, voice, flixz, …
├── dashboard/                  # Vue 3 frontend
│   ├── src/components/         # UI panels (chat, terminal, voice, git, …)
│   ├── src/views/              # 14 page views
│   └── src/stores/             # Pinia: app, auth, notifications
├── tests/                      # 25 pytest modules for the orchestrator
├── slice_of_pi/                # Abstract contract package (ABCs) — not wired to orchestrator
├── pi-mcp-server/              # Optional MCP STDIO bridge to the HTTP API
├── pi-coding-agent/            # Extracted Pi agent reference docs (not runtime)
├── docs/                       # Architecture, design, ops, archive
├── PROJECT_STATE.md            # Authoritative project state from the tree
└── README.md
```

---

## Commands

| Command | What it does |
|---------|-------------|
| `./slices` | Build dashboard + start orchestrator on port 8420 |
| `PI_NO_AUTH=1 python3 start-orchestrator.py --serve-dashboard` | Start API + static dashboard |
| `python3 -m pytest tests/ -v` | Run all tests |
| `python3 -m pytest tests/test_e2e_api.py -v` | Run end-to-end API tests |
| `cd dashboard && npm run dev` | Vite dev server (port 5173) against a running API |

Optional MCP bridge (requires a running orchestrator):

```bash
cd pi-mcp-server && npm install && npm run dev
```

---

## Package identity

| Package | Location | Role |
|---------|----------|------|
| **pi-orchestrator** | `pi_orchestrator/` | Runnable multi-agent manager API |
| **slice-of-pi** | `slice_of_pi/` + root `pyproject.toml` | Architectural contracts only (not imported by the orchestrator) |
| **slice-of-pi-dashboard** | `dashboard/` | Vue UI |
| **pi-mcp-server** | `pi-mcp-server/` | MCP tools over orchestrator HTTP |
