# Backend review — `pi_orchestrator/`

| Field | Value |
|-------|--------|
| **Git SHA** | `9249dfa` |
| **Date** | 2026-07-15 |
| **Scope** | `pi_orchestrator/` — main, config, database, models, routers/, services/ |
| **Product binding** | Local single-operator; default `127.0.0.1:8420` + `PI_NO_AUTH=1` ([`docs/PRODUCT_INTENT.md`](../PRODUCT_INTENT.md)) |
| **Method** | Static evidence review of running code; **no fixes implemented** |

Severity scale used here:

| Level | Meaning (local single-operator lens) |
|-------|--------------------------------------|
| **P0** | Broken critical path or guaranteed crash / data corruption on normal operator use |
| **P1** | Serious correctness or security defect; high impact if host bound beyond loopback or any local process can hit the API |
| **P2** | Schema/API drift, weak crypto, incomplete lifecycle; degraded reliability or false confidence |
| **P3** | Hygiene, incomplete cleanup, dead/unused hooks, low-likelihood edge cases |

---

## Threat model (localhost, single-user)

**Intended posture**

- One operator on one machine; API default host `127.0.0.1` ([`config.py:32-33`](../../pi_orchestrator/config.py)).
- Daily path: `PI_NO_AUTH=1` → most REST routes intentionally unauthenticated; operator identity is “whoever can reach the port” ([`auth.py:32,128-130`](../../pi_orchestrator/routers/auth.py)).
- Agents are **host-user-privileged `pi` / shell subprocesses**, not sandboxed containers ([`pi_session_service.py`](../../pi_orchestrator/services/pi_session_service.py), [`terminal.py`](../../pi_orchestrator/routers/terminal.py)).
- Persistence: SQLite under `~/.pi/agent/orchestrator.db` + JSONL session files + shared-memory files ([`config.py:28`](../../pi_orchestrator/config.py), [`shared_memory_service.py:18`](../../pi_orchestrator/services/shared_memory_service.py)).

**Trust boundaries that matter**

| Boundary | Risk if crossed |
|----------|-----------------|
| Loopback-only bind | Primary control. Anything that can open TCP to `:8420` as the operator’s user can drive agents, terminals, credentials, settings, ops. |
| `PI_ORCHESTRATOR_HOST=0.0.0.0` (or LAN bind) + `PI_NO_AUTH=1` | Full remote equivalent of local shell via `/ws/terminal?mode=bash`, chat with bash tools, credential dump, package install. |
| Optional “auth mode” (`PI_NO_AUTH` unset) | **Does not currently protect** agents/chat/credentials/ops/files (auth deps only on a few routers). Treat as incomplete convenience, not a hardened boundary. |
| Same-machine local processes / malware | Can call unauthenticated REST; can read SQLite and key material under `~/.pi/agent/` if filesystem perms allow. |
| Webhook tokens (`/api/connectors/webhook/{token}`) | Network-callable knowledge injection if host is reachable and token known/guessable. |
| Subprocess surface | `pi`, `/bin/bash --login`, `ffmpeg`/`yt-dlp`, `git`, `tail -F` inherit operator env and FS rights. |

**Out of scope for this product (do not “fix” with SaaS controls)**

Multi-tenant isolation, cloud IdP, billing, fleet RBAC. Local optional login/sharing exists as convenience only.

**Assumptions for “acceptable” under intent**

- Bind remains loopback unless the operator knowingly expands it.
- Operator understands agents run with their full user privileges (bash tool, terminal bash mode).
- Secrets live on the same machine; encryption-at-rest is obfuscation against casual disk inspection, not multi-tenant crypto.

---

## Findings

### P0 — Credentials write/delete path calls non-existent DB helpers

**Evidence:** [`routers/credentials.py:126-134,148-150`](../../pi_orchestrator/routers/credentials.py) calls `db._safe_execute` and `db._safe_commit`.

**Evidence:** Grep of `pi_orchestrator/` shows **no** `def _safe_execute` / `def _safe_commit` in `database.py` (only `_safe_add_column` at [`database.py:307`](../../pi_orchestrator/database.py)).

