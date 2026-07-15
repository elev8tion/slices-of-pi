# Codebase inventory

| Field | Value |
|-------|--------|
| **Git SHA** | `9249dfa` |
| **Date** | 2026-07-15 |
| **Product target** | **T1** — local single-operator (`docs/PRODUCT_INTENT.md`, `docs/health/TARGET.md`, `AGENTS.md`) |
| **Scope** | Runnable product: `pi_orchestrator/` + `dashboard/`; notes on adjacent packages |
| **Method** | Path enumeration, `main.py` / `main.ts` registration reads, import greps, test module headers |

Facts only. Paths relative to repo root unless absolute.

---

## 1. Router registration completeness

**Router package:** `pi_orchestrator/routers/`  
**Registration site:** `pi_orchestrator/main.py` (imports L44–75; `app.include_router(...)` L167–198)  
**Test app mirror:** `tests/conftest.py` `_build_test_app()` (same 32 routers)

### 1.1 Every router module vs `main.py`

| File under `pi_orchestrator/routers/` | Imported in `main.py` | `include_router` | Route prefix / notable paths |
|--------------------------------------|----------------------|------------------|------------------------------|
| `activities.py` | yes | yes | `/api/activities` |
| `agents.py` | yes | yes | `/api/agents` |
| `audit_log.py` | yes | yes | `/api/audit-log` |
| `auth.py` | yes | yes | `/api/auth` |
| `chat.py` | yes | yes | `/api/agents` (chat subpaths) |
| `coms.py` | yes | yes | `/api/coms` |
| `connectors.py` | yes | yes | `/api/connectors` |
| `console.py` | yes | yes | `/api/logs/tail`, `/ws/logs` |
| `credentials.py` | yes | yes | `/api/agents/{agent_id}/credentials` |
| `events.py` | yes | yes | `/ws/events` |
| `extensions.py` | yes | yes | `/api/extensions` |
| `files.py` | yes | yes | `/api/agents/{agent_id}/files` |
| `flixz.py` | yes | yes | `/api/flixz/*`, `/api/agents/{id}/flixz/*` |
| `git.py` | yes | yes | `/api/agents/{agent_id}/git` |
| `mcp_keys.py` | yes | yes | `/api/mcp-keys` |
| `operator_queue.py` | yes | yes | `/api/operator-queue` |
| `ops.py` | yes | yes | `/api/ops` |
| `profile.py` | yes | yes | `/api/agents` (profile subpaths) |
| `schedules.py` | yes | yes | `/api/schedules` |
| `sessions.py` | yes | yes | `/api/sessions` |
| `settings_router.py` | yes | yes | `/api/settings` |
| `sharing.py` | yes | yes | `/api/agents` (shares / access-requests) |
| `skills.py` | yes | yes | `/api/skills` |
| `system.py` | yes | yes | `/api/system` |
| `tags.py` | yes | yes | `/api/tags`, `PATCH /api/agents/{id}/tags` |
| `teams.py` | yes | yes | `/api/teams` |
| `telemetry.py` | yes | yes | `/api/telemetry` |
| `templates.py` | yes | yes | `/api/templates` |
| `terminal.py` | yes | yes | `/ws/terminal/{agent_id}` |
| `users.py` | yes | yes | `/api/users` |
| `voice.py` | yes | yes | `/api/voice/*`, `/ws/voice/{agent_id}` |
| `ws_tickets.py` | yes | yes | `/api/ws/ticket` |
| `__init__.py` | n/a (package init) | n/a | empty / not a router |

**Also on app (not a routers/ module):** `GET /health` defined in `pi_orchestrator/main.py` L236–243.

### 1.2 Orphan routers

**None.** All 32 router modules under `pi_orchestrator/routers/*.py` (excluding `__init__.py`) are imported and `include_router`’d in `pi_orchestrator/main.py`. No extra router file sits unregistered.

### 1.3 Endpoint surface (from `@router` decorators)

