# Connectors — Auto-Sync Pattern for Slice of Pi

> How Supermemory's external data sync pattern could bring connectors to Slice of Pi — with a plugin system for custom connectors.

---

## What Supermemory Does

Supermemory syncs data from external sources so your AI can search across them:

| Connector | What It Syncs | How |
|-----------|--------------|-----|
| **Google Drive** | Docs, PDFs, Slides, Sheets | OAuth → webhook-driven sync |
| **Gmail** | Emails | OAuth → periodic poll |
| **Notion** | Pages, databases | OAuth → webhook-driven sync |
| **OneDrive** | Office documents | OAuth → webhook-driven sync |
| **GitHub** | Repos, issues, PRs | GitHub App → webhook-driven sync |
| **Browser Extension** | Web pages you visit | Chrome extension → POST to API |
| **Apple Shortcuts** | Any shortcut output | Native iOS Shortcuts → API |
| **Granola** | Meeting notes | Partner integration → API |

**The key pattern:** Each connector:
1. Has an **OAuth flow** to get access
2. Has a **sync mechanism** (poll or webhook)
3. Converts external data into **Supermemory documents** (which get chunked, embedded, and indexed)
4. Documents are **scoped to a container tag** (project)
5. Status is tracked in a **`connections` table** with `provider`, `email`, `expiresAt`, `containerTags`, `metadata`

```typescript
// The supermemory connection schema
interface Connection {
  id: string
  provider: string        // "google-drive" | "notion" | "onedrive" | "granola"
  email?: string           // The connected account email
  containerTags?: string[] // Which projects this data flows into
  expiresAt?: string       // Token expiry
  metadata?: Record<string, any>  // Provider-specific state
  documentLimit?: number
  createdAt: string
}
```

---

## What Slice of Pi Already Has That's Close

Slice of Pi already has **80% of the infrastructure** for connectors:

| Infrastructure | Slice of Pi File | What It Does |
|---------------|-----------------|-------------|
| **Encrypted storage** | `routers/credentials.py` | Fernet AES-128 encrypted API key storage per agent |
| **MCP key storage** | `routers/mcp_keys.py` | Encrypted MCP server key management |
| **Schedule/cron** | `routers/schedules.py` | Cron-based recurring execution |
| **Extensions** | `routers/extensions.py` | Plugin discovery from `~/.pi/agent/extensions/` |
| **Git service** | `services/git_service.py` | Git operations via subprocess |
| **Event bus** | `services/event_bus.py` | In-process WebSocket pub/sub |
| **SQLite persistence** | `database.py` | Tables for any new connector data |

**What's missing:**
- ❌ No `connectors` table or model
- ❌ No OAuth flow (credentials are static API keys, not OAuth tokens)
- ❌ No webhook listener
- ❌ No sync engine (scheduled content ingestion)
- ❌ No abstraction for "connector plugin" — each connector needs to be separately coded

---

## The Connector Abstraction (Plugin System)

The key design decision: **every connector is a plugin** with a standard interface, so anyone can add their own.

```python
# pi_orchestrator/services/connectors/_base.py

class ConnectorPlugin(ABC):
    """Abstract connector for external data sources.
    
    Connectors sync external data into the agent's knowledge pool.
    Each connector is a self-contained plugin that handles its own
    auth, sync logic, and document conversion.
    """

    @property
    @abstractmethod
    def provider(self) -> str:
        """Unique provider name, e.g. 'google-drive', 'custom-slack'."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name, e.g. 'Google Drive'."""
        ...

    @abstractmethod
    async def authorize(self, config: dict) -> dict:
        """Initiate OAuth flow or validate API key.
        
        Returns auth state dict with tokens, expiry, etc.
        """
        ...

    @abstractmethod
    async def sync(self, auth: dict, since: datetime | None = None) -> list[dict]:
        """Fetch new/changed content since last sync.
        
        Returns list of documents:
          [{"id", "title", "content", "url", "type", "updated_at"}, ...]
        
        Called by the sync engine on a schedule.
        """
        ...

    @abstractmethod
    async def verify(self, auth: dict) -> bool:
        """Check if the connector's auth is still valid."""
        ...

    def get_schedule(self) -> str | None:
        """Cron expression for auto-sync. None = manual only.
        
        Default: None (manual sync)
        """
        return None
```

