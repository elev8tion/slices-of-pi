# Gap Matrix

**Audit SHA:** `9249dfa` · **Post A–C:** see [HEALTH_BRIEF.md](./HEALTH_BRIEF.md)  
**Target:** T1 local single-operator · **Sources:** INVENTORY, TEST_REPORT, E2E_PROBE, FRONTEND_REVIEW, BACKEND_REVIEW, CONTRACTS_VERDICT · **Updated after Tracks A–C**

| Capability | Code | Test | UI | Docs claim | Status |
|------------|------|------|-----|------------|--------|
| Start + `/health` | Y | Y (unit + probe) | Y | Y | **OK** |
| Agent CRUD | Y | Y unit; live e2e needs server | Y | Y | **OK** (probe create/get/delete) |
| Agent PATCH (edit) | Y (A3) | Y | Y | Y | **OK** |
| Chat SSE + real pi | Y | Y unit (mock); probe real pi **pong** | Y | Y | **OK** |
| Session list/export | Y | Y unit; probe list | Y | Y | **OK** |
| Terminal WS | Y | unit; e2e live separate | Y | Y | **Partial** — ticket/auth edge cases |
| Schedules | Y | Y | Y | Y | **OK** (unit) |
| Skills / extensions | Y | Y | Y | Y | **OK** |
| Templates | Y list | Y | display-only | Y | **Partial** |
| Teams | Y | Y | Y | Y | **OK** unit |
| Voice | Y | Y | Y | Y | **OK** unit |
| Flixz | Y | Y | Y | Y | **Partial** — path safety P1 |
| Credentials | Y | thin | Y | overclaims | **GAP** — P0 write crash; plaintext GET |
| Files | Y | path tests (B1) | Y | Y | **OK** (hardened) |
| Git | Y | thin | Y | Y | **Partial** |
| Auth local | Y | thin | Y | PI_NO_AUTH | **OK for T1**; incomplete if auth on |
| Sharing / users | Y | thin | Y | Y | **Partial** — convenience only |
| Ops / operator queue | Y | thin | Y Settings Slice Ops | Y | **OK** (C1) |
| Audit log | Y | thin | Y | Y | **Partial** |
| MCP keys UI | Y | thin | Y Settings | Y | **OK** (C1) |
| Settings health path | Y `/health` | — | Y | Y | **OK** (A2) |
| General Flixz | Y `/api/flixz` | Y | Y `/flixz` | Y | **OK** |
| CI (.github) | Y | Y | — | — | **OK** (C4) |
| CapacityMeter / ResourceModal / YamlEditor | primitives only | — | unmounted | — | **Planned** Track D |
| `slice_of_pi` wired | N | N | N | contracts package | **Intentional dormant** |
| SaaS / multi-tenant | N | N | N | **rejected** | **N/A — out of scope** |

Legend: **OK** shippable for T1 · **Partial** works with known debt · **GAP** broken or misleading · **N/A** rejected destination