**Impact:** `POST /api/agents/{id}/credentials` and `DELETE .../credentials/{name}` raise `AttributeError` on every use. Credential **set/delete is broken** on current code. List and `/values` still use raw `conn.execute`.

---

### P0 — Optional auth mode is incomplete (most mutating surfaces unauthenticated)

**Evidence:** `get_current_user` / `require_admin` appear only in:

- [`routers/auth.py`](../../pi_orchestrator/routers/auth.py) (`/me`)
- [`routers/users.py`](../../pi_orchestrator/routers/users.py)
- [`routers/sharing.py`](../../pi_orchestrator/routers/sharing.py)
- Partial ticket gating on some WebSockets ([`terminal.py`](../../pi_orchestrator/routers/terminal.py), [`voice.py`](../../pi_orchestrator/routers/voice.py), [`console.py`](../../pi_orchestrator/routers/console.py), mint in [`ws_tickets.py`](../../pi_orchestrator/routers/ws_tickets.py))

**Evidence:** No `Depends(get_current_user)` on agents, chat, credentials, files, ops, system, settings, schedules, connectors, flixz, git, mcp_keys, operator_queue, telemetry, etc.

**Impact under product intent:** With default `PI_NO_AUTH=1` this matches “open localhost API.” **P0 if an operator disables `PI_NO_AUTH` expecting protection** — JWT gate is illusory for almost all control plane actions (create/delete agents, stop-all, install extensions, plaintext credential read, bash terminal ticket still obtainable only via unauthenticated ticket mint when `PI_NO_AUTH` is off *for tickets*, but REST remains open).

When `PI_NO_AUTH` is off, ticket mint requires JWT ([`ws_tickets.py:41-46`](../../pi_orchestrator/routers/ws_tickets.py)), but REST chat/ops/credentials do not.

---

### P1 — Plaintext credential dump endpoint contradicts API contract

**Evidence:** Module docstring claims values are never returned plaintext and are injected into pi sessions ([`credentials.py:1-6`](../../pi_orchestrator/routers/credentials.py)).

**Evidence:** `GET /api/agents/{agent_id}/credentials/values` returns `{name: decrypted}` ([`credentials.py:158-168`](../../pi_orchestrator/routers/credentials.py)).

**Evidence:** No auth dependency on that route. No call sites inject credentials into `stream_chat` / terminal env (grep: inject language only in docs; `pi_session_service` does not load credentials table).

**Impact:** Any local client that can hit the API can exfiltrate all stored agent secrets. Doc claim of session injection is false — secrets sit encrypted-ish in SQLite and are re-exportable via HTTP.

---

### P1 — Terminal `mode=bash` is full login shell as the orchestrator user

**Evidence:** [`terminal.py:104-113`](../../pi_orchestrator/routers/terminal.py) spawns `/bin/bash --login` with `env = os.environ.copy()` ([`terminal.py:89-90`](../../pi_orchestrator/routers/terminal.py)).

**Evidence:** WS gated only by single-use ticket; under `PI_NO_AUTH=1`, ticket mint requires no credential ([`ws_tickets.py:38-49`](../../pi_orchestrator/routers/ws_tickets.py)).

**Impact:** Equivalent to interactive host shell on the operator account. Acceptable only under strict loopback + trusted local clients. Catastrophic if host is network-reachable.

---

### P1 — Flixz accepts arbitrary local filesystem paths (and URLs)

**Evidence:** `FlixzExtractRequest.video_path: str` with no workspace root constraint ([`flixz.py:21-28`](../../pi_orchestrator/routers/flixz.py)).

**Evidence:** `_resolve_video_path` expands user path and passes any existing file to ffprobe/ffmpeg ([`flixz_service.py:60-72,409-427`](../../pi_orchestrator/services/flixz_service.py)); HTTP(S) triggers `yt-dlp` download ([`flixz_service.py:74-118`](../../pi_orchestrator/services/flixz_service.py)).

**Impact:** Unauthenticated REST can read arbitrary files the OS user can read (via ffmpeg) and can pull remote media to disk under `~/.pi/flixz/output/`. SSRF-ish + local file processing, not multi-tenant isolation, but high local impact.

---

### P1 — Files path check uses prefix `startswith` (traversal / sibling prefix risk)

**Evidence:** [`files.py:42-50`](../../pi_orchestrator/routers/files.py):