### Built-in connectors ship as plugins

```
pi_orchestrator/services/connectors/
├── __init__.py
├── _base.py               ← ConnectorPlugin base class
├── registry.py            ← Connector registry
├── engine.py              ← Sync engine (scheduler)
├── builtins/
│   ├── __init__.py
│   ├── google_drive.py    ← Example built-in
│   ├── github.py          ← Example built-in
│   └── webhook.py         ← Generic incoming webhook (ultra-easy custom)
└── user/                  ← User-installed custom connectors
    └── ...                ← Loaded from ~/.pi/connectors/*.py
```

---

## The Database Model

```sql
CREATE TABLE IF NOT EXISTS connectors (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,          -- 'google-drive', 'custom-slack', etc.
    label TEXT NOT NULL,             -- User-given label, e.g. "Work Gmail"
    auth_state TEXT NOT NULL,        -- Encrypted JSON: tokens, expiry, etc.
    container_tags TEXT NOT NULL,    -- JSON array: which memory scopes
    enabled INTEGER NOT NULL DEFAULT 1,
    last_sync_at TEXT,
    last_sync_status TEXT,           -- 'success', 'error', 'running'
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS connector_sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    connector_id TEXT NOT NULL REFERENCES connectors(id) ON DELETE CASCADE,
    status TEXT NOT NULL,             -- 'running', 'success', 'error'
    items_found INTEGER DEFAULT 0,
    items_imported INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT
);
```

---

## The Sync Engine

```python
# pi_orchestrator/services/connectors/engine.py

class SyncEngine:
    """Runs connector syncs on schedule or on demand.
    
    Flow:
      1. Load all enabled connectors for all agents
      2. For each connector: call connector.sync(auth, since=last_sync)
      3. Convert returned docs → write to shared knowledge pool
      4. Update last_sync_at
      5. Log results to connector_sync_log
    """

    def __init__(self, db, shared_memory_service):
        self.db = db
        self.shared_memory = shared_memory_service
    
    async def sync_connector(self, connector_id: str) -> dict:
        """Sync a single connector. Returns sync result."""
        row = self.db.get_connector(connector_id)
        if not row:
            return {"error": "Connector not found"}
        
        plugin = registry.get(row["provider"])
        if not plugin:
            return {"error": f"Unknown provider: {row['provider']}"}
        
        auth = json.loads(row["auth_state"])
        
        # Verify auth is still valid
        if not await plugin.verify(auth):
            return {"error": "Auth expired — re-authorize"}
        
        # Run sync
        try:
            self.db.log_sync_start(connector_id)
            since = row["last_sync_at"]
            docs = await plugin.sync(auth, since)
            
            # Write each doc to the shared knowledge pool
            tag = json.loads(row["container_tags"])[0] if row["container_tags"] else "default"
            for doc in docs:
                self.shared_memory.write_fact(
                    agent_id=row["agent_id"],
                    tag=tag,
                    fact=f"[{plugin.display_name}] {doc['title']}: {doc['content'][:200]}...",
                    fact_type="document",
                    metadata={"url": doc.get("url"), "type": doc.get("type")},
                )
            
            self.db.log_sync_complete(connector_id, len(docs), len(docs))
            return {"status": "success", "items": len(docs)}
        except Exception as e:
            self.db.log_sync_error(connector_id, str(e))
            return {"error": str(e)}
    
    async def sync_all(self):
        """Sync all enabled connectors for all agents."""
        connectors = self.db.list_connectors(enabled_only=True)
        results = []
        for c in connectors:
            result = await self.sync_connector(c["id"])
            results.append({"connector": c["id"], "provider": c["provider"], **result})
        return results
```

