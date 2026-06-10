# Pi vs Trinity — Capability & Infrastructure Comparison

**Generated**: 2026-06-09
**Purpose**: Clean comparison of pi (the coding agent) vs Trinity (AgentForge) capabilities and infrastructure, identifying what can be learned/implemented in Slice Of Pi — a UI visualization layer for working with pi.

---

## 1. Executive Summary

**Pi** is a single-agent coding assistant running in a terminal (TUI). It has an extension/plugin system, skills, packages, and an SDK. Its lifecycle is session-based: you start a session, it runs tools, it exits. No persistence layer, no orchestration of multiple agents, no backend server.

**Trinity (AgentForge)** is a multi-agent orchestration platform. Each agent is an isolated Docker container. It has a full backend (FastAPI), frontend (Vue.js), MCP server (62 tools), scheduler, event bus, and deployment infrastructure. Agents are long-lived, scheduled, monitored, and composable into multi-agent systems.

**Slice Of Pi** currently contains 22 abstract interfaces (ABCs, Protocols, dataclasses) extracted from Trinity's architecture — pure contracts, no implementation. The goal is to build a UI visualization that works with pi, inspired by Trinity's frontend.

---

## 2. Architecture Comparison

### 2.1 Pi Architecture

```
┌─────────────────────────────────────────────┐
│                  TUI (Terminal)               │
│  Box | Text | Container | Markdown | Input    │
│  Footer | Overlays | Dialogs | Status        │
├─────────────────────────────────────────────┤
│              Extension System                  │
│  Custom Tools | Event Hooks | Commands        │
│  Custom UI Components | State Persistence     │
├─────────────────────────────────────────────┤
│              Core Agent Engine                 │
│  Provider Adapters (Anthropic, OpenAI, etc.)  │
│  Session Management (JSONL)                   │
│  Compaction | Branching | Forking            │
│  Tool System (read, bash, web_search, etc.)   │
├─────────────────────────────────────────────┤
│              Resource Layer                    │
│  Skills (.md) | Packages (npm/git)           │
│  Prompt Templates | Themes                    │
│  Extensions Dir (~/.pi/agent/extensions/)     │
└─────────────────────────────────────────────┘
```

**Key characteristics:**
- Single process, no server
- Session-based (start → work → exit)
- No database, no API, no authentication
- Local filesystem only (~/.pi/ directory)
- TypeScript/Node.js runtime

### 2.2 Trinity (AgentForge) Architecture

```
┌──────────────────────────────────────────────┐
│         05-web-frontend (Vue.js 3)            │
│   Dashboard / AgentMgr / Chat / Settings      │
│   ~150 components, 15+ views                  │
│   WebSocket events, Pinia stores              │
└──────────────────┬───────────────────────────┘
                   │ HTTP + WS
┌──────────────────▼───────────────────────────┐
│      01-agent-orchestrator (FastAPI)           │
│   300+ endpoints, 40+ routers                  │
│   ┌─────────────────────────────────────────┐ │
│   │ Services: docker, skill, git, ssh,      │ │
│   │ event_bus, credentials, scheduling,      │ │
│   │ monitoring, subscriptions, validation    │ │
│   └─────────────────────────────────────────┘ │
└──┬───────────┬──────────────┬────────────────┘
   │           │              │
┌──▼──────┐ ┌──▼─────────┐ ┌─▼──────────────┐
│ 02-docker│ │ 04-mcp     │ │ 07-scheduler    │
│ -runtime │ │ -server    │ │                 │
│ (1 ctr   │ │ (62 tools) │ │ (cron + Redis   │
│  per     │ │ MCP proto  │ │  distributed    │
│  agent)  │ │            │ │  locking)       │
└──────────┘ └────────────┘ └─────────────────┘
```

**Key characteristics:**
- Multi-service (Docker Compose)
- Full REST API + WebSocket
- SQLite + Redis persistence
- JWT authentication + email whitelist
- OpenTelemetry observability
- Python/FastAPI + TypeScript/Vue

---

## 3. Capability-by-Capability Comparison

