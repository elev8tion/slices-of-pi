# Trinity → Slice of Pi Sanitization Guide

**Generated**: 2026-06-09
**Principle**: Strip Docker, strip multi-tenant auth, strip Redis, strip OpenTelemetry, strip Slack/Telegram/WhatsApp. Keep router→service→database architecture. Replace Docker agent runtime with pi session management.

---

## Module 1: `01-agent-orchestrator` → Pi Orchestrator

### What Trinity Has (56 routers, 60+ services)
Trinity's `main.py` is a 1,056-line FastAPI app that:
- Manages Docker containers as agents (start/stop/restart/inspect)
- Proxies chat messages via HTTP to the agent's internal server
- Runs Redis Streams event bus for WebSocket broadcasting
- Runs 10+ background services (cleanup, capacity, sync health, operator queue, log archive, audit retention, DB vacuum, session cleanup, canary watching)
- Integrates Slack (Socket Mode + webhook), Telegram, WhatsApp channel adapters
- Has OpenTelemetry distributed tracing
- Has multi-user auth with JWT, email whitelist, roles, scoped WebSocket events

### What Stays (architectural patterns)
| Pattern | Keep? | Pi Version |
|---------|-------|------------|
| FastAPI with `@asynccontextmanager` lifespan | ✅ | Same — start/stop pi session pools in lifespan |
| Router/service split | ✅ | Routers = thin HTTP layer, services = business logic |
| WebSocket event broadcasting | ✅ | Simplified: no Redis, just in-process EventEmitter → WebSocket |
| Activity tracking (activity_service) | ✅ | Track pi session lifecycle events |
| Task execution service | ✅ | pi SDK prompts instead of Docker exec |
| Background services pattern | ✅ | Staggered startup with `asyncio.create_task()` |
| Pydantic models for request/response | ✅ | Same, pi-ified field names |

### What Gets Cut
| Feature | Why Cut |
|---------|---------|
| Docker client / docker_service | No Docker — agents are pi sessions |
| OpenTelemetry (OTLP exporter, tracing) | Overkill for single-user tool |
| Redis Streams event bus | In-process EventEmitter + WebSocket |
| Multi-tenant WebSocket scoping | Single user, no scoping needed |
| Slack/Telegram/WhatsApp adapters | Not a chat platform |
| Operator queue service | No human operator needed |
| Capacity manager (slot service) | Single-user, no capacity limits |
| Canary service | No fleet to canary |
| Log archive service | Console logging is sufficient |
| Audit retention service | No compliance requirement |
| DB vacuum service | SQLite auto-vacuum is fine |
| System agent auto-deploy | No system agent |
| Setup token / admin recovery | Single user, no setup flow |
| Subscription auto-switch | No subscription management |
| Voice (Gemini) | Separate concern |
| Image generation | Separate concern |

### Sanitized Router List (40+ → ~15)

```
pi_orchestrator/src/routers/
├── agents.py          # CRUD agents (pi sessions), list, status
├── agent_config.py    # Per-agent settings (model, tools, skills)
├── agent_files.py     # Workspace file management
├── chat.py            # Stream chat via pi SDK
├── sessions.py        # Session history (browse, resume, export)
├── schedules.py       # Cron schedule management
├── skills.py          # Skills catalog (read from ~/.pi/agent/skills/)
├── extensions.py      # Extension list/status (read from ~/.pi/agent/extensions/)
├── templates.py       # Agent persona templates
├── templates_gallery.py # Template discovery from GitHub
├── settings.py        # App settings
├── events.py          # WebSocket event stream
├── mcp_keys.py        # MCP API key management
├── systems.py         # Multi-agent team management
└── coms.py            # Peer-to-peer agent pool status
```

### Sanitized Service List (60+ → ~12)

```
pi_orchestrator/src/services/
├── pi_session_service.py    # ← docker_service.py — start/stop/monitor pi sessions
├── task_execution_service.py # ← same name — but calls pi SDK, not Docker exec
├── event_bus.py             # ← stripped: no Redis, in-process only
├── activity_service.py      # ← same — tracks session events to DB
├── template_service.py      # ← same — GitHub template discovery, pi persona format
├── skill_service.py         # ← simplified — reads ~/.pi/agent/skills/, no git sync
├── extension_service.py     # ← new — reads ~/.pi/agent/extensions/
├── schedule_service.py      # ← simplified — SQLite + pi SDK
├── git_service.py           # ← same — per-agent git operations
├── settings_service.py      # ← simplified — single-user settings
├── credential_service.py    # ← simplified — pi auth.json management
└── system_service.py        # ← new — multi-agent team deployment
```

