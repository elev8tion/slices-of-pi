# Maestro Execution Plan — Agent Profiles, Shared Knowledge, Slice Plays & Connectors

> This is a `/pi-multi-agent-maestro` execution plan. It defines exactly what to build,
> in what order, with verification gates at every step. No breaking changes.
> Every phase is additive-first and independently testable.

---

## Execution Strategy

**Pattern:** Agent Chain (`plan-build-review`)
**Team:** `planner` → `builder` → `reviewer`

| Role | Responsible for |
|------|----------------|
| **Planner** | Reads this plan, traces the codebase, confirms insertion points |
| **Builder** | Executes each phase in order, runs verification at every gate |
| **Reviewer** | Audits all changes, runs full test suite, signs off |

**Cardinal rule:** Every phase must pass its verification gate before the next phase starts.
If verification fails, the phase must be fixed before proceeding.

---

## Phase 0: Codebase Snapshot (Before Any Changes)

### Task
Take a snapshot of the current state so we can verify nothing broke.

```bash
# Run the existing test suite
cd /Users/kc/slice-of-pi
python3 -m pytest tests/ -v --tb=short 2>&1 | tail -30

# Check that the app starts
python3 -c "from pi_orchestrator.database import init_db; init_db(); print('DB OK')"

# Count agents, routes, tables for comparison
sqlite3 ~/.pi/agent/orchestrator.db ".tables"
grep -c 'def \|@router\|@app\.get\|@app\.post\|@app\.put\|@app\.delete' pi_orchestrator/routers/*.py
```

### Pass Criteria
- All existing tests pass
- DB initializes cleanly
- Counts recorded for comparison after changes

---

## Phase 1: Agent Profiles (2-3 hours)

**Doc reference:** `02-patterns-to-steal.md` (Pattern 1), `05-implementation-roadmap.md` (Session 1)

This is the highest-ROI change. Makes every agent session smarter trivially.

### Step 1.1 — Add `profile_json` column to agents table

**File:** `pi_orchestrator/database.py`

Add to SCHEMA string:
```sql
ALTER TABLE agents ADD COLUMN profile_json TEXT DEFAULT '{"static": {}, "dynamic": []}';
```

Also add these CRUD functions (append to the file):

```python
def get_agent_profile(agent_id: str) -> dict:
    """Get the profile JSON for an agent. Returns default if none set."""
    conn = _get_conn()
    row = conn.execute("SELECT profile_json FROM agents WHERE id = ?", (agent_id,)).fetchone()
    if not row or not row["profile_json"]:
        return {"static": {}, "dynamic": []}
    try:
        return json.loads(row["profile_json"])
    except (json.JSONDecodeError, TypeError):
        return {"static": {}, "dynamic": []}


def update_agent_profile(agent_id: str, profile: dict) -> None:
    """Replace the entire profile JSON for an agent."""
    conn = _get_conn()
    conn.execute(
        "UPDATE agents SET profile_json = ?, updated_at = ? WHERE id = ?",
        (json.dumps(profile), _now_iso(), agent_id)
    )
    conn.commit()


def append_agent_memory(agent_id: str, fact: str, fact_type: str = "dynamic") -> None:
    """Append a fact to an agent's dynamic memory.
    
    Deduplicates: if the fact already exists (static or dynamic), skip it.
    Caps dynamic array at 50 entries (oldest rotated out).
    """
    profile = get_agent_profile(agent_id)
    static = profile.get("static", {})
    dynamic = profile.get("dynamic", [])
    
    # Check for duplicates across both static and dynamic
    if fact_type == "static":
        static[fact.split(":")[0].strip()] = fact  # Use key: value format
    else:
        if fact in dynamic:
            return  # Already exists
        dynamic.append(fact)
        # Cap at 50 entries
        if len(dynamic) > 50:
            dynamic = dynamic[-50:]
    
    profile["static"] = static
    profile["dynamic"] = dynamic
    update_agent_profile(agent_id, profile)
```

