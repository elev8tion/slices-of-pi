# Health Brief

**SHA:** `9249dfa`  
**Date:** 2026-07-15  
**Product:** Local single-operator pi fleet manager ([PRODUCT_INTENT.md](../PRODUCT_INTENT.md))  
**Not:** SaaS / multi-tenant / Tier-4  

## Where we are (facts)

| Dimension | Score (1–5) | Evidence |
|-----------|-------------|----------|
| Starts & health | **5** | E2E_PROBE: `/health` ok; SPA 200; docs 200 |
| Core agent lifecycle | **5** | Probe create/get/delete; unit agents tests |
| Chat path (real pi) | **5** | Probe SSE `text_delta` → `pong` with pi 0.80.7 |
| UI production build | **4** | vite PASS; vue-tsc FAIL (9 errors) |
| Automated tests | **4** | 297/297 unit; live e2e suite broken without server |
| Localhost security model | **3** | Intentional open plane under PI_NO_AUTH; dangerous if non-loopback |
| Docs / intent clarity | **5** | PRODUCT_INTENT + AGENTS + rejected archives |
| Packaging clarity | **3** | Dual package still confuses; contracts unwired by design |
| CI | **1** | No `.github` workflows |
| **Overall (T1)** | **~4** | **Runnable and useful locally; stabilize gaps next** |

## What works end-to-end (probed)

1. Orchestrator starts on `127.0.0.1:8420` with `PI_NO_AUTH=1`  
2. Dashboard static serve returns 200  
3. Agent create → chat with real **pi 0.80.7** → SSE text → delete  
4. Skills discovery and host telemetry respond  
5. Lifespan services start: event bus, sync engine, scheduler, cleanup  

## Top risks (fixable product / operator)

| Sev | Issue | Source |
|-----|--------|--------|
| **P0** | Credentials write path crashes (`_safe_execute` missing) | BACKEND_REVIEW |
| **P0** | Settings UI calls `/api/health` (does not exist; only `/health`) | FRONTEND_REVIEW / INVENTORY |
| **P0** | vue-tsc fails (type errors block strict quality bar) | FRONTEND_REVIEW |
| **P1** | Files path `startswith` traversal risk | BACKEND / SECURITY |
| **P1** | Session dir name vs agent_id inconsistency (chat vs terminal) | BACKEND_REVIEW |
| **P1** | System chat `create_agent` signature mismatch | BACKEND_REVIEW |
| **P1** | Scheduler may bypass managed session path | BACKEND_REVIEW |
| **P1** | UI expects agent PATCH; backend may not implement | INVENTORY |
| **P1** | Dead UI: McpKeysPanel, YamlEditor, etc. unmounted | INVENTORY / FRONTEND |
| **P2** | No CI; live e2e tests not wired to start server | TEST_REPORT |
| **P2** | Auth-on mode is incomplete (false security if misused) | SECURITY_NOTES |

**Localhost single-op under `PI_NO_AUTH=1`:** open control plane is **by design**. Do **not** bind `0.0.0.0` or port-forward without understanding SECURITY_NOTES.

## Where we need to be (fixed)

> One operator. One machine. Many pi agents. No SaaS.

Quality bar for T1:

1. Critical operator paths never crash (credentials, agent edit, settings health)  
2. Unit suite green + optional live e2e with harness  
3. Typecheck green or intentionally relaxed  
4. Path safety for files/flixz on a trusted local machine  
5. Docs/UI match API  

## How to get there

See [ROADMAP.md](./ROADMAP.md) — Stabilize → Harden (localhost) → Local polish.  
**No** multi-tenant or Tier-4 work packages.

## Artifact index

| File | Role |
|------|------|
| [TARGET.md](./TARGET.md) | Fixed T1 target |
| [INVENTORY.md](./INVENTORY.md) | Surface map |
| [TEST_REPORT.md](./TEST_REPORT.md) | Pytest / build |
| [E2E_PROBE.md](./E2E_PROBE.md) | Live probe |
| [BACKEND_REVIEW.md](./BACKEND_REVIEW.md) | Backend findings |
| [FRONTEND_REVIEW.md](./FRONTEND_REVIEW.md) | Frontend findings |
| [SECURITY_NOTES.md](./SECURITY_NOTES.md) | Localhost threat model |
| [CONTRACTS_VERDICT.md](./CONTRACTS_VERDICT.md) | slice_of_pi / MCP disposition |
| [GAP_MATRIX.md](./GAP_MATRIX.md) | Feature matrix |
| [ROADMAP.md](./ROADMAP.md) | Ordered next work |