### Critical Sanitization: `docker_service.py` → `pi_session_service.py`

Trinity's docker_service.py manages Docker containers:

```python
# TRINITY (what we replace)
def get_agent_container(name):
    return docker_client.containers.get(f"agent-{name}")

def list_all_agents():
    containers = docker_client.containers.list(filters={"label": "agentforge.platform=agent"})
    return [AgentStatus(name=c.name, status=c.status, ...) for c in containers]
```

Pi's equivalent manages pi sessions (processes + JSONL files):

```python
# PI (replacement)
from pi_sdk import AgentSession, SessionManager

async def create_pi_session(config: PiAgentConfig) -> str:
    """Spawn a pi agent as a managed process."""
    session = await AgentSession.create(
        model=config.model,
        tools=config.tools,
        system_prompt=config.system_prompt,
        session_file=f"~/.pi/agent/sessions/managed/{config.name}/{uuid4()}.jsonl"
    )
    return session.id

async def list_pi_sessions() -> list[PiAgentStatus]:
    """List all managed pi sessions."""
    sessions = []
    for session_file in glob("~/.pi/agent/sessions/managed/**/*.jsonl"):
        sessions.append(parse_session_metadata(session_file))
    return sessions

async def stream_chat(agent_id: str, prompt: str) -> AsyncIterator[str]:
    """Send a prompt and stream the response."""
    session = await SessionManager.load(agent_id)
    async for chunk in session.prompt(prompt):
        yield chunk
```

### Critical Sanitization: `main.py` lifespan

Trinity's lifespan starts Docker, Redis, OpenTelemetry, 10+ background services, Slack adapter.

Pi's lifespan:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pi orchestrator lifespan — minimal startup."""
    # 1. Initialize SQLite
    await init_database()
    
    # 2. Start in-process event bus
    await event_bus.start()
    logger.info("Event bus started (in-process)")
    
    # 3. Recover orphaned pi sessions from last run
    recovered = await recover_orphaned_sessions()
    logger.info(f"Session recovery: recovered={recovered} orphaned sessions")
    
    # 4. Start schedule watcher (cron)
    asyncio.create_task(schedule_watcher_loop())
    
    # 5. Discover pi extensions and skills for catalog
    await refresh_extension_catalog()
    await refresh_skill_catalog()
    
    print(f"Pi Orchestrator ready — {len(active_sessions)} active sessions")
    
    yield  # App runs here
    
    # Shutdown
    await event_bus.stop()
    print("Pi Orchestrator shut down")
```

---

## Module 2: `03-api-backend` → Pi Config / Models / DB

### What Trinity Has
- `config.py`: Docker-specific config, Redis URL, CORS origins, API endpoints
- `models.py`: Pydantic models for agents, users, tokens, chat, schedules, subscriptions
- `database.py`: 2,000+ line SQLite facade with 40+ model classes
- `db_models.py`: SQLAlchemy-style dataclasses for users, agents, shares, MCP keys, schedules, chats, activities, notifications, subscriptions
- `dependencies.py`: FastAPI dependency injection for auth, roles, agent ownership

### What Stays
- SQLite as the database
- Pydantic models for API contracts
- Database facade pattern (DatabaseManager class)
- FastAPI dependency injection for route handlers

### What Gets Cut
- User management (single user)
- JWT auth with roles
- Email whitelist
- Subscription models
- Agent sharing/permissions
- Public links
- Notifications system (simplify)
- Nevermined/paid features
- OAuth scoped MCP keys (simplify to API keys)

### Sanitized `config.py`

```python
"""Pi Orchestrator configuration — single-user, no Docker."""

import os
from pathlib import Path

