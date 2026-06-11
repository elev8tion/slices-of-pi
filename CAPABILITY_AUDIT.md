# Pi ↔ Slice of Pi Capability Audit

**Generated**: 2026-06-10

Every pi native capability mapped against Slice of Pi support.

---

## ✅ FULLY SUPPORTED

| Pi Capability | Slice of Pi Equivalent | How |
|---------------|----------------------|-----|
| Start a session (`pi "prompt"`) | POST /api/agents → POST /chat | Create agent, send message, stream response |
| Read files (read tool) | ✓ Available to agents | Agents have `read` in default tools |
| Run commands (bash tool) | ✓ Available to agents | Agents have `bash` in default tools |
| Edit files (edit tool) | ✓ Available to agents | Agents have `edit` in default tools |
| Write files (write tool) | ✓ Available to agents | Agents have `write` in default tools |
| Web search (web_search) | ✓ Available to agents | Agents have `web_search` in default tools |
| List skills | GET /api/skills | 150 skills detected, frontmatter parsed |
| List extensions | GET /api/extensions | 2 extensions detected |
| Multi-agent (sub-agents) | POST /api/teams/:name/deploy | Deploy teams from teams.yaml |
| Peer-to-peer coms | GET /api/coms | Pool status, peer names |
| Multi-agent maestro | Teams page + deploy-all | 5 team rosters surfaced |
| Session history | GET /api/sessions | Browse, view messages, export JSONL |
| Activity tracking | GET /api/activities | Agent lifecycle events |
| Scheduled execution | GET/POST /api/schedules | Cron-based recurring pi runs |
| Token tracking | Agent dashboard cards | Per-agent token counts |
| Model choice | Agent config (model field) | Select model when creating agent |
| Health monitoring | GET /health | Agent count, session count |

---

## ⚠️ PARTIALLY SUPPORTED (gaps exist)

| Pi Capability | What Works | What's Missing |
|---------------|-----------|----------------|
| Session resume (`pi --resume`) | Session files stored, viewable in UI | **No resume endpoint** — each chat creates new session, can't continue existing one |
| Session forking (`pi --fork`) | — | **Not supported at all** — no fork endpoint |
| Branch management (`/tree`) | — | **Not supported** — no session tree view |
| Session naming (`pi --name`) | — | **Not supported** — sessions have auto-generated IDs, no user-friendly names |
| Tool results viewing | Tool results streamed in chat | Truncated to 2000 chars, no expand-to-full |
| Web content reading (web_scrape) | Not enabled by default | Tool exists in pi but not in Slice defaults |
| Image analysis (analyze_image) | Not available | florence2-vision extension exists but not surfaced |
| System prompts | `system_prompt` field in agent config | Can set on create, edit via PATCH |
| Compaction | Happens in pi sessions | **No visibility** — no compaction config/settings in UI |

---

## ❌ NOT SUPPORTED (missing entirely)

| Pi Capability | Why Missing | Priority |
|---------------|-------------|----------|
| **Session resume** | No endpoint to continue a session | 🔴 HIGH |
| **Model switching mid-session** | No `/model` equivalent in API | 🔴 HIGH |
| **Thinking level control** | No `set_thinking_level` equivalent | 🔴 HIGH |
| **Extension enable/disable** | Read-only list, no toggle | 🟡 MEDIUM |
| **Skill injection into agents** | Skills listed but not applied to agents | 🟡 MEDIUM |
| **Prompt templates** | Not surfaced at all | 🟡 MEDIUM |
| **Theme management** | Not surfaced | 🟢 LOW |
| **Provider/config management** | No settings UI for providers | 🟢 LOW |
| **Package install/uninstall** | No `pi install` equivalent in UI | 🟢 LOW |
| **Damage control rules** | No safety rule management | 🟢 LOW |
| **Keybinding customization** | Not applicable (web UI) | N/A |
| **TUI component customization** | Not applicable (web UI) | N/A |
| **Shell aliases** | Not applicable | N/A |
| **Terminal setup** | Not applicable | N/A |

---

## 🔴 TOP 3 GAPS (must-fix for parity)

### 1. Session Resume
**Current**: Each chat creates a new pi session. No way to continue.
**Needed**: A resume endpoint + UI button that continues the existing session file.
```python
POST /api/agents/{id}/resume  # continues last session
```

### 2. Model Switching
**Current**: Model locked at agent creation.
**Needed**: Switch model mid-session, cycle through models.
```python
POST /api/agents/{id}/chat  # add model param, respects it per-message
POST /api/agents/{id}/model  # switch default model
```

### 3. Thinking Level
**Current**: No thinking control.
**Needed**: Set thinking level (low/medium/high) per agent or per chat.
```python
PATCH /api/agents/{id}  # add thinking_level field
```