| Module | Methods / paths (as declared) |
|--------|-------------------------------|
| `agents` | `POST ""`, `GET ""`, `GET /{id}`, `DELETE /{id}` under `/api/agents` |
| `chat` | `POST /{id}/chat`, `GET /{id}/chat/history` |
| `profile` | `GET /{id}/profile`, `POST /{id}/profile/fact/forget` |
| `credentials` | `GET ""`, `POST ""`, `DELETE /{name}`, `GET /values` |
| `files` | `GET ""`, `GET /download`, `GET /preview`, `POST /upload`, `POST /mkdir`, `DELETE ""` |
| `git` | `GET /status`, `/log`, `/diff`; `POST /init`, `/commit`, `/push`, `/pull` |
| `sharing` | shares + access-requests CRUD under agent |
| `tags` | `GET /api/tags`, `PATCH /api/agents/{id}/tags` |
| `flixz` | system extract/runs; agent extract/runs |
| `sessions` | list, get, export |
| `activities` | list |
| `skills` | list |
| `extensions` | list |
| `schedules` | create, list, get, patch, delete |
| `templates` | list, get |
| `coms` | list peers |
| `connectors` | available, reload, CRUD, webhook, sync |
| `teams` | list, deploy |
| `system` | models, version, update, extensions/install, chat |
| `telemetry` | `/host` |
| `operator_queue` | list, stats, get, create, patch, delete |
| `ops` | status, agents stop/restart-all, scheduler pause/resume |
| `settings_router` | get, put |
| `auth` | register, login, me |
| `users` | list, search |
| `ws_tickets` | `POST /ticket` |
| `audit_log` | list, export, stats, types |
| `mcp_keys` | list, create, delete |
| `console` | `GET /api/logs/tail`, `WS /ws/logs` |
| `events` | `WS /ws/events` |
| `terminal` | `WS /ws/terminal/{agent_id}` |
| `voice` | process, tts, tts/status, `WS /ws/voice/{agent_id}` |

**Note (registration complete, capability gap):** Dashboard `AgentDetail.vue` issues `PATCH /api/agents/{id}`; `agents.py` has no `@router.patch`. Inventory fact only.

---

## 2. Service → consumer map

**Service package:** `pi_orchestrator/services/`  
Consumers found via imports under `pi_orchestrator/`, `tests/`, and self-imports within services.

| Service path | Primary responsibility (from module / usage) | Consumers (who imports) |
|--------------|-----------------------------------------------|-------------------------|
| `services/pi_session_service.py` | Agent create/destroy, `pi` JSONL chat, process registry, kill_all | `main.py` (kill_all); `routers/agents.py`, `routers/chat.py`, `routers/ops.py`; `services/voice_service.py`; tests: `conftest.py`, `test_pi_session_service.py` |
| `services/event_bus.py` | In-process pub/sub for WS fan-out | `main.py`; `routers/events.py`, `agents.py`, `profile.py`, `tags.py`; `services/connectors/engine.py` (via `routers.events.event_bus`); tests: `conftest.py`, `test_event_bus.py`, `test_events_ws.py`, `test_agents_api.py` |
| `services/schedule_service.py` | APScheduler cron → pi sessions (`scheduler` singleton) | `main.py` (lifespan start/stop); `routers/ops.py` (pause/resume/status). **Not** imported by `routers/schedules.py` (that router uses `database` only; scheduler reloads DB) |
| `services/cleanup_service.py` | GC managed sessions; calls shared-memory cleanup | `main.py` (lifespan); internally imports `shared_memory_service.cleanup_expired_facts` |
| `services/git_service.py` | Per-agent git under `~/.pi/agent/repos/` | `routers/git.py` only (`from ..services import git_service as git`) |
| `services/audit_service.py` | Wrappers over `database.log_audit_event` | `routers/credentials.py` (`log_credential_*`); `routers/operator_queue.py` (`log_queue_resolved`); `routers/settings_router.py` (`log_settings_changed`); `routers/audit_log.py` (`from ..services.audit_service import *` — star import; handlers use `db.query_audit_*` not the log helpers) |
| `services/agent_profile_service.py` | Profile → prompt text; session summary extract | `routers/profile.py`; `services/pi_session_service.py`; tests: `test_agent_profile_service.py`, `test_new_services.py` |
| `services/shared_memory_service.py` | Cross-agent facts on disk | `services/pi_session_service.py` (`read_context`); `services/cleanup_service.py`; `routers/connectors.py` (`write_fact`); `routers/coms.py` (`SHARED_MEMORY_DIR`); `services/connectors/engine.py`; tests: `test_shared_memory_service.py`, `test_new_services.py` |
| `services/system_chat_service.py` | System/voice intents without self-HTTP | `routers/system.py` (`handle_system_message` for `POST /api/system/chat`) only |
| `services/voice_service.py` | Transcript → agent chat + memory | `routers/voice.py`; tests: `test_voice.py` |
| `services/tts_service.py` | Mossy TTS bridge (`localhost:7860`) | `routers/voice.py` (`synthesize`, `is_available`). **Unused exports:** `ensure_warm`, `wav_base64_to_audio_element_src` (defined only in this file) |
| `services/ws_ticket_service.py` | In-memory single-use WS tickets | `routers/ws_tickets.py`, `terminal.py`, `console.py`, `voice.py` |
| `services/flixz_service.py` | ffmpeg extract + optional vision | `routers/flixz.py`; tests: `test_flixz.py` |
| `services/frame_description_service.py` | Gemini/Claude frame description | `services/flixz_service.py` only (`describe_frame_batch`) |
| `services/connectors/engine.py` | Periodic connector sync (`sync_engine`) | `main.py` (start/stop); `routers/connectors.py` |
| `services/connectors/registry.py` | Plugin discover/get/list/reload | `routers/connectors.py`; `services/connectors/engine.py`; tests: `test_connectors.py`, `test_new_services.py` |
| `services/connectors/_base.py` | `ConnectorPlugin` ABC | `services/connectors/registry.py`, `builtins/webhook.py` |
| `services/connectors/builtins/webhook.py` | Builtin webhook connector | Loaded by `registry.discover_plugins()`; tests: `test_connectors.py` |
| `services/__init__.py` | Package marker | no runtime exports observed |