# Paths
PI_HOME = Path(os.path.expanduser("~/.pi"))
PI_AGENT_DIR = PI_HOME / "agent"
PI_SESSIONS_DIR = PI_AGENT_DIR / "sessions" / "managed"
PI_EXTENSIONS_DIR = PI_AGENT_DIR / "extensions"
PI_SKILLS_DIR = PI_AGENT_DIR / "skills"
PI_TEMPLATES_DIR = PI_AGENT_DIR / "templates"
PI_DATABASE_PATH = PI_AGENT_DIR / "orchestrator.db"

# Server
HOST = os.getenv("PI_ORCHESTRATOR_HOST", "127.0.0.1")
PORT = int(os.getenv("PI_ORCHESTRATOR_PORT", "8420"))
CORS_ORIGINS = ["http://localhost:5173", "http://localhost:8420"]

# Pi SDK
PI_BINARY = os.getenv("PI_BINARY", "pi")

# Scheduling
SCHEDULE_POLL_INTERVAL = int(os.getenv("SCHEDULE_POLL_INTERVAL", "30"))
```

### Sanitized `models.py` (key models only)

```python
"""Pi Orchestrator Pydantic models."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class PiAgentStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    IDLE = "idle"
    BUSY = "busy"
    STOPPED = "stopped"
    ERROR = "error"


class PiAgentConfig(BaseModel):
    """Configuration for creating a managed pi agent."""
    name: str
    persona: Optional[str] = None       # Reference to .pi/agents/<persona>.md
    model: Optional[str] = None         # Model override
    tools: list[str] = ["read", "bash", "web_search"]
    skills: list[str] = []              # Skills to inject
    extensions: list[str] = []          # Extensions to load
    system_prompt: Optional[str] = None
    git_repo: Optional[str] = None      # GitHub repo for the agent
    schedule: Optional[str] = None      # Cron expression


class PiAgentSummary(BaseModel):
    """Lightweight agent info for the dashboard grid."""
    id: str
    name: str
    persona: Optional[str]
    status: PiAgentStatus
    model: str
    tokens_used: int
    session_count: int
    last_active: datetime
    uptime_pct: float


class PiSessionEntry(BaseModel):
    """A single session in the history."""
    id: str
    agent_id: str
    agent_name: str
    started: datetime
    ended: Optional[datetime]
    turns: int
    tokens_in: int
    tokens_out: int
    model: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    model: Optional[str] = None
    timeout_seconds: Optional[int] = None


class ScheduleConfig(BaseModel):
    agent_id: str
    cron_expression: str
    message: str
    enabled: bool = True
    model: Optional[str] = None
    max_turns: Optional[int] = None
```

### Sanitized `database.py` (schema only — tables needed)

```sql
-- Pi Orchestrator schema

CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    persona TEXT,
    model TEXT NOT NULL DEFAULT 'claude-sonnet-4-5',
    tools TEXT NOT NULL DEFAULT '["read","bash","web_search"]',
    skills TEXT DEFAULT '[]',
    extensions TEXT DEFAULT '[]',
    system_prompt TEXT,
    git_repo TEXT,
    status TEXT NOT NULL DEFAULT 'created',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    session_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL REFERENCES agents(id),
    session_file TEXT NOT NULL,         -- Path to pi JSONL session file
    status TEXT NOT NULL DEFAULT 'running',
    turns INTEGER DEFAULT 0,
    tokens_in INTEGER DEFAULT 0,
    tokens_out INTEGER DEFAULT 0,
    model TEXT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);

CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    event_type TEXT NOT NULL,           -- 'session_start', 'turn_complete', 'tool_call', 'error', etc.
    event_data TEXT,                    -- JSON blob
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);

CREATE TABLE IF NOT EXISTS schedules (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    cron_expression TEXT NOT NULL,
    message TEXT NOT NULL,
    model TEXT,
    max_turns INTEGER,
    enabled INTEGER NOT NULL DEFAULT 1,
    last_run_at TEXT,
    next_run_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);

CREATE TABLE IF NOT EXISTS schedule_executions (
    id TEXT PRIMARY KEY,
    schedule_id TEXT NOT NULL,
    session_id TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    started_at TEXT NOT NULL,
    completed_at TEXT,
    exit_code INTEGER,
    error_message TEXT,
    FOREIGN KEY (schedule_id) REFERENCES schedules(id)
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mcp_keys (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    key_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    last_used_at TEXT
);
```

---

## Module 3: `04-mcp-server` → Pi MCP Server

### What Trinity Has
- 18 tool files: agents, channels, chat, docs, events, executions, files, memory, messages, monitoring, nevermined, notifications, schedules, skills, subscriptions, systems, tags
- TypeScript MCP server (STDIO + HTTP/SSE transport)
- API key authentication
- MCP Inspector compatibility

### What Stays
- TypeScript MCP server structure
- Tool-per-file organization
- STDIO + HTTP/SSE transport options
- MCP protocol compliance

### What Gets Cut
- channels (no Slack/Telegram/WhatsApp)
- docs (not a doc platform)
- monitoring (no fleet monitoring)
- nevermined (no payments)
- notifications (simplified)
- subscriptions (no subscriptions)
- tags (simplified)

### Sanitized Tool List (18 → ~10)

```
pi-mcp-server/src/tools/
├── agents.ts       # list, get, create, start, stop, delete agents
├── chat.ts         # send prompt, stream response, get history
├── sessions.ts     # list sessions, get session, resume, export
├── skills.ts       # list skills, get skill, search skills
├── extensions.ts   # list extensions, get extension, toggle
├── schedules.ts    # list, create, update, delete schedules
├── files.ts        # list workspace files, read file, write file
├── coms.ts         # list peer agents, send message, check status
├── events.ts       # subscribe to event stream (WebSocket bridge)
└── settings.ts     # get/set orchestrator settings
```

### Sanitized `agents.ts` tool

```typescript
// Trinity's agents.ts manages Docker containers.
// Pi's version manages pi sessions.

export const piAgentsListTool = {
  name: "pi_agents_list",
  description: "List all managed pi agents with status, model, token usage",
  inputSchema: {
    type: "object",
    properties: {
      status: { type: "string", enum: ["running", "idle", "stopped", "error"] },
      persona: { type: "string" }
    }
  },
  handler: async (params) => {
    const agents = await piOrchestrator.listAgents(params);
    return {
      content: [{ type: "text", text: JSON.stringify(agents, null, 2) }]
    };
  }
};

export const piAgentStartTool = {
  name: "pi_agent_start",
  description: "Start a pi agent and begin a managed session",
  inputSchema: {
    type: "object",
    required: ["agent_id"],
    properties: {
      agent_id: { type: "string" },
      prompt: { type: "string" }
    }
  },
  handler: async (params) => {
    const session = await piOrchestrator.startSession(params.agent_id, params.prompt);
    return {
      content: [{ type: "text", text: JSON.stringify(session, null, 2) }]
    };
  }
};
```

---

## Module 4: `05-web-frontend` → Pi Dashboard

### What Trinity Has
- Vue 3 + Tailwind CSS SPA
- 15 views, ~80 components
- Pinia stores for agents, chat, settings
- Vue Router with auth guards
- WebSocket event listeners
- File manager, terminal, YAML editor, advanced settings

### What Stays
- Vue 3 + Tailwind CSS (user's choice from mock)
- Pinia stores
- Vue Router
- WebSocket event listeners (simplified)

### What Gets Cut
- Login/SetupPassword views (single user)
- MobileAdmin view
- Enterprise views
- PublicChat view
- OperatingRoom (complex operator queue)
- Slack/Telegram/WhatsApp channel panels
- NeverminedPanel
- Subscription management
- User management
- Email whitelist settings
- OAuth integration settings

### Sanitized View List (15 → ~8)

```
src/views/
├── Dashboard.vue      # Fleet overview (user's mock)
├── Agents.vue         # Agent grid with filters
├── AgentDetail.vue    # Overlay: chat, terminal, files, activity, settings
├── Sessions.vue       # Session history browser
├── Schedules.vue      # Cron schedule manager
├── Skills.vue         # Skills catalog
├── Extensions.vue     # Extension list and toggles
├── Templates.vue      # Agent persona templates
└── Settings.vue       # App settings
```

### Sanitized Component List (~80 → ~25)

These map directly to the design patterns in the user's HTML mock:

```
src/components/
├── NavIsland.vue          # Fluid pill nav (from mock)
├── Sidebar.vue            # 220px sidebar with saved views
├── StatCard.vue           # Stat card with trend badge
├── AgentCard.vue          # Agent card with sparkline + tags
├── AgentGrid.vue          # 3-column responsive grid
├── AgentDetail.vue        # Overlay with tabs
├── AgentHeader.vue        # Detail header with actions
├── AgentTabs.vue          # Chat/Terminal/Files/Activity/Settings
├── ChatPanel.vue          # Chat with streaming + thinking indicator
├── ChatBubble.vue         # Single message bubble
├── ChatInput.vue          # Input with send button
├── ActivityFeed.vue       # Recent activity list
├── ActivityItem.vue       # Single activity entry
├── OpsQueue.vue           # Operations queue (from mock)
├── OpsItem.vue            # Single ops queue entry
├── TagCloud.vue           # Filter tag cloud
├── FilterPills.vue        # Filter pill group
├── SectionBar.vue         # Section header with filters
├── DashboardHeader.vue    # Title + action buttons
├── SparklineChart.vue     # Mini sparkline for agent cards
├── StatusDot.vue          # Online/busy/idle/error dot
├── AgentAvatar.vue        # Colored avatar with status dot
├── ConfirmDialog.vue      # Generic confirm modal
├── SessionTimeline.vue     # Scrollable session history
└── SkillsPanel.vue        # Skills browser for agent detail
```

---

## Module 5: `07-scheduler` → Pi Scheduler

### What Trinity Has
- Standalone Python service with APScheduler
- Redis distributed locking (prevents duplicate execution)
- SQLite database for schedule persistence
- Health check HTTP endpoint
- APScheduler job stores (memory)
- Retry with exponential backoff
- Timezone-aware cron scheduling
- Pre-check validation before execution

### What Stays
- APScheduler for cron parsing and scheduling
- SQLite persistence
- Health check endpoint
- Cron scheduling with timezone support
- Retry logic

### What Gets Cut
- Redis distributed locking (single instance, no contention)
- Lock auto-renewal (no lock needed)
- Multi-instance safety (single user)
- The whole `locking.py` module
- Auth indicator detection (no subscription management)

### Sanitized Scheduler

```python
"""Pi Scheduler — cron-based pi session execution (single-instance, no Redis)."""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
import pytz
import subprocess
import json

logger = logging.getLogger(__name__)


class PiScheduler:
    """Single-instance scheduler for recurring pi sessions."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.scheduler = AsyncIOScheduler(
            jobstores={"default": MemoryJobStore()},
            timezone=pytz.UTC
        )
        self._running_jobs: dict[str, subprocess.Popen] = {}

    async def start(self):
        """Load enabled schedules from DB and start the scheduler."""
        schedules = self._load_schedules()
        for schedule in schedules:
            if schedule["enabled"]:
                self._add_job(schedule)
        self.scheduler.start()
        logger.info(f"Scheduler started with {len(schedules)} schedules")

    async def stop(self):
        """Graceful shutdown — wait for running jobs."""
        self.scheduler.shutdown(wait=True)
        # Kill any running pi processes
        for job_id, proc in self._running_jobs.items():
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()

    def _add_job(self, schedule: dict):
        """Register a cron job with APScheduler."""
        trigger = CronTrigger.from_crontab(
            schedule["cron_expression"],
            timezone=schedule.get("timezone", "UTC")
        )
        self.scheduler.add_job(
            self._execute_schedule,
            trigger=trigger,
            args=[schedule],
            id=schedule["id"],
            replace_existing=True
        )

    async def _execute_schedule(self, schedule: dict):
        """Execute a scheduled pi session.

        Spawns `pi --mode json --session-file <path> "<message>"` 
        as a subprocess. Tracks execution in the database.
        """
        execution_id = self._record_execution_start(schedule["id"])
        
        try:
            cmd = [
                "pi",
                "--mode", "json",
                "--model", schedule.get("model", "claude-sonnet-4-5"),
                "--session-file", f"~/.pi/agent/sessions/scheduled/{execution_id}.jsonl",
                schedule["message"]
            ]
            
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self._running_jobs[execution_id] = proc
            
            stdout, stderr = proc.communicate(timeout=schedule.get("timeout_seconds", 900))
            
            if proc.returncode == 0:
                self._record_execution_complete(execution_id, "success", stdout)
            else:
                self._record_execution_complete(execution_id, "failed", stderr)
                
        except subprocess.TimeoutExpired:
            proc.kill()
            self._record_execution_complete(execution_id, "timeout", "Execution timed out")
        except Exception as e:
            self._record_execution_complete(execution_id, "error", str(e))
        finally:
            self._running_jobs.pop(execution_id, None)

    def _load_schedules(self) -> list[dict]:
        """Load enabled schedules from SQLite."""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM schedules WHERE enabled = 1"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def _record_execution_start(self, schedule_id: str) -> str:
        import secrets, sqlite3
        execution_id = secrets.token_urlsafe(12)
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO schedule_executions (id, schedule_id, status, started_at) VALUES (?, ?, 'running', ?)",
            (execution_id, schedule_id, datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()
        return execution_id

    def _record_execution_complete(self, execution_id: str, status: str, output: str):
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE schedule_executions SET status = ?, completed_at = ?, error_message = ? WHERE id = ?",
            (status, datetime.utcnow().isoformat(), output[:1000], execution_id)
        )
        conn.commit()
        conn.close()
