# Roadmap — T1 Local Single-Operator

**Audit baseline:** `9249dfa`  
**Tracks A–C complete through:** `6a7d777` (+ Flixz general `d5ab850`)  
**Authority:** [PRODUCT_INTENT.md](../PRODUCT_INTENT.md), [HEALTH_BRIEF.md](./HEALTH_BRIEF.md)  
**Rejected:** SaaS, multi-tenant, Tier-4, billing (see `docs/archive/rejected/`)

---

## Executive status

| Track | Theme | Status | Detail |
|-------|--------|--------|--------|
| **A** | Stabilize | **DONE** | [TRACK_A_STATUS.md](./TRACK_A_STATUS.md) |
| **B** | Harden (localhost) | **DONE** | [TRACK_B_STATUS.md](./TRACK_B_STATUS.md) |
| **C** | Local polish | **DONE** | [TRACK_C_STATUS.md](./TRACK_C_STATUS.md) |
| Flixz general | Dashboard operator tool | **DONE** | `/flixz` route + nav |
| **D** | Operator UX | **DONE** | [TRACK_D_STATUS.md](./TRACK_D_STATUS.md) · [OPERATOR_UX_PLAN.md](./OPERATOR_UX_PLAN.md) |

**T1 health bar:** met. Tracks A–D complete under PRODUCT_INTENT.

---

## Track A — Stabilize — **DONE**

| ID | Work | Status |
|----|------|--------|
| A1 | Credentials DB helpers | Done |
| A2 | Settings `/health` | Done |
| A3 | Agent PATCH | Done |
| A4 | vue-tsc green | Done |
| A5 | system_chat create_agent | Done |
| A6 | Live e2e skip without server | Done |

## Track B — Harden — **DONE**

| ID | Work | Status |
|----|------|--------|
| B1 | Files path containment | Done |
| B2 | Terminal workspace = agent name | Done |
| B3 | Flixz path allowlist | Done |
| B4 | Non-loopback bind warning | Done |
| B5 | Credentials `?reveal=1` | Done |

## Track C — Local polish — **DONE**

| ID | Work | Status |
|----|------|--------|
| C1 | Settings: Slice Ops + MCP Keys | Done |
| C2 | Chat history hydration | Done |
| C3 | Scheduler via stream_chat | Done |
| C4 | GitHub CI | Done |
| C5 | Packaging / README clarity | Done |

## Track D — Operator UX — **DONE 2026-07-15**

See [TRACK_D_STATUS.md](./TRACK_D_STATUS.md) and [OPERATOR_UX_PLAN.md](./OPERATOR_UX_PLAN.md).

| ID | Work | Status |
|----|------|--------|
| D4 | Wire notifications store to WS events | Done |
| D1 | Mount CapacityMeter (dashboard/settings + telemetry) | Done |
| D2 | ResourceModal as New Agent flow | Done |
| D5 | Empty-state / copy polish | Done |
| D3 | YamlEditor for local orchestrator config (safe write) | Done |

---

## Explicitly not on this roadmap

- Multi-tenant auth productization  
- Billing, cloud control plane  
- Slack/Telegram/WhatsApp as product channels  
- Wiring `slice_of_pi` into a Docker/K8s framework  
- Redis-backed bus as a requirement  

---

## Definition of done for “healthy T1”

- [x] Unit pytest green (including credential paths)  
- [x] CI: `.github/workflows/ci.yml`  
- [x] vue-tsc green  
- [x] No known P0 crash on daily operator paths  
- [x] PRODUCT_INTENT still binding; no SaaS docs revived  
- [x] Tracks A–C complete  

---

*Optional next: execute Track D under PRODUCT_INTENT only.*