---

## Making Custom Connectors Trivial

The whole point is that **adding a new connector doesn't require changing a single line of slice-of-pi core code**. A user writes a plugin:

```python
# ~/.pi/connectors/my_slack_bookmarks.py

from pi_orchestrator.services.connectors._base import ConnectorPlugin

class SlackBookmarksConnector(ConnectorPlugin):
    provider = "slack-bookmarks"
    display_name = "Slack Bookmarks"
    
    async def authorize(self, config):
        # config: {"token": "xoxb-..."}
        # Validate the token, return auth state
        return {"token": config["token"], "team": "my-team"}
    
    async def sync(self, auth, since=None):
        # Fetch bookmarked messages from Slack API
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://slack.com/api/...",
                headers={"Authorization": f"Bearer {auth['token']}"},
            )
            data = resp.json()
            return [
                {
                    "id": item["id"],
                    "title": item.get("title", "Slack bookmark"),
                    "content": item.get("text", ""),
                    "url": item.get("permalink"),
                    "type": "slack_message",
                    "updated_at": item["updated"],
                }
                for item in data.get("bookmarks", [])
            ]
    
    async def verify(self, auth):
        return bool(auth.get("token"))
    
    def get_schedule(self):
        return "0 */6 * * *"  # Every 6 hours

# Register it
connector = SlackBookmarksConnector()
```

The user drops this file in `~/.pi/connectors/` and it shows up in the dashboard. No restart needed if the registry scans on each request.

---

## The Dashboard Surface

The dashboard should have a **Connectors tab** (like Settings → Integrations in supermemory):

```
Agent Detail
├── Chat
├── Terminal
├── Files
├── Settings
├── Slice Plays
├── Connectors          ← NEW
│   ├── Google Drive    [Configure] [Sync Now] ✅ Last sync: 2h ago
│   ├── GitHub          [Configure] [Sync Now] ✅ Last sync: 30m ago
│   ├── Slack Bookmarks [Configure] [Sync Now] ⚠️ Auth needed
│   └── [+ Add Connector]  ← Discover plugins from ~/.pi/connectors/
│
│   Configure modal:
│   ┌─────────────────────────────────────────┐
│   │  Google Drive                          │
│   │                                        │
│   │  Auth: [Connect Google Account] (OAuth) │
│   │  or                                    │
│   │  API Key: [___________________]        │
│   │                                        │
│   │  Scope to tags: [frontend] [infra]     │
│   │                                        │
│   │  Auto-sync: ● Every 4h  ○ Manual       │
│   │                                        │
│   │  [Save]                                │
│   └─────────────────────────────────────────┘
```

---

## Code Points Map

### New files to create

| File | Purpose |
|------|---------|
| `pi_orchestrator/services/connectors/__init__.py` | Package init |
| `pi_orchestrator/services/connectors/_base.py` | `ConnectorPlugin` base class |
| `pi_orchestrator/services/connectors/registry.py` | Connector registry (discover builtins + user plugins) |
| `pi_orchestrator/services/connectors/engine.py` | Sync engine (on-demand + scheduled) |
| `pi_orchestrator/services/connectors/builtins/__init__.py` | Built-in connector package |
| `pi_orchestrator/services/connectors/builtins/webhook.py` | Generic incoming webhook (anyone POSTs → becomes knowledge) |
| `pi_orchestrator/routers/connectors.py` | FastAPI router: CRUD + sync trigger |

### Existing files to modify

| File | Change |
|------|--------|
| `pi_orchestrator/database.py` | Add `connectors` and `connector_sync_log` tables + CRUD methods |
| `pi_orchestrator/models.py` | Add `Connector`, `ConnectorPluginManifest` Pydantic models |
| `pi_orchestrator/main.py` | Register `/api/connectors` router, init sync engine |
| `pi_orchestrator/services/schedule_service.py` | Register connector auto-sync cron jobs |
| `pi_orchestrator/config.py` | Add `CONNECTORS_DIR` config pointing to `~/.pi/connectors/` |
| `dashboard/src/views/Settings.vue` | Add "Connectors" section |
| `dashboard/src/components/AgentDetail.vue` | Add Connectors tab |