**Verification gate (Step 1.1):**
```bash
cd /Users/kc/slice-of-pi
python3 -c "
from pi_orchestrator import database as db
db.init_db()
# Test profile CRUD
db.create_agent('test-profile-agent')
agents = db.list_agents()
test_agent = [a for a in agents if a['name'] == 'test-profile-agent'][0]
profile = db.get_agent_profile(test_agent['id'])
assert profile == {'static': {}, 'dynamic': []}, f'Expected empty profile, got {profile}'
db.append_agent_memory(test_agent['id'], 'Working on dashboard auth')
profile = db.get_agent_profile(test_agent['id'])
assert len(profile['dynamic']) == 1, f'Expected 1 dynamic fact, got {len(profile[\"dynamic\"])}'
db.append_agent_memory(test_agent['id'], 'Working on dashboard auth')  # Duplicate
profile = db.get_agent_profile(test_agent['id'])
assert len(profile['dynamic']) == 1, f'Expected 1 (deduped), got {len(profile[\"dynamic\"])}'
db.delete_agent(test_agent['id'])
print('✅ Step 1.1 passed')
"
```

### Step 1.2 — Create profile formatting service

**New file:** `pi_orchestrator/services/agent_profile_service.py`

```python
"""
Agent Profile Service — format agent profiles for system prompt injection.

Converts agent profiles into injectable system prompt context.
"""

from __future__ import annotations

from typing import Optional
from .. import database as db


def format_profile_as_prompt(agent_id: str) -> str:
    """Format an agent's profile as markdown for system prompt injection.
    
    Returns empty string if no profile data exists.
    """
    profile = db.get_agent_profile(agent_id)
    if not profile:
        return ""
    
    parts = []
    
    static = profile.get("static", {})
    if static:
        parts.append("## Agent Profile")
        for key, value in static.items():
            parts.append(f"- {key}: {value}")
    
    dynamic = profile.get("dynamic", [])
    if dynamic:
        parts.append("\n## Recent Context")
        # Only include last 5 entries for prompt injection
        for fact in dynamic[-5:]:
            parts.append(f"- {fact}")
    
    return "\n".join(parts) if parts else ""


def extract_session_summary(agent_id: str, prompt: str, session_id: str) -> str:
    """Create a summary fact from a completed session.
    
    Truncated to keep prompts clean.
    """
    truncated = prompt[:80].replace("\n", " ")
    return f"Session {session_id[:8]}: {truncated}..."
```

**Verification gate (Step 1.2):**
```bash
cd /Users/kc/slice-of-pi
python3 -c "
from pi_orchestrator import database as db
from pi_orchestrator.services.agent_profile_service import format_profile_as_prompt, extract_session_summary
db.init_db()
db.create_agent('test-profile-svc')
agents = db.list_agents()
aid = [a['profile-service' in a['name']] for a in agents]
# This is a basic import check
result = format_profile_as_prompt('nonexistent')
assert result == '', f'Expected empty for nonexistent agent, got {repr(result)}'
summary = extract_session_summary('test', 'Fix the authentication middleware', 'sess_abc123')
assert 'authentication' in summary, f'Expected summary to contain auth text'
print('✅ Step 1.2 passed')
"
```

### Step 1.3 — Inject profile at session start

**File:** `pi_orchestrator/services/pi_session_service.py`

Find the section that builds the pi command (around lines 98-108):

```python
# ── Build pi command ──────────────────────────────────────
cmd = [PI_BINARY, "--mode", "json", "--session", str(session_file)]
if agent.get("system_prompt"):
    cmd.extend(["--system-prompt", agent["system_prompt"]])
```

**Insert BEFORE the cmd building block** (after `db.record_activity(...)` around line 90,
before the `# ── Build pi command` comment at line ~96):

```python
    # ── Inject profile context into system prompt ───────────
    from .agent_profile_service import format_profile_as_prompt
    profile_context = format_profile_as_prompt(agent_id)
    if profile_context:
        existing_prompt = agent.get("system_prompt") or ""
        if existing_prompt:
            agent["system_prompt"] = existing_prompt + "\n\n" + profile_context
        else:
            agent["system_prompt"] = profile_context
        logger.info(f"Injected profile context ({len(profile_context)} chars) for agent {agent_id[:12]}")
```

### Step 1.4 — Append memory after session completion

**File:** `pi_orchestrator/services/pi_session_service.py`

Find the session finalization block (around lines 140-153):

```python
        # Finalize session
        db.update_session(...)
        db.update_agent_tokens(...)
        db.update_agent_status(...)
        db.record_activity(...)
```

**Insert AFTER `db.update_agent_status(agent_id, "idle")` and BEFORE `db.record_activity(...)`:**

