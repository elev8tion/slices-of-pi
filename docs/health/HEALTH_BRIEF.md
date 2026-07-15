# Health Brief (post Tracks A–C)

**Audit baseline SHA:** `9249dfa`  
**Tracks complete through:** `6a7d777` (C) + Flixz general `d5ab850`  
**Date:** 2026-07-15  
**Product:** Local single-operator pi fleet manager ([PRODUCT_INTENT.md](../PRODUCT_INTENT.md))  
**Not:** SaaS / multi-tenant / Tier-4  

## Tracks status

| Track | Theme | Status | Notes |
|-------|--------|--------|--------|
| **A** | Stabilize | **Done** | [TRACK_A_STATUS.md](./TRACK_A_STATUS.md) |
| **B** | Harden (localhost) | **Done** | [TRACK_B_STATUS.md](./TRACK_B_STATUS.md) |
| **C** | Local polish | **Done** | [TRACK_C_STATUS.md](./TRACK_C_STATUS.md) |
| Flixz general | Operator tool on dashboard | **Done** | `/flixz` + nav + dashboard card |

## Where we are (post A–C)

| Dimension | Score (1–5) | Evidence |
|-----------|-------------|----------|
| Starts & health | **5** | E2E probe; Settings uses `/health` |
| Core agent lifecycle | **5** | CRUD + PATCH; unit tests |
| Chat path (real pi) | **5** | Probe pong; history hydration (C2) |
| UI production build | **5** | vite PASS; vue-tsc green (A4) |
| Automated tests | **5** | 315+ unit pass; live e2e skips without server |
| Localhost security model | **4** | Path harden, reveal gate, bind warn (B); still open under `PI_NO_AUTH` by design |
| Docs / intent clarity | **5** | PRODUCT_INTENT + AGENTS + track statuses |
| Packaging clarity | **4** | Dual package explained (C5) |
| CI | **5** | `.github/workflows/ci.yml` (C4) |
| **Overall (T1)** | **~5** | **Stabilize → harden → polish complete for T1 bar** |

## Closed risks (were P0/P1 at audit)

| Was | Resolution |
|-----|------------|
| Credentials write crash | A1 `_safe_execute` / `_safe_commit` |
| Settings `/api/health` | A2 → `/health` |
| vue-tsc failures | A4 fixed |
| Agent PATCH missing | A3 implemented |
| system_chat create_agent | A5 fixed |
| Live e2e noise | A6 skip without server |
| Files path traversal | B1 `relative_to` + lstrip fix |
| Terminal vs chat session dirs | B2 agent **name** |
| Flixz arbitrary paths | B3 allowlist |
| Non-loopback silent bind | B4 warning |
| Casual credential dump | B5 `?reveal=1` |
| Dead McpKeys / Slice Ops | C1 on Settings |
| Chat session empty on switch | C2 hydrate |
| Scheduler ad-hoc pi | C3 via `stream_chat` |
| No CI | C4 |
| Package confusion | C5 |

## Remaining residual (not blockers)

- Auth-on mode incomplete if `PI_NO_AUTH` unset (by design for T1 daily path)  
- Optional UI primitives still unmounted: `CapacityMeter`, `ResourceModal`, `YamlEditor` — see [OPERATOR_UX_PLAN.md](./OPERATOR_UX_PLAN.md)  
- `stores/notifications.ts` available but not wired to global WS toasts  

## Product target (unchanged)

> One operator. One machine. Many pi agents. No SaaS.

See [TARGET.md](./TARGET.md) and [PRODUCT_INTENT.md](../PRODUCT_INTENT.md).

## Next (optional Track D — operator UX)

Plan only: [OPERATOR_UX_PLAN.md](./OPERATOR_UX_PLAN.md) — wire CapacityMeter / ResourceModal / YamlEditor under local operator UX. Not required for T1 health bar.