| Capability | Pi | Trinity (AgentForge) | Gap |
|---|---|---|---|
| **Agent Execution** | Single process, inline | Isolated Docker containers | Trinity: multi-agent isolation |
| **Agent Lifecycle** | Session-based (start/exit) | Full state machine (CREATED→RUNNING→STOPPED) | Trinity: long-lived agents |
| **Multi-Agent** | Sub-agents (async/chain/parallel) | Full multi-agent systems (SystemManifest) | Trinity: richer topology |
| **UI** | TUI (terminal components) | Vue.js SPA (dashboard, 15+ views) | Trinity: full web UI |
| **Extensions** | TypeScript hooks + tools + commands | API-based plugin system | Pi: deeper agent integration; Trinity: UI plugins |
| **Tools** | read, bash, web_search, analyze_image, subagent, etc. | 62 MCP tools across 18 categories | Trinity: broader tool surface |
| **Skills** | Markdown skills (Agent Skills standard) | Skill injection system + marketplace | Pi: simpler authoring; Trinity: marketplace |
| **Event System** | Internal event hooks (tool_call, agent_start, etc.) | Redis Streams → WebSocket pub/sub | Trinity: durable, distributed |
| **Scheduling** | None | Cron-based scheduler + Redis locking | Trinity: automated recurring execution |
| **Persistence** | ~/.pi/agent/sessions/ (JSONL files) | SQLite + Redis | Trinity: queryable, relational |
| **Auth** | API keys + OAuth subscriptions | JWT + email whitelist + API keys + OAuth | Trinity: multi-tenant |
| **Observability** | None built-in | OpenTelemetry + Vector logs + audit trail | Trinity: production-grade |
| **API** | SDK (programmatic, in-process) | REST API (300+ endpoints) + MCP | Trinity: network-accessible |
| **CLI** | Single `pi` binary | Separate CLI tool (deploy + chat) | Similar scope |
| **Communication Channels** | None (terminal only) | Slack, Telegram, WhatsApp adapters | Trinity: multi-channel |
| **Workflow Engine** | Skill chains (file-based handoff) | YAML-defined multi-step workflows | Trinity: formal workflow engine |
| **Git Integration** | None built-in | Per-agent git repos, branch working trees | Trinity: git-native agents |
| **Deployment** | npm install -g | Docker Compose multi-service | Trinity: production deployment |
| **Session Model** | Tree-based (branch, fork, compact) | Linear sessions | Pi: richer session topology |
| **Theming** | 256-color JSON themes | CSS framework (Tailwind) | Different mediums |
| **Prompt Templates** | .md files with frontmatter | None | Pi only |
| **Custom Providers** | TypeScript provider interface | None needed (models via API) | Pi only |
| **Peer-to-Peer Comms** | Unix sockets + HTTP/SSE | Docker networking | Different transport models |
| **Damage Control** | Extension-based safety rules | GuardrailHook interface | Both have safety |

---

## 4. Infrastructure Comparison

| Layer | Pi | Trinity |
|---|---|---|
| **Runtime** | Node.js process | Docker Compose (3+ services) |
| **Database** | None (filesystem) | SQLite + Redis |
| **API Protocol** | None (in-process SDK) | REST (FastAPI) + MCP + WebSocket |
| **Frontend** | TUI (TypeScript components) | Vue.js 3 SPA (151 files) |
| **Package Manager** | npm + custom pi install | pip + Docker images |
| **Testing** | Shell scripts | 316 test files (unit, integration, security, E2E) |
| **CI/CD** | GitHub Actions (monorepo) | GitHub Actions + deployment scripts |
| **Config** | ~/.pi/agent/settings.json | .env + Docker Compose + YAML templates |
| **Logging** | Console | Vector → JSON files + OpenTelemetry |
| **Monitoring** | None | Health endpoints + canary alerts + fleet audit |

---

## 5. What Slice Of Pi Already Has

The 22 interfaces in `slice_of_pi/` are Trinity's architecture distilled into pure contracts:

```
Layer            Interfaces
─────────────────────────────────────────
Core             3: AgentLifecycle, AgentCapability, CredentialProvider
Orchestration    7: AgentRuntime, WorkflowEngine, EventBus, SkillProvider,
                    ChannelAdapter, CLIPlugin, AgentClient
Execution        2: ExecutionEnvironment, GuardrailHook
Specification    2: AgentManifest, SystemManifest
Infrastructure   3: TemplateEngine, ScheduleEngine, PlatformDeployment
Testing          2: TestFixtureFactory, ScenarioRunner
Plugin (TS)      5: UIPlugin, DashboardWidget, AgentAction,
                    ToolRegistry, MCPTransport
```

