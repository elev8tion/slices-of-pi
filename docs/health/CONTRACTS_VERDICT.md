# Contracts & satellites — verdict

**Date:** 2026-07-15  
**Git SHA (inspection):** `9249dfa`  
**Binding product target:** [docs/PRODUCT_INTENT.md](../PRODUCT_INTENT.md) — *One operator. One machine. Many pi agents. No SaaS.*  
**Health target:** [docs/health/TARGET.md](./TARGET.md) — T1 local single-operator only.  
**Scope of this note:** facts about `slice_of_pi/`, `pi-mcp-server/`, `pi-coding-agent/`, and dual Python package identity; recommendations limited to the **local product**.

---

## Executive summary

| Asset | Role today | Product import path? | Verdict (local product) |
|-------|------------|----------------------|-------------------------|
| `slice_of_pi/` | Abstract ABCs / Protocols / TS interface stubs | **No** — zero imports from `pi_orchestrator/` or `dashboard/` | **Keep (dormant contracts)** — do **not** wire as a cloud framework |
| `pi_orchestrator/` + `dashboard/` | Runnable product (API + UI) | N/A — this *is* the product | **Keep / primary** |
| `pi-mcp-server/` | Optional STDIO MCP → localhost HTTP bridge | Not started by `./slices`; optional | **Keep (optional local bridge)** — small hygiene fixes only |
| `pi-coding-agent/` | Extracted external pi docs + graph artifacts | Not runtime; not imported | **Keep as reference only** (or soft-archive later) |
| Root `pyproject.toml` vs `pi_orchestrator/pyproject.toml` | Two package names, two identities | Runtime uses path import of `pi_orchestrator` | **Keep dual identity explicit** — do not merge into a SaaS framework package |

**Do not:** implement Docker/K8s/Redis/multi-tenant targets sketched inside `slice_of_pi/` docstrings as product roadmap. Those sketches are historical contract imagination, not T1 goals.

---

## 1. `slice_of_pi/` — abstract contracts

### 1.1 Facts

**Location:** [`/Users/kc/slice-of-pi/slice_of_pi/`](../../slice_of_pi/)  
**Packaged by:** root [`pyproject.toml`](../../pyproject.toml) as project name **`slice-of-pi`** (`include = ["slice_of_pi*"]`).  
**Declared version:** `0.1.0` (also `slice_of_pi/__init__.py` `__version__`).  
**Description (root pyproject):** *“Architectural contract layer for a new agentic framework — abstract interfaces, ABCs, and Protocols.”*  
**Classifier:** Development Status :: 2 - Pre-Alpha.  
**Runtime deps:** only `rich>=13.0` (not used by the orchestrator path).

**Layers (from package docstring and tree):**

| Path | Content |
|------|---------|
| `slice_of_pi/core/` | `AgentLifecycle`, `AgentCapability`, `CredentialProvider` |
| `slice_of_pi/orchestration/` | `AgentRuntime`, `WorkflowEngine`, `EventBus`, `SkillProvider`, `ChannelAdapter`, `CLIPlugin`, `AgentClient`, … |
| `slice_of_pi/execution/` | `ExecutionEnvironment`, `GuardrailHook` |
| `slice_of_pi/specification/` | `AgentManifest`, `SystemManifest` |
| `slice_of_pi/infra/` | `TemplateEngine`, `ScheduleEngine`, `PlatformDeployment` |
| `slice_of_pi/testing/` | `TestFixtureFactory`, `ScenarioRunner` |
| `slice_of_pi/interfaces/` | TypeScript stubs: `frontend.ts`, `index.ts` (UI plugin / MCP-shaped types) |
| `slice_of_pi/shared.py` | Shared dataclasses/enums (resource limits, sandbox handles, …) |

**ABC inventory (Python):** at least 15 `ABC` classes under `slice_of_pi/` (lifecycle, runtime, event bus, schedule engine, platform-adjacent types, etc.).

**Import graph — product does not depend on contracts:**

- Grep for `from slice_of_pi` / `import slice_of_pi` / `slice_of_pi.` across the repo: **no matches** in product sources.
- Grep inside `slice_of_pi/` for `pi_orchestrator`: **no matches**.
- Grep in `dashboard/src` for `slice_of_pi`: **no matches**.
- Tests under `tests/` target **`pi_orchestrator` only** — no `slice_of_pi` ABC tests.