**Lifespan-started services** (`main.py` lifespan): `event_bus`, `sync_engine`, optional `scheduler`, optional `cleanup`.

---

## 3. View → API map

### 3.1 Vue routes (`dashboard/src/main.ts`)

| Route path | Route name | View file |
|------------|------------|-----------|
| `/login` | login | `dashboard/src/views/Login.vue` |
| `/` | dashboard | `dashboard/src/views/Dashboard.vue` |
| `/agents` | agents | `dashboard/src/views/Agents.vue` |
| `/sessions` | sessions | `dashboard/src/views/Sessions.vue` |
| `/schedules` | schedules | `dashboard/src/views/Schedules.vue` |
| `/skills` | skills | `dashboard/src/views/Skills.vue` |
| `/extensions` | extensions | `dashboard/src/views/Extensions.vue` |
| `/templates` | templates | `dashboard/src/views/Templates.vue` |
| `/teams` | teams | `dashboard/src/views/Teams.vue` |
| `/console` | console | `dashboard/src/views/Console.vue` |
| `/ops` | ops | `dashboard/src/views/OperatorRoom.vue` |
| `/replay` | replay | `dashboard/src/views/Replay.vue` |
| `/audit` | audit | `dashboard/src/views/AuditLog.vue` |
| `/settings` | settings | `dashboard/src/views/Settings.vue` |

Auth guard in `main.ts`: skips login when `auth.checkNoAuth()`; else requires auth store.

### 3.2 View / store / panel → API paths

Direct `fetch` / `WebSocket` targets from dashboard sources:

| UI surface | File(s) | API / WS paths |
|------------|---------|----------------|
| **Login** | `views/Login.vue` → `stores/auth.ts` | `POST /api/auth/login`, `POST /api/auth/register`; `GET /api/auth/me` |
| **Auth bootstrap** | `stores/auth.ts` | `GET /api/auth/me` (no-auth detect + loadUser) |
| **Dashboard** | `views/Dashboard.vue` + `stores/app.ts` | `GET /api/agents`, `GET /api/activities`, `WS /ws/events` (via `connectWebSocket`) |
| **Agents list** | `views/Agents.vue` | `POST /api/agents`, `DELETE /api/agents/{id}`; store WS as above |
| **Agent detail shell** | `components/AgentDetail.vue` | `GET /api/skills`, `GET /api/tags`, `PATCH /api/agents/{id}` (no matching backend patch in `agents.py`), agent load via store `GET /api/agents/{id}` |
| **Info tab** | `InfoPanel.vue` | `GET /api/agents/{id}`, `GET /api/agents/{id}/profile` |
| **Chat tab** | `ChatPanel.vue`, `chat/ChatHistoryDropdown.vue` | `POST /api/agents/{id}/chat`, `GET /api/sessions?agent_id=…`, `GET /api/sessions/{id}` |
| **Slice Plays tab** | `SlicePlaysPanel.vue` | `GET /api/skills`, `POST /api/agents/{id}/chat` |
| **Terminal tab** | `TerminalPanel.vue` | `POST /api/ws/ticket`, `WS /ws/terminal/{agentId}` |
| **Files tab** | `FileManager.vue` | `/api/agents/{id}/files` (list, preview, download, upload, mkdir, delete) |
| **Git tab** | `GitPanel.vue` | `/api/agents/{id}/git/{status,log,diff,init,commit,push,pull}` |
| **Credentials tab** | `CredentialsPanel.vue` | `/api/agents/{id}/credentials` (+ `/values`, DELETE by name) |
| **Connectors tab** | `ConnectorsPanel.vue` | `GET/POST/DELETE /api/connectors`, `GET /api/connectors/available` |
| **Flixz (agent) tab** | `FlixzPanel.vue` | `POST /api/agents/{id}/flixz/extract` |
| **Sharing tab** | `SharingPanel.vue` | `/api/agents/{id}/shares`, `/access-requests` |
| **Voice (agent + system)** | `VoiceWorkspace.vue` (also `NavIsland.vue`) | `POST /api/ws/ticket`, `WS /ws/voice/{id\|__system__}`, `POST /api/voice/process`, `POST /api/system/chat`, `POST /api/voice/tts`, `GET /api/voice/tts/status` |
| **Sessions** | `views/Sessions.vue` | `GET /api/sessions`, `GET /api/sessions/{id}` |
| **Schedules** | `views/Schedules.vue` | `GET /api/schedules` only (list UI; no create/patch/delete fetch in this file) |
| **Skills** | `views/Skills.vue` | `GET /api/skills` |
| **Extensions** | `views/Extensions.vue` | `GET /api/extensions` |
| **Templates** | `views/Templates.vue` | `GET /api/templates` |
| **Teams** | `views/Teams.vue` | `GET /api/teams`, `POST /api/teams/{name}/deploy` |
| **Console** | `views/Console.vue` + panels | `GET /api/voice/tts/status`; `SystemConsole.vue`: `POST /api/ws/ticket`, `WS /ws/logs`; `SystemFlixzPanel.vue`: `/api/flixz/extract`, `/api/flixz/runs`, `/api/flixz/runs/{id}` |
| **Ops (Operator Room)** | `views/OperatorRoom.vue` + `OperatorQueue.vue` | `GET /api/operator-queue/stats`, `GET /api/operator-queue`, `PATCH/DELETE /api/operator-queue/{id}` |
| **Replay** | `views/Replay.vue` + `ReplayTimeline.vue` | `GET /api/sessions` (timeline consumes session data from parent) |
| **Audit** | `views/AuditLog.vue` | `GET /api/audit-log`, `/types`, `/stats`, export open `/api/audit-log/export` |
| **Settings** | `views/Settings.vue` | `fetch('/api/health')` — **backend health is `GET /health`**, not `/api/health` |
| **Nav / telemetry** | `NavIsland.vue` → `HostTelemetry.vue` | `GET /api/telemetry/host` |
| **Sidebar ops badge** | `Sidebar.vue` | `GET /api/operator-queue/stats` |
| **Coms (dashboard panel)** | `ComsPanel.vue` | `GET /api/coms` |
| **Onboarding** | `OnboardingChecklist.vue` (`App.vue`) | `GET /api/agents`, `/api/sessions`, `/api/tags` |
| **Activity feed** | `ActivityFeed.vue` | data from store (`/api/activities`) |
| **OpsQueue (dashboard)** | `OpsQueue.vue` | local props only (no direct fetch) |

### 3.3 Backend routes with no dashboard caller found

From grepping `dashboard/src` for path strings (MCP bridge may still call some):