```python
        # ── Store session memory ─────────────────────────────
        from .agent_profile_service import extract_session_summary
        session_note = extract_session_summary(agent_id, prompt, session_id)
        db.append_agent_memory(agent_id, session_note, fact_type="dynamic")
```

**Add import at top of file** (with other imports around line 13):
```python
from ..services.agent_profile_service import format_profile_as_prompt, extract_session_summary
```

(And remove the inline imports added in steps 1.3/1.4 — they were written inline for clarity, but for the final version, a top-level import is cleaner.)

**Verification gate (Step 1.3 + 1.4):**
```bash
cd /Users/kc/slice-of-pi
python3 -m pytest tests/ -v --tb=short -k "test_session or test_agent" 2>&1 | tail -20
# If no tests exist for this yet, the import alone is sufficient
python3 -c "
from pi_orchestrator.services.pi_session_service import stream_chat
import inspect
src = inspect.getsource(stream_chat)
assert 'format_profile_as_prompt' in src, 'Profile injection not found in stream_chat'
assert 'append_agent_memory' in src, 'Memory storage not found in stream_chat'
print('✅ Steps 1.3/1.4 passed — profile injection and memory capture integrated')
"
```

### Phase 1 Verification Gate (Complete)

```bash
cd /Users/kc/slice-of-pi
python3 -m pytest tests/ -v --tb=short 2>&1 | tail -30
# ALL tests must pass
```

---

## Phase 2: Richer SKILL.md Parsing + Schema Support (2 hours)

**Doc reference:** `03-slice-plays-deep-dive.md` (Gaps 1-2)

### Step 2.1 — Replace regex frontmatter parser with proper YAML

**File:** `pi_orchestrator/routers/skills.py`

Replace the entire `_parse_frontmatter()` function:

```python
import yaml

def _parse_frontmatter(path: Path) -> dict | None:
    """Extract YAML frontmatter from a SKILL.md file using real YAML parser.
    
    Returns full frontmatter dict including inputs, outputs, triggers, etc.
    """
    try:
        text = path.read_text()
        match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
        if not match:
            return None
        return yaml.safe_load(match.group(1))
    except Exception:
        return None
```

### Step 2.2 — Add SkillSchema and SkillParameter to models

**File:** `pi_orchestrator/models.py`

Add after the existing `SkillSummary` class:

```python
class SkillParameter(BaseModel):
    """A parameter for a slice play skill."""
    type: str = "string"
    required: bool = False
    default: Any = None
    description: str = ""


class SkillSchema(BaseModel):
    """Full skill schema including typed inputs/outputs."""
    name: str
    description: str = ""
    location: str = ""
    inputs: dict[str, SkillParameter] = Field(default_factory=dict)
    outputs: dict[str, SkillParameter] = Field(default_factory=dict)
    triggers: list[str] = Field(default_factory=list)
```

Add `from typing import Any` to the file's imports.

### Step 2.3 — Update the skills API to return full schema

**File:** `pi_orchestrator/routers/skills.py`

Update `_discover_skills()` to return richer data:

```python
def _discover_skills(base_dir: Path) -> list[dict]:
    """Walk a directory and discover all skills with full metadata."""
    skills = []
    if not base_dir.exists():
        return skills

    for entry in sorted(base_dir.iterdir()):
        if entry.is_dir():
            skill_md = entry / "SKILL.md"
            if skill_md.exists():
                meta = _parse_frontmatter(skill_md) or {}
                skills.append({
                    "name": meta.get("name", entry.name),
                    "description": meta.get("description", ""),
                    "location": str(entry),
                    "inputs": meta.get("inputs", {}),
                    "outputs": meta.get("outputs", {}),
                    "triggers": meta.get("triggers", meta.get("trigger", [])),
                })
        elif entry.suffix == ".md":
            meta = _parse_frontmatter(entry) or {}
            skills.append({
                "name": meta.get("name", entry.stem),
                "description": meta.get("description", ""),
                "location": str(entry),
                "inputs": meta.get("inputs", {}),
                "outputs": meta.get("outputs", {}),
                "triggers": meta.get("triggers", meta.get("trigger", [])),
            })
    return skills
```

### Phase 2 Verification Gate