```python
target = (base / clean).resolve()
if not str(target).startswith(str(base.resolve())):
    raise HTTPException(status_code=403, detail="Path traversal denied")
```

**Impact:** Classic failure mode: base `.../managed/agent` allows `.../managed/agent2/...` because of string prefix without path separator boundary. Combined with unauthenticated list/download/upload/delete, can cross agent workspaces when names share a prefix. Prefer `Path.relative_to` / commonpath checks (not implemented).

**Related:** Upload uses `file.filename` then `relative_to` ([`files.py:277-279`](../../pi_orchestrator/routers/files.py)); malicious names that leave `base` raise unhandled `ValueError` rather than clean 403.

---

### P1 — Session workspace path key is inconsistent (`agent_name` vs `agent_id`)

| Component | Path key | Evidence |
|-----------|----------|----------|
| Chat / session service | `PI_MANAGED_SESSIONS_DIR / agent_name` | [`pi_session_service.py:55-60,148`](../../pi_orchestrator/services/pi_session_service.py) |
| Files router | `PI_MANAGED_SESSIONS_DIR / agent["name"]` | [`files.py:108`](../../pi_orchestrator/routers/files.py) |
| Terminal | `PI_MANAGED_SESSIONS_DIR / agent_id` | [`terminal.py:85-87`](../../pi_orchestrator/routers/terminal.py) |
| Cleanup walker | any subdir under managed | [`cleanup_service.py:88-105`](../../pi_orchestrator/services/cleanup_service.py) |

**Impact:** Terminal JSONL sessions land under a different tree than chat/files. File manager does not see terminal sessions; cleanup may expire mismatched layouts. Operator confusion and silent data split.

---

### P1 — System chat “create agent” calls wrong `db.create_agent` signature

**Evidence:** [`system_chat_service.py:88`](../../pi_orchestrator/services/system_chat_service.py):

```python
db.create_agent(agent_id, name, tools=["read", "bash", "web_search"])
```

**Evidence:** Real signature is `create_agent(name, model="", persona=None, tools=..., ...)` and **generates its own id** ([`database.py:360-388`](../../pi_orchestrator/database.py)).

**Impact:** Voice/system intent “create agent X” stores `agent_id` as **name** and spoken name as **model**. Creates wrong agents or integrity errors; does not use `pi_session_service.create_agent` (no session dir setup).

---

### P1 — Scheduler does not use session service / `PI_BINARY` / managed sessions

**Evidence:** [`schedule_service.py:105-122`](../../pi_orchestrator/services/schedule_service.py) builds `cmd = ["pi", "--mode", "json", "--print"]` with hardcoded `"pi"`, not `config.PI_BINARY`.

**Evidence:** No `--session` file, no profile/shared-memory injection, no `_running` registry, no `stream_chat`.

**Impact:** Scheduled work diverges from interactive chat: different binary resolution, no durable session JSONL under managed paths, no credential/profile injection (even if chat had it), harder ops/kill/timeout alignment with dashboard session history.

---

### P2 — Deterministic Fernet keys for connectors/credentials; weak XOR fallback

**Evidence — connectors:** Key = `sha256(f"slice-of-pi-connector-{hostname}-{port}")` then Fernet; on missing `cryptography`, plaintext stored ([`database.py:27-55`](../../pi_orchestrator/database.py)).

**Evidence — credentials:** Separate derivation `slice-of-pi-cred-{hostname}-{port}` or `orchestrator.key`; without Fernet, XOR with key bytes ([`credentials.py:29-77`](../../pi_orchestrator/routers/credentials.py)).

**Evidence — MCP keys:** Random key file `.mcp_key` under agent dir ([`mcp_keys.py:34-51`](../../pi_orchestrator/routers/mcp_keys.py)) — stronger, but third scheme.

**Impact:** Three incompatible schemes. Hostname+port-derived keys are reproducible by any process that knows them. XOR is not authenticated encryption. DB copy + known hostname decrypts connector/credential ciphertext. Fine as local obfuscation only — do not treat as strong secret store.

---

### P2 — Password hashing is unsalted SHA-256; default admin password `admin`

