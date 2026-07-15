# Multi-Agent Health Audit — Orchestration Plan

**Purpose:** Orchestrate a team of agents to examine Slice of Pi **end-to-end**, run review + tests, and produce a **fact-only** picture of:

1. **Where the project is** (health, coverage, defects, drift)  
2. **Where it needs to be** (explicit product target — user-confirmed)  
3. **How to get there** (prioritized, evidence-backed roadmap)

**Authority hierarchy (non-negotiable):**

1. Running code + automated tests + live probes  
2. [PROJECT_STATE.md](../PROJECT_STATE.md) (tree truth)  
3. [architecture.md](./architecture.md)  
4. Archived plans under `docs/archive/` — **inputs for intent only**, never treated as implemented  

**Product target (fixed):** Local single-operator only — see [`PRODUCT_INTENT.md`](./PRODUCT_INTENT.md).  
**Out of scope for this audit:** Implementing features; **any** SaaS / multi-tenant / Tier-4 work; rewriting `slice_of_pi` contracts unless the audit proves they block local shipping.

---

## 0. Success criteria

The audit is done when these artifacts exist and agree:

| Artifact | Path | Must contain |
|----------|------|----------------|
| Test report | `docs/health/TEST_REPORT.md` | Pass/fail counts, skipped, failures with root cause, coverage map (module → tests) |
| Backend review | `docs/health/BACKEND_REVIEW.md` | Severity-ranked findings (P0–P3) with file:line evidence |
| Frontend review | `docs/health/FRONTEND_REVIEW.md` | Same; API contract mismatches called out |
| Integration / E2E probe | `docs/health/E2E_PROBE.md` | What was run live vs mocked; pi binary present/absent |
| Gap matrix | `docs/health/GAP_MATRIX.md` | Feature × (code exists? tested? UI wired? docs claim?) |
| Contracts package verdict | `docs/health/CONTRACTS_VERDICT.md` | Keep / wire / archive `slice_of_pi` recommendation |
| Master health brief | `docs/health/HEALTH_BRIEF.md` | One-page score + top risks + top next moves |
| Roadmap | `docs/health/ROADMAP.md` | Ordered work packages with effort, deps, acceptance tests |

**Definition of “fact only”:** Every claim in the health brief must cite one of: test output, source path, probe log, or “not present in tree.”

---

## 1. Team roster (roles)

Orchestrator (you / parent agent) does **not** deep-dive every module. It assigns, merges, resolves conflicts, and writes the master brief.

| Agent ID | Role | Subagent type | Capability | Owns |
|----------|------|---------------|------------|------|
| **A0-Scout** | Surface map | `explore` (very thorough) | read-only | Inventory: routers, services, views, tests, dead paths |
| **A1-Test** | Test runner | `general-purpose` | execute | Full pytest; categorize fail/skip; coverage gaps |
| **A2-API** | Backend deep review | `general-purpose` | read-only (or execute for import checks) | `pi_orchestrator/` correctness, security, lifecycle |
| **A3-UI** | Frontend deep review | `general-purpose` | read-only + execute dashboard build | `dashboard/` typecheck/build, API call sites vs routers |
| **A4-Runtime** | Live E2E probe | `general-purpose` | execute | `./slices` or API-only; `/health`; critical paths with mocks if no `pi` |
| **A5-Contracts** | Package dual-identity | `explore` / general | read-only | `slice_of_pi` vs orchestrator; MCP server; pi-coding-agent |
| **A6-Security** | Auth & secrets | `general-purpose` | read-only | Auth, credentials encryption, tickets, CORS, path traversal |
| **A7-Synth** | Synthesis | `general-purpose` | read-write | Merge all artifacts → HEALTH_BRIEF + ROADMAP |

**Parallelism rule:** A0 first (or A0 || A1 if inventory already trusted). Then **A2 ‖ A3 ‖ A5 ‖ A6** in parallel. **A4** after A1 green enough to trust harness (or always, isolated). **A7** last, only when A1–A6 reports exist.

```
        ┌─────────┐
        │ A0-Scout│
        └────┬────┘
             │
    ┌────────┼────────────────┐
    ▼        ▼                ▼
┌───────┐ ┌──────┐      ┌──────────┐
│A1-Test│ │A4-Run│*     │ (wait)   │
└───┬───┘ └──┬───┘      └──────────┘
    │        │
    └────┬───┘
         │
  ┌──────┼──────┬──────┬──────┐
  ▼      ▼      ▼      ▼      ▼
 A2     A3     A5     A6    (A4 if delayed)
  │      │      │      │
  └──────┴──────┴──────┘
              │
              ▼
           A7-Synth
```

\*A4 may run in parallel with reviews if the environment is clean; if port 8420 conflicts, serialize after A1.

