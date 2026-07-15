# Frontend Review — `dashboard/src`

**Date:** 2026-07-15  
**Git SHA:** 9249dfa  
**Scope:** views, components, stores, `main.ts` router  
**Binding:** local single-operator product (`docs/PRODUCT_INTENT.md`). No SaaS recommendations.  
**Actions taken:** typecheck + production build only. **No code fixes.**

Logs:

| Command | Log |
|---------|-----|
| `npx vue-tsc -b --pretty false` | [`docs/health/vue-tsc.log`](./vue-tsc.log) |
| `npx vite build` | [`docs/health/vite-build.log`](./vite-build.log) |

---

## 1. Typecheck / build status

| Check | Exit | Result |
|-------|------|--------|
| **vue-tsc** | **1** | **FAIL** — 9 diagnostics across 5 files |
| **vite build** | **0** | **PASS** — production bundle written; 192 modules; ~2.5s |

### vue-tsc errors (from log)

| File | Issue |
|------|--------|
| `components/chat/ChatHistoryDropdown.vue:114` | `HTMLElement` has no `.select()` (needs `HTMLInputElement`) |
| `components/UserMenu.vue:160,165,168` | custom `_clickOutside` not on `HTMLElement` |
| `components/VoiceWorkspace.vue:30,108` | missing `SpeechRecognition` / `SpeechRecognitionEvent` DOM types |
| `stores/notifications.ts:24` | `toastBus` has no `warning` method; dynamic index fails |
| `views/AuditLog.vue:202–203` | `v-for="(count, type) in stats.event_types"` types key as `number`; `.replace` invalid |

**Note:** Vite does not run vue-tsc; a green build does **not** mean types are clean.

### Build notes

- Largest chunk: `AgentDetail-*.js` ~**592 kB** / ~155 kB gzip (xterm, agent tabs, etc.). Vite warns >500 kB.
- Lazy routes work (`() => import('./views/...')`); heavy deps still pull into the AgentDetail chunk.

---

## 2. Routes → primary APIs

Router: [`dashboard/src/main.ts`](../../dashboard/src/main.ts). Layout shell on most pages: `NavIsland` + `Sidebar` (Sidebar polls `/api/operator-queue/stats`).

| Route | View | Primary APIs / WS | Nested UI that hits APIs |
|-------|------|-------------------|---------------------------|
| `/login` | `Login.vue` | `POST /api/auth/login`, `POST /api/auth/register` | — |
| `/` | `Dashboard.vue` | `GET /api/agents`, `GET /api/activities`, **`WS /ws/events`** (no ticket) | `AgentDetail` (full agent surface), `ComsPanel` → `GET /api/coms`; TagCloud static |
| `/agents` | `Agents.vue` | `GET/POST /api/agents`, `DELETE /api/agents/:id`, **`WS /ws/events`** | same `AgentDetail` |
| `/sessions` | `Sessions.vue` | `GET /api/sessions`, `GET /api/sessions/:id` | — |
| `/schedules` | `Schedules.vue` | `GET /api/schedules` | read-only list |
| `/skills` | `Skills.vue` | `GET /api/skills` | — |
| `/extensions` | `Extensions.vue` | `GET /api/extensions` | — |
| `/templates` | `Templates.vue` | `GET /api/templates` | display only (no deploy/create from UI) |
| `/teams` | `Teams.vue` | `GET /api/teams`, `POST /api/teams/:name/deploy` | — |
| `/console` | `Console.vue` | `GET /api/voice/tts/status` | `SystemConsole` → ticket + `WS /ws/logs`; `SystemFlixzPanel` → flixz REST |
| `/ops` | `OperatorRoom.vue` | `GET /api/operator-queue/stats` | `OperatorQueue` → list/PATCH/DELETE `/api/operator-queue` |
| `/replay` | `Replay.vue` | `GET /api/sessions` | `ReplayTimeline` (client-side timeline) |
| `/audit` | `AuditLog.vue` | `GET /api/audit-log`, `/types`, `/stats`, `/export` | — |
| `/settings` | `Settings.vue` | **`GET /api/health`** (see drift) | paths are hardcoded labels only |