**Evidence:** Register/login hash with `hashlib.sha256(password.encode()).hexdigest()` ([`auth.py:106,193,215-216`](../../pi_orchestrator/routers/auth.py)).

**Evidence:** `_get_default_admin` creates `admin` / hash of `"admin"` if missing ([`auth.py:102-109`](../../pi_orchestrator/routers/auth.py)).

**Impact:** Optional local auth is weak against offline DB theft. Open registration with min password length 4 ([`auth.py:160-163`](../../pi_orchestrator/routers/auth.py)). JWT signing secret defaults to hash of hostname ([`auth.py:34-36`](../../pi_orchestrator/routers/auth.py)).

---

### P2 — Operator queue schema vs row mapping drift

**Evidence — SCHEMA:** columns  
`id, agent_id, agent_name, item_type, description, details, status, priority (INTEGER), created_at, resolved_at, resolved_by, resolution`  
([`database.py:199-212`](../../pi_orchestrator/database.py)).

**Evidence — migrations:** add `type`, `title`, `description` (already exists), `updated_at`, `resolution_note`, `priority TEXT` (name already exists as INTEGER → add fails) ([`database.py:331-337`](../../pi_orchestrator/database.py)).

**Evidence — API mapping:** `_row_to_dict` uses fixed indices assuming  
`type, title, description, status, priority, created_at, updated_at, resolved_at, resolution_note` at positions 3–11 ([`operator_queue.py:35-48`](../../pi_orchestrator/routers/operator_queue.py)).

**Evidence — INSERT:** writes both `item_type` and `type`, stores string priority into column typed INTEGER in CREATE ([`operator_queue.py:117-119`](../../pi_orchestrator/routers/operator_queue.py)).

**Impact:** `SELECT *` column order after CREATE+ALTER does not match `_row_to_dict` index layout → wrong fields in API (e.g. `title` may be `description`/`details`, `updated_at` may be `resolved_at`). Fresh vs migrated DBs can differ. Positional indexing on `sqlite3.Row` is fragile.

---

### P2 — MCP key model vs storage inconsistency

**Evidence:** Pydantic/`models.py` MCP key story is hash-only create response ([`models.py:243-261`](../../pi_orchestrator/models.py)).

**Evidence:** `create_mcp_key` stores encrypted blob in **both** `key_hash` and `value` ([`database.py:1142-1145`](../../pi_orchestrator/database.py)); `list_mcp_keys` selects `value` ([`database.py:1127-1129`](../../pi_orchestrator/database.py)).

**Evidence:** Migration adds `value` column ([`database.py:350`](../../pi_orchestrator/database.py)); schema also has `key_hash NOT NULL UNIQUE` ([`database.py:141-147`](../../pi_orchestrator/database.py)).

**Impact:** `key_hash` is not a hash of the secret; uniqueness is on ciphertext. Dual columns invite confusion for any consumer expecting one-way hashes.

---

### P2 — Dual agent identity stores for tags

**Evidence:** `agents.tags` JSON column + normalized `tags` / `agent_tags` tables; `update_agent` keeps both in sync ([`database.py:417-450`](../../pi_orchestrator/database.py)).

**Evidence:** Chat injection reads only `agent.get("tags")` JSON ([`pi_session_service.py:172-174`](../../pi_orchestrator/services/pi_session_service.py)).

**Impact:** Direct SQL or partial writers can desync list-by-tag vs prompt injection. Tags router uses the dual-write path ([`tags.py`](../../pi_orchestrator/routers/tags.py) via `db.update_agent`).

---

### P2 — Voice REST path double-creates sessions and double-counts metrics

**Evidence:** `process_voice_transcript` creates a session row, then calls `stream_chat` which **also** creates a full session + process ([`voice_service.py:47-65`](../../pi_orchestrator/services/voice_service.py), [`pi_session_service.py:147-164`](../../pi_orchestrator/services/pi_session_service.py)).

**Evidence:** After stream, voice path again `update_session`, `update_agent_tokens`, `increment_session_count` ([`voice_service.py:81-84`](../../pi_orchestrator/services/voice_service.py)) though `stream_chat` already updated tokens/count ([`pi_session_service.py:254-260`](../../pi_orchestrator/services/pi_session_service.py)).

