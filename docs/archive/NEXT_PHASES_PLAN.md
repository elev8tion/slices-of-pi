# Slice of Pi — Next Phase Orchestration Plan

A staged plan for 3 remaining tiers of features, designed for
`/pi-multi-agent-maestro` parallel execution. Each phase ships
independently. Stop and report after each phase.

---

## Phase 1 — Chat UI Upgrade (3 workers in parallel)

**Goal**: Replace Slice of Pi's basic `ChatPanel.vue` with a richer
rich chat component architecture.

### Worker 1.1 — ChatBubble + ChatMessages
- Create `dashboard/src/components/chat/ChatBubble.vue`:
  - Rich message bubble component
  - Props: `role` (user/agent), `content` (string), `timestamp`, `toolCalls?`
  - Agent messages: indigo left-aligned with agent avatar/name header
  - User messages: dim white right-aligned
  - Markdown rendering in agent messages (code blocks, bold, lists)
  - Tool call chips: small inline badges showing tool name + truncated input
  - Thinking indicator: animated dots when agent is thinking
  - Timestamp: relative time (`2m ago`, `1h ago`)
  - Collapsible code blocks with copy button
- Create `dashboard/src/components/chat/ChatMessages.vue`:
  - Scrollable message list using ChatBubble
  - Auto-scroll to bottom on new messages (pause if user scrolled up)
  - Virtualized rendering (only render visible messages + buffer)
  - "Jump to bottom" button when scrolled away
  - Loading skeleton for initial fetch

### Worker 1.2 — ChatInput + ChatLoadingIndicator
- Create `dashboard/src/components/chat/ChatInput.vue`:
  - Multi-line textarea (Shift+Enter = newline, Enter = send)
  - Send button (indigo accent, disabled when empty)
  - Character count (optional, hidden unless > 80% of limit)
  - File attachment button → file picker → upload → attach to message
  - Disabled state during streaming
  - Auto-resize textarea as content grows (max 8 lines)
  - Keyboard shortcut tooltip: `Enter to send · Shift+Enter for newline`
  - Props: `disabled`, `placeholder`, `modelValue`
  - Emits: `send(text)`, `attach(file)`
- Create `dashboard/src/components/chat/ChatLoadingIndicator.vue`:
  - Three animated bouncing dots (indigo)
  - Pulsing "Thinking..." text below dots
  - Smooth CSS animation, 1s cycle
  - Small variant for inline use, large variant for full-width

### Worker 1.3 — ChatHistoryDropdown + Wire into ChatPanel
- Create `dashboard/src/components/chat/ChatHistoryDropdown.vue`:
  - Dropdown button showing current session name/ID
  - Click opens dropdown list of recent sessions (fetched from `/api/sessions?agent_id=X`)
  - Each session shows: name/ID, turn count, relative time
  - Click to switch session → emits `switch-session(sessionId)`
  - "New Session" button at top
  - Loading state while fetching
  - Teleported dropdown (renders at body level)
- **Rewrite** `dashboard/src/components/ChatPanel.vue`:
  - Integrate ChatMessages, ChatInput, ChatHistoryDropdown
  - Wire ChatInput `send` → existing SSE streaming logic
  - Wire ChatHistoryDropdown → session switch → reload message history
  - Wire file attachments → multipart upload to chat API
  - Replace raw text rendering with ChatBubble
  - Add ChatLoadingIndicator during streaming
  - Keep existing resume and session name functionality
  - Keep existing tool block expand/collapse pattern

**End state**: ChatPanel uses 5 new components. SSE streaming, session
switching, file attachments, markdown rendering all work.

---

## Phase 2 — Productivity Tools (2-3 workers in parallel)

### Worker 2.1 — Slice Plays Panel
- Create `dashboard/src/components/SlicePlaysPanel.vue`:
  - Lists all pi skills (from `GET /api/skills`) in a searchable grid
  - Each skill card: name, description, trigger phrase, run button
  - Click "Run" → sends skill-triggered message to agent chat
  - "Agent Not Running" empty state with guidance
  - Search/filter bar
  - Categories/grouping by skill domain
  - Loading, error, empty states