**These interfaces align with Trinity's implementation, NOT pi's.** Pi has no backend server, no Docker runtime, no scheduler, no REST API. The interfaces assume a server-based multi-agent orchestration platform.

---

## 6. What to Learn & Implement for Slice Of Pi

### ⭐ Priority 1 — Directly Applicable to Visualizing pi

These are things Trinity does that can be adapted to build a pi UI visualization:

| # | Feature | Trinity Source | How to Adapt for pi UI | Effort |
|---|---|---|---|---|
| 1 | **Agent Dashboard** | `Dashboard.vue`, `DashboardPanel.vue` | Pi session overview — list sessions, status, token usage per session. Pi has SDK methods for this. | Medium |
| 2 | **Real-Time Session View** | `ChatPanel.vue`, `AgentWorkspace.vue` | Stream pi session output (AgentSession.subscribe() gives text_delta events). Real-time token streaming to a web UI. | Medium |
| 3 | **Session Timeline / Replay** | `ReplayTimeline.vue`, `UnifiedActivityPanel.vue` | Pi sessions are JSONL files — parse and render a scrollable timeline of user messages, assistant responses, tool calls/results. | Low |
| 4 | **Session Tree Visualization** | `AgentNode.vue`, `SystemAgentNode.vue` | Pi sessions have branching/forking (tree structure via session file IDs). Visualize the session tree like a git graph. | Medium |
| 5 | **Tool Call Inspector** | `LogsPanel.vue`, `MetricsPanel.vue` | Parse pi JSONL for tool_call entries. Show tools used, parameters, results, timing in a structured panel. | Low |
| 6 | **Token Usage Dashboard** | `CapacityMeter.vue`, `SparklineChart.vue` | Track token usage across sessions from pi's usage events. Sparklines, cost estimates per provider. | Low |
| 7 | **Event Bus** | `event_bus.py` (Redis Streams) | Pi's SDK has session events. Bridge them to a WebSocket for the UI. Lightweight adapter — no Redis needed for single-user. | Medium |
| 8 | **Skills Catalog UI** | `SkillsPanel.vue` | Render pi's skills directory as a browsable catalog. Show frontmatter, descriptions, trigger phrases. Read from ~/.pi/agent/skills/. | Low |
| 9 | **Extension Manager** | `Settings.vue` settings tabs | List installed pi extensions, toggle enable/disable, view registered tools and commands. | Low |
| 10 | **Prompt Template Library** | `Templates.vue` | Browse and preview pi prompt templates from ~/.pi/agent/prompt-templates/. | Low |

### ⭐ Priority 2 — Infrastructure to Support the UI

These are system-level pieces needed to connect a web UI to pi:

| # | Feature | Trinity Source | How to Implement | Effort |
|---|---|---|---|---|
| 11 | **Lightweight API Server** | `main.py` (FastAPI) | A minimal server wrapping pi's SDK: `POST /sessions` (create), `GET /sessions` (list), `GET /sessions/:id` (stream events via SSE), `POST /sessions/:id/prompt` (send message). No Docker, no auth for v1. | Medium |
| 12 | **WebSocket Session Streaming** | `event_bus.py` → WebSocket | Pi's `session.subscribe()` emits events. Bridge to WebSocket so the frontend receives live updates. Single-user = simple in-process bridge. | Medium |
| 13 | **Session Persistence Layer** | `database.py` (SQLite) | pi stores sessions as JSONL files. Add an index: parse JSONL headers, store session metadata (id, name, timestamps, provider, model) in SQLite for fast searching. | Low |
| 14 | **Agent Client Protocol** | `agent_client.py` | SDK's `AgentSession` is the equivalent. Write a TypeScript wrapper that mirrors `AgentClient` interface but delegates to pi's SDK (running in the API server process). | Low |
| 15 | **Plugin System for the UI** | `UIPlugin` interface (frontend.ts) | Pi has extensions. Extend the concept: a pi UI plugin registers dashboard widgets, custom views, and agent actions — same as Trinity's UIPlugin contract. | High |
| 16 | **MCP Server for pi** | `04-mcp-server/src/tools/` | Expose pi capabilities as MCP tools: `pi_sessions_list`, `pi_session_create`, `pi_session_prompt`, `pi_skills_list`, `pi_extensions_list`. This lets any MCP client (Claude Desktop, etc.) control pi sessions. | High |
| 17 | **Scheduled Agent Execution** | `07-scheduler/` | Cron-based recurring pi prompts. Sister concept to Trinity's scheduler. Schedule: "every morning at 8, run `pi -p "Review overnight PRs"`". | High |
| 18 | **Credential Manager UI** | `CredentialsPanel.vue` | Visual manager for pi's auth.json: show configured providers, add/remove API keys, toggle OAuth. | Low |