**Impact:** Orphan/duplicate session rows; inflated token and session_count; voice `session_id` param does not resume the pi JSONL conversation (stream_chat always new file).

---

### P2 — Flixz delete does not remove output files

**Evidence:** Router claims “Delete a flixz run and its output files” ([`flixz.py:68-74`](../../pi_orchestrator/routers/flixz.py)).

**Evidence:** `delete_flixz_run` only `DELETE FROM flixz_runs` ([`database.py:1269-1274`](../../pi_orchestrator/database.py)). No `shutil.rmtree` of `output_dir`.

**Impact:** Disk retention under `~/.pi/flixz/output/` after “delete.”

---

### P2 — Agent destroy does not remove on-disk session directories

**Evidence:** `destroy_agent` kills processes and `delete_agent` DB row ([`pi_session_service.py:102-113`](../../pi_orchestrator/services/pi_session_service.py)); no `rmtree` of `_session_dir(agent_name)`.

**Impact:** Orphan JSONL under managed sessions until cleanup retention (default 7 days, age by mtime) ([`cleanup_service.py:27-28`](../../pi_orchestrator/services/cleanup_service.py)).

---

### P2 — Events WebSocket has no ticket; console/logs REST unauthenticated

**Evidence:** `/ws/events` accepts immediately with comment “No auth needed” ([`events.py:22-32`](../../pi_orchestrator/routers/events.py)).

**Evidence:** `GET /api/logs/tail` reads `~/.pi/agent/orchestrator.log` with no auth ([`console.py:34-50`](../../pi_orchestrator/routers/console.py)); live `/ws/logs` requires ticket.

**Impact:** Consistent with PI_NO_AUTH localhost; log tail may leak secrets written to DEBUG logs if any component logs sensitive data.

---

### P2 — SPA static fallback can serve paths outside `dashboard/dist`

**Evidence:** [`main.py:221-226`](../../pi_orchestrator/main.py):

```python
file_path = DASHBOARD_DIST / path
if file_path.is_file():
    return FileResponse(file_path)
```

No `resolve()` + containment check. Path segments with `..` can escape `DASHBOARD_DIST` depending on platform path joining.

**Impact:** Only when `--serve-dashboard` is enabled; potential arbitrary file read as the server user if path traversal succeeds.

---

### P2 — SQLite DB and key files lack enforced `chmod 600`

**Evidence:** `ORCHESTRATOR_CONFIG` is chmod’d user-only ([`config.py:85-89`](../../pi_orchestrator/config.py)); `DATABASE_PATH` connection has no permission hardening ([`database.py:282-289`](../../pi_orchestrator/database.py)). Credential/MCP key files not consistently permissioned after write.

**Impact:** Multi-user host: group/other-readable DB/key files increase secret exposure. Single-user Mac default often umask-restricted, but not guaranteed.

---

### P2 — Models vs DB status / API surface drift

**Evidence:** `PiAgentStatus` includes `RUNNING`, `IDLE`, `BUSY`, etc. ([`models.py:22-28`](../../pi_orchestrator/models.py)); create sets DB status `'created'` then service sets `'idle'` ([`database.py:377`](../../pi_orchestrator/database.py), [`pi_session_service.py:98`](../../pi_orchestrator/services/pi_session_service.py)).

**Evidence:** `SessionStatus` has no `expired`; cleanup writes `'expired'` ([`database.py:1293-1300`](../../pi_orchestrator/database.py), [`models.py:31-35`](../../pi_orchestrator/models.py)).

**Evidence:** No general agent config PATCH (model/tools/skills/system_prompt) — only tags ([`tags.py`](../../pi_orchestrator/routers/tags.py)); agents router is create/list/get/delete only ([`agents.py:94-138`](../../pi_orchestrator/routers/agents.py)).

**Impact:** Client validation / OpenAPI types can reject or mislabel real DB values; operator cannot edit agent config via API without delete/recreate (unless other undocumented paths).

---

### P3 — Lifespan never starts WS ticket periodic cleanup

**Evidence:** `WsTicketService.start_periodic_cleanup` exists ([`ws_ticket_service.py:77-91`](../../pi_orchestrator/services/ws_ticket_service.py)) but is not called from [`main.py` lifespan](../../pi_orchestrator/main.py). Cleanup only on mint/consume.