```bash
cd /Users/kc/slice-of-pi
python3 -m pytest tests/ -v --tb=short 2>&1 | tail -30
# Add a quick integration check:
python3 -c "
from pi_orchestrator.routers.skills import _parse_frontmatter
from pathlib import Path
import tempfile
# Write a test SKILL.md with rich frontmatter
with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
    f.write('''---
name: test-skill
description: A test skill
inputs:
  file:
    type: string
    required: true
    description: Path to file
outputs:
  result:
    type: string
triggers:
  - /test-skill
---
Content here
''')
    result = _parse_frontmatter(Path(f.name))
    assert result, 'Frontmatter parsing returned None'
    assert result['name'] == 'test-skill'
    assert 'inputs' in result
    assert result['inputs']['file']['type'] == 'string'
    assert result['inputs']['file']['required'] == True
    assert 'triggers' in result
    print(f'✅ Rich frontmatter parsed: {result[\"name\"]} with {len(result[\"inputs\"])} inputs')
"
```

---

## Phase 3: Shared Knowledge Pool (3-4 hours)

**Doc reference:** `04-agent-coms-deep-dive.md` (the shared memory pattern)

### Step 3.1 — Create the shared memory service

**New file:** `pi_orchestrator/services/shared_memory_service.py`

```python
"""
Shared Knowledge Pool — cross-agent memory accumulation.

Cross-agent memory accumulation.
Agents don't message each other — they all read/write to a shared pool.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

SHARED_MEMORY_DIR = Path.home() / ".pi" / "agent" / "shared-memory"
MAX_DYNAMIC_FACTS = 200  # Total facts before rotation
FACT_TTL_DAYS = 30       # Auto-expire facts older than this


def _ensure_dir(tag: str) -> Path:
    """Ensure the directory for a tag exists."""
    path = SHARED_MEMORY_DIR / tag
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_fact(
    agent_id: str,
    tag: str,
    fact: str,
    fact_type: str = "dynamic",
    metadata: Optional[dict] = None,
) -> None:
    """Write a fact to the shared knowledge pool.
    
    Args:
        agent_id: The agent that learned this fact
        tag: Scope tag (e.g., 'frontend', 'infra')
        fact: The fact text
        fact_type: 'static' or 'dynamic'
        metadata: Optional metadata dict
    """
    _ensure_dir(tag)
    path = SHARED_MEMORY_DIR / tag / "knowledge.jsonl"
    
    entry = {
        "agent_id": agent_id,
        "tag": tag,
        "fact": fact,
        "type": fact_type,
        "metadata": metadata or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def deduplicate_facts(facts: list[dict]) -> list[dict]:
    """Deduplicate facts. Static wins over dynamic. Later wins over earlier.
    
    Priority: static > dynamic (within same priority, last wins).
    Deduplication ensures the same fact isn't injected twice.
    """
    seen = set()
    result = []
    
    # Sort: static first, then dynamic
    sorted_facts = sorted(facts, key=lambda f: (0 if f.get("type") == "static" else 1, f.get("timestamp", "")))
    
    for fact in sorted_facts:
        text = fact.get("fact", "").strip()
        if text and text not in seen:
            seen.add(text)
            result.append(fact)
    
    return result


def read_context(
    tags: list[str],
    max_age_hours: int = 72,
    max_facts: int = 20,
) -> str:
    """Read relevant facts for given tags, deduplicate, return as markdown.
    
    Args:
        tags: List of scope tags to read from
        max_age_hours: Maximum age of facts to include
        max_facts: Maximum number of facts to return
    
    Returns:
        Markdown string ready for prompt injection, or empty string.
    """
    cutoff = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
    all_facts = []
    
    for tag in tags:
        path = SHARED_MEMORY_DIR / tag / "knowledge.jsonl"
        if not path.exists():
            continue
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    ts = datetime.fromisoformat(entry.get("timestamp", "")).timestamp()
                    if ts < cutoff:
                        continue
                    all_facts.append(entry)
                except (json.JSONDecodeError, ValueError):
                    continue
    
    if not all_facts:
        return ""
    
    deduped = deduplicate_facts(all_facts)
    
    # Take only the most recent N
    recent = deduped[-max_facts:]
    
    parts = ["## Shared Workspace Knowledge"]
    for fact in recent:
        text = fact.get("fact", "")
        agent = fact.get("agent_id", "unknown")[:8]
        parts.append(f"- [{agent}] {text}")
    
    return "\n".join(parts)
```

### Step 3.2 — Inject shared context into sessions

**File:** `pi_orchestrator/services/pi_session_service.py`

In the same injection block added in Step 1.3, add shared context **after** the profile context:

```python
    # ── Inject profile context into system prompt ──────────────
    from .agent_profile_service import format_profile_as_prompt
    profile_context = format_profile_as_prompt(agent_id)
    
    # ── Inject shared context from knowledge pool ──────────────
    from .shared_memory_service import read_context
    agent_tags_raw = agent.get("tags")
    agent_tags = json.loads(agent_tags_raw) if isinstance(agent_tags_raw, str) else (agent_tags_raw or [])
    shared_context = read_context(agent_tags) if agent_tags else ""
    
    context_parts = []
    if profile_context:
        context_parts.append(profile_context)
    if shared_context:
        context_parts.append(shared_context)
    
    if context_parts:
        full_context = "\n\n".join(context_parts)
        existing_prompt = agent.get("system_prompt") or ""
        if existing_prompt:
            agent["system_prompt"] = existing_prompt + "\n\n" + full_context
        else:
            agent["system_prompt"] = full_context
        logger.info(f"Injected context ({len(full_context)} chars) for agent {agent_id[:12]}")
```

### Step 3.3 — Extend coms API to include shared context

**File:** `pi_orchestrator/routers/coms.py`

Add to the `_discover_peers()` function (after gathering basic peer info):

```python
    # Add recent facts from the shared knowledge pool for each peer
    try:
        from ..services.shared_memory_service import SHARED_MEMORY_DIR, read_context
        # Extract recent facts that this agent contributed
        peer_facts = []
        tag_path = SHARED_MEMORY_DIR / project_dir.name / "knowledge.jsonl"
        if tag_path.exists():
            with open(tag_path) as f:
                for line in f:
                    entry = json.loads(line)
                    if entry.get("agent_id", "").startswith(agent_file.stem) or entry.get("agent_name") == agent_file.stem:
                        peer_facts.append(entry.get("fact", ""))
                        if len(peer_facts) >= 5:
                            break
        
        peer_data["recent_facts"] = peer_facts
        peer_data["fact_count"] = len(peer_facts)
    except Exception:
        peer_data["recent_facts"] = []
        peer_data["fact_count"] = 0
```

### Phase 3 Verification Gate

```bash
cd /Users/kc/slice-of-pi
python3 -m pytest tests/ -v --tb=short 2>&1 | tail -30

python3 -c "
# Test the shared memory service end-to-end
from pi_orchestrator.services.shared_memory_service import write_fact, read_context, deduplicate_facts
import tempfile, shutil, os
# Use a temp dir for testing
from pi_orchestrator.services.shared_memory_service import SHARED_MEMORY_DIR
original_dir = SHARED_MEMORY_DIR
import pathlib
# Write some test facts
write_fact('agent-a', 'test-tag', 'Database has users table', 'static')
write_fact('agent-b', 'test-tag', 'Working on auth middleware', 'dynamic')
write_fact('agent-c', 'test-tag', 'Database has users table', 'dynamic')  # Duplicate of static
# Read context
context = read_context(['test-tag'], max_age_hours=9999)
assert 'Users table' in context, 'Expected static fact in context'
assert 'auth middleware' in context, 'Expected dynamic fact in context'
# Dedup should have kept only one 'users table' entry
users_count = context.count('users table') + context.count('Users table')
assert users_count == 1, f'Expected dedup to 1, got {users_count}'
print(f'✅ Shared knowledge pool working. Context length: {len(context)} chars')
"
```

---

## Phase 4: Connectors Plugin System (4-5 hours)

**Doc reference:** `06-connectors-pattern.md`

### Step 4.1 — Create connector plugin base class

**New file:** `pi_orchestrator/services/connectors/__init__.py`

```python
"""Connectors package — external data sync plugins for Slice of Pi."""
```

**New file:** `pi_orchestrator/services/connectors/_base.py`

```python
"""
ConnectorPlugin — abstract base class for external data connectors.

Each connector syncs data from an external source into the shared
knowledge pool. Connectors are self-contained plugins: anyone can
add one by dropping a .py file in ~/.pi/connectors/.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class ConnectorPlugin(ABC):
    """Abstract connector for external data sources."""

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
    async def sync(self, auth: dict, since: Optional[str] = None) -> list[dict]:
        """Fetch new/changed content since last sync.
        
        Returns list of documents:
          [{"id": str, "title": str, "content": str, "url": str, 
            "type": str, "updated_at": str}, ...]
        """
        ...

    @abstractmethod
    async def verify(self, auth: dict) -> bool:
        """Check if the connector's auth is still valid."""
        ...

    def get_schedule(self) -> str | None:
        """Cron expression for auto-sync. None = manual only."""
        return None
```