---

## 2. Work packages (mapped to real code)

### WP-0 — Baseline inventory (A0)

**Inputs:** repo tree, `PROJECT_STATE.md`, `main.py` router list  
**Tasks:**

1. Confirm every file under `pi_orchestrator/routers/` is registered in `main.py` (or note orphans).  
2. Confirm every service module is imported by at least one router/lifespan.  
3. Map each `dashboard/src/views/*` and major panels → API paths they call.  
4. Map each `tests/test_*.py` → modules under test.  
5. Flag: no CI (`.github` absent), dual launchers (`slices` vs `install.sh`), dual package identity.

**Output:** `docs/health/INVENTORY.md`  
**Gate:** No phase-1 agent starts without this file.

### WP-1 — Automated test campaign (A1)

**Commands (canonical):**

```bash
cd /Users/kc/slice-of-pi
python3 -m pytest tests/ -v --tb=short 2>&1 | tee docs/health/pytest-full.log
# Optional second pass excluding true e2e that needs live server:
python3 -m pytest tests/ -v --tb=short --ignore=tests/test_terminal_e2e.py 2>&1 | tee docs/health/pytest-unit.log
```

**Tasks:**

1. Install missing deps from `slices` list if imports fail (`fastapi`, `uvicorn`, `pydantic`, `apscheduler`, `pytest`, `pytest-asyncio`, `httpx`, `pyyaml`, `psutil`, `cryptography`, `aiohttp`).  
2. Record: total passed / failed / skipped / errors.  
3. For each failure: file, test name, one-line root cause, “blocker vs flaky.”  
4. Coverage matrix:

| Area | Test modules present | Routers/services with **no** tests |
|------|----------------------|-------------------------------------|
| agents/chat/sessions | test_agents_api, test_chat_api, test_sessions_api | … |
| schedules | test_schedules_api | … |
| voice/flixz | test_voice, test_flixz | … |
| terminal | test_terminal, test_terminal_e2e | … |
| auth/sharing/users | ? | … |
| files/git/credentials | ? | … |
| ops/audit/mcp_keys | ? | … |
| connectors | test_connectors | … |

**Output:** `docs/health/TEST_REPORT.md` + logs  
**Gate for “healthy tests”:** unit/API suite (excluding live e2e) is green, or all failures triaged with owners.

### WP-2 — Backend review (A2)

**Scope:** `pi_orchestrator/{main,config,database,models}.py`, all `routers/`, all `services/`

**Checklist (must answer with evidence):**

| Theme | Questions |
|-------|-----------|
| Lifecycle | Lifespan start/stop order; kill_all on shutdown; scheduler/cleanup failures soft? |
| Session | `pi_session_service` JSONL parsing edge cases; timeout; concurrent chats per agent |
| DB | Schema vs migrations (`_safe_add_column`); FK cascades; thread-local SQLite safety |
| Auth | `PI_NO_AUTH`; JWT mint/verify; default secrets from hostname |
| Credentials | Encryption path; plaintext fallback when cryptography missing |
| Files | Path traversal on `files.py` agent workspace |
| Terminal | PTY lifecycle, ticket auth, agent isolation |
| Voice/TTS | Behavior when mossy/`GEMINI_API_KEY` absent |
| Flixz | ffmpeg missing; describe backends |
| Connectors | Webhook token safety; sync engine error handling |
| Consistency | `models.py` fields vs DB columns vs router responses |

**Severity scale:**

- **P0** — data loss, RCE, auth bypass, corruption  
- **P1** — core path broken (create agent, chat, start)  
- **P2** — feature broken or untested but non-core  
- **P3** — polish, debt, docs drift  

**Output:** `docs/health/BACKEND_REVIEW.md`

### WP-3 — Frontend review (A3)

**Scope:** `dashboard/src/**`, `package.json`, build

**Commands:**

```bash
cd dashboard && npm ci || npm install
npx vue-tsc -b --pretty false 2>&1 | tee ../docs/health/vue-tsc.log
npx vite build 2>&1 | tee ../docs/health/vite-build.log
```

**Checklist:**

1. Typecheck + production build status.  
2. For each view/route: primary API endpoints; 404/error handling.  
3. Auth store vs `PI_NO_AUTH` / login flow.  
4. WebSocket clients (events, logs, terminal, voice): ticket usage.  
5. Dead UI: components with no parent import.  
6. Contract drift: frontend expects fields backend no longer returns.

**Output:** `docs/health/FRONTEND_REVIEW.md`

### WP-4 — Live / E2E probe (A4)

**Goal:** Prove the **runnable product** path, not just unit mocks.

**Phase 4a — Static serve path (preferred):**

