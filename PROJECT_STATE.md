# Slice of Pi — Project State (Codebase Truth)

**Authority:** This document is derived only from files and folders present in the working tree.  
**Date of inspection:** 2026-07-15  
**Last documentation cleanup:** 2026-07-15 (root `.md` files archived, updated, or deleted per §9)  
**Method:** Directory inventory, package manifests, entry points, router/service/module reads, import graph checks, test layout. No external product claims.

---

## 1. What this repository actually is

There are **two named packages** and **one primary runnable product**:

| Identity | Where declared | What it is in practice |
|----------|----------------|------------------------|
| **slice-of-pi** | Root `pyproject.toml` | Python package of **abstract contracts** (ABCs / Protocols). Version `0.1.0`. Classifiers: Pre-Alpha. Description: “Architectural contract layer… abstract interfaces, ABCs, and Protocols.” |
| **pi-orchestrator** | `pi_orchestrator/pyproject.toml` | FastAPI app: “manage multiple pi coding agents with an API server and dashboard.” Version `0.1.0`. |
| **Product (user-facing)** | `README.md`, `slices`, `start-orchestrator.py`, `dashboard/` | Local **web dashboard + API** that manages **pi coding agent** subprocesses on a single machine. |

**Important structural finding:** `pi_orchestrator` does **not** import `slice_of_pi` anywhere in Python or TypeScript sources. The only non-doc reference to the package name is packaging (`pyproject.toml` `include = ["slice_of_pi*"]`). The contracts package and the orchestrator are **side-by-side**, not wired together.

**Runtime model (from code comments and implementation):**

- Single-user, localhost-oriented (default bind `127.0.0.1:8420`)
- No Docker, no Redis in the orchestrator design (`main.py`, `config.py`)
- Agents are **not** containers: they are **pi binary subprocesses** with JSONL session files
- Persistence: **SQLite** at `~/.pi/agent/orchestrator.db` (overridable via config paths)
- Auth can be disabled with `PI_NO_AUTH=1` (used by `./slices`)

---

## 2. How the system starts (executable truth)

| Entry | Role |
|-------|------|
| `./slices` | Primary launcher: kills ports 8420/5173, pip-installs core Python deps if needed, `npm install` + `vite build` for dashboard, starts `start-orchestrator.py --serve-dashboard` with `PI_NO_AUTH=1`, opens browser |
| `start-orchestrator.py` | Adds project root to `sys.path`, runs uvicorn on `127.0.0.1:8420`; optional `--serve-dashboard` |
| `pi_orchestrator/main.py` | FastAPI app definition, lifespan (dirs, DB, event bus, connector sync engine, scheduler, cleanup), all routers, `/health`, optional SPA static serve from `dashboard/dist` |
| `install.sh` | Alternate: install Python deps, build dashboard, start orchestrator **and** Vite dev server on 5173 (does not set `PI_NO_AUTH` or force static dashboard serve the same way as `slices`) |

**Health endpoint:** `GET /health` → `{ status, version: "0.1.0", agent_count, active_session_count }`.

**External binary dependency:** `PI_BINARY` (default `"pi"` on `PATH`). Without it, session creation logs a warning and chat/session flows fail.

**Data directories (from `config.py`):** under `~/.pi/` — `agent/`, `agent/sessions/`, `agent/sessions/managed/`, `agent/sessions/scheduled/`, `agent/skills/`, `agent/extensions/`, `agent/prompt-templates/`, `agents/`, SQLite `orchestrator.db`, optional `orchestrator.json` profiles.

---

## 3. Repository layout (what builds the product)