This matches [PROJECT_STATE.md](../../PROJECT_STATE.md) §1 / §6.1 and [AGENTS.md](../../AGENTS.md): *“`slice_of_pi` = abstract contracts; **not imported** by the orchestrator today.”*

**Concept drift vs running product:**

| Contract sketch (examples) | Running product reality |
|----------------------------|-------------------------|
| `AgentRuntime` docstring: Docker / K8s / Firecracker sandboxes (`slice_of_pi/orchestration/_agent_runtime.py`) | Agents = **`pi` subprocesses** (`pi_orchestrator/services/pi_session_service.py`) |
| `EventBus` ABC mentions Redis Streams / NATS (`slice_of_pi/orchestration/_event_bus.py`) | In-process bus only (`pi_orchestrator/services/event_bus.py` — “no Redis”) |
| `PlatformDeployment` example YAML: postgres, redis, traefik, docker/k8s (`slice_of_pi/infra/_platform_deployment.py`) | SQLite + localhost FastAPI + optional static Vue; no compose/helm product path |
| `interfaces/frontend.ts` UI plugin / MCP registry types | Dashboard is concrete Vue components; does not import these TS contracts |
| `ChannelAdapter` | Explicitly non-roadmap for SaaS channels; product is local console |

**Product intent already allows dormancy:** [PRODUCT_INTENT.md](../PRODUCT_INTENT.md) lists *“Abstract contracts in `slice_of_pi/` — May stay as interfaces; **not** a mandate to build a cloud framework.”*

### 1.2 Recommendation — **KEEP (dormant); do not WIRE as framework**

| Option | Decision | Why |
|--------|----------|-----|
| **Keep** | **Yes** | Small pure-Python surface; no runtime cost when unused; allowed by product intent as interfaces-only. |
| **Wire** into `pi_orchestrator` | **No** (as a goal) | Would be a large, low-value refactor for T1. Concrete services already work without ABCs. Forcing ABC inheritance does not improve local operator UX. Wiring “toward” Docker/K8s/Redis contracts would violate product direction. |
| **Archive** | Optional later, not required now | Only if ownership wants less tree noise. Prefer `docs/archive/` *or* a clearly labeled contracts-only package — **not** treating archive as a mandate to delete useful vocabulary. |

**Local-product rules if kept:**

1. Treat `slice_of_pi/` as **vocabulary / historical interface sketches**, not a second product.  
2. Do **not** open workstreams whose purpose is “implement PlatformDeployment / K8s runtime / Redis event bus.”  
3. If a *local* abstraction is needed later (e.g. test doubles), prefer extracting **from** `pi_orchestrator` reality upward — not implementing cloud-shaped ABCs downward.  
4. Do not add dashboard imports of `slice_of_pi/interfaces/*.ts` unless a concrete local UI plugin system is intentionally built (out of scope for T1 stabilization unless asked).

---

## 2. `pi-mcp-server/` — optional MCP STDIO bridge

### 2.1 Facts

**Location:** [`/Users/kc/slice-of-pi/pi-mcp-server/`](../../pi-mcp-server/)  
**Package:** `package.json` name `pi-mcp-server` `0.1.0`, `"type": "module"`.  
**Entry:** `src/server.ts` → build output `dist/server.js` (`main`).  
**Deps:** `@modelcontextprotocol/sdk`, `zod`. Dev: `typescript`, `@types/node`.  
**Scripts:** `build` = `tsc`; `start` = `node dist/server.js`; `dev` = `tsx src/server.ts`.  
**Launcher:** **not** started by `./slices` or `start-orchestrator.py`. Documented as optional in [README.md](../../README.md).  
**Product intent:** *“Optional MCP bridge — Local STDIO tools against localhost API”* is **in scope**.

**Transport / base URL:**

```text
PI_ORCHESTRATOR_URL || "http://127.0.0.1:8420"
STDIO (McpServer + StdioServerTransport)
```

**Tools registered in `src/server.ts` (inline — 10 tools):**

