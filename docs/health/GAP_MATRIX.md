# Gap Matrix

**SHA:** `9249dfa` · **Target:** T1 local single-operator · **Sources:** INVENTORY, TEST_REPORT, E2E_PROBE, FRONTEND_REVIEW, BACKEND_REVIEW, CONTRACTS_VERDICT

| Capability | Code | Test | UI | Docs claim | Status |
|------------|------|------|-----|------------|--------|
| Start + `/health` | Y | Y (unit + probe) | Y | Y | **OK** |
| Agent CRUD | Y | Y unit; live e2e needs server | Y | Y | **OK** (probe create/get/delete) |
| Agent PATCH (edit) | Partial / missing API | N | Y expects PATCH | Y | **GAP** — UI/API drift |
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
| Files | Y | thin | Y | Y | **Partial** — path check P1 |
| Git | Y | thin | Y | Y | **Partial** |
| Auth local | Y | thin | Y | PI_NO_AUTH | **OK for T1**; incomplete if auth on |
| Sharing / users | Y | thin | Y | Y | **Partial** — convenience only |
| Ops / operator queue | Y | thin | Y | Y | **Partial** |
| Audit log | Y | thin | Y | Y | **Partial** |
| MCP keys UI | API Y | thin | **dead panel** | Y | **GAP** — UI unmounted |
| Settings health path | N at `/api/health` | — | wrong URL | — | **GAP** |
| CI (.github) | N | N | — | — | **GAP** |
| `slice_of_pi` wired | N | N | N | contracts package | **Intentional dormant** |
| SaaS / multi-tenant | N | N | N | **rejected** | **N/A — out of scope** |

Legend: **OK** shippable for T1 · **Partial** works with known debt · **GAP** broken or misleading · **N/A** rejected destination