```
slice-of-pi/                          # git root
├── slices                            # production-style single-port launcher
├── start-orchestrator.py             # uvicorn entry
├── install.sh                        # dual-process (API + Vite) installer/launcher
├── pyproject.toml                    # package: slice-of-pi (contracts only)
├── pi_orchestrator/                  # runnable FastAPI backend (~9.5k LOC Python)
├── dashboard/                        # Vue 3 + TS + Vite + Tailwind UI (~14.8k LOC src)
├── tests/                            # pytest suite for orchestrator (25 test modules)
├── slice_of_pi/                      # abstract contract package (~2.7k LOC) — not wired to orchestrator
├── pi-mcp-server/                    # optional MCP STDIO bridge (~219 LOC TS) to orchestrator HTTP API
├── pi-coding-agent/                  # extracted Pi agent docs + graph artifacts (not runtime code)
├── docs/                             # living architecture/design/ops + archive/
├── .pi/                              # local runtime scaffold (gitignored pattern exists; present on disk)
├── README.md                         # user entry / quick start
└── PROJECT_STATE.md                  # this file — codebase truth
```

Approximate sizes (source only, excluding `node_modules`, `__pycache__`, built assets):

| Area | Files | ~Lines |
|------|-------|--------|
| `pi_orchestrator/` | 60 `.py` | ~9,535 |
| `dashboard/src/` | 67 vue/ts/js | ~14,765 |
| `tests/` | 25 test modules + conftest | ~4,638 |
| `slice_of_pi/` | 30 `.py` + TS interfaces | ~2,676 |
| `pi-mcp-server/src/` | 7 `.ts` | ~219 |

---

## 4. Backend — `pi_orchestrator`

### 4.1 Application shell

- **Framework:** FastAPI + uvicorn  
- **Config:** env-overridable host/port, pi binary, schedule poll, session timeout, default model/tools  
- **CORS:** localhost Vite (`5173`) and self (`8420`)  
- **Lifespan starts:** logging, directories, DB init/migrations, in-process event bus, connector `sync_engine`, APScheduler-backed schedule service (optional if import fails), cleanup service (optional), then shutdown reverses (kill sessions, stop services)

### 4.2 Routers (registered in `main.py`)

32 router modules under `pi_orchestrator/routers/`. Endpoint map from source:

| Prefix / path | Module | Capabilities present in code |
|---------------|--------|------------------------------|
| `/api/agents` | `agents.py` | Create, list, get, delete agents |
| `/api/agents/{id}/chat` | `chat.py` | SSE chat stream; chat history |
| `/api/agents/{id}/profile` | `profile.py` | Profile read; forget fact |
| `/api/agents/{id}/credentials` | `credentials.py` | List/create/delete credentials; values |
| `/api/agents/{id}/files` | `files.py` | Browse, download, preview, upload, mkdir, delete |
| `/api/agents/{id}/git` | `git.py` | status, log, diff, init, commit, push, pull |
| `/api/agents/{id}/shares` + access-requests | `sharing.py` | Share/unshare; access request flow |
| `/api/agents/{id}/tags` (PATCH) | `tags.py` | Tag assignment |
| `/api/agents/{id}/flixz/*` | `flixz.py` | Per-agent video extract / runs |
| `/api/sessions` | `sessions.py` | List, get, export |
| `/api/activities` | `activities.py` | Activity feed |
| `/api/skills` | `skills.py` | List skills from filesystem |
| `/api/extensions` | `extensions.py` | List extensions |
| `/api/schedules` | `schedules.py` | CRUD schedules |
| `/api/templates` | `templates.py` | List/get persona templates |
| `/api/coms` | `coms.py` | Peer discovery under `~/.pi/coms/` |
| `/api/connectors` | `connectors.py` | Connector CRUD, sync, webhook, available/reload |
| `/api/teams` | `teams.py` | List teams; deploy team |
| `/api/system` | `system.py` | models, version, update, extension install, system chat |
| `/api/telemetry` | `telemetry.py` | Host metrics |
| `/api/operator-queue` | `operator_queue.py` | HITL queue CRUD/stats |
| `/api/ops` | `ops.py` | stop/restart all agents; scheduler pause/resume |
| `/api/settings` | `settings_router.py` | Get/put settings |
| `/api/auth` | `auth.py` | register, login, me; `PI_NO_AUTH` short-circuit |
| `/api/users` | `users.py` | list, search |
| `/api/ws/ticket` | `ws_tickets.py` | Mint short-lived WS tickets |
| `/api/audit-log` | `audit_log.py` | query, export, stats, types |
| `/api/mcp-keys` | `mcp_keys.py` | List/create/delete MCP keys |
| `/api/tags` | `tags.py` | List tags |
| `/api/flixz/*` | `flixz.py` | System-level flixz extract/runs |
| `/api/voice/*` | `voice.py` | process transcript, TTS, TTS status |
| `/api/logs/tail` | `console.py` | Log tail |
| `/ws/events` | `events.py` | Live event WebSocket |
| `/ws/logs` | `console.py` | Live logs WebSocket |
| `/ws/terminal/{agent_id}` | `terminal.py` | PTY terminal WebSocket |
| `/ws/voice/{agent_id}` | `voice.py` | Voice WebSocket |
| `/health` | `main.py` | Liveness + counts |

