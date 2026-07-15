# Test Report

**SHA:** `9249dfa`  
**Date:** 2026-07-15  
**Product target:** T1 local single-operator ([TARGET.md](./TARGET.md))

## Summary

| Suite | Result | Notes |
|-------|--------|--------|
| Full `pytest tests/` | **297 passed, 9 failed, 3 skipped** (~2.8s) | Failures only in live e2e (no server) |
| Unit/API (ignore live e2e) | **297 passed** | `--ignore=test_e2e_api.py --ignore=test_terminal_e2e.py` |
| Live e2e (`test_e2e_api.py`) | **9 failed** | `Connection refused` — expects server on 8420 |
| Dashboard `vue-tsc` | **FAIL** | 9 errors / 5 files ([vue-tsc.log](./vue-tsc.log)) |
| Dashboard `vite build` | **PASS** | ([vite-build.log](./vite-build.log)) |

## Live e2e failures (environment, not logic)

All 9 failures in `tests/test_e2e_api.py` are:

```
{'_error': '<urlopen error [Errno 61] Connection refused>'}
```

Root cause: suite hits real `localhost:8420` without starting the orchestrator. **Not** a product regression when unit suite is green.

**Skipped (3):** recorded in [pytest-full.log](./pytest-full.log) (typically live terminal e2e or conditional skips).

## Coverage map (module → tests present)

| Area | Test modules | Untested / thin (from inventory) |
|------|--------------|----------------------------------|
| health | test_health_api | — |
| agents | test_agents_api | PATCH agent (UI expects, API may lack) |
| chat | test_chat_api | — |
| sessions | test_sessions_api | — |
| schedules | test_schedules_api | — |
| skills/extensions/templates/teams | dedicated tests | — |
| voice / flixz | test_voice, test_flixz | — |
| terminal | test_terminal | test_terminal_e2e needs live server |
| connectors / shared memory / profile | present | — |
| auth / users / sharing | thin or missing | security-relevant |
| files / git / credentials | thin or missing | P0 credentials crash cited in backend review |
| ops / audit / mcp_keys / telemetry | thin or missing | — |
| console / ws events | partial | — |

## Logs

- [pytest-full.log](./pytest-full.log)  
- [pytest-unit.log](./pytest-unit.log)  

## Verdict

**Automated unit/API health: GOOD (297/297).**  
**Live HTTP e2e tests: need server harness or mark as integration.**  
**Frontend typecheck: FAIL (build still succeeds).**