### Global (App.vue)

| Component | APIs |
|-----------|------|
| `OnboardingChecklist` | `GET /api/agents`, `/api/sessions`, `/api/tags` |
| `EditorHelpPanel` | none (static help) |
| `ToastContainer` | none (toast bus) |

### AgentDetail surface (modal from Dashboard / Agents)

| Tab / panel | APIs / WS |
|-------------|-----------|
| Info | `GET /api/agents/:id`, `GET /api/agents/:id/profile` |
| Chat | `GET /api/sessions?agent_id=…`, `POST /api/agents/:id/chat` (SSE), session detail |
| Slice Plays | `GET /api/skills`, `POST /api/agents/:id/chat` |
| Terminal | `POST /api/ws/ticket` → **`WS /ws/terminal/:id?ticket=&mode=`** |
| Files | list/preview/download/upload/mkdir/delete under `/api/agents/:id/files` |
| Git | status/log/diff/init/commit/push/pull under `/api/agents/:id/git` |
| Credentials | CRUD `/api/agents/:id/credentials` (+ `/values`) |
| Connectors | `/api/connectors`, `/available` |
| Flixz | `POST /api/agents/:id/flixz/extract` |
| Sharing | shares + access-requests (uses `authHeaders()`) |
| Edit | `GET /api/agents/:id`, `GET /api/skills`, `GET /api/tags`, `PATCH/PUT`-style update via `PUT`-ish agent update fetch |
| Voice (workspace) | ticket → **`WS /ws/voice/:id`**, `POST /api/system/chat` or `/api/voice/process`, TTS REST |

### NavIsland extras

- `HostTelemetry` → `GET /api/telemetry/host`
- System voice → `VoiceWorkspace` with `agentId=__system__`
- `UserMenu` → auth store logout / user display

---

## 3. Auth store vs `PI_NO_AUTH`

**Frontend:** [`dashboard/src/stores/auth.ts`](../../dashboard/src/stores/auth.ts)  
**Backend:** [`pi_orchestrator/routers/auth.py`](../../pi_orchestrator/routers/auth.py) (`PI_NO_AUTH` env), [`ws_tickets.py`](../../pi_orchestrator/routers/ws_tickets.py)

### Intended daily path (`PI_NO_AUTH=1`)

1. Router `beforeEach` calls `checkNoAuth()`.
2. `GET /api/auth/me` **without** `Authorization` → backend returns default admin via `get_current_user` → `res.ok` → `_noAuth = true` → **all routes open** (no login).
3. Most REST calls omit Bearer tokens; that is fine while core routers do **not** depend on `get_current_user` (only sharing, users, `/me`, and ticket mint in auth mode do).

### Optional local auth (`PI_NO_AUTH` off)

1. `checkNoAuth()` fails (401 without header) → guard requires `auth.isAuthenticated` (token in `localStorage` key `pi_auth_token`).
2. Login/register set token + user; `loadUser()` hits `GET /api/auth/me` with Bearer.
3. **`authHeaders()` is almost unused** — only [`SharingPanel.vue`](../../dashboard/src/components/SharingPanel.vue) attaches it. WS ticket mint, chat, agents, terminal, etc. do **not**.

### Implications

| Mode | Behavior |
|------|----------|
| `PI_NO_AUTH=1` | Matches product intent; login page is unreachable in practice (guard always allows). |
| Auth on | Login works; **terminal/voice/logs tickets fail** without Bearer on `POST /api/ws/ticket`; sharing works if token present; rest of API still open on backend (no `Depends(get_current_user)` on agents/chat/etc.). |

`checkNoAuth` caches the first result for the SPA lifetime (`_noAuthChecked`); env flip requires reload.

---

## 4. WebSocket ticket usage

Backend mint: `POST /api/ws/ticket` → single-use ~30s ticket (`ws_ticket_service`).