```bash
# If nothing listening on 8420:
PI_NO_AUTH=1 python3 start-orchestrator.py --serve-dashboard &
# wait for health
curl -s http://127.0.0.1:8420/health
curl -s http://127.0.0.1:8420/docs -o /dev/null -w "%{http_code}"
curl -s http://127.0.0.1:8420/api/agents
```

**Phase 4b — Critical API sequence (mocked pi if needed):**

1. `POST /api/agents` create  
2. `GET /api/agents` list  
3. `POST /api/agents/{id}/chat` (expect fail if no pi — document)  
4. `GET /api/sessions`  
5. `GET /api/skills`, `/api/extensions`, `/api/templates`  
6. `GET /api/telemetry/host`  
7. WebSocket `/ws/events` with ticket if required  

**Phase 4c — Optional real pi:** only if `which pi` succeeds; one short chat turn; capture session JSONL path.

**Phase 4d — Teardown:** kill server; note port leftovers.

**Output:** `docs/health/E2E_PROBE.md` (commands + raw status codes + conclusions)

### WP-5 — Contracts & satellites (A5)

| Package | Questions |
|---------|-----------|
| `slice_of_pi/` | Any import from product? Any tests? Value as future contract vs delete/archive? |
| `pi-mcp-server/` | Builds? Tools match current API paths? Documented in README? |
| `pi-coding-agent/` | Size/noise; should stay as reference only? |
| Packaging | Root vs `pi_orchestrator` pyproject dual identity — product confusion risk |

**Output:** `docs/health/CONTRACTS_VERDICT.md`

### WP-6 — Security pass (A6)

Focused read of:

- `routers/auth.py`, `ws_tickets.py`, `credentials.py`, `mcp_keys.py`, `files.py`, `terminal.py`  
- `database.py` encryption helpers  
- `config.py` CORS / bind address  

Report: threat model for **localhost single-user** vs accidental exposure if bound to `0.0.0.0`.

**Output:** section in `BACKEND_REVIEW` or `docs/health/SECURITY_NOTES.md`

### WP-7 — Gap matrix + roadmap (A7)

**Gap matrix columns:**

| Capability | Code | Test | UI | Docs claim | Status |
|------------|------|------|-----|------------|--------|
| Agent CRUD | Y/N | Y/N | Y/N | Y/N | OK / partial / gap |
| Chat SSE | … | | | | |
| Terminal | | | | | |
| Schedules | | | | | |
| Voice | | | | | |
| Flixz | | | | | |
| Optional local auth | | | | | |
| Local sharing/teams (non-SaaS) | | | | | |
| Connectors | | | | | |
| MCP server | | | | | |
| CI | | | | | |
| Contracts wired | | | | | |

**Roadmap rules:**

1. Only items justified by P0–P2 findings or explicit product goal.  
2. Each item: acceptance test, estimated effort (S/M/L), dependency.  
3. Separate tracks: **Stabilize** (tests/CI/bugs) → **Harden** (localhost security/paths) → **Local product polish** (operator UX).  
4. **Never** add SaaS, multi-tenant cloud, Tier-4 enterprise fleet, or billing as roadmap items — owner rejected; see `PRODUCT_INTENT.md`.

**Outputs:** `GAP_MATRIX.md`, `HEALTH_BRIEF.md`, `ROADMAP.md`

---

## 3. Product target (“where it needs to be”) — FIXED

**Confirmed owner intent:** **T1 only** — best-in-class **local single-operator** pi fleet manager on one machine.

| Option | Status |
|--------|--------|
| **T1 Local operator** | **ACTIVE TARGET** |
| T2 Team self-host as product pivot | Rejected as destination (local sharing code may remain convenience-only) |
| T3 Contracts-as-cloud-framework | Rejected as product pivot |
| T4 SaaS / commercial multi-tenant | **REJECTED** |
| Tier-4 enterprise channels product | **REJECTED** |

Write `docs/health/TARGET.md` as a copy of this T1 commitment (link `PRODUCT_INTENT.md`). Do not re-open target selection with agents.

---

## 4. Orchestrator runbook (how I execute this)

### Phase A — Prep (orchestrator only)

1. Create `docs/health/` directory.  
2. Snapshot git SHA: `git rev-parse HEAD` → write into every report header.  
3. Spawn **A0-Scout** with isolation none, read-only.  
4. Await `INVENTORY.md`.

### Phase B — Evidence (parallel)

Spawn in one wave:

- **A1-Test** (execute) — pytest campaign  
- **A4-Runtime** (execute) — after confirming port free  
- **A2-API**, **A3-UI**, **A5-Contracts**, **A6-Security** (read-only / limited execute)

Prompts **must** include:

- Absolute repo path  
- “Cite file paths; no claims without evidence”  
- Exact output file path under `docs/health/`  
- Reference to `PROJECT_STATE.md` as baseline  