```

---

## Module 6: `08-config-templates` → Pi Personas & Templates

### What Trinity Has
- Agent templates (YAML + .pi/ directories)
- Process templates (YAML workflow definitions)
- Hooks (pre/post execution scripts)
- Manifests (system topology definitions)
- Canary fleet configuration
- OpenTelemetry collector config
- Vector log config

### What Stays
- Agent persona templates (`.pi/agents/<name>.md` with frontmatter)
- Team rosters (`.pi/agents/teams.yaml`)
- Process templates for workflow definitions

### What Gets Cut
- Docker-specific configs
- Canary fleet config
- OpenTelemetry collector config
- Vector log config
- Docker Compose templates

### Pi Persona Template Format (Already Exists in Pi)

The pi-multi-agent-maestro skill already defines this format:

```markdown
---
name: code-reviewer
description: Reviews PRs for quality, security, and style issues
tools: read,bash,grep,find,web_search
model: claude-sonnet-4-5
skills: review,security
extensions: []
schedule: "0 9 * * 1-5"
---
You are a senior code reviewer. When given a PR:

1. Read the diff carefully
2. Check for: security issues, performance regressions, style violations, 
   missing tests, breaking API changes
3. For each issue found, provide: file:line, severity (critical/high/medium/low),
   explanation, and suggested fix