| MCP tool | HTTP | Path | Body / notes |
|----------|------|------|----------------|
| `pi_agents_list` | GET | `/api/agents` | — |
| `pi_agent_create` | POST | `/api/agents` | `{ name, model }` — default model `"claude-sonnet-4-5"` |
| `pi_agent_delete` | DELETE | `/api/agents/{agent_id}` | — |
| `pi_chat_send` | POST | `/api/agents/{agent_id}/chat` | `{ message }`; returns **raw response text** (SSE stream body) |
| `pi_sessions_list` | GET | `/api/sessions` | — |
| `pi_session_get` | GET | `/api/sessions/{session_id}` | — |
| `pi_skills_list` | GET | `/api/skills` | — |
| `pi_extensions_list` | GET | `/api/extensions` | — |
| `pi_schedules_list` | GET | `/api/schedules` | — |
| `pi_schedule_create` | POST | `/api/schedules` | `{ agent_id, cron_expression, message }` via `cron` arg |

**API path alignment:** paths and methods match current routers:

- `pi_orchestrator/routers/agents.py` — prefix `/api/agents`
- `pi_orchestrator/routers/chat.py` — `POST /{agent_id}/chat` (SSE)
- `pi_orchestrator/routers/sessions.py` — prefix `/api/sessions`
- `pi_orchestrator/routers/skills.py` — `/api/skills`
- `pi_orchestrator/routers/extensions.py` — `/api/extensions`
- `pi_orchestrator/routers/schedules.py` — `/api/schedules` with field `cron_expression` (MCP maps correctly)

**Partial mismatches / gaps (not path wrong, but incomplete vs API models):**

| Topic | Detail |
|-------|--------|
| Create agent fields | API `PiAgentConfig` also accepts `persona`, `tools`, `skills`, `extensions`, `system_prompt`, `git_repo`, `schedule` (`pi_orchestrator/models.py`). MCP only sends `name` + `model`. |
| Default model | MCP hardcodes `"claude-sonnet-4-5"`; API default is empty string (pi default). |
| Chat | API streams SSE events; MCP collapses to full `res.text()` — usable for tools, not a structured event client. |
| Auth | MCP sends **no** `Authorization` header. Fine under default `PI_NO_AUTH=1` daily path; will not satisfy routes that use `get_current_user` if auth is enabled for those routes. Core agent/chat/session list routes are not globally auth-gated the same way as sharing/users. |
| `mcp_keys` API | `/api/mcp-keys` stores **encrypted secrets for agent MCP usage** (`pi_orchestrator/routers/mcp_keys.py`). It is **not** how `pi-mcp-server` authenticates to the orchestrator. No coupling today. |

**Dead / divergent code:**

- `pi-mcp-server/src/tools/*.ts` (`agents.ts`, `chat.ts`, `sessions.ts`, `schedules.ts`, `skills.ts`, `extensions.ts`) implement the same surface but are **not imported** by `server.ts` (no `from "./tools/..."`).  
- Orphan modules slightly diverge (e.g. `tools/agents.ts` create supports optional `tools` CSV; `server.ts` does not).  
- Effective source of truth: **`src/server.ts` only**.

**Build / run hygiene (static analysis; no CI job observed for this package):**

| Item | Status |
|------|--------|
| `tsc` config | `tsconfig.json`: ES2022, `outDir` `./dist`, `include` `src/**/*.ts` — structurally buildable |
| `dist/` committed | **No** `dist/` present in tree listing |
| `npm run dev` | Uses `tsx`, which is **not** listed in `dependencies` or `devDependencies` — `dev` script is broken unless tsx is global |
| `npm start` | Requires prior `npm run build` |
| `node_modules/` | Present on disk (local install done at some point) |
| Tests | None under `pi-mcp-server/` |
| Started by product launcher | No |

### 2.2 Recommendation — **KEEP (optional local bridge)**

| Option | Decision | Why |
|--------|----------|-----|
| **Keep** | **Yes** | Matches PRODUCT_INTENT optional MCP; thin HTTP proxy; useful for local Claude Desktop / pi MCP wiring against `127.0.0.1:8420`. |
| **Wire** deeper into product process | **No** | Do not embed MCP server inside FastAPI as a multi-tenant control plane. Optional separate STDIO process is correct for single-operator. |
| **Archive** | **No** | Actively described in README and product intent; ~200 LOC of real (if small) value. |

**Hygiene (local-only, optional, small):**

