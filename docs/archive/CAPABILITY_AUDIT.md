# Slice of Pi — Capability Audit

**Generated**: 2026-06-11

Every pi native capability mapped against Slice of Pi support.
Updated to reflect the current codebase state.

---

## ✅ FULLY SUPPORTED

| Pi Capability | Slice of Pi Equivalent |
|---------------|----------------------|
| Start a session | POST /api/agents → POST /api/agents/{id}/chat |
| Resume a session | POST /api/agents/{id}/chat with `resume: true` |
| Fork a session | POST /api/agents/{id}/fork |
| Session naming | Pass `name` field in chat request; inline editor in ChatHistoryDropdown |
| Read files (read tool) | Available in default agent tools |
| Run commands (bash tool) | Available in default agent tools |
| Edit files (edit tool) | Available in default agent tools |
| Write files (write tool) | Available in default agent tools |
| Web search (web_search) | Available in default agent tools |
| Web scrape (web_scrape) | Available in default tool list |
| Image analysis (analyze_image) | Available in default tool list |
| List skills | GET /api/skills — parses frontmatter from ~/.pi/agent/skills/ |
| List extensions | GET /api/extensions |
| Multi-agent (sub-agents) | POST /api/teams/:name/deploy from teams.yaml |
| Peer-to-peer coms | GET /api/coms |
| Multi-agent maestro | Teams page with deploy-all |
| Session history | GET /api/sessions — browse, view messages, export JSONL |
| Activity tracking | GET /api/activities + real-time WebSocket events |
| Scheduled execution | CRUD schedules, cron-based via APScheduler |
| Token tracking | Per-agent token counts in dashboard cards |
| Model choice | ModelSelector component in agent create/edit |
| Health monitoring | GET /health |
| Skill injection | Skills selectable in AgentDetail Edit tab |
| Extension toggle | Toggle via PATCH /api/extensions (backend ready) |
| Config/settings viewer | Settings page with YAML editor for ~/.pi/agent/settings.json |
| System prompt editing | system_prompt field in agent create/edit |
| Session compaction config | auto_compact + context_window fields in agent config |

---

## PARTIALLY SUPPORTED

| Pi Capability | What's Missing |
|---------------|----------------|
| Branch management (`/tree`) | No session tree view — sessions are flat |
| Theme management | pi themes not surfaced in dashboard |
| Provider config management | No provider settings UI |
| Package install/uninstall | No `pi install` equivalent in UI |
| Keybinding customization | Not applicable (web UI) |
| Shell aliases | Not applicable |
| TUI customization | Not applicable |

---

## Features Beyond pi

Slice of Pi adds capabilities pi doesn't natively provide:

| Feature | Description |
|---------|-------------|
| **Voice control** | System voice with intent parsing + per-agent voice mode |
| **System Console** | Live orchestrator log streaming |
| **Host Telemetry** | CPU/RAM/Disk monitoring in nav bar |
| **Audit Log** | Full event trail with filters + CSV export |
| **Operator Queue** | Human-in-loop approval for agent requests |
| **Credential Management** | Encrypted API key storage per agent |
| **Git Integration** | GitHub-backed agent configs |
| **File Manager** | Browse/upload/preview agent workspace files |
| **Slice Plays** | One-click skill execution from dashboard |
| **Tag System** | Custom labels + filtering for agents |
| **Session Replay** | Zoomable timeline of agent activity |
| **Onboarding Checklist** | Guided setup for new users |
| **Agent Info Panel** | Read-only overview of agent capabilities |
| **Resource Estimator** | Pre-creation RAM/disk estimates |
| **Editor Help Panel** | Keyboard shortcuts reference |
| **Runtime Badge** | pi-code runtime indicator |
| **Capacity Meter** | Agent slot usage gauge |
| **Replay Timeline** | Visual session timeline with zoom/pan |