### 4.3 Services

| Service | Responsibility (from module docstrings / code) |
|---------|-----------------------------------------------|
| `pi_session_service` | Core: create/destroy agents, spawn `pi --mode json`, stream JSONL chat, process registry, kill_all |
| `event_bus` | In-process pub/sub for dashboard WebSocket fan-out (no Redis, no persistence) |
| `schedule_service` | APScheduler cron jobs → pi sessions; execution tracking |
| `cleanup_service` | Periodic GC of old managed session JSONL files |
| `git_service` | Per-agent repos under `~/.pi/agent/repos/<name>/` |
| `audit_service` | Structured audit logging wrappers over DB |
| `agent_profile_service` | Format profile JSON for system prompt injection |
| `shared_memory_service` | Cross-agent knowledge pool (file-based) |
| `system_chat_service` | Intentful system/voice actions without self-HTTP |
| `voice_service` | Voice transcript → agent chat pipeline + memory |
| `tts_service` | Optional bridge to mossy TTS on `localhost:7860` |
| `ws_ticket_service` | Single-use WS auth tickets (in-memory) |
| `flixz_service` | ffmpeg frame extraction + optional vision description |
| `frame_description_service` | Gemini Vision frame analysis (`GEMINI_API_KEY` / auth.json) |
| `connectors/` | Plugin engine + registry; builtin `webhook` provider |

### 4.4 Data model (`database.py`)

SQLite schema tables found in `SCHEMA` (+ column migrations in `init_db`):

- `agents`, `sessions`, `activities`
- `schedules`, `schedule_executions`
- `settings`, `mcp_keys`
- `users`, `tags`, `agent_tags`
- `credentials`, `audit_log`, `operator_queue`
- `agent_shares`, `access_requests`
- `connectors`, `connector_sync_log`
- `flixz_runs`

Fernet-style encryption helpers exist for sensitive connector/auth state (key derived from hostname + port; plaintext fallback if `cryptography` missing).

### 4.5 API models (`models.py`)

Pydantic request/response models for agents, sessions, chat, schedules, activities, skills/extensions, personas, MCP keys, health. Enums for agent/session/execution status.

### 4.6 Declared Python dependencies

**Packaged (`pi_orchestrator/pyproject.toml`):** fastapi, uvicorn, pydantic, apscheduler.  
**Installed by `slices` script (broader than package metadata):** also pyyaml, psutil, cryptography, aiohttp.  
**Root package deps:** only `rich` — unrelated to orchestrator runtime.

---

## 5. Frontend — `dashboard/`

| Item | Truth |
|------|--------|
| Stack | Vue 3, TypeScript, Vite 6, Pinia, Vue Router, Tailwind 3, xterm + addons, js-yaml |
| Package name | `slice-of-pi-dashboard` `0.1.0` private |
| Build | `vue-tsc -b && vite build` → `dashboard/dist` (served by orchestrator when enabled) |
| Routes | `/login`, `/`, `/agents`, `/sessions`, `/schedules`, `/skills`, `/extensions`, `/templates`, `/teams`, `/console`, `/ops`, `/replay`, `/audit`, `/settings` |
| Stores | `app`, `auth`, `notifications` |
| Auth guard | Skips login when backend reports no-auth mode; else requires auth store |

