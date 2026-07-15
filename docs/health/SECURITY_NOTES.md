# Security notes — local single-operator threat model

**Date:** 2026-07-15  
**Scope:** Review of `pi_orchestrator` auth, WebSocket tickets, credentials, MCP keys, files, terminal, DB encryption helpers, and bind/CORS config.  
**Product binding:** Local single-operator console ([`docs/PRODUCT_INTENT.md`](../PRODUCT_INTENT.md)). Not a multi-tenant or SaaS security model.  
**Action:** Findings only — no fixes implemented in this pass.

---

## Threat model (what “safe” means here)

| Context | Assumption | Verdict if defaults held |
|---------|------------|---------------------------|
| **Intended daily path** | `PI_ORCHESTRATOR_HOST=127.0.0.1` (default), `PI_NO_AUTH=1` (via `./slices`), one trusted operator on the machine | **Acceptable for localhost single-op** — the API is intentionally open to whoever can reach the loopback port |
| **Accidental LAN/WAN exposure** | Host set to `0.0.0.0` / non-loopback, or port forwarded, same process still running with no auth | **Dangerous** — unauthenticated shell, agent control, and secret exfil |

**Default bind is correct:** `HOST = os.getenv("PI_ORCHESTRATOR_HOST", "127.0.0.1")` in [`pi_orchestrator/config.py`](../../pi_orchestrator/config.py); uvicorn uses that host in [`pi_orchestrator/main.py`](../../pi_orchestrator/main.py).

There is **no startup guard or log warning** if the operator overrides host to `0.0.0.0`.

---

## Severity legend

| Level | Meaning in this repo |
|-------|----------------------|
| **P0** | Full compromise or secret dump if the process is reachable beyond the trusted operator (esp. non-localhost bind) |
| **P1** | High-impact gap even for “I turned auth on” or multi-user local machines; false sense of security |
| **P2** | Weak crypto / at-rest hygiene / incomplete hardening; limited under pure single-user localhost |
| **P3** | Defense-in-depth, consistency, or low practical impact under the intended model |

Each finding is tagged:

- **Localhost single-op:** safe / residual / concerning  
- **If bound `0.0.0.0`:** dangerous impact  

---

## P0 — Critical if reachable beyond the operator

### P0-1 — Open control plane under `PI_NO_AUTH=1` (by design)

**Evidence:**  
- [`pi_orchestrator/routers/auth.py`](../../pi_orchestrator/routers/auth.py) — `PI_NO_AUTH` short-circuits `get_current_user` to default admin.  
- Almost all routers (`agents`, `chat`, `files`, `credentials`, `ops`, `mcp_keys`, `schedules`, …) do **not** call `Depends(get_current_user)`. Auth dependency is used only on `auth` (`/me`), `users`, and `sharing`.  
- Launch path: `./slices` / docs set `PI_NO_AUTH=1` ([`PROJECT_STATE.md`](../../PROJECT_STATE.md), [`README.md`](../../README.md)).

**Impact if bound `0.0.0.0`:** Anyone who can hit `:8420` can create/stop agents, chat (tool use as the host user), manage files, set/delete credentials, mint WS tickets, run ops (`stop-all`, scheduler pause), etc.

**Localhost single-op:** **Safe by product intent** — same trust boundary as other local dev tools.  
**If bound `0.0.0.0`:** **Dangerous** — treat as unauthenticated RCE + data plane.

---

### P0-2 — Terminal WebSocket can spawn a login bash shell

**Evidence:** [`pi_orchestrator/routers/terminal.py`](../../pi_orchestrator/routers/terminal.py)

- `mode=bash` runs `/bin/bash --login` with the orchestrator process environment.  
- Ticket gate: `ws_ticket_service.consume_ticket(ticket)` — but under `PI_NO_AUTH=1`, tickets are free via `POST /api/ws/ticket` ([`pi_orchestrator/routers/ws_tickets.py`](../../pi_orchestrator/routers/ws_tickets.py)).