4. Summarize with an overall assessment and approval recommendation
```

### Team Roster Format (Already Exists)

```yaml
# .pi/agents/teams.yaml
code-review:
  - code-reviewer
  - security-auditor
  - test-writer

devops:
  - deployment-bot
  - monitor-watcher
  - incident-responder

research:
  - web-researcher
  - data-analyst
  - report-writer
```

This format is already supported by pi-multi-agent-maestro. The orchestrator just needs to read these files and surface them in the UI.

---

## Implementation Order

| Phase | What | Files to Create |
|-------|------|-----------------|
| **1** | Database schema + models | `database.py`, `models.py`, `config.py` |
| **2** | Pi session service (no Docker) | `services/pi_session_service.py` |
| **3** | Agent router (CRUD + status) | `routers/agents.py` |
| **4** | Chat router (streaming via pi SDK) | `routers/chat.py` |
| **5** | Event bus (WebSocket) | `services/event_bus.py`, `routers/events.py` |
| **6** | Activity service | `services/activity_service.py` |
| **7** | Session history router | `routers/sessions.py` |
| **8** | Skills catalog router | `routers/skills.py` |
| **9** | Extensions catalog router | `routers/extensions.py` |
| **10** | Scheduler service + router | `services/schedule_service.py`, `routers/schedules.py` |
| **11** | MCP server | `pi-mcp-server/src/tools/*.ts` |
| **12** | Template gallery router | `routers/templates.py` |
| **13** | Coms integration router | `routers/coms.py` |
| **14** | Settings router | `routers/settings.py` |
| **15** | main.py (app + lifespan) | `main.py` |
| **16** | Vue 3 dashboard (design from mock) | `src/views/*.vue`, `src/components/*.vue` |
