# Health audit — fixed product target

**Confirmed:** 2026-07-15  
**Authority:** [PRODUCT_INTENT.md](../PRODUCT_INTENT.md), [AGENTS.md](../../AGENTS.md)

## Active target: T1 — Local single-operator

Best-in-class **local** pi agent fleet manager on **one machine**.

- One operator (default `PI_NO_AUTH=1`)
- Localhost FastAPI + Vue dashboard
- SQLite + `pi` subprocesses
- Improve reliability, tests, and operator UX

## Explicitly rejected (do not roadmap)

- SaaS / multi-tenant cloud product  
- Tier-4 enterprise fleet / channel productization  
- Commercial multi-tenant self-host as the goal  
- Billing, tenant usage metering, cloud control plane  

Historical sketches: `docs/archive/rejected/` (nullified).