**Localhost single-op:** **Safe** for a trusted operator (interactive shell is a feature).  
**If bound `0.0.0.0`:** **Dangerous** — remote interactive shell as the orchestrator OS user (typically the developer account).

---

### P0-3 — Credential plaintext API: `GET /api/agents/{id}/credentials/values`

**Evidence:** [`pi_orchestrator/routers/credentials.py`](../../pi_orchestrator/routers/credentials.py) (`get_credential_values`)

- Decrypts all stored credential values and returns them in JSON.  
- **No auth dependency.**  
- List/create endpoints correctly mask as `••••••••`; this values endpoint is the break-glass path for inject/debug.

**Localhost single-op:** **Residual** — any local process or XSS-to-loopback can dump API keys. Acceptable only if the host is single-user and loopback-only.  
**If bound `0.0.0.0`:** **Dangerous** — remote secret dump of all agent API keys.

---

### P0-4 — Host override has no “you are exposed” barrier

**Evidence:**  
- [`pi_orchestrator/config.py`](../../pi_orchestrator/config.py): `HOST` from `PI_ORCHESTRATOR_HOST`, default `127.0.0.1`.  
- [`pi_orchestrator/main.py`](../../pi_orchestrator/main.py): logs `starting on {HOST}:{PORT}` only; no refuse/warn for non-loopback.

**Localhost single-op:** Defaults are fine.  
**If bound `0.0.0.0`:** Combines with P0-1–P0-3 for full remote compromise. **Operator error is the primary footgun.**

---

## P1 — High impact / false security

### P1-1 — Optional auth mode does not protect the product surface

**Evidence:** Grep of `get_current_user` / `require_admin` — only:

| Router | Auth dependency |
|--------|-----------------|
| `auth.py` | `/me` |
| `users.py` | list/search (admin) |
| `sharing.py` | share CRUD / access requests |
| `ws_tickets.py` | JWT only when `PI_NO_AUTH` is off |

**Not gated when auth is “on”:** agents, chat, sessions, files, terminal (via ticket mint still needing JWT for tickets only), credentials, mcp_keys, ops, connectors, schedules, voice, flixz, etc.

**Localhost single-op:** N/A if never using auth mode.  
**If bound `0.0.0.0` with `PI_NO_AUTH` unset:** Still **dangerous** — turning “auth on” does not lock the fleet. Do not assume login equals access control.

---

### P1-2 — Open registration always available

**Evidence:** [`pi_orchestrator/routers/auth.py`](../../pi_orchestrator/routers/auth.py) `POST /api/auth/register` — no admin gate, no disable flag, min password length 4.

**Localhost single-op:** Low relevance under `PI_NO_AUTH=1`.  
**If bound `0.0.0.0`:** Attackers create users; still mostly irrelevant until routes actually enforce JWT, but worsens the false-security story with sharing/admin APIs.

---

### P1-3 — Default admin user password material is weak

**Evidence:** [`pi_orchestrator/routers/auth.py`](../../pi_orchestrator/routers/auth.py) `_get_default_admin`:

- Creates user `admin` with `password_hash = sha256("admin")` if missing.  
- Used whenever `PI_NO_AUTH=1` resolves the current user.

**Localhost single-op:** Harmless while no-auth bypasses password checks.  
**If auth mode later used on a shared host / exposed bind:** Trivial default credential if that user is used for login.

---

### P1-4 — Password storage: unsalted SHA-256

**Evidence:** register/login in [`auth.py`](../../pi_orchestrator/routers/auth.py) — `hashlib.sha256(password.encode()).hexdigest()`; compare via `hmac.compare_digest` (good against timing on the hash string, not against offline cracking).

**Localhost single-op:** Residual (DB is local SQLite).  
**If DB or host compromised:** Offline password recovery is easy; no salt/pepper, no slow hash (bcrypt/argon2).

---

### P1-5 — JWT signing secret defaults to hostname-derived material

**Evidence:** [`auth.py`](../../pi_orchestrator/routers/auth.py):