- Add "Slice Plays" tab to AgentDetail.vue (after Chat tab)
- Backend: `GET /api/agents/{id}/slice-plays/run` — POST endpoint that
  dispatches a skill invocation to the agent's pi session and returns
  the result stream

### Worker 2.2 — Agent Info Panel + StatusIndicator
- Create `dashboard/src/components/InfoPanel.vue`:
  - Read-only panel showing everything about a Slice of Pi agent
  - Template metadata: name, description, version, author
  - Capabilities: tools list, skills list, extensions list
  - Runtime info: model, context window, auto-compact setting
  - Resource info: session count, total tokens, last active
  - Git info: repo URL, branch, last commit (if git enabled)
  - Created/updated timestamps
  - Clean card layout with labeled sections
  - No edit controls — this is view-only
- Add "Info" tab to AgentDetail.vue (first tab, before Chat)
- Create `dashboard/src/components/StatusIndicator.vue`:
  - Reusable status dot component
  - Props: `status` (string: idle/busy/error/created/stopped), `size` (sm/md/lg), `label` (boolean)
  - Color mapping: idle=green, busy=blue, error=red, created=gray, stopped=gray
  - Optional text label next to dot
  - Pulse animation for busy status
- **Refactor** all existing status dots across Slice of Pi to use
  StatusIndicator (AgentCard, AgentDetail header, Sidebar, Dashboard)

### Worker 2.3 — WebSocket Ticket Auth
- Backend: Create `pi_orchestrator/services/ws_ticket_service.py`:
  - `mint_ticket(user_id, ttl=30)` → generates a single-use ticket
    (crypto-random 32-byte hex, stored in memory with expiry)
  - `consume_ticket(ticket)` → validates and invalidates ticket,
    returns user_id or None
  - Ticket cleanup: periodic sweep of expired tickets (every 60s)
  - Thread-safe with a lock
- Create `pi_orchestrator/routers/ws_tickets.py`:
  - `POST /api/ws/ticket` — mint a new ticket (requires auth)
  - Returns `{"ticket": "abc123..."}`
- Update all existing WebSocket endpoints (`/ws/events`, `/ws/logs`,
  `/ws/terminal/{id}`, `/ws/voice/{id}`):
  - Accept `?ticket=` query parameter on connect
  - Validate ticket via `consume_ticket()` before allowing connection
  - Reject with 4001 close code if ticket invalid/expired
- Register ws_tickets_router in `pi_orchestrator/main.py`
- Frontend: Update `connectWebSocket()` in `stores/app.ts`:
  - Fetch ticket from `POST /api/ws/ticket` before each WebSocket connect
  - Append `?ticket=<ticket>` to WebSocket URL
  - Handle 4001 close → redirect to login

---

## Phase 3 — Observability & Operations (2-3 workers in parallel)

### Worker 3.1 — Audit Log
- Backend: `pi_orchestrator/services/audit_service.py`:
  - `log_event(event_type, agent_id, user_id, metadata)` — inserts into
    audit_log table
  - `query_events(filters, pagination)` — searchable query builder
  - Event types: agent_created, agent_updated, agent_deleted,
    session_started, session_ended, credential_set, credential_deleted,
    git_push, git_pull, queue_resolved, settings_changed
- Backend: `pi_orchestrator/routers/audit_log.py`:
  - `GET /api/audit-log` — paginated list, filterable by
    event_type, agent_id, date_range, user_id
  - `GET /api/audit-log/export` — CSV download of filtered results
  - `GET /api/audit-log/stats` — event counts by type over time
  - Admin-only (or PI_NO_AUTH=1 bypass)
- Add audit_log table to `pi_orchestrator/database.py`
- Wire existing operations to push audit events:
  - Agent create/update/delete → audit log
  - Session start/end → audit log
  - Credential set/delete → audit log
  - Operator queue resolve → audit log