### ⭐ Priority 3 — Advanced Features (Future)

| # | Feature | Trinity Source | Notes | Effort |
|---|---|---|---|---|
| 19 | **Multi-Agent System Editor** | `SystemViewEditor.vue`, `SystemViewsSidebar.vue` | If pi adds multi-agent capabilities (sub-agents are already a start), visualize agent-to-agent connections. | Very High |
| 20 | **Agent Template Gallery** | `Templates.vue` + `template_service.py` | Pre-configured pi setups (which extensions, skills, system prompts per use case). | High |
| 21 | **Git-Integrated Sessions** | `git_service.py`, `GitPanel.vue` | Auto-commit session state to git branches. Pi sessions could branch per git branch. | High |
| 22 | **Channel Adapters for pi** | `ChannelAdapter` interface | Let pi respond to Slack/Telegram messages. Extend pi's extension system with channel adapters. | Very High |

---

## 7. Key Design Decisions from Trinity to Adopt

### 7.1 The Plugin System Pattern

Trinity's `UIPlugin` + `DashboardWidget` + `AgentAction` contracts are the cleanest thing to borrow:

```typescript
// Trinity pattern — adapt for pi UI
interface PiUIPlugin {
  registerRoutes(router): void;         // Custom views
  registerWidgets(): PiDashboardWidget[];  // Dashboard panels
  registerAgentActions(): PiAgentAction[]; // Per-session action buttons
  init(context: PiPluginContext): Promise<void>;
}
```

This gives pi's UI the same extensibility pi's TUI extensions give the agent.

### 7.2 Event Bus for UI Updates

Trinity uses Redis Streams → WebSocket fan-out. For a single-user pi UI, simplify:

```
pi SDK events → in-memory EventEmitter → WebSocket → frontend stores
```

No Redis needed. But keep the `EventBus` interface (`publish`, `subscribe`, `unsubscribe`) from slice_of_pi's contracts so it's swappable later.

### 7.3 Session as a First-Class Entity

Trinity treats sessions as database rows with full metadata. pi treats them as JSONL files. Bridge the gap:

- **Index**: Parse JSONL headers into a lightweight metadata table
- **Search**: Filter by date, model, provider, session name
- **Export**: pi already supports `export_html` — surface that in the UI

### 7.4 Separation of Runtime from Orchestration

Trinity's `AgentRuntime` ABC is one of its best abstractions. For pi, the "runtime" is the local process — but keeping the interface lets you swap in remote runtimes later:

```python
class PiRuntime(AgentRuntime):
    """Local pi process as an agent runtime"""
    async def create(self, config): return spawn_pi_session(config)
    async def execute(self, agent_id, prompt, context): ...
    async def destroy(self, agent_id): return cleanup_session(agent_id)
```

### 7.5 Observatory-Style Monitoring

Trinity's `Monitoring.vue`, `ObservabilityPanel.vue`, `HostTelemetry.vue` are good templates. For pi, monitor:
- Active sessions count
- Tokens consumed (today/week/month)
- Tool call frequency distribution
- Error rate by provider
- Cost estimates

---

## 8. What NOT to Implement (pi Is Different)

Trinity features that don't make sense to port directly:

| Feature | Why Skip |
|---|---|
| Docker agent isolation | pi runs locally — no container-per-agent needed |
| Full REST API | pi SDK already provides programmatic access |
| JWT auth + email whitelist | Single-user tool, not multi-tenant |
| Redis Streams event bus | Overkill for single-user; in-process bridge suffices |
| Slack/Telegram adapters | pi is terminal-first; channels are a separate concern |
| Workflow engine (YAML DAG) | pi skill chains are simpler and sufficient |
| Git-native agents | pi works on the host's git, not per-agent repos |
| OpenTelemetry | Console logging is fine for v1 |
| Docker Compose deployment | pi is an npm package |

