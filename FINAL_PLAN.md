# Slice of Pi — Final Completeness Plan

**Goal**: Close all remaining gaps so Slice of Pi matches 100% of pi's native capabilities.

---

## Phase F — Capability Parity (8 steps)

### F1: Session Fork
**What**: Fork an existing session into a new branch.
**Backend**: `POST /api/agents/:id/fork` — copies the session JSONL file, creates new session record, returns new session ID.
**Frontend**: Fork button in Sessions.vue next to each session.
**Verify**: `curl -X POST /api/agents/:id/fork` → returns new session_id, session file is a copy.

### F2: Prompt Templates API
**What**: Expose pi prompt templates via API and UI.
**Backend**: `GET /api/templates/prompts` — reads `.pi/agent/prompt-templates/*.md`, parses frontmatter, returns list with content.
**Frontend**: New "Prompts" tab in Templates.vue showing template cards with name, description, and expandable content preview.
**Verify**: `curl /api/templates/prompts` → returns array, Templates page has Prompts tab.

### F3: Skill Injection
**What**: Apply skills to agents (currently listed but not injected).
**Backend**: When creating/updating an agent with `skills` field, pass skills via `--skill` flag to pi binary. Add skill content to system prompt as context.
**Frontend**: Multi-select skills in agent create/edit form.
**Verify**: Create agent with `skills:["review"]` → pi session has review skill context.

### F4: Extension Toggle
**What**: Enable/disable extensions for agents via API.
**Backend**: `PATCH /api/extensions/:name` with `{"enabled":bool}`. Agent config stores enabled extensions list. When spawning pi, pass only enabled extensions.
**Frontend**: Toggle switch on each extension card in Extensions.vue.
**Verify**: `curl PATCH /api/extensions/...` → toggles enabled state, reflected in list.

### F5: Config/Settings Viewer
**What**: View and edit pi settings.json from the dashboard.
**Backend**: `GET /api/settings` — reads `~/.pi/agent/settings.json`, returns parsed JSON. `PUT /api/settings` — writes back.
**Frontend**: Settings page shows current config as formatted JSON with edit capability.
**Verify**: `curl /api/settings` → returns settings JSON, Settings page shows it.

### F6: Web Scrape + Image Analysis Tools
**What**: Add `web_scrape` and `analyze_image` to available tools.
**Backend**: Add to DEFAULT_TOOLS in config. Ensure pi binary has these tools.
**Verify**: Create agent → tools include web_scrape and analyze_image.

### F7: Full Tool Results
**What**: Remove 2000-char truncation on tool results in chat streaming.
**Backend**: In `_stream_jsonl`, increase or remove the `[:2000]` truncation on tool_result content. Add a `truncated` flag when content exceeds render limit.
**Frontend**: Show "Show full output (12KB)" expand button on truncated results.
**Verify**: Agent runs a bash command with >2000 chars output → full output visible with expand.

### F8: Session Naming + Compaction Config
**What**: User-friendly session names and compaction visibility.
**Backend**: Add `name` field to session create/update. Add `auto_compact` and `context_window` fields to agent config.
**Frontend**: Session name input in ChatPanel. Compaction settings in Agent Edit tab.
**Verify**: Create session with name → name appears in Sessions list. Agent has compaction config.

---

## Plan Integrity

- Total steps: 8
- All verify conditions: runnable, binary, specific
- Dependencies: None (all independent)
- Unbounded steps: 0
- Gate: PASSED