| Client | Ticket? | Endpoint | Evidence |
|--------|---------|----------|----------|
| `TerminalPanel.vue` | **Yes** | `POST /api/ws/ticket` then `WS /ws/terminal/{agentId}?ticket=&mode=` | ticket required; backend closes 4001 if invalid |
| `SystemConsole.vue` | **Yes** | ticket → `WS /ws/logs?ticket=` | same |
| `VoiceWorkspace.vue` | **Yes** | ticket → `WS /ws/voice/{agentId\|__system__}?ticket=` | same |
| `stores/app.ts` `connectWebSocket` | **No** | `WS /ws/events` | intentional on server: “No auth needed — single-user, bound to localhost” (`events.py`) |

**Gaps when optional auth is enabled:**

- Ticket `fetch` calls do **not** pass `auth.authHeaders()` → 401 from mint → silent fail / reconnect loop (terminal returns early; console retries every 3s).
- `/ws/events` remains open without ticket (by design for localhost bus).

**PI_NO_AUTH=1:** mint always succeeds as user `admin`; ticketed sockets work without login.

---

## 5. Dead components (no parent import)

Static import graph of `dashboard/src` (filename / path references only). **No parent import:**

| Component | Notes |
|-----------|--------|
| `components/CapacityMeter.vue` | Generic used/total bar; unused |
| `components/McpKeysPanel.vue` | Full UI for `GET/POST/DELETE /api/mcp-keys`; never mounted (settings does not include it) |
| `components/ResourceModal.vue` | Create-agent modal with tools/skills; only imports `ModelSelector`; nothing opens it |
| `components/SlicesPanel.vue` | Ops control plane UI (`/api/ops/*`); unused (ops page uses OperatorQueue instead) |
| `components/YamlEditor.vue` | YAML textarea + highlight; unused |
| `components/chat/ChatLoadingIndicator.vue` | Only re-exported from `chat/index.js`; barrel is never imported |

### Dead / unwired store

| Store | Notes |
|-------|--------|
| `stores/notifications.ts` | **Never imported** by any view/component. Defines `handleWsEvent` but `app.ts` WS handler does not call it. Also fails typecheck (`toastBus.warning` missing). |

`ResourceModal` → `ModelSelector` does not keep ModelSelector alive; AgentDetail imports ModelSelector separately.

---

## 6. API contract drift suspects

| # | Frontend | Backend / reality | Severity |
|---|----------|-------------------|----------|
| 1 | `Settings.vue` → `GET /api/health` | App exposes **`GET /health`** only (`main.py`) | Settings system card always empty |
| 2 | WS ticket mint without `Authorization` | Auth mode requires Bearer on `POST /api/ws/ticket` | Terminal/voice/logs break with auth on |
| 3 | Almost all `fetch` omit `authHeaders()` | Sharing/users require user; rest open | Inconsistent optional-auth UX |
| 4 | `Agents.vue` create body `{ name }` only | `PiAgentConfig.name` must match `^[a-zA-Z0-9_-]+$` | Spaces/special chars → 400; no UI validation |
| 5 | `ChatPanel.switchSession` loads `GET /api/sessions/:id` but only applies `name` | Session payload has `messages` (Sessions view uses them) | Switching history does not restore chat bubbles |
| 6 | `ChatPanel.loadMessages` only sets latest session id | Does not hydrate prior turns into UI | “Resume” may send session_id without showing history |
| 7 | `TagCloud.vue` hardcoded tags/counts | `GET /api/tags` exists; OnboardingChecklist uses it | Dashboard tag UI is decorative |
| 8 | Dashboard “Uptime 99.8%” hardcoded | `GET /api/ops/status` has `uptime_hours` (dead SlicesPanel) | Fake metric on home |
| 9 | `Templates.vue` list only | Backend has template detail; no create-from-template in UI | Dashboard “New Agent” → templates is display-only |
| 10 | `useNotificationStore` / toast on WS events | `app.ts` only refetches agents/activities | Event bus types like `agent_created` never toast via store |
| 11 | AuditLog `stats.event_types` iteration typing | Runtime object keys are strings; TS thinks numeric | Typecheck fail; runtime usually OK |
| 12 | AgentDetail chunk pulls full agent stack | Build works; operator load cost | Performance smell, not contract |

---

## 7. Findings P0–P3 (evidence; no fixes)

### P0 — correctness / intended daily path