---

## 9. Recommended Implementation Order

### Phase 1: Foundation (Week 1-2)
1. **Session index**: Parse pi JSONL → SQLite metadata table
2. **Session list UI**: Basic dashboard showing all sessions
3. **Session viewer**: Read a session file, render messages in a chat-like view
4. **Lightweight API**: Minimal HTTP server wrapping pi SDK

### Phase 2: Live Interaction (Week 3-4)
5. **Live session streaming**: WebSocket bridge from pi events to frontend
6. **Chat interface**: Real-time pi conversation in the browser
7. **Token usage dashboard**: Charts and cost estimates
8. **Tool call inspector**: Parse and display tool invocations

### Phase 3: Power Features (Week 5-6)
9. **Session tree visualization**: Branch/fork graph
10. **Skills catalog**: Browse pi skills with descriptions
11. **Extension manager**: List, toggle extensions
12. **Plugin system**: UIPlugin contract + widget registration

### Phase 4: Advanced (Week 7-8+)
13. **Scheduled sessions**: Cron-based recurring pi runs
14. **MCP server**: Expose pi as MCP tools
15. **Template gallery**: Pre-configured pi setups
16. **Export & sharing**: Rich session exports

---

## 10. Technology Recommendations

| Component | Trinity Used | Recommended for pi UI |
|---|---|---|
| Backend | Python FastAPI | **Python FastAPI** (or Bun/Node for consistency with pi's TS runtime) |
| Frontend | Vue.js 3 + Tailwind | **Vue.js 3 + Tailwind** (reuse Trinity's `.vue` patterns directly) or **React** (if team prefers) |
| Database | SQLite + Redis | **SQLite only** (no Redis needed for single-user) |
| Real-time | Redis Streams + WebSocket | **In-process EventEmitter → WebSocket** |
| Package mgmt | pip + Docker | pip + npm (pi is npm, UI backend can be pip) |
| Testing | pytest + Playwright | pytest (backend) + Playwright (frontend E2E) |

---

## 11. Key Files to Study from Trinity

| File | What to Learn |
|---|---|
| `05-web-frontend/src/views/Dashboard.vue` | Dashboard layout, widget grid, real-time metrics |
| `05-web-frontend/src/views/AgentDetail.vue` | Agent detail page — tabs for chat, files, skills, settings |
| `05-web-frontend/src/components/ChatPanel.vue` | Chat interface with streaming, tool call rendering |
| `05-web-frontend/src/components/ReplayTimeline.vue` | Scrollable session timeline |
| `05-web-frontend/src/components/SkillsPanel.vue` | Skills catalog UI |
| `05-web-frontend/src/components/MetricsPanel.vue` | Sparklines, capacity meters, usage charts |
| `05-web-frontend/src/components/Templates.vue` | Template gallery + instantiation UI |
| `01-agent-orchestrator/src/services/event_bus.py` | Event bus architecture (simplify for in-process) |
| `01-agent-orchestrator/src/services/skill_service.py` | Skill management pattern |
| `07-scheduler/src/service.py` | Scheduler service design (if adding cron to pi) |
| `04-mcp-server/src/tools/` | MCP tool patterns for exposing pi capabilities |

---

## 12. Summary

**What pi has that Trinity doesn't:**
- TUI (terminal-native components)
- Session tree branching/forking
- Extensions that hook directly into agent lifecycle
- Prompt templates
- Custom providers
- npm-based package distribution

**What Trinity has that pi doesn't:**
- Web dashboard with real-time metrics
- Multi-agent orchestration at scale
- Production infrastructure (auth, DB, monitoring, CI/CD)
- Scheduled execution
- External channel adapters
- MCP server (62 tools)
- Formal workflow engine

**What Slice Of Pi should build:**
A web UI that visualizes pi's session model, streams live agent output, catalogs skills/extensions, tracks token usage, and optionally schedules pi runs. Start with the session viewer + live streaming + dashboard trifecta.