```text
PI_AUTH_SECRET or sha256(f"slice-of-pi-auth-{nodename}")[:32]
```

Custom HS256-like tokens (`header.payload.hex_hmac`), 24h expiry, `hmac.compare_digest` on signature (good).

**Localhost single-op:** Residual.  
**If bound / multi-user:** Predictable secret if hostname is known and `PI_AUTH_SECRET` unset → forge tokens for any registered user id.

---

### P1-6 — Event WebSocket has no ticket

**Evidence:** [`pi_orchestrator/routers/events.py`](../../pi_orchestrator/routers/events.py) — `await websocket.accept()` with comment “No auth needed — single-user, bound to localhost.”

Contrast: terminal / voice / console logs require tickets.

**Localhost single-op:** **Safe** under product intent.  
**If bound `0.0.0.0`:** Real-time agent/activity event leakage (and enumeration aid).

---

### P1-7 — Free ticket mint under no-auth is full WS capability

**Evidence:**  
- [`ws_tickets.py`](../../pi_orchestrator/routers/ws_tickets.py) — no-auth path mints for `user_id="admin"`.  
- Consumers: [`terminal.py`](../../pi_orchestrator/routers/terminal.py), [`voice.py`](../../pi_orchestrator/routers/voice.py), [`console.py`](../../pi_orchestrator/routers/console.py).  
- Service: cryptographically random 32-byte hex, 30s TTL, single-use pop — solid implementation ([`ws_ticket_service.py`](../../pi_orchestrator/services/ws_ticket_service.py)).

**Localhost single-op:** Tickets mainly stop accidental bare WS connects; not a network ACL.  
**If bound `0.0.0.0`:** Ticket is a 30s hop, not a barrier — mint then connect.

---

## P2 — Crypto / at-rest / path hygiene

### P2-1 — Three separate encryption schemes; mixed strength

| Store | Location | Key material | Fallback |
|-------|----------|--------------|----------|
| Agent credentials | `credentials` table | `~/.pi/agent/orchestrator.key` or `sha256("slice-of-pi-cred-{host}-{port}")` | XOR if `cryptography` missing |
| Connector `auth_state` | `connectors` table | `sha256("slice-of-pi-connector-{host}-{port}")` only — no key file | **plaintext store** if Fernet import fails |
| MCP keys | `mcp_keys.value` | Random Fernet key in `~/.pi/agent/.mcp_key` | decrypt returns `""` on failure |

**Evidence:**  
- [`credentials.py`](../../pi_orchestrator/routers/credentials.py) `_get_encryption_key` / `_encrypt_value` / `_decrypt_value`  
- [`database.py`](../../pi_orchestrator/database.py) `_get_fernet_key` / `_encrypt_value` / `_decrypt_value`  
- [`mcp_keys.py`](../../pi_orchestrator/routers/mcp_keys.py) `_get_cipher`

**Localhost single-op:** Encryption-at-rest is best-effort against casual file reads; **not** against same-user access (keys live beside the DB).  
**If disk shared / backup leaked:** Hostname-derived keys without a secret file are reproducible by anyone who knows hostname + port.

---

### P2-2 — Key files not forced to mode `0600`

**Evidence:**  
- `orchestrator.key` / `.mcp_key` written with default umask; only `orchestrator.json` gets explicit `chmod` user R/W in [`config.py`](../../pi_orchestrator/config.py) `save_orchestrator_config`.  
- SQLite `orchestrator.db` also no explicit `chmod`.

**Localhost single-op:** Residual on multi-user Unix accounts.  
**If multi-user machine:** Other local UIDs may read secrets if home directory permissions are loose.

---

### P2-3 — MCP `key_hash` column stores ciphertext, not a hash

**Evidence:** [`database.py`](../../pi_orchestrator/database.py) `create_mcp_key` inserts `encrypted_value` into both `key_hash` and `value`. Schema still says `key_hash TEXT NOT NULL UNIQUE`.

