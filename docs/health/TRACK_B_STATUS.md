# Track B execution status

**Date:** 2026-07-15  
**Product:** T1 local single-operator only  
**Overall program:** Tracks **A + B + C complete** (see [HEALTH_BRIEF.md](./HEALTH_BRIEF.md), [ROADMAP.md](./ROADMAP.md))  

## Completed

| ID | Item | Change |
|----|------|--------|
| **B1** | Files path containment | `Path.relative_to` + fixed `lstrip("./")` traversal bug; tests in `test_files_path.py` |
| **B2** | Session workspace unify | Terminal uses agent **name** dir (same as chat/files); `test_terminal_workspace.py` |
| **B3** | Flixz path allowlist | Local videos only under `~/.pi/flixz/*`, managed sessions, agent dir, or `PI_FLIXZ_ALLOW_ROOTS`; `test_flixz_paths.py` |
| **B4** | Non-loopback bind warning | Lifespan logs warning if `HOST` not 127.0.0.1/localhost/::1 |
| **B5** | Credentials reveal gate | `GET .../values` requires `?reveal=1`; UI updated; `PI_ALLOW_CREDENTIAL_VALUES=0` disables |

## Verification

```
pytest tests/ --ignore=tests/test_terminal_e2e.py  → green (see CI log)
```

## Next

Track C — local polish (dead panels, chat hydration, scheduler path, CI, packaging). See [ROADMAP.md](./ROADMAP.md).