1. Either delete unused `src/tools/` **or** make `server.ts` import them (eliminate dual truth).  
2. Add `tsx` as a devDependency **or** change `dev` to `npx tsx` / document `npm run build && npm start` only.  
3. Document assumption: orchestrator on `127.0.0.1:8420` with `PI_NO_AUTH=1` for daily MCP use.  
4. Do **not** expand tool surface toward SaaS/admin multi-tenant APIs; if expanding, prefer operator-local actions already on the localhost API (ops, sessions, schedules).

---

## 3. `pi-coding-agent/` — reference only

### 3.1 Facts

**Location:** [`/Users/kc/slice-of-pi/pi-coding-agent/`](../../pi-coding-agent/)

| Path | Nature |
|------|--------|
| `source/*.md` | Extracted documentation for the external **pi** coding agent (sessions, skills, RPC, SDK, providers, …) |
| `graph.json`, `graph.html`, `GRAPH_REPORT.md`, `EXTRACTION_SUMMARY.json` | Graphify / analysis artifacts |
| `source/graphify-out/cache/ast/*.json` | Nested AST cache |

**Not application code:** no Python package, no Node package for the orchestrator, no imports from `pi_orchestrator` / `dashboard` / `slice_of_pi`.  
**Not on the launch path:** `./slices`, `start-orchestrator.py`, `install.sh` ignore it.  
**Provenance note:** `EXTRACTION_SUMMARY.json` records root `/Users/kc/doc-kbs/pi-coding-agent/source` (external doc-kb extraction), dated in report metadata 2026-05-17.

**Documented as reference:** [PROJECT_STATE.md](../../PROJECT_STATE.md) §6.3, [docs/architecture.md](../architecture.md) related-packages table, [README.md](../../README.md) structure tree.

**Runtime product dependency on pi:** the **`pi` binary on PATH** (`PI_BINARY`), not this documentation tree.

### 3.2 Recommendation — **KEEP as reference only** (soft-archive optional)

| Option | Decision | Why |
|--------|----------|-----|
| **Keep (reference)** | **Yes (default)** | Helful when debugging session JSONL, skills layout, RPC mode used by `pi_session_service`. |
| **Wire** into build | **No** | Docs/cache must not become a runtime dependency. |
| **Archive** | Optional | Move under `docs/archive/pi-coding-agent/` or git-submodule/external wiki if tree size/noise becomes painful. Graph AST cache is pure noise for product runs. |

**Local-product rule:** when implementing orchestrator features, prefer live `pi` behavior + `pi_orchestrator` code; use `pi-coding-agent/source/*.md` as secondary reference only.

---

## 4. Dual package identity

### 4.1 Facts

| Manifest | Project name | Packages included | Role |
|----------|--------------|-------------------|------|
| [`pyproject.toml`](../../pyproject.toml) (repo root) | **`slice-of-pi`** | `slice_of_pi*` | Contracts / ABCs only |
| [`pi_orchestrator/pyproject.toml`](../../pi_orchestrator/pyproject.toml) | **`pi-orchestrator`** | `pi_orchestrator*` | Runnable FastAPI app |

**Also present:**

- `slice_of_pi.egg-info/` — evidence root package was installable / installed in editable or build form.  
- `dashboard/package.json` — separate frontend package (`slice-of-pi-dashboard` per README table).  
- `pi-mcp-server/package.json` — separate optional Node package.

**How the product actually starts** ([`start-orchestrator.py`](../../start-orchestrator.py)):

1. Inserts **repo root** on `sys.path`.  
2. Imports `pi_orchestrator.main:app`.  
3. Does **not** install or import `slice_of_pi`.  
4. Does **not** require `pip install -e pi_orchestrator/` if the tree is on `PYTHONPATH` (which the launcher ensures).

**Tests:** `tests/conftest.py` and modules import `pi_orchestrator.*` after path/env setup — not `slice_of_pi`.

**Naming tension:**

- Git / product brand: **Slice of Pi**  
- Root PyPI-style name: **slice-of-pi** = contracts only  
- Runnable backend name: **pi-orchestrator**  
- User mental model from README: Slice of Pi ≈ dashboard + orchestrator  

This is **documented** (README “Package identity”, PROJECT_STATE §1) but easy to misread as “install root package to run the app.”