**Views (14):** Login, Dashboard, Agents, Sessions, Schedules, Skills, Extensions, Templates, Teams, Console, OperatorRoom, Replay, AuditLog, Settings.

**Components (sample of surface area):** chat suite, ChatPanel, TerminalPanel, VoiceOrb/VoiceWorkspace, Flixz panels, Git/Credentials/Files/Sharing, Operator/Ops queues, SystemConsole, ReplayTimeline, HostTelemetry, YamlEditor, Connectors/Coms/Slice Plays panels, onboarding checklist, toasts, nav/sidebar.

---

## 6. Supporting packages (present, not primary launcher path)

### 6.1 `slice_of_pi/` — contract layer only

Layers declared in package docstring:

- **core/** — `AgentLifecycle`, `AgentCapability`, `CredentialProvider`
- **orchestration/** — `AgentRuntime`, `WorkflowEngine`, `EventBus`, `SkillProvider`, `ChannelAdapter`, `CLIPlugin`, `AgentClient`, …
- **execution/** — `ExecutionEnvironment`, `GuardrailHook`
- **specification/** — `AgentManifest`, `SystemManifest`
- **infra/** — `TemplateEngine`, `ScheduleEngine`, `PlatformDeployment`
- **testing/** — `TestFixtureFactory`, `ScenarioRunner`
- **interfaces/** — TypeScript contracts (`frontend.ts`, `index.ts`)

These are abstract interfaces / dataclasses. **No concrete implementation of these ABCs lives inside `pi_orchestrator`.** They describe a target architecture; the running product does not implement them as subclasses.

### 6.2 `pi-mcp-server/`

TypeScript MCP server (STDIO) proxying HTTP to `PI_ORCHESTRATOR_URL` (default `http://127.0.0.1:8420`). Tools: list/create/delete agents, chat, sessions, skills, extensions, schedules. Separate `package.json`; not started by `./slices`.

### 6.3 `pi-coding-agent/`

Not application code. Contains:

- `source/*.md` — extracted Pi coding agent documentation (sessions, skills, RPC, SDK, …)
- `graph.json` / `graph.html` / `GRAPH_REPORT.md` / `EXTRACTION_SUMMARY.json` — analysis artifacts
- Nested AST cache under `source/graphify-out/`

Useful as **reference material for the `pi` binary**, not as part of the orchestrator build.

---

## 7. Tests

- **Location:** `tests/` + `conftest.py`
- **Style:** pytest + pytest-asyncio; temp DB paths patched before imports; pi binary mocked for unit/API tests
- **Modules cover:** health, agents, chat, sessions, schedules, skills, extensions, templates, teams, activities, coms, connectors, event bus, events WS, database, profile, shared memory, pi session service, flixz, voice, terminal (+ e2e terminal requiring live server), broader e2e API

Tests target **`pi_orchestrator`**, not `slice_of_pi` ABCs.

---

## 8. Runtime features vs package identity (synthesis)

**What you can run today (files present and wired):**

1. Manage multiple named pi agents (CRUD, tags, profiles, credentials)
2. Stream chat (SSE) and terminal (WS + xterm)
3. Session history, export, activity feed, replay UI route
4. Schedules (cron), skills/extensions discovery, persona templates
5. Teams deploy, connectors (webhook builtin), shared memory service
6. Git per agent, file manager, operator queue, ops controls
7. Auth/users/sharing (usable; default launch disables auth)
8. Audit log, host telemetry, system console logs
9. Voice pipeline + optional TTS (mossy) + Flixz (ffmpeg + optional Gemini)
10. Optional MCP tool bridge package
11. Static or Vite-hosted Vue dashboard

**What the tree also contains but does not drive the product:**

- Full ABC framework package (`slice_of_pi`) with **zero imports from orchestrator**
- Pi agent documentation extraction tree (`pi-coding-agent/`)
- Historical plans/reports under `docs/archive/` (see §9)

**What is explicitly not in the running design:** Docker orchestration, Redis, multi-tenant SaaS, billing, Slack/Telegram fleet features (those appear only in `docs/archive/` roadmaps, not as implemented routers).

---

## 9. Documentation disposition — **applied 2026-07-15**

### Living documentation (authoritative or operational)

| Path | Role |
|------|------|
| `PROJECT_STATE.md` | Codebase truth (this file) |
| `README.md` | Quick start, features, structure (updated to match tree) |
| `docs/architecture.md` | System architecture (updated router/service tables) |
| `docs/design.md` | Design system (moved from root `DESIGN.md`) |
| `docs/ops/CLAUDE_OAUTH_SETUP.md` | Ops notes for Pi/Claude OAuth |
| `docs/README.md` | Doc index |
| `docs/archive/README.md` | Archive index + reasons |

### Archived (`docs/archive/`)

| File | Reason |
|------|--------|
| `VOICE_FLIXZ_PLAN.md` | Plan superseded by code |
| `PLAN-maestro-execution.md` | Build plan; substantial code shipped |
| `NEXT_PHASES_PLAN.md` | Phase plan; many UI targets shipped |
| `PRODUCTIZATION_PATH.md` | Future multi-user/SaaS only |
| `FUTURE_TIER4.md` | Enterprise wishlist only |
| `FRAME_VIZ_REPORT.md` | Historical implementation report |
| `CAPABILITY_AUDIT.md` | Dated matrix; not re-verified as living truth |
| `memory-handoff-map.md` | Residual planning map |
| `.karpathy-session.md` | Ephemeral session log |
| `UNRELATED-BUILD_PLAN-digia.md` | Quarantined unrelated Digia plan (was root `BUILD_PLAN.md`) |

### Deleted

| File | Reason |
|------|--------|
| `progress.md` | Empty stub (was gitignored) |

### Not relocated (still reference subtrees)

| Path | Note |
|------|------|
| `pi-coding-agent/source/*.md` | Upstream pi reference docs |
| `pi-coding-agent` graph/cache artifacts | Analysis outputs; not product docs |

### Packaging note (unchanged by doc cleanup)

Root `pyproject.toml` still describes the **contracts** package (“architectural contract layer”), while the runnable product is `pi_orchestrator` + `dashboard`. Dual identity is real; metadata and product README intentionally describe different layers (see §10).

---

## 10. Dual identity (explicit)

| Aspect | Contracts package | Runnable product |
|--------|-------------------|------------------|
| Name | slice-of-pi | Pi Orchestrator + dashboard |
| Code | `slice_of_pi/` | `pi_orchestrator/` + `dashboard/` |
| Wired? | Not imported by product | Imports itself only |
| Version | 0.1.0 Pre-Alpha | 0.1.0 |
| Purpose | Future/shared interface layer | Manage pi agents via UI/API |

Any documentation that treats them as one fully integrated framework **overstates** the current tree. Correct statement: **the product implements a concrete multi-agent manager; the contracts package is a separate, unimplemented interface surface.**

---

## 11. Documentation end-state (current)

```
README.md
PROJECT_STATE.md
docs/
  README.md
  architecture.md
  design.md
  ops/CLAUDE_OAUTH_SETUP.md
  archive/                 # superseded plans & reports
    README.md
    …
```

---

## 12. Source of truth hierarchy (for future agents/humans)

When documentation and code disagree, prefer:

1. `pi_orchestrator/main.py` (what is registered and started)
2. `pi_orchestrator/routers/*` + `services/*` + `database.py` + `config.py`
3. `dashboard/src/main.ts` routes + views/components
4. `tests/` (intended behavior under test)
5. `slices` / `start-orchestrator.py` (how it is launched)
6. This `PROJECT_STATE.md`
7. All other markdown (plans, roadmaps, audits) — **non-authoritative** until re-verified

---

*End of codebase-truth state document. Generated from local filesystem inspection only.*