### Phase C — Synthesis

1. Orchestrator reads all reports.  
2. Spawn **A7-Synth** with full list of artifact paths.  
3. Orchestrator validates HEALTH_BRIEF: every P0/P1 has a source citation.  
4. Present brief + open target question (§3) to user.  
5. After target confirmed, A7 (or orchestrator) finalizes ROADMAP.

### Phase D — Optional follow-on (not part of audit unless asked)

- Fix P0/P1 only, with tests  
- Add minimal CI workflow  
- Doc patches only  

---

## 5. Agent prompt templates (copy-paste for spawn)

### A0-Scout

```
Repo: /Users/kc/slice-of-pi
Read PROJECT_STATE.md, pi_orchestrator/main.py, dashboard/src/main.ts, tests/*.
Write docs/health/INVENTORY.md with:
- Router registration completeness
- Service → consumer map
- View → API map
- Test → module map
- Orphans / dead code suspects
No recommendations beyond facts. Cite paths.
```

### A1-Test

```
Repo: /Users/kc/slice-of-pi
Install test deps if needed. Run pytest as in HEALTH_AUDIT plan WP-1.
Write docs/health/TEST_REPORT.md + log files.
Do not fix code unless a one-line import fix is required to run tests; note any env changes.
```

### A2 / A3 / A5 / A6

```
Repo: /Users/kc/slice-of-pi
Scope: [WP-N checklist from plan]
Evidence only. Severity P0–P3.
Write [output path].
Do not implement fixes.
```

### A7-Synth

```
Read all docs/health/*.md. Produce GAP_MATRIX.md, HEALTH_BRIEF.md, draft ROADMAP.md.
Health brief must answer: where we are; top risks; test health score; untested surfaces.
Roadmap Stabilize/Harden first; Product track empty until TARGET.md exists.
```

---

## 6. Health scorecard (for HEALTH_BRIEF)

Fill after evidence:

| Dimension | Score 1–5 | Evidence |
|-----------|-----------|----------|
| Starts & health endpoint | | E2E_PROBE |
| Core agent lifecycle | | tests + probe |
| Chat path | | tests + pi presence |
| UI build | | vue-tsc / vite |
| Automated test suite | | pass rate |
| Security (localhost) | | A6 |
| Docs accuracy | | README vs code |
| Packaging clarity | | dual identity |
| CI/automation | | .github absent = 1 |
| Overall | weighted | |

---

## 7. Timeboxing (guidance)

| Phase | Wall clock (approx) | Agents |
|-------|---------------------|--------|
| A0 inventory | 15–30 min | 1 |
| A1 tests | 20–45 min | 1 |
| A2–A6 parallel | 45–90 min | 4–5 |
| A4 probe | 20–40 min | 1 |
| A7 synth + user target | 30–60 min | 1 + human |

Total: **~half day wall clock** with parallel agents; longer if many test failures need triage.

---

## 8. Risks to the audit itself

| Risk | Mitigation |
|------|------------|
| No `pi` binary | Mock-based unit tests still authoritative; E2E marks chat as “unverified live” |
| Port 8420 busy | Kill only processes we started; document pre-existing listeners |
| Agent hallucinated features | Orchestrator rejects findings without path/test citation |
| Scope creep into FUTURE_TIER4 | Archive is non-goal unless user picks T2/T3 |
| Destructive ops | Agents may not `rm -rf`, force-push, or wipe `~/.pi` production DB; use temp paths / PI_* overrides |

---

## 9. Deliverable checklist (exit)

- [ ] `docs/health/INVENTORY.md`  
- [ ] `docs/health/TEST_REPORT.md` + pytest logs  
- [ ] `docs/health/BACKEND_REVIEW.md`  
- [ ] `docs/health/FRONTEND_REVIEW.md`  
- [ ] `docs/health/E2E_PROBE.md`  
- [ ] `docs/health/CONTRACTS_VERDICT.md`  
- [ ] `docs/health/SECURITY_NOTES.md` (or folded into backend)  
- [ ] `docs/health/GAP_MATRIX.md`  
- [ ] `docs/health/HEALTH_BRIEF.md`  
- [ ] `docs/health/TARGET.md` (user-approved)  
- [ ] `docs/health/ROADMAP.md`  

When all boxes checked: audit complete. Next step is **execute ROADMAP** as a separate orchestration (stabilize PR stack first).

---

## 10. Immediate next action for orchestrator

On user approval (“run the plan”):

1. `mkdir -p docs/health`  
2. Spawn A0-Scout  
3. Spawn A1-Test  
4. Continue per §4  

Until approval: this document is the plan only; no multi-agent audit has been executed.

---

*Plan version: 2026-07-15 · Grounded in PROJECT_STATE.md and repo layout only.*