**Impact:** Minor; tickets are short TTL and popped on use.

---

### P3 — Schedule job reload rebinds stale schedule dicts

**Evidence:** `_reload_schedules` adds jobs with `args=[schedule]` snapshot ([`schedule_service.py:90-96`](../../pi_orchestrator/services/schedule_service.py)); for existing jobs only `reschedule_job` (trigger), not message/model args update.

**Impact:** Changing schedule message/model may not apply until remove/re-add job cycle if job id already present.

---

### P3 — Connector engine imports event_bus from routers package

**Evidence:** [`connectors/engine.py:87`](../../pi_orchestrator/services/connectors/engine.py) `from ...routers.events import event_bus` while canonical bus is [`services/event_bus.py`](../../pi_orchestrator/services/event_bus.py) and routers re-export/use that. (Router file imports `from ..services.event_bus import event_bus`.)

**Impact:** Works today if same object; layering smell; risk if re-export ever diverges.

---

### P3 — System chat stop-all only flips DB status, does not kill processes

**Evidence:** `_stop_all_agents` calls `update_agent_status(..., "stopped")` only ([`system_chat_service.py:148-157`](../../pi_orchestrator/services/system_chat_service.py)); ops `stop-all` calls `kill_all()` ([`ops.py:51-56`](../../pi_orchestrator/routers/ops.py)).

**Impact:** Voice “stop all” leaves pi subprocesses running.

---

### P3 — Hardcoded operator-local path in TTS error string

**Evidence:** Unavailable mossy message embeds `/Users/kc/mossy` ([`tts_service.py:104-107`](../../pi_orchestrator/services/tts_service.py)).

**Impact:** Leaks developer machine path in API errors; wrong for other operators.

---

### P3 — Webhook auth_state matched by linear decrypt of all connectors

**Evidence:** [`connectors.py:89-102`](../../pi_orchestrator/routers/connectors.py) loads every enabled connector’s decrypted `auth_state` to compare `token`.

**Impact:** O(n) decrypt on each webhook; tokens ≥8 chars only ([`webhook.py:29-33`](../../pi_orchestrator/services/connectors/builtins/webhook.py)). Acceptable at small local scale; token quality is the only auth for that route.

---

### P3 — `init_db` trailing line-continuation on `commit`

