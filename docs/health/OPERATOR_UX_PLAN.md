# Operator UX Plan — Track D

**Status:** **IMPLEMENTED** — see [TRACK_D_STATUS.md](./TRACK_D_STATUS.md)  
**Authority:** [PRODUCT_INTENT.md](../PRODUCT_INTENT.md) — local single-operator only.  
**Prerequisite:** Tracks A–C complete.  
**Not in scope:** SaaS, multi-tenant, enterprise channels, cloud control plane.

## Goal

Refine **operator-facing** dashboard UX so unused building blocks earn a clear role—or stay explicitly library-only. Prefer small, reversible mounts over new product surfaces.

## Inventory of leftover primitives

| Component | File | What it is today | Fit for T1 |
|-----------|------|------------------|------------|
| **CapacityMeter** | `dashboard/src/components/CapacityMeter.vue` | Pure bar: `used` / `total` / `label` + color thresholds | High — host/agent capacity at a glance |
| **ResourceModal** | `dashboard/src/components/ResourceModal.vue` | Modal to create agent (name, model, tools, skills) with rough RAM/disk estimates | High — better “New Agent” flow than templates-only |
| **YamlEditor** | `dashboard/src/components/YamlEditor.vue` | In-browser YAML editor with light highlighting + validation hook | Medium — local config editing (`orchestrator.json`, personas) |

Also related (already partly mounted):

| Component | Status |
|-----------|--------|
| General Flixz `/flixz` | Shipped |
| Settings → Slice Ops / MCP Keys | Shipped (C1) |
| HostTelemetry | On nav |
| notifications store | Unwired |

---

## Principles (PRODUCT_INTENT)

1. **Local operator first** — every UX piece helps *one person on one machine*.  
2. **No multi-tenant framing** — no “orgs”, billing meters, or fleet SaaS language.  
3. **Reuse APIs** — do not invent new backends unless a clear gap (prefer existing agents, settings, telemetry, system).  
4. **Mount or document** — no silent orphans; either use or mark `// library: optional` in component header.  
5. **Small PRs** — one component integration per PR when possible.

---

## Proposed work packages

### D1 — CapacityMeter on Dashboard + Settings (S)

**Where**

- Dashboard stats row: optional meter for *agents online / registered* (reuse store counts).  
- Settings Status tab: optional meters fed by `GET /api/telemetry/host` (CPU %, RAM %, disk %).

**How**

```vue
<CapacityMeter :used="store.onlineAgents" :total="store.agents.length || 1" label="online" />
<CapacityMeter :used="host.memory.used_gb" :total="host.memory.total_gb" label="GB RAM" />
```

**Acceptance**

- [ ] At least one live mount on Dashboard or Settings  
- [ ] No new API required  
- [ ] Labels stay operator-local (no “tenant quota”)

**Effort:** S  

---

### D2 — ResourceModal as primary “New Agent” (M)

**Where**

- Dashboard header / Agents page: replace or complement “New Agent” → templates-only link.  
- Flow: ResourceModal → `POST /api/agents` → open AgentDetail or toast + refresh list.

**How**

- Wire `@create` to existing create API (`name`, `model`, `tools`, `skills`).  
- Keep estimates as **soft UX hints only** (do not claim hard resource isolation — product is subprocesses, not containers).  
- Name validation must match backend `PiAgentConfig` pattern `^[a-zA-Z0-9_-]+$`.

**Acceptance**

- [ ] Create agent from modal on Dashboard and/or Agents  
- [ ] Success refreshes agent list; failure shows toast  
- [ ] Copy says “local agent” not “provision instance”

**Effort:** M  

---

### D3 — YamlEditor for local config (M)

**Where (pick one primary)**

| Option | Target file | API |
|--------|-------------|-----|
| **A (recommended)** | Settings → “Config” tab | Read/write via existing settings or a thin `GET/PUT /api/settings` + path allowlist for `orchestrator.json` |
| B | Templates detail edit | Persona `.md` / prompt templates under `~/.pi` |
| C | Agent Edit tab advanced | Agent-specific YAML snippet if we store profile_json |

**Recommended:** Option A — edit `~/.pi/agent/orchestrator.json` (profiles) with YamlEditor, save through a **path-safe** settings endpoint (only that file or known keys). Do **not** open arbitrary filesystem write.

**Acceptance**

- [ ] Open, edit, validate, save orchestrator profile JSON/YAML  
- [ ] Reject paths outside allowlist  
- [ ] No SaaS “config sync” language  

**Effort:** M (needs careful backend if file write is new)

---

### D4 — Notifications store wiring (S)

**Where**

- On Dashboard WebSocket `/ws/events`, call `useNotificationStore().handleWsEvent`.  
- Ensure `toastBus.warning` remains available (A4).

**Acceptance**

- [ ] Agent created/deleted show toast/history without new APIs  

**Effort:** S  

---

### D5 — Copy & empty-state polish (S)

- Dashboard empty agents: CTA opens ResourceModal (D2).  
- Flixz card already present — keep path hints.  
- Operator Room / Settings: consistent section labels (“Local operator”, not “Workspace”).

**Effort:** S  

---

## Explicitly out of scope for this plan

| Do not do | Why |
|-----------|-----|
| Multi-user onboarding UX as product | PRODUCT_INTENT |
| Cloud resource quotas / billing meters | Rejected |
| Docker capacity as primary model | Rejected |
| Wiring `slice_of_pi` ABCs into UI | Dormant contracts |
| Removing general Flixz or re-burying it | Already T1 value |

---

## Suggested order

```
D4 (notifications) → D1 (CapacityMeter) → D2 (ResourceModal) → D5 (copy)
         → D3 (YamlEditor + safe config write) last
```

D3 last because it may need a small backend allowlist; the rest are frontend-first.

---

## Definition of done for Track D

- [x] CapacityMeter mounted usefully  
- [x] ResourceModal can create a local agent end-to-end  
- [x] YamlEditor mounted for orchestrator config (fixed path API)  
- [x] PRODUCT_INTENT unchanged  
- [x] Tests/CI still green  

---

## Owner decision (recorded)

Implemented per owner choice **B** with recommended order D4 → D1 → D2 → D5 → D3.