### Step 4.2 — Create connector registry

**New file:** `pi_orchestrator/services/connectors/registry.py`

```python
"""
Connector Registry — discover built-in and user-installed connectors.

Scans:
  1. pi_orchestrator.services.connectors.builtins — built-in connectors
  2. ~/.pi/connectors/ — user-installed connector plugins
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Optional

from ._base import ConnectorPlugin

CONNECTORS_DIR = Path.home() / ".pi" / "connectors"

# Module-level cache populated on first call
_registry: dict[str, ConnectorPlugin] = {}


def discover_plugins() -> dict[str, ConnectorPlugin]:
    """Scan builtins and ~/.pi/connectors/ for all ConnectorPlugin classes."""
    plugins = {}
    
    # 1. Load builtins
    try:
        from .builtins.webhook import WebhookConnector
        for cls in [WebhookConnector]:
            inst = cls()
            plugins[inst.provider] = inst
    except ImportError:
        pass  # Builtins may not exist yet
    
    # 2. Load user plugins from ~/.pi/connectors/
    if CONNECTORS_DIR.exists():
        for file in sorted(CONNECTORS_DIR.glob("*.py")):
            try:
                spec = importlib.util.spec_from_file_location(file.stem, file)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    for attr_name in dir(mod):
                        attr = getattr(mod, attr_name)
                        if isinstance(attr, type) and issubclass(attr, ConnectorPlugin) and attr is not ConnectorPlugin:
                            inst = attr()
                            plugins[inst.provider] = inst
            except Exception as e:
                print(f"Failed to load connector plugin {file.name}: {e}")
    
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


def reload() -> None:
    """Force rediscovery of all plugins. Call after installing a new plugin."""
    _registry.clear()
    _registry.update(discover_plugins())
```

### Step 4.3 — Create the webhook built-in connector

**New directory:** `pi_orchestrator/services/connectors/builtins/`

**New file:** `pi_orchestrator/services/connectors/builtins/__init__.py`

```python
"""Built-in connector plugins shipped with Slice of Pi."""
```

**New file:** `pi_orchestrator/services/connectors/builtins/webhook.py`

```python
"""
Generic Incoming Webhook Connector — easiest custom connector.

Anyone can POST data to an endpoint and it becomes agent knowledge.
No OAuth, no polling — just a URL and a payload.
"""

from __future__ import annotations

from typing import Optional
from .._base import ConnectorPlugin


class WebhookConnector(ConnectorPlugin):
    """Generic incoming webhook connector.
    
    Configure with a secret token. POST JSON to /api/connectors/webhook/{token}.
    The JSON body becomes a knowledge fact.
    """
    
    @property
    def provider(self) -> str:
        return "webhook"
    
    @property
    def display_name(self) -> str:
        return "Incoming Webhook"
    
    async def authorize(self, config: dict) -> dict:
        token = config.get("token", "")
        if len(token) < 8:
            raise ValueError("Webhook token must be at least 8 characters")
        return {"token": token}
    
    async def sync(self, auth: dict, since: Optional[str] = None) -> list[dict]:
        # Webhooks are push-based, not poll-based
        return []
    
    async def verify(self, auth: dict) -> bool:
        return bool(auth.get("token"))
```

### Step 4.4 — Add connectors and connector_sync_log tables

**File:** `pi_orchestrator/database.py`

Add to the SCHEMA string (append before the `-- Indexes` section):

```sql
CREATE TABLE IF NOT EXISTS connectors (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    label TEXT NOT NULL,
    auth_state TEXT NOT NULL,
    container_tags TEXT NOT NULL DEFAULT '[]',
    enabled INTEGER NOT NULL DEFAULT 1,
    last_sync_at TEXT,
    last_sync_status TEXT,
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS connector_sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    connector_id TEXT NOT NULL REFERENCES connectors(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'running',
    items_found INTEGER DEFAULT 0,
    items_imported INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT
);
```

Add CRUD functions:

```python
def list_connectors(enabled_only: bool = False) -> list[dict]:
    conn = _get_conn()
    if enabled_only:
        rows = conn.execute("SELECT * FROM connectors WHERE enabled = 1 ORDER BY created_at DESC").fetchall()
    else:
        rows = conn.execute("SELECT * FROM connectors ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def get_connector(connector_id: str) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM connectors WHERE id = ?", (connector_id,)).fetchone()
    return dict(row) if row else None


def create_connector(
    agent_id: str, provider: str, label: str,
    auth_state: dict, container_tags: list[str] | None = None,
) -> dict:
    conn = _get_conn()
    connector_id = _new_id()
    now = _now_iso()
    conn.execute(
        """INSERT INTO connectors (id, agent_id, provider, label, auth_state,
           container_tags, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (connector_id, agent_id, provider, label, json.dumps(auth_state),
         json.dumps(container_tags or []), now, now)
    )
    conn.commit()
    return get_connector(connector_id)
```

### Step 4.5 — Create connectors API router

**New file:** `pi_orchestrator/routers/connectors.py`

```python
"""
Connectors Router — manage external data connectors for agents.

Provides CRUD for connector configurations + sync trigger endpoint.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from .. import database as db
from ..services.connectors.registry import get as get_connector_plugin, list_available

router = APIRouter(prefix="/api/connectors", tags=["connectors"])


@router.get("/available")
async def available_connectors():
    """List all available connector plugins (installed + built-in)."""
    return {"connectors": list_available()}


@router.get("")
async def list_connectors(agent_id: str | None = None):
    """List all configured connectors, optionally filtered by agent."""
    connectors = db.list_connectors()
    # Mask auth state
    for c in connectors:
        c["auth_state"] = "••••••••"
    return {"connectors": connectors}


@router.post("", status_code=201)
async def create_connector(body: dict):
    """Create a new connector configuration."""
    errors = []
    for field in ["agent_id", "provider", "label", "auth_state"]:
        if field not in body:
            errors.append(f"{field} is required")
    if errors:
        raise HTTPException(status_code=400, detail=", ".join(errors))
    
    # Validate provider exists
    plugin = get_connector_plugin(body["provider"])
    if not plugin:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {body['provider']}")
    
    # Validate auth
    try:
        auth_state = await plugin.authorize(body["auth_state"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    connector = db.create_connector(
        agent_id=body["agent_id"],
        provider=body["provider"],
        label=body.get("label", body["provider"]),
        auth_state=auth_state,
        container_tags=body.get("container_tags"),
    )
    connector["auth_state"] = "••••••••"
    return connector


@router.delete("/{connector_id}")
async def delete_connector(connector_id: str):
    """Delete a connector configuration."""
    deleted = db.delete_connector(connector_id)  # Add this to database.py
    if not deleted:
        raise HTTPException(status_code=404, detail="Connector not found")
    return {"status": "deleted"}
```

### Step 4.6 — Register the connectors router

**File:** `pi_orchestrator/main.py`

Add import:
```python
from .routers.connectors import router as connectors_router
```

And include:
```python
app.include_router(connectors_router)
```

Place it near the other router registrations (alphabetical — between `coms_router` and `console_router`).

### Phase 4 Verification Gate

```bash
cd /Users/kc/slice-of-pi
python3 -m pytest tests/ -v --tb=short 2>&1 | tail -30

python3 -c "
# Test connector plugin discovery
from pi_orchestrator.services.connectors.registry import list_available, get
available = list_available()
print(f'Available connector plugins: {len(available)}')
for name, info in available.items():
    print(f'  - {name}: {info[\"display_name\"]}')

# Test DB operations
from pi_orchestrator import database as db
db.init_db()
connectors = db.list_connectors()
print(f'Connectors in DB: {len(connectors)}')

# Test the webhook connector
webhook = get('webhook')
assert webhook is not None, 'Webhook connector not found'
assert webhook.provider == 'webhook'
print('✅ Phase 4 passed')
"
```

---

## Phase 5: Verify Everything (1 hour)

### Step 5.1 — Run full test suite

```bash
cd /Users/kc/slice-of-pi
python3 -m pytest tests/ -v --tb=short 2>&1
```

### Step 5.2 — Verify app starts and serves

