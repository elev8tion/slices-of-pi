# Track C execution status

**Date:** 2026-07-15  
**Product:** T1 local single-operator only  

## Completed

| ID | Item | Change |
|----|------|--------|
| **C1** | Dead panels mounted | Settings: **Slice Ops** (`SlicesPanel`) + **MCP Keys** (`McpKeysPanel`); Status tab keeps health/paths |
| **C2** | Chat history hydration | `ChatPanel.switchSession` loads `/api/sessions/{id}` messages; initial load hydrates latest session; sessions router includes more JSONL event types |
| **C3** | Scheduler session path | `schedule_service` runs via `stream_chat` → managed `~/.pi/agent/sessions/managed/<name>/` |
| **C4** | CI | `.github/workflows/ci.yml` — pytest + vue-tsc + vite build |
| **C5** | Packaging clarity | Root/pi_orchestrator `pyproject` descriptions + README package table |

## Left as utility (not product nav)

- `CapacityMeter.vue`, `ResourceModal.vue`, `YamlEditor.vue` — reusable primitives without dedicated settings surface  
- `stores/notifications.ts` — available for future WS toast wiring  

## Next

Roadmap Tracks A–C complete for T1 stabilize/harden/polish. Further work is product UX by choice only (PRODUCT_INTENT remains binding).