| Backend path area | Dashboard usage |
|-------------------|-----------------|
| `GET/PUT /api/settings` | no fetch in `dashboard/src` |
| `GET /api/users`, `/api/users/search` | no |
| `GET /api/system/models`, `/version`, `POST /update`, `POST /extensions/install` | no (system chat only via voice) |
| `GET /api/logs/tail` | no (console uses WS logs) |
| `POST /api/connectors/{id}/sync`, webhook, patch | no (list/create/delete/available only) |
| `DELETE /api/flixz/runs/{id}` | no |
| Agent flixz runs list | no list path in FlixzPanel (extract only) |
| `GET /api/agents/{id}/chat/history` | no (sessions API used instead) |
| `GET /api/sessions/{id}/export` | no |
| Schedule write APIs (POST/PATCH/DELETE) | no in Schedules view |
| Full MCP keys UI | see orphans (`McpKeysPanel.vue` unmounted) |
| Ops fleet controls (`/api/ops/*`) | only in unmounted `SlicesPanel.vue` |

`pi-mcp-server/src/` calls: `/api/agents`, chat, sessions, skills, extensions, schedules (optional bridge; not started by `./slices`).

---

## 4. Test → module map

| Test file | Modules / surface covered |
|-----------|---------------------------|
| `tests/conftest.py` | Builds test FastAPI app with all routers; patches DB/session service; fixtures for agents, async_client, event_bus |
| `tests/test_health_api.py` | `main`/`conftest` `GET /health`; `database` counts |
| `tests/test_agents_api.py` | `routers/agents.py`, `services/pi_session_service` (create/destroy), `services/event_bus`, `database` agents |
| `tests/test_chat_api.py` | `routers/chat.py`, stream_chat path, history; `database` |
| `tests/test_sessions_api.py` | `routers/sessions.py`, managed session files, `database` sessions |
| `tests/test_schedules_api.py` | `routers/schedules.py`, `database` schedules |
| `tests/test_skills_api.py` | `routers/skills.py`, `config.PI_SKILLS_DIR` |
| `tests/test_extensions_api.py` | `routers/extensions.py`, `config.PI_EXTENSIONS_DIR` |
| `tests/test_templates_api.py` | `routers/templates.py`, `config.PI_AGENTS_CONFIG_DIR` |
| `tests/test_teams_api.py` | `routers/teams.py`, teams.yaml / personas under config dir |
| `tests/test_activities_api.py` | `routers/activities.py`, `database` activities |
| `tests/test_coms_api.py` | `routers/coms.py` peer discovery |
| `tests/test_profile_api.py` | `routers/profile.py`, `database` agent memory/profile |
| `tests/test_connectors.py` | `services/connectors/registry.py`, `builtins/webhook.py` |
| `tests/test_new_services.py` | `agent_profile_service`, `shared_memory_service`, connector registry + connector DB helpers |
| `tests/test_agent_profile_service.py` | `services/agent_profile_service.py` unit |
| `tests/test_shared_memory_service.py` | `services/shared_memory_service.py` unit |
| `tests/test_pi_session_service.py` | `services/pi_session_service.py` unit (create/destroy/status/stream/kill_all) |
| `tests/test_event_bus.py` | `services/event_bus.py` unit |
| `tests/test_events_ws.py` | `routers/events.py` + live `main.app` WS; `event_bus` |
| `tests/test_database.py` | `pi_orchestrator/database.py` (agents, sessions, activities, schedules) |
| `tests/test_flixz.py` | `database` flixz_runs; `routers/flixz.py`; `services/flixz_service.py` |
| `tests/test_voice.py` | `routers/voice.py` routes; `services/voice_service.py`; frontend file existence checks |
| `tests/test_terminal.py` | terminal modes/config (`config` / orchestrator config); router registration for terminal |
| `tests/test_terminal_e2e.py` | Live server e2e: `/api/ws/ticket`, `/ws/terminal`, agents; requires running orchestrator |
| `tests/test_e2e_api.py` | Live server e2e: `/health`, `/api/system/version`, `/api/settings`, agents CRUD/PATCH, chat stream, sessions; requires `localhost:8420` |

### 4.1 Product areas without dedicated `tests/test_*.py` (observed)

No dedicated test modules found for: `auth`, `users`, `sharing`, `credentials`, `files`, `git`, `operator_queue`, `ops`, `audit_log`, `mcp_keys`, `telemetry`, `console`, `settings_router` (except e2e settings GET), `ws_tickets` (covered partly by terminal e2e), `system` (partial e2e version/settings), `cleanup_service`, `schedule_service` (runtime), `tts_service`, `frame_description_service`, `system_chat_service`, `git_service`.