---

## Custom Connector Loading (Plugin Discovery)

```python
# pi_orchestrator/services/connectors/registry.py

import importlib.util
from pathlib import Path
from typing import Optional
from ._base import ConnectorPlugin

CONNECTORS_DIR = Path.home() / ".pi" / "connectors"
_registry: dict[str, ConnectorPlugin] = {}


def discover_plugins() -> dict[str, ConnectorPlugin]:
    """Scan ~/.pi/connectors/ and builtins for all ConnectorPlugin classes."""
    plugins = {}
    
    # 1. Load builtins
    from .builtins.webhook import WebhookConnector
    for cls in [WebhookConnector]:
        inst = cls()
        plugins[inst.provider] = inst
    
    # 2. Load user plugins from ~/.pi/connectors/
    if CONNECTORS_DIR.exists():
        for file in CONNECTORS_DIR.glob("*.py"):
            spec = importlib.util.spec_from_file_location(file.stem, file)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if isinstance(attr, type) and issubclass(attr, ConnectorPlugin) and attr is not ConnectorPlugin:
                    inst = attr()
                    plugins[inst.provider] = inst
    
    return plugins


def get(provider: str) -> Optional[ConnectorPlugin]:
    """Get a connector plugin by provider name."""
    if not _registry:
        _registry.update(discover_plugins())
    return _registry.get(provider)


def list_available() -> dict[str, dict]:
    """List all available connector plugins (for the dashboard)."""
    if not _registry:
        _registry.update(discover_plugins())
    return {
        name: {
            "provider": plugin.provider,
            "display_name": plugin.display_name,
            "has_schedule": plugin.get_schedule() is not None,
            "schedule": plugin.get_schedule(),
        }
        for name, plugin in _registry.items()
    }
```

---

## Why This Pattern Works for Slice of Pi

1. **Reuses existing credential encryption** — The `credentials.py` Fernet system becomes the `auth_state` storage
2. **Reuses existing schedule system** — `get_schedule()` returns a cron expression that feeds into the existing `schedule_service.py`
3. **Feeds into the shared knowledge pool** — Synced documents become facts in the pool, which agents read at session start
4. **Zero-dependency for custom connectors** — A file in `~/.pi/connectors/*.py` just needs to implement 3 methods
5. **Graceful degradation** — If a connector's auth expires, agents just don't get that data; no crash

### Example: The Simplest Possible Custom Connector

```python
# ~/.pi/connectors/my_notes.py
# No deps, no OAuth, just reads a file

from pi_orchestrator.services.connectors._base import ConnectorPlugin
from pathlib import Path

class MyNotesConnector(ConnectorPlugin):
    provider = "my-notes"
    display_name = "My Local Notes"
    
    async def authorize(self, config):
        # Just validate the path exists
        path = Path(config["path"]).expanduser()
        if path.exists():
            return {"path": str(path)}
        raise ValueError(f"Path does not exist: {path}")
    
    async def sync(self, auth, since=None):
        path = Path(auth["path"])
        docs = []
        for file in path.glob("*.md"):
            mtime = file.stat().st_mtime
            if since and mtime <= since.timestamp():
                continue
            docs.append({
                "id": file.name,
                "title": file.stem,
                "content": file.read_text(),
                "type": "markdown",
                "updated_at": datetime.fromtimestamp(mtime).isoformat(),
            })
        return docs
    
    async def verify(self, auth):
        return Path(auth["path"]).exists()
```

You drop that one file in `~/.pi/connectors/my_notes.py` and suddenly every agent can search your local markdown notes. **No core code changes.**