- Frontend: Create `dashboard/src/views/AuditLog.vue`:
  - `/audit` route with NavIsland + Sidebar layout
  - Filterable table: event type, agent, user, timestamp
  - Date range picker
  - Event type filter dropdown
  - CSV export button
  - Click row to expand details
  - Auto-refresh toggle
- Wire into `NavIsland.vue` — add "Audit" nav link
- Wire into `dashboard/src/main.ts` — add `/audit` route

### Worker 3.2 — Slice Operations + MCP Key Management
- Backend: `pi_orchestrator/routers/ops.py`:
  - `POST /api/ops/agents/stop-all` — stop all running pi sessions
  - `POST /api/ops/agents/restart-all` — restart all agents
  - `POST /api/ops/scheduler/pause` — pause scheduled executions
  - `POST /api/ops/scheduler/resume` — resume scheduled executions
  - `GET /api/ops/status` — status across all slices
- Frontend: Add "Slices" section to Settings page:
  - Stop All / Restart All buttons with confirmation dialogs
  - Scheduler Pause/Resume toggle
  - Slice status summary card
  - Emergency Stop button (red, with double confirmation)
- Backend: `pi_orchestrator/routers/mcp_keys.py`:
  - `GET /api/mcp-keys` — list configured MCP server keys
  - `POST /api/mcp-keys` — add a new MCP key
  - `DELETE /api/mcp-keys/{id}` — remove an MCP key
  - Keys stored encrypted in the database
- Frontend: Add "MCP Keys" tab to Settings page:
  - List of configured MCP keys (name only, value masked)
  - Add key form: name + value (password field)
  - Delete with confirmation
  - Copy to clipboard

### Worker 3.3 — Polish Components (batch of small components)
- Create `dashboard/src/components/RuntimeBadge.vue`:
  - Props: `runtime` (string: 'pi-code' / 'gemini-cli'), `size` (sm/md)
  - pi-code: indigo badge with π icon
  - gemini-cli: blue badge with ✦ icon
  - Shown on AgentCard and AgentDetail header
- Create `dashboard/src/components/CapacityMeter.vue`:
  - Props: `used` (number), `total` (number), `label` (string)
  - Visual gauge bar: green < 50%, yellow < 80%, red >= 80%
  - Text label: "3/10 agents"
  - Thin horizontal bar style matching Slice of Pi design
- Create `dashboard/src/components/ResourceModal.vue`:
  - Modal showing estimated resource usage for an agent
  - Fields: model (dropdown), tools (checkboxes), skills (chip list)
  - Computed estimates: RAM (MB), disk (MB), context window tokens
  - Estimates based on model + tool count heuristic
  - "Create Agent" button at bottom that pre-fills create form
- Create `dashboard/src/components/EditorHelpPanel.vue`:
  - Slide-out panel showing keyboard shortcuts and tips
  - Sections: Chat shortcuts, Terminal shortcuts, Navigation
  - Triggered by `?` key or help button
  - Dark overlay with slide-in panel from right
- Wire EditorHelpPanel into App.vue (global keyboard shortcut listener)

---

## Phase 4 — Future Reference Only (see `FUTURE_TIER4.md`)

Enterprise features, channel integrations, and complex infrastructure
that are not part of this build cycle.

---

## Execution Guide

```bash
# For each phase:
echo "--- Phase N started ---"

# Phase 1 — Chat UI
cd /Users/kc/slice-of-pi
PI_NO_AUTH=1 python3 start-orchestrator.py &
python3 e2e_test.py && python3 e2e_new_features.py

# Phase 2 — Productivity Tools
# ...
```

**Process**: Run `/pi-multi-agent-maestro` for each phase.
Report results after each phase. No phase depends on a later phase.
Stop after Phase 3.

**Verification**: After each phase, run `npx vite build` + both e2e test
suites. All must pass before advancing.
