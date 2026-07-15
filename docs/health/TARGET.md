# Health audit — fixed product target

**Confirmed:** 2026-07-15  
**Authority:** [PRODUCT_INTENT.md](../PRODUCT_INTENT.md), [AGENTS.md](../../AGENTS.md)  
**Tracks A–C:** complete (T1 health bar met)

## Active target: T1 — Local single-operator

Best-in-class **local** pi agent fleet manager on **one machine**.

- One operator (default `PI_NO_AUTH=1`)
- Localhost FastAPI + Vue dashboard
- SQLite + `pi` subprocesses
- Stabilize / harden / polish: **done** (see ROADMAP + TRACK_*_STATUS)
- Optional next: operator UX primitives ([OPERATOR_UX_PLAN.md](./OPERATOR_UX_PLAN.md))

## Explicitly rejected (do not roadmap)

- SaaS / multi-tenant cloud product  
- Tier-4 enterprise fleet / channel productization  
- Commercial multi-tenant self-host as the goal  
- Billing, tenant usage metering, cloud control plane  

Historical sketches: `docs/archive/rejected/` (nullified).