**Evidence:** [`database.py:352`](../../pi_orchestrator/database.py): `conn.commit()\`.

**Impact:** Valid Python continuation over blank line; noise only. Not a crash.

---

## Theme summaries

### Lifecycle (startup / shutdown / background jobs)

- Lifespan starts: logging, dirs, `init_db`, event bus, connector sync engine, optional scheduler/cleanup, then yield; shutdown stops sync, `kill_all`, scheduler, cleanup, bus, DB conn ([`main.py:85-143`](../../pi_orchestrator/main.py)).
- Pi binary absence is **warning only** at startup ([`main.py:92-100`](../../pi_orchestrator/main.py)); sessions fail later.
- Scheduler/cleanup optional via ImportError ([`main.py:33-41`](../../pi_orchestrator/main.py)).
- Gaps: agent delete leaves files; flixz delete leaves files; voice/system stop incomplete; schedule path not integrated with session registry.

### Session / pi binary

- Primary path: `asyncio.create_subprocess_exec(PI_BINARY, "--mode", "json", "--session", ...)` ([`pi_session_service.py:197-213`](../../pi_orchestrator/services/pi_session_service.py)).
- In-memory `_running` registry; timeout kill; stderr drain for deadlock avoidance.
- Divergent invokers: terminal, schedule (`"pi"` literal), system_chat (`--system` not `--system-prompt`).
- Session dirs: name vs id split (P1 above).

### DB schema / migrations

- Idempotent `CREATE TABLE IF NOT EXISTS` + `_safe_add_column` ([`database.py:316-352`](../../pi_orchestrator/database.py)).
- No versioned migration table; additive only; cannot rename/drop cleanly.
- Clear drift: operator_queue, mcp_keys, audit_log dual columns (`action` + `event_type`).
- Thread-local SQLite + WAL ([`database.py:279-289`](../../pi_orchestrator/database.py)); fine for single writer local use.

### Auth (`PI_NO_AUTH`)

- Intended open loopback API when `PI_NO_AUTH=1`.
- Custom HMAC “JWT-like” tokens ([`auth.py:51-99`](../../pi_orchestrator/routers/auth.py)); not a standard JWT library.
- Sharing/users gated; core fleet API not gated → incomplete optional auth (P0/P1 depending on operator expectation).
- WS tickets 30s single-use ([`ws_ticket_service.py`](../../pi_orchestrator/services/ws_ticket_service.py)).

### Credentials encryption

- Store-encrypt, list-mask, **values endpoint decrypts all** (P1).
- Encryption schemes inconsistent; no session env injection despite docs (P1/P2).
- Write path broken via missing helpers (P0).

### Files path traversal

- Intentional confinement to managed session tree; implementation uses `startswith` (P1).
- Upload size cap 50MB; empty-dir-only delete; root workspace delete blocked ([`files.py:30,330-348`](../../pi_orchestrator/routers/files.py)).

### Terminal

- PTY + async bridge; solid lifecycle cleanup in `finally` ([`terminal.py:233-263`](../../pi_orchestrator/routers/terminal.py)).
- `pi` vs `bash` modes; bash is full host shell (P1).
- Ticket-gated WS.

### Voice / TTS

- WS is ack/status only; REST `/api/voice/process` drives chat ([`voice.py`](../../pi_orchestrator/routers/voice.py)).
- TTS proxies mossy on `127.0.0.1:7860` ([`tts_service.py:19`](../../pi_orchestrator/services/tts_service.py)).
- Double session/metrics bug (P2).

### Flixz

- Heavy local media pipeline; no path allowlist; base64 frames in response (up to 30) ([`flixz_service.py:429-433`](../../pi_orchestrator/services/flixz_service.py)).
- Optional Gemini/Claude describe + native macOS STT.

### Connectors

- Plugin registry + webhook builtin; auth_state Fernet-encrypted in DB.
- Sync engine background loop 60s ([`engine.py:23,176-207`](../../pi_orchestrator/services/connectors/engine.py)).
- Writes shared-memory facts by tag.

### Model / DB consistency

- Many routers return raw dicts, not Pydantic response models.
- Status enums incomplete vs runtime (`expired`, lifecycle strings).
- Operator queue and MCP key shapes diverge from SCHEMA intent.
- No agent config update model path.

---

## Highest-risk combinations (local operator)

1. **`PI_ORCHESTRATOR_HOST` non-loopback + `PI_NO_AUTH=1`** → unauthenticated terminal bash / chat tools / credential dump / ops kill / package install.
2. **Credentials `/values` + broken set/delete** → secrets readable if any were stored by older code; new writes fail.
3. **Flixz `video_path` + unauthenticated POST** → arbitrary local file processing / remote download to home.
4. **Optional auth enabled for “safety”** without realizing agents/chat/ops remain open → false sense of security.

---

## Explicit non-recommendations

Per product intent, this review does **not** recommend:

- Multi-tenant isolation, SaaS IdP, billing, or fleet RBAC as the fix path.
- Moving core execution to Docker/K8s as the default model.
- Cloud control planes or shared hosted backends.

Prefer hardening that preserves **one operator, one machine**: loopback bind warnings, correct local secrets lifecycle, path confinement, session path consistency, and honest docs about `PI_NO_AUTH` and subprocess privilege.

---

## File inventory reviewed

| Area | Paths |
|------|--------|
| Core | `main.py`, `config.py`, `database.py`, `models.py`, `logging_config.py` |
| Routers | `agents`, `chat`, `sessions`, `auth`, `credentials`, `files`, `terminal`, `voice`, `flixz`, `connectors`, `ops`, `system`, `console`, `mcp_keys`, `operator_queue`, `ws_tickets`, `events`, `git`, `settings_router`, `sharing`, `users`, `schedules`, `skills`, `tags`, … |
| Services | `pi_session_service`, `schedule_service`, `cleanup_service`, `flixz_service`, `tts_service`, `voice_service`, `ws_ticket_service`, `connectors/*`, `shared_memory_service`, `system_chat_service`, `git_service`, `event_bus` |

---

*End of evidence-only backend review. No code changes performed.*
