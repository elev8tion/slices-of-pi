# Instructions for coding agents

## Product direction (mandatory)

**Read [`docs/PRODUCT_INTENT.md`](./docs/PRODUCT_INTENT.md) first.**

This repository is a **local, single-user (single-operator) pi agent manager**. It is **not** becoming:

- a SaaS product  
- a multi-tenant cloud service  
- a Tier-4 / enterprise fleet platform  
- a billing-backed commercial multi-tenant offering  

Do **not** propose or implement work whose primary purpose is those destinations. Historical text in `docs/archive/` is not a product roadmap.

**North star:** *One operator. One machine. Many pi agents. No SaaS.*

## Source of truth

| Priority | Source |
|----------|--------|
| 1 | Running code (`pi_orchestrator/`, `dashboard/`) |
| 2 | [`PROJECT_STATE.md`](./PROJECT_STATE.md) |
| 3 | [`docs/PRODUCT_INTENT.md`](./docs/PRODUCT_INTENT.md) |
| 4 | [`README.md`](./README.md), [`docs/architecture.md`](./docs/architecture.md) |
| 5 | Tests under `tests/` |
| last | `docs/archive/**` (historical only; some items explicitly **REJECTED**) |

## Architecture constraints (do not “upgrade away” without owner ask)

- Localhost-oriented FastAPI on port **8420**  
- SQLite + in-process event bus (no Redis requirement)  
- Agents = **`pi` subprocesses**, not Docker containers as the core model  
- `PI_NO_AUTH=1` is the intended daily path  

Optional local auth, sharing, and teams in the codebase are **local convenience**, not a multi-tenant product foundation.

## Dual packages

- **`pi_orchestrator` + `dashboard`** = the product you run  
- **`slice_of_pi`** = abstract contracts; **not imported** by the orchestrator today  
Do not assume wiring contracts into a cloud framework is required.

## Preferred work

Stabilize and improve the **local operator experience**: correctness, tests, security for localhost, UI, docs accuracy, launch scripts. Prefer small, verifiable changes.

**Delivery status (2026-07-15):** Tracks **A (stabilize) → B (harden) → C (polish)** are complete for T1. See `docs/health/TRACK_*_STATUS.md` and `docs/health/HEALTH_BRIEF.md`. Optional next: operator UX plan `docs/health/OPERATOR_UX_PLAN.md` (CapacityMeter, ResourceModal, YamlEditor) — still under PRODUCT_INTENT only.