| ID | Finding | Evidence |
|----|---------|----------|
| P0-1 | **Settings health endpoint wrong** | `Settings.vue` fetches `/api/health`; orchestrator only registers `/health`. Card stays `-`. |
| P0-2 | **vue-tsc fails (CI risk if typecheck is gated)** | Exit 1; 9 errors in `vue-tsc.log`. Vite still green. |

### P1 — operator UX / optional-auth footguns

| ID | Finding | Evidence |
|----|---------|----------|
| P1-1 | **Ticketed WebSockets do not send auth headers** | `TerminalPanel`, `SystemConsole`, `VoiceWorkspace`: bare `POST /api/ws/ticket`. Fails when `PI_NO_AUTH` is off. |
| P1-2 | **Chat history UI not restored on session switch / load** | `ChatPanel.vue` `switchSession` / `loadMessages` ignore message bodies from `/api/sessions/:id`. |
| P1-3 | **Agent create name validation mismatch** | UI free text; backend `PiAgentConfig` regex `^[a-zA-Z0-9_-]+$`. |

### P2 — dead code / incomplete surfaces

| ID | Finding | Evidence |
|----|---------|----------|
| P2-1 | **Five dead components + ChatLoadingIndicator** | Import graph: CapacityMeter, McpKeysPanel, ResourceModal, SlicesPanel, YamlEditor (+ loading indicator only in barrel). |
| P2-2 | **notifications store unwired** | No importers; WS path in `app.ts` does not call `handleWsEvent`. |
| P2-3 | **Ops / MCP / rich create UI exist but unmounted** | `SlicesPanel` (`/api/ops/*`), `McpKeysPanel` (`/api/mcp-keys`), `ResourceModal` unused; Settings/Ops don’t host them. |
| P2-4 | **TagCloud + uptime placeholders** | Static tags; hardcoded uptime on Dashboard. |

### P3 — polish / types / bundle

| ID | Finding | Evidence |
|----|---------|----------|
| P3-1 | DOM / toast typing debt | ChatHistoryDropdown `.select`, UserMenu `_clickOutside`, SpeechRecognition types, `toastBus.warning` missing. |
| P3-2 | AuditLog `event_types` key typing | Lines 202–203 vue-tsc errors. |
| P3-3 | AgentDetail ~592 kB chunk | vite-build.log size warning. |
| P3-4 | Dual `connectWebSocket` entry | Dashboard + Agents each call it; reconnect is on close only (usually one page at a time). |
| P3-5 | Templates/Schedules read-only | Copy admits “Create one via the API” for schedules. |

---

## 8. Architecture snapshot (local operator)

```
main.ts router + auth guard (checkNoAuth)
    │
    ├─ App.vue: ToastContainer, OnboardingChecklist, EditorHelpPanel
    │
    ├─ stores/app.ts: agents, activities, WS /ws/events (no ticket)
    ├─ stores/auth.ts: token, checkNoAuth, authHeaders (rarely used)
    └─ stores/notifications.ts: DEAD (unimported)

Most pages: NavIsland + Sidebar + view content
Agent detail: modal stack → chat SSE / ticketed terminal & voice / files / git / …
```

**Aligned with product intent:** localhost FastAPI, `PI_NO_AUTH=1` happy path, pi subprocess agents, no cloud control plane required.

**Not in scope of this review:** implementing fixes, SaaS multi-tenant hardening, or expanding beyond local single-operator UX.

---

## 9. Suggested local-only follow-ups (observation only)

Ordered for a single-machine operator console—not productization:

1. Point Settings at `/health` (or add `/api/health` alias on the backend—pick one).
2. Clear the nine vue-tsc errors so typecheck can gate PRs.
3. If optional auth remains: pass `authHeaders()` on ticket mint (and document that core REST is still open).
4. Wire or delete dead panels (McpKeys, Slices/ops controls, ResourceModal) into Settings/Ops as needed for the local operator.
5. Hydrate chat messages from session API on load/switch.
6. Replace TagCloud / uptime placeholders with real `/api/tags` and `/api/ops/status` data (or remove).

---

*End of review. Logs: `docs/health/vue-tsc.log`, `docs/health/vite-build.log`.*