### 4.2 Recommendation — **KEEP dual identity; clarify; do not merge into cloud framework**

| Option | Decision | Why |
|--------|----------|-----|
| **Keep** two Python projects | **Yes** | Matches reality: contracts vs runnable app. Avoids forcing FastAPI deps onto a pure-ABC package and vice versa. |
| **Wire** contracts package as hard dependency of orchestrator | **No** | Adds coupling with zero user benefit for T1. |
| **Merge** into one “agentic framework” distribution | **No** | That path reopens SaaS/framework productization rejected in PRODUCT_INTENT / `docs/archive/rejected/`. |
| **Clarify docs / packaging** | **Yes (light)** | Continue stating: *product = `pi_orchestrator` + `dashboard` via `./slices`*. Root `pyproject.toml` is contracts-only. Optional future: add one-line `readme` note in root pyproject description already partially correct. |

**Install mental model for operators (local):**

```text
./slices                          → product (API + UI)
pi_orchestrator/                  → backend code
dashboard/                        → UI code
slice_of_pi/                      → unused contracts (safe to ignore daily)
pi-mcp-server/                    → optional MCP STDIO client of the API
pi-coding-agent/                  → optional human reference docs
```

---

## 5. Cross-check matrix (local product only)

| Question | Answer | Evidence |
|----------|--------|----------|
| Does orchestrator import contracts? | **No** | No `slice_of_pi` imports in product tree |
| Does dashboard import contracts? | **No** | No matches under `dashboard/src` |
| Does MCP match API paths? | **Yes (core subset)** | `server.ts` paths ↔ routers listed above |
| Does MCP cover full API? | **No** | Subset of agents/chat/sessions/skills/extensions/schedules only |
| Does MCP build cleanly in-repo CI? | **Unknown / not product-gated** | No dist; `tsx` missing from package.json deps; no tests |
| Is `pi-coding-agent` required to run? | **No** | Reference docs + graphs only |
| Is dual pyproject a runtime bug? | **No** | Launcher path-imports `pi_orchestrator`; contracts unused |
| Any mandate to implement cloud ABCs? | **No** | PRODUCT_INTENT + AGENTS.md forbid SaaS/Tier-4 destinations |

---

## 6. Final disposition (actionable)

### Do now (documentation / disposition — no product rewrite)

1. Treat this file as the health-audit answer for WP-5 (contracts & satellites).  
2. Operators and agents: **optimize `pi_orchestrator` + `dashboard`**, not `slice_of_pi` framework completion.  
3. Keep optional MCP as a **localhost STDIO bridge**, not a hosted control plane.

### Do not do

1. **Do not** implement `PlatformDeployment`, K8s/Docker `AgentRuntime`, or Redis `EventBus` “to fulfill contracts.”  
2. **Do not** make `pi_orchestrator` subclass `slice_of_pi` ABCs as a large refactor for its own sake.  
3. **Do not** productize multi-tenant MCP auth/billing around `mcp_keys`.  
4. **Do not** treat `pi-coding-agent/` graph caches as source of truth for code changes.

### Optional low-cost hygiene (only if touching those trees anyway)

| Item | Effort | Value |
|------|--------|-------|
| Remove or wire `pi-mcp-server/src/tools/*` | Small | Remove dual implementation |
| Fix MCP `dev` script deps | Trivial | `npm run dev` works as documented |
| Note in root pyproject that package is contracts-not-app | Trivial | Reduce package-identity confusion |
| Move `pi-coding-agent` graph cache out of primary tree / archive | Small–medium | Noise reduction only |

---

## 7. One-line verdicts

| Path | Verdict |
|------|---------|
| `slice_of_pi/` | **KEEP dormant contracts** — never “wire for SaaS”; optional archive later |
| `pi-mcp-server/` | **KEEP optional local bridge** — paths mostly match; fix orphans/`tsx` when convenient |
| `pi-coding-agent/` | **KEEP reference-only** — not runtime; soft-archive if noisy |
| Dual `pyproject` | **KEEP split** — product is `pi-orchestrator` + dashboard; root is contracts |

**North star preserved:** one operator, one machine, many pi agents — contracts and satellites must not pull the tree toward multi-tenant cloud productization.
)
