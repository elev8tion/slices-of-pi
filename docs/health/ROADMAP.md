# Roadmap — T1 Local Single-Operator

**SHA baseline:** `9249dfa`  
**Authority:** [PRODUCT_INTENT.md](../PRODUCT_INTENT.md), [HEALTH_BRIEF.md](./HEALTH_BRIEF.md)  
**Rejected:** SaaS, multi-tenant, Tier-4, billing (see `docs/archive/rejected/`)

---

## Track A — Stabilize (do first)

| ID | Work | Effort | Acceptance | Evidence |
|----|------|--------|------------|----------|
| **A1** | Fix credentials DB helpers so create/delete does not crash | S | Unit test write/delete credential; no AttributeError | BACKEND P0 |
| **A2** | Fix Settings health: call `GET /health` or add thin `/api/health` alias | S | Settings panel loads health without 404 | FRONTEND P0 |
| **A3** | Agent edit: implement `PATCH /api/agents/{id}` **or** change UI to supported API | M | Edit name/model/tools from UI persists | INVENTORY drift |
| **A4** | Fix vue-tsc errors (9 in 5 files) or document deliberate skip | M | `npx vue-tsc -b` exit 0 | FRONTEND |
| **A5** | Align system_chat `create_agent` call with `db.create_agent` / service API | S | Voice/system create agent works | BACKEND P1 |
| **A6** | Live e2e: start orchestrator in fixture **or** mark `test_e2e_api` integration-only | S | Full pytest either green or clearly split | TEST_REPORT |

## Track B — Harden (localhost, not multi-tenant) — **DONE 2026-07-15**

| ID | Work | Effort | Acceptance | Evidence |
|----|------|--------|------------|----------|
| **B1** | Files path resolution: use resolved Path compare, not `startswith` | S | Path-traversal tests pass | See TRACK_B_STATUS |
| **B2** | Session workspace: one rule for agent_id vs name (chat/terminal/files) | M | Terminal and chat hit same session root | See TRACK_B_STATUS |
| **B3** | Flixz: restrict paths to agent workspace / explicit allowlist | M | Cannot pass arbitrary system paths | See TRACK_B_STATUS |
| **B4** | Warn in logs if `PI_ORCHESTRATOR_HOST` is not loopback | S | Log warning on non-127.0.0.1 bind | See TRACK_B_STATUS |
| **B5** | Credentials: stop returning full plaintext on casual GET **or** document + gate for operator-only local | S | Values endpoint behavior matches docs | See TRACK_B_STATUS |

## Track C — Local product polish — **DONE 2026-07-15**

| ID | Work | Effort | Acceptance | Evidence |
|----|------|--------|------------|----------|
| **C1** | Mount or remove dead panels (McpKeys, YamlEditor, SlicesPanel, …) | S | No orphan components claiming features | TRACK_C_STATUS |
| **C2** | Chat history hydration on session switch | M | Switching session restores messages | TRACK_C_STATUS |
| **C3** | Scheduler uses same session path as managed chat | M | Cron runs produce same session layout | TRACK_C_STATUS |
| **C4** | Minimal CI: pytest unit + vite build on PR | M | `.github/workflows/ci.yml` green | TRACK_C_STATUS |
| **C5** | Packaging note only: root vs pi-orchestrator identity in README (done-ish); optional pyproject clarify | S | New contributors not confused | TRACK_C_STATUS |

## Explicitly not on this roadmap

- Multi-tenant auth productization  
- Billing, cloud control plane  
- Slack/Telegram/WhatsApp as product channels  
- Wiring `slice_of_pi` into a Docker/K8s framework  
- Redis-backed bus as a requirement  

`slice_of_pi/` stays **dormant contracts** unless owner reopens intent.  
`pi-mcp-server/` stays **optional local** bridge.

## Suggested execution order

```
A1 → A2 → A5 → A3 → A6 → A4
     ↓
B1 → B2 → B4 → B5 → B3
     ↓
C1 → C2 → C3 → C4 → C5
```

## Definition of done for “healthy T1”

- [x] Unit pytest green (including credential paths)  
- [x] Live probe / CI documents tests (`.github/workflows/ci.yml`)  
- [x] vue-tsc green (Track A)  
- [x] No known P0 crash on daily operator paths (Track A)  
- [x] PRODUCT_INTENT still binding; no SaaS docs revived  

Tracks A–C complete. See TRACK_A_STATUS / TRACK_B_STATUS / TRACK_C_STATUS.

---

*Optional next: operator UX polish only under PRODUCT_INTENT (local single-operator).*