**Localhost single-op:** Naming/schema smell; Fernet ciphertext is unique per encrypt so UNIQUE rarely bites.  
**Risk:** Misleading operators/auditors; not a live exploit by itself.

---

### P2-4 — MCP key HTTP surface unauthenticated; values masked on list only

**Evidence:** [`mcp_keys.py`](../../pi_orchestrator/routers/mcp_keys.py) — list/create/delete with no `Depends`; list masks values. No public decrypt endpoint (good). Decrypt helper exists for internal use.

**Localhost single-op:** OK under no-auth product model.  
**If bound `0.0.0.0`:** Attacker can delete/overwrite MCP keys (availability / poison).

---

### P2-5 — File path checks use `str.startswith` after resolve

**Evidence:** [`files.py`](../../pi_orchestrator/routers/files.py) `_safe_resolve`:

```text
if not str(target).startswith(str(base.resolve())):
```

Classic edge case: base `/path/agent` vs sibling `/path/agent_other` (prefix false positive). Prefer `Path.is_relative_to` (3.9+ / 3.12) or separator-aware compare.

Upload uses `_safe_resolve` on dest after combining `file.filename` — good intent. Workspace is restricted under `PI_MANAGED_SESSIONS_DIR / agent_name`.

**Localhost single-op:** Low practical risk with normal `~/.pi/...` layout.  
**If bound `0.0.0.0`:** Still mostly confined to agent workspace; traversal bug would be high if exploitable.

---

### P2-6 — CORS is localhost-scoped with credentials

**Evidence:** [`config.py`](../../pi_orchestrator/config.py) `CORS_ORIGINS` — only `localhost` / `127.0.0.1` on 5173 and 8420; [`main.py`](../../pi_orchestrator/main.py) `allow_credentials=True`, methods/headers `*`.

**Localhost single-op:** Appropriate for Vite + API. Browser sites on other origins should not get credentialed CORS.  
**Note:** Non-browser clients ignore CORS; CORS is not an auth substitute (especially with `PI_NO_AUTH`).

---

### P2-7 — Webhook connector token in URL path

**Evidence:** [`connectors.py`](../../pi_orchestrator/routers/connectors.py) `POST /webhook/{token}` — token compared after decrypting each connector’s `auth_state`.

**Localhost single-op:** Residual (logs, proxies).  
**If bound `0.0.0.0`:** Token in path/query logs; still better than open write, but bearer-in-path is weaker than header secrets.

---

## P3 — Lower priority / consistency

### P3-1 — Ticket `user_id="admin"` vs real admin UUID

**Evidence:** no-auth mint uses string `"admin"`; `_get_default_admin` may use DB user id. Ticket consumer only checks non-None user_id — no agent ACLs.

**Impact:** None under single-op; would break real multi-user authorization if ever built on tickets alone.

---

### P3-2 — Custom JWT, unused `_b64url`, header `alg` ignored (fixed HS256 verify)

**Evidence:** [`auth.py`](../../pi_orchestrator/routers/auth.py). Signature is over header+payload with fixed HMAC; not classic alg-confusion. Dead `_b64url` helper.

**Impact:** Maintainability / ecosystem tooling only.

---

### P3-3 — Image preview can base64-encode full file into JSON

**Evidence:** [`files.py`](../../pi_orchestrator/routers/files.py) preview path for images — no size cap like text `PREVIEW_MAX_BYTES`.

**Localhost single-op:** Local DoS / memory spike if huge image.  
**If bound `0.0.0.0`:** Cheap bandwidth/memory abuse.

---

### P3-4 — Upload max 50 MB; no rate limit / auth

**Evidence:** `MAX_UPLOAD_BYTES` in [`files.py`](../../pi_orchestrator/routers/files.py).

**Localhost single-op:** Fine.  
**If bound `0.0.0.0`:** Disk fill.

---

### P3-5 — Ops and chat are high-power and unauthenticated by design

