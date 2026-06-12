# Supermemory → Slice of Pi: Inspirations

> Documentation folder capturing patterns from the [Supermemory](https://github.com/supermemoryai/supermemory) codebase that could inspire improvements to Slice of Pi.
>
> Source toolchest: `~/supermemory-toolchest/`
> Extraction date: 2026-06-12

## Index

| File | What It Covers |
|------|----------------|
| [01-what-is-supermemory.md](./01-what-is-supermemory.md) | Simple explanation of what Supermemory is and how it works |
| [02-patterns-to-steal.md](./02-patterns-to-steal.md) | Cross-project pattern analysis — what to steal, what to skip |
| [03-slice-plays-deep-dive.md](./03-slice-plays-deep-dive.md) | Deep dive on Slice Plays: current limitations + supermemory-inspired future |
| [04-agent-coms-deep-dive.md](./04-agent-coms-deep-dive.md) | Deep dive on agent-to-agent communication: shared pool pattern |
| [05-implementation-roadmap.md](./05-implementation-roadmap.md) | Ordered, concrete code steps — which files to change and what to add |
| [06-connectors-pattern.md](./06-connectors-pattern.md) | Connector plugin system — external data sync with custom plugin support |
| [PLAN-maestro-execution.md](/PLAN-maestro-execution.md) | **Maestro execution plan** — moved to project root. Pass to `/pi-multi-agent-maestro`. |

## The Core Thesis

Supermemory's most valuable pattern for Slice of Pi is the **profile + shared knowledge pool** model:

1. Every entity (user/agent) has a **living profile** — static facts + dynamic context
2. All agents contribute to and read from a **shared knowledge pool**, scoped by tags
3. At session start, the orchestrator **injects relevant context** into the system prompt
4. After each session, **new facts are extracted and stored**
5. **Deduplication** prevents redundant context from piling up

This gives every agent **memory across sessions** and **awareness of other agents' work** — without requiring direct agent-to-agent messaging.

## Quick Reference — All Code Points

| Area | Key Files to Create | Key Files to Modify |
|------|--------------------|--------------------|
| **Agent Profiles** | `agent_profile_service.py` | `database.py`, `models.py`, `pi_session_service.py` |
| **Shared Knowledge** | `shared_memory_service.py` | `coms.py`, `ComsPanel.vue` |
| **Slice Plays** | `slice_play_service.py`, `routers/slice_plays.py` | `skills.py`, `SlicePlaysPanel.vue`, `models.py` |
| **Connectors** | `services/connectors/` (6 files), `routers/connectors.py` | `database.py`, `main.py`, `schedule_service.py`, `Settings.vue` |
| **Agent-to-Agent** | (uses shared knowledge pool) | `pi_session_service.py`, `coms.py` |