`slice_of_pi/` has **no** tests under `tests/`.

---

## 5. Orphans / dead-code suspects

Facts from import greps; “suspect” means no in-repo consumer found (may still be intentional scaffolding).

### 5.1 Package not wired to product

| Path | Fact |
|------|------|
| `slice_of_pi/**` | Zero `from slice_of_pi` / `import slice_of_pi` in `.py`/`.ts`/`.vue` product sources. Declared by root `pyproject.toml` only. Documented in `PROJECT_STATE.md` §1, §6.1, §10. |

### 5.2 Backend functions defined but never called outside definition file

| Symbol | File | Call sites outside definition |
|--------|------|-------------------------------|
| `log_agent_created`, `log_agent_updated`, `log_agent_deleted`, `log_session_started`, `log_session_ended` | `services/audit_service.py` | **None** (only defined; not called by agents/chat/session paths) |
| `ensure_warm`, `wav_base64_to_audio_element_src` | `services/tts_service.py` | **None** |
| `audit_log.py` star-import of `audit_service` | `routers/audit_log.py` | Handlers use `db.query_audit_events` / `get_audit_event_stats`; star import unused for symbols |

### 5.3 Dashboard components with no importer

Grep for component name as import/tag from other `dashboard/src` files returned only self/docs:

| Component | Path | Importers in `dashboard/src` |
|-----------|------|------------------------------|
| `McpKeysPanel.vue` | `dashboard/src/components/` | **none** (API `/api/mcp-keys` only referenced inside this file) |
| `SlicesPanel.vue` | same | **none** (only UI that fetches `/api/ops/*`) |
| `CapacityMeter.vue` | same | **none** |
| `ResourceModal.vue` | same | **none** (imports `ModelSelector` only) |
| `YamlEditor.vue` | same | **none** |

### 5.4 Dashboard store unused

| Store | Path | Importers |
|-------|------|-----------|
| `useNotificationStore` | `dashboard/src/stores/notifications.ts` | **none** outside its own file |

### 5.5 UI ↔ API mismatches (fact)

| UI | Calls | Backend |
|----|-------|---------|
| `Settings.vue` | `GET /api/health` | Health is `GET /health` in `main.py` |
| `AgentDetail.vue` save | `PATCH /api/agents/{id}` | `agents.py` has POST/GET/DELETE only (no PATCH) |
| `test_e2e_api.py` | `PATCH /api/agents/{id}` | same gap |

### 5.6 Adjacent trees (not product runtime)

| Path | Role |
|------|------|
| `pi-mcp-server/` | Optional MCP STDIO → HTTP to orchestrator; not started by `./slices` |
| `pi-coding-agent/` | Extracted pi docs + graph artifacts; not orchestrator code |
| `docs/archive/**` | Historical; not registration surface |
| `dashboard/dist/` | Build output |

### 5.7 Router completeness summary (repeat)

- **Orphan router modules:** 0  
- **Unregistered services used only internally:** `frame_description_service` (via flixz only) is registered indirectly; not a router orphan  
- **Registered routers with thin/no dashboard coverage:** `users`, `settings_router`, `mcp_keys` (API registered; panel orphan), `ops` (API registered; SlicesPanel orphan)

---

## 6. Quick structural counts (from tree / PROJECT_STATE)

| Area | Count (inspection) |
|------|-------------------|
| Router modules (`routers/*.py` excl. `__init__`) | 32, all registered |
| Service modules (top-level + connectors tree) | `pi_session`, `event_bus`, `schedule`, `cleanup`, `git`, `audit`, `agent_profile`, `shared_memory`, `system_chat`, `voice`, `tts`, `ws_ticket`, `flixz`, `frame_description`, connectors engine/registry/_base/webhook |
| Vue views | 14 |
| Vue routes | 14 |
| `tests/test_*.py` | 25 |

---

## 7. Sources used

- `pi_orchestrator/main.py`
- `pi_orchestrator/routers/*`
- `pi_orchestrator/services/*`
- `dashboard/src/main.ts`, `views/*`, `components/*`, `stores/*`
- `tests/*`
- `docs/PRODUCT_INTENT.md`, `docs/health/TARGET.md`, `PROJECT_STATE.md`, `AGENTS.md`
- Git SHA at inventory time: `9249dfa`