```bash
cd /Users/kc/slice-of-pi

# Test that the app module loads cleanly
python3 -c "
from pi_orchestrator.main import app
# Verify all routers are registered
routes = [r.path for r in app.routes]
assert '/api/agents' in str(routes), 'Agents router missing'
assert '/api/skills' in str(routes), 'Skills router missing'
assert '/api/coms' in str(routes), 'Coms router missing'
assert '/api/connectors' in str(routes), 'Connectors router missing'
assert '/health' in str(routes), 'Health endpoint missing'
print(f'✅ App loaded with {len(app.routes)} routes')
"

# Quick DB smoke test
python3 -c "
from pi_orchestrator import database as db
db.init_db()
db.create_agent('verify-agent')
agents = db.list_agents()
assert len(agents) >= 1
profile = db.get_agent_profile(agents[0]['id'])
assert profile == {'static': {}, 'dynamic': []}, 'Profile column works'
print('✅ DB smoke test passed')
"
```

### Step 5.3 — Verify no SQLite schema breakage

```bash
cd /Users/kc/slice-of-pi
python3 -c "
from pi_orchestrator.database import _get_conn
conn = _get_conn()
# Verify all expected tables exist
tables = [r['name'] for r in conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()]
expected = ['agents', 'sessions', 'activities', 'schedules', 'settings', 
            'mcp_keys', 'users', 'tags', 'agent_tags', 'credentials', 
            'audit_log', 'operator_queue', 'agent_shares', 'access_requests',
            'connectors', 'connector_sync_log']
for t in expected:
    assert t in tables, f'Missing table: {t}'
# Verify the profile_json column exists on agents
cols = [r['name'] for r in conn.execute('PRAGMA table_info(agents)').fetchall()]
assert 'profile_json' in cols, 'Missing profile_json column'
print(f'✅ All {len(expected)} tables present including 2 new connector tables')
print(f'✅ profile_json column on agents table')
"
```

---

## Rollback Plan

If any verification gate fails, here's how to roll back each phase cleanly:

| Phase | Rollback |
|-------|----------|
| **Phase 1** | Remove `profile_json` column: not needed — it's a nullable column with a default. Remove the `append_agent_memory` and `format_profile_as_prompt` injections from `pi_session_service.py`. Delete `agent_profile_service.py`. |
| **Phase 2** | The regex→yaml change is backward-compatible (richer output). If yaml isn't installed, import error: add `PyYAML` to dependencies, or wrap import. Rollback: revert `skills.py` to regex parser, revert `models.py`. |
| **Phase 3** | Remove `shared_memory_service.py`. Revert `pi_session_service.py` injection. Revert `coms.py` extension. No DB changes — shared memory is file-based. |
| **Phase 4** | Remove `services/connectors/` directory. Remove `routers/connectors.py`. Revert `database.py` (remove tables + functions). Revert `main.py` router registration. |

---

## Summary: Files Created vs Modified

### New Files (9)

| File | Phase |
|------|-------|
| `pi_orchestrator/services/agent_profile_service.py` | 1 |
| `pi_orchestrator/services/shared_memory_service.py` | 3 |
| `pi_orchestrator/services/connectors/__init__.py` | 4 |
| `pi_orchestrator/services/connectors/_base.py` | 4 |
| `pi_orchestrator/services/connectors/registry.py` | 4 |
| `pi_orchestrator/services/connectors/builtins/__init__.py` | 4 |
| `pi_orchestrator/services/connectors/builtins/webhook.py` | 4 |
| `pi_orchestrator/routers/connectors.py` | 4 |

### Modified Files (6)

| File | What Changed | Phase |
|------|-------------|-------|
| `pi_orchestrator/database.py` | +profile_json column + CRUD, +connectors tables + CRUD | 1, 4 |
| `pi_orchestrator/models.py` | +SkillParameter, +SkillSchema models | 2 |
| `pi_orchestrator/routers/skills.py` | yaml parser + richer response | 2 |
| `pi_orchestrator/services/pi_session_service.py` | Profile injection + shared context injection + memory capture | 1, 3 |
| `pi_orchestrator/routers/coms.py` | Peer facts + fact_count in response | 3 |
| `pi_orchestrator/main.py` | Register connectors router | 4 |

### No Change Files

The following were identified as touchpoints in the inspiration docs but are NOT modified in this plan (they'd be future UI work or require a separate frontend-focused phase):

- `dashboard/src/components/SlicePlaysPanel.vue` — UI work (parameter forms, pipeline builder)
- `dashboard/src/components/ComsPanel.vue` — UI work (show facts)
- `dashboard/src/components/AgentDetail.vue` — Add Connectors tab
- `dashboard/src/views/Settings.vue` — Add Connectors section
- `pi_orchestrator/services/schedule_service.py` — Connector auto-sync scheduling (future)