**Evidence:** [`ops.py`](../../pi_orchestrator/routers/ops.py) stop-all / scheduler; [`chat.py`](../../pi_orchestrator/routers/chat.py) SSE stream with agent tools.

Documented for completeness: same class as P0-1, lower novelty.

---

## Summary matrix

| ID | Topic | Localhost single-op | Bound `0.0.0.0` |
|----|--------|---------------------|----------------|
| P0-1 | Open API + `PI_NO_AUTH` | Safe (intent) | Full remote control |
| P0-2 | Terminal bash | Safe (feature) | Remote shell |
| P0-3 | Credentials `/values` | Residual local leak | Remote secret dump |
| P0-4 | Host override no warn | Defaults OK | Footgun amplifier |
| P1-1 | Auth mode incomplete | N/A if unused | False security |
| P1-2 | Open register | Low | Account spam |
| P1-3 | Default admin/`admin` | Low under no-auth | Weak login if used |
| P1-4 | SHA-256 passwords | Residual | Offline crack |
| P1-5 | Hostname JWT secret | Residual | Forgeable tokens |
| P1-6 | `/ws/events` open | Safe (intent) | Event leak |
| P1-7 | Free tickets no-auth | Residual | Shell/voice/logs |
| P2-1 | Weak/derived at-rest keys | Residual | Backup/disk risk |
| P2-2 | Key/DB file modes | Residual multi-user | Same |
| P2-3 | MCP `key_hash` misuse | Hygiene | Hygiene |
| P2-4 | MCP API open | Intent | Key sabotage |
| P2-5 | Path `startswith` | Low | Potential traversal edge |
| P2-6 | CORS localhost | Good | Not a bind ACL |
| P2-7 | Webhook token in path | Residual | Log leakage |
| P3-* | Misc | Low | Low–moderate abuse |

---

## Operator checklist (no product change required)

**Safe defaults (keep):**

1. Leave `PI_ORCHESTRATOR_HOST` unset or `127.0.0.1`.  
2. Use `PI_NO_AUTH=1` only on a machine you fully trust (single operator).  
3. Do not port-forward 8420; do not put this process behind a public reverse proxy without an external auth layer you control.  
4. Treat `~/.pi/agent/orchestrator.db`, `orchestrator.key`, and `.mcp_key` as secret material (permissions, backups, sync tools).

**Dangerous configurations:**

1. `PI_ORCHESTRATOR_HOST=0.0.0.0` (or any non-loopback) with current code.  
2. Assuming `PI_NO_AUTH=0` alone makes the fleet multi-user safe.  
3. Exposing 8420 on a LAN “just for the phone” without OS-level or reverse-proxy auth.

**Out of scope for this note (per product intent):** SaaS tenancy, cloud IAM, billing isolation, enterprise SSO productization.

---

## Evidence index (files reviewed)

| Area | Paths |
|------|--------|
| Auth / JWT / no-auth | `pi_orchestrator/routers/auth.py` |
| WS tickets | `pi_orchestrator/routers/ws_tickets.py`, `pi_orchestrator/services/ws_ticket_service.py` |
| Credentials encrypt + API | `pi_orchestrator/routers/credentials.py` |
| MCP keys | `pi_orchestrator/routers/mcp_keys.py`, `database.py` `create_mcp_key` / schema |
| Files / path safety | `pi_orchestrator/routers/files.py` |
| Terminal / bash | `pi_orchestrator/routers/terminal.py` |
| Events WS | `pi_orchestrator/routers/events.py` |
| Connectors / webhook | `pi_orchestrator/routers/connectors.py`, `database.py` connector encrypt |
| DB encryption helpers | `pi_orchestrator/database.py` (`_get_fernet_key`, credentials/mcp schema) |
| CORS / bind | `pi_orchestrator/config.py`, `pi_orchestrator/main.py` |
| Partial auth usage | `pi_orchestrator/routers/users.py`, `sharing.py` |
| Product intent | `docs/PRODUCT_INTENT.md`, `docs/health/TARGET.md` |

---

*End of review. No code changes.*
