# Operator UX 1–3 — Implementation Plan

**Date:** 2026-07-15  
**Authority:** PRODUCT_INTENT — local single-operator only  
**No PR** — implement on current branch and verify locally.

## Goals (from design review)

| # | Goal | Outcome |
|---|------|---------|
| **1** | Agent workspace | Near full-viewport agent surface; Chat/Terminal first-class; secondary tabs under “More” |
| **2** | Live reactions | Real activity sparklines (no `Math.random`); WS-driven card/nav glow on busy/error/disconnect |
| **3** | AppShell + ⌘K | Shared shell + global motion tokens; command palette for jump/create/nav |

## Non-goals

- SaaS, multi-tenant, new backend product surfaces  
- Light mode / theme marketplace  
- Full rewrite of every secondary view’s internal CSS  

## Architecture

```
App.vue
  noise-overlay
  CommandPalette (⌘K / Ctrl+K)
  router-view
    AppShell (most authenticated pages)
      NavIsland
      Sidebar | <slot> main
    Login (no shell)

AgentDetail → workspace overlay (~96vw / 92vh, flex column)
  primary tabs: Chat | Terminal | Files | Info
  more: Slice Plays, Git, Credentials, Connectors, Flixz, Sharing, Activity, Edit, Settings
```

## Work packages

### P0 — Global motion + tokens (`main.css`, `tailwind.config.js`)

- Add CSS utilities: `.fade-up`, `.fade-up-d2`…`.fade-up-d8`, `@keyframes fadeUp`
- `prefers-reduced-motion: reduce` → disable entrance animations
- Optional CSS vars: `--ease-out`, `--accent` (document only if used)

### P1 — AppShell + PageHeader

**New:** `dashboard/src/components/AppShell.vue`  
**New:** `dashboard/src/components/PageHeader.vue`

- AppShell: NavIsland + flex shell (Sidebar + main, max-width 1440, padding)
- PageHeader: title, subtitle slot, actions slot
- Migrate: Dashboard, Agents, Console, Flixz, OperatorRoom, Sessions, Settings (minimum); others if time

### P2 — Command palette

**New:** `dashboard/src/components/CommandPalette.vue`  
**Wire:** `App.vue` (global keydown ⌘K / Ctrl+K)

Commands:

- Navigate: Dashboard, Agents, Sessions, Flixz, Console, Ops, Replay, Audit, Settings, …
- Agents: open agent by name (emit event / use a small bus or pinia flag)
- Actions: New agent → set `store.requestCreateAgent` or custom event

**Store addition (minimal):**

```ts
// app store
commandOpenAgentId: ref<string | null>(null)
requestCreateAgent: ref(false)
openAgentFromCommand(id)
requestNewAgent()
clearCommandFlags()
```

Dashboard/Agents watch flags to open AgentDetail / ResourceModal.

### P3 — Agent workspace (AgentDetail.vue)

- Overlay panel: `width: min(96vw, 1400px); height: min(92vh, 900px)` (or 96vw/94vh flex)
- Flex column: header (fixed) → tabs (fixed) → **content flex-1 min-h-0 overflow auto**
- Remove `max-h-80` bottleneck
- Primary tabs visible; secondary in “More” dropdown
- Chat/Terminal panels get full remaining height (min-height ~50vh)

### P4 — Live reactions

**app store:**

- On WS message + activity fetch: maintain `activityPulse: Record<agentId, number[]>` (last 12 buckets) derived from activities or increment on event for that agent
- `recentStatusFlash: Record<agentId, 'busy' | 'error' | null>` with TTL clear (~2.5s) on status change
- `errorAgents` / `busyAgents` already exist — expose for nav

**AgentCard:**

- Replace random sparkline with `pulse` prop or store-derived series
- Classes: `.agent-card--busy`, `.agent-card--error` border glow
- Avatar colors: lime/moss (drop indigo `#818CF8`)

**NavIsland:**

- Pulse connection when `!connected`
- Optional accent on Ops if errors/busy (lightweight)

### P5 — Verify

```
cd dashboard && npx vue-tsc -b --pretty false
cd dashboard && npx vite build
```

Manual smoke: shell layout, ⌘K open/close, open agent workspace size, card glow if busy/error mock.

## Agent team split

| Agent | Owns | Does not touch |
|-------|------|----------------|
| **Shell** | AppShell, PageHeader, main.css motion, migrate views | AgentDetail, CommandPalette |
| **Palette** | CommandPalette.vue, App.vue palette mount, store command flags | AgentDetail layout CSS |
| **Workspace** | AgentDetail.vue workspace layout + tabs | AppShell, CommandPalette |
| **Live** | app.ts pulse/flash, AgentCard, NavIsland glow | View migrations |

**Orchestrator** merges, resolves conflicts, runs verify, fixes.

## Acceptance

- [x] AppShell used on Dashboard + Agents (+ Console, Flixz, Ops)
- [x] Global fade-up works; reduced-motion respected (`main.css`)
- [x] ⌘K opens palette; navigate + open agent works (`CommandPalette` + store flags)
- [x] AgentDetail near full viewport (`min(96vw,1400px)` / `min(92vh,920px)`); primary Chat/Terminal/Files/Info; no max-h-80
- [x] No Math.random sparklines; cards react to status / activity pulse
- [x] vue-tsc + vite build pass (2026-07-15)
- [x] No SaaS framing in copy

## Files (expected touch list)

```
docs/health/OPERATOR_UX_1_3_PLAN.md          (this plan)
dashboard/src/assets/main.css
dashboard/src/components/AppShell.vue        (new)
dashboard/src/components/PageHeader.vue      (new)
dashboard/src/components/CommandPalette.vue  (new)
dashboard/src/App.vue
dashboard/src/stores/app.ts
dashboard/src/components/AgentDetail.vue
dashboard/src/components/AgentCard.vue
dashboard/src/components/NavIsland.vue
dashboard/src/views/Dashboard.vue
dashboard/src/views/Agents.vue
dashboard/src/views/Console.vue              (optional)
dashboard/src/views/Flixz.vue                (optional)
```
