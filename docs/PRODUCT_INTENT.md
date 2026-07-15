# Product Intent (binding)

**Status:** Binding for all humans and agents working in this repository.  
**Last confirmed:** 2026-07-15 by project owner.  
**Delivery status:** T1 health tracks **A (stabilize) → B (harden) → C (polish)** are **complete**. Optional operator UX only: [health/OPERATOR_UX_PLAN.md](./health/OPERATOR_UX_PLAN.md).

## What this project is

**Slice of Pi** is a **local, single-machine operator console** for managing multiple **pi** coding agents on **one host** (typically a developer Mac).

- Default bind: `127.0.0.1:8420`
- Default auth mode for daily use: `PI_NO_AUTH=1` (single operator)
- Runtime: FastAPI + SQLite + in-process event bus + `pi` subprocesses
- UI: Vue dashboard served from the same process (or Vite in dev)
- General **Flixz** at `/flixz` (system-level frame extraction; no agent required)
- Settings: status, slice ops, MCP keys

## Explicit non-goals (do not build toward these)

The following are **rejected product directions**. Do not plan, implement, document as roadmap, or “leave hooks for” them:

| Rejected direction | Examples (non-exhaustive) |
|--------------------|---------------------------|
| **SaaS / multi-tenant cloud** | Hosted product, tenants, usage billing, cloud control plane |
| **Tier-4 / enterprise fleet product** | Slack/Telegram/WhatsApp product channels, fleet billing, A2A productization as roadmap |
| **Commercial multi-tenant self-host as the goal** | “Productization path” phases that turn this into a company product platform |
| **Docker/K8s-first orchestration** | Replacing pi subprocesses with container fleets as the core model |

Archived files under `docs/archive/` (especially anything labeled **REJECTED**) may describe those ideas historically. **They are not goals.** Prefer this file, `AGENTS.md`, `README.md`, and `PROJECT_STATE.md`.

## What *is* in scope

| In scope | Notes |
|----------|--------|
| Local multi-agent management | Create, chat, terminal, sessions, schedules, skills |
| Operator UX quality | Dashboard, voice, general + per-agent flixz, audit, ops, telemetry |
| Optional local login / sharing | Exists for convenience; **not** a multi-tenant SaaS foundation |
| Stabilization / harden / polish | Tracks A–C done; CI green; path/credential harden |
| Optional MCP bridge | Local STDIO tools against localhost API; MCP keys UI in Settings |
| Abstract contracts in `slice_of_pi/` | Stay dormant unless owner reopens; **not** a cloud framework mandate |
| Optional UX primitives | CapacityMeter, ResourceModal, YamlEditor — plan only until Track D |

## How agents must behave

1. **Read this file and `AGENTS.md` before planning large work.**  
2. If a task implies SaaS, multi-tenant, billing, or Tier-4 enterprise integrations as a product destination — **stop and refuse that framing**; re-scope to local single-operator value.  
3. Do not revive `docs/archive/PRODUCTIZATION_PATH.md` or `docs/archive/FUTURE_TIER4.md` as active plans.  
4. When unsure, optimize for: *“better local pi agent fleet on one machine.”*

## Short north-star sentence

> One operator. One machine. Many pi agents. No SaaS.
