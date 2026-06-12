# Supermemory Patterns to Steal for Slice of Pi

> Cross-project pattern analysis
> Slice of Pi = web dashboard for managing pi coding agents
> Supermemory = persistent memory layer for AI assistants

## What Slice of Pi Already Has

| Feature | Status |
|---------|--------|
| Agent CRUD (name, persona, model, tools, skills) | ✅ Done |
| Session chat with streaming | ✅ Done |
| Agent tags for organization | ✅ Done |
| Schedules (cron-based execution) | ✅ Done |
| Credentials (encrypted API keys) | ✅ Done |
| Audit log | ✅ Done |
| Teams (group agents from YAML) | ✅ Done |
| Skill listing from SKILL.md files | ✅ Done |
| Peer discovery (coms registry) | ✅ Done |
| Abstract interfaces (WorkflowEngine, ChannelAdapter) | ⚠️ Defined but not implemented |

## What Supermemory Has That Slice of Pi Doesn't

### Pattern 1: Static + Dynamic Agent Profiles

**Supermemory:** Every user has a **profile** with two layers:
- **Static** — stable facts that rarely change (name, job, long-term preferences)
- **Dynamic** — recent context (current projects, recent interests)

**Slice of Pi application:** Every agent could have a **living profile** that accumulates knowledge across sessions:

```python
# ~/.pi/agent/profiles/{agent_id}/profile.json
{
  "static": {
    "persona": "code-reviewer",
    "tools": ["read", "bash", "web_search"],
    "model": "claude-sonnet-4",
    "strengths": ["TypeScript", "Python", "Rust"],
    "limitations": ["No direct DB access"]
  },
  "dynamic": [
    "Session #42: reviewed PR #84 (auth middleware)",
    "Session #43: reviewed PR #87 (SQLite migration)",
    "Session #44: caught null pointer in user service"
  ]
}
```

Instead of an agent starting each session from scratch, inject this into the system prompt:

```
## Agent Profile (Static)
- Purpose: Code review specialist
- Strengths: TypeScript, Python, Rust
- Known limitations: No direct DB access

## Recent Context
- Previously reviewed: PR #84 (auth middleware), PR #87 (SQLite migration)
- Ongoing pattern: catching null pointer issues in user service layer
```

### Pattern 2: Cross-Session Memory (The Big One)

**Supermemory's killer feature:** Facts survive conversations. You tell it something once, it's there next time.

**Slice of Pi application:** Today, each pi agent session is a blank slate. Supermemory patterns suggest:

```
Agent session starts
      │
  ┌───▼───────────────────────────────────────────────┐
  │  "memory" tool — "Remember: user prefers          │
  │  verbose TypeScript with explicit error handling"  │
  └───────────────────────────────────────────────────┘
      │
  ┌───▼───────────────────────────────────────────────┐
  │  Stored in agent's profile JSON                   │
  │  ~/.pi/agent/profiles/{agent_id}/memories.json    │
  └───────────────────────────────────────────────────┘
      │
  ┌───▼───────────────────────────────────────────────┐
  │  Next session injected into system prompt:        │
  │  "Known preferences for this user: ..."           │
  └───────────────────────────────────────────────────┘
```

This is a **tiny JSON file per agent** — no infrastructure needed.

### Pattern 3: Tag-Based Memory Scoping (Container Tags)

**Supermemory:** Projects are identified by `containerTag` — a simple string that scopes all operations.

**Slice of Pi application:** Agents already have **tags** (a set of strings). Tags could double as memory scopes:

| Tag | Meaning | Memory Scope |
|-----|---------|-------------|
| `default` | Catch-all | Shared knowledge |
| `frontend` | Frontend work | React/Vue patterns |
| `infra` | Infrastructure | K8s/Docker knowledge |

An agent tagged `frontend` would only see frontend-relevant memories when injected.

### Pattern 4: Profile-as-Prompt Injection

**Supermemory:** Fetches the profile, converts it to markdown, injects into the system prompt via a `context` prompt template. The prompt template is **customizable**.

**Slice of Pi application:** The agent system prompt (`system_prompt` field in `PiAgentConfig`) could automatically include a `{profile}` token that gets replaced at session start:

```
Current system prompt:
  "You are a helpful coding assistant..."

With profile injection:
  "You are a helpful coding assistant...
   
   [Profile automatically injected here]
   
   Known facts about this workspace:
   - Preferred language: Python
   - Current project: slice-of-pi dashboard"
```

This requires **no new infrastructure** — just a format string template expansion when spawning the pi subprocess.

### Pattern 5: The Deduplication Strategy

**Supermemory:** When building the profile for prompt injection, it **deduplicates** across static, dynamic, and search results — static wins, then dynamic, then search. Prevents redundant context.

**Slice of Pi application:** If an agent runs 5 sessions in a day, you'd see 5 identical "I'm working on the dashboard" entries. Deduplication collapses them:

```python
def deduplicate_memories(static, dynamic, search_results):
    """Superpriority: static > dynamic > search_results."""
    seen = set(static)
    deduped_dynamic = [m for m in dynamic if m not in seen and not seen.add(m)]
    deduped_search = [m for m in search_results if m not in seen and not seen.add(m)]
    return static, deduped_dynamic, deduped_search
```

Simple set logic. No dependencies.

### Summary: Effort Matrix

| Pattern | Supermemory | Slice of Pi | Effort | File Changes |
|---------|-------------|-------------|--------|-------------|
| **Static + Dynamic profiles** | ✅ Core feature | ❌ Missing | Low | Add `profile_json` column to agents table + inject at session start |
| **Cross-session memory** | ✅ Core feature | ❌ Missing | Medium | Profile JSON read/write + memory accumulation logic |
| **Tag-based scoping** | ✅ Container tags | ⚠️ Already has tags | Low | Use existing tags as memory scope keys |
| **Profile-in-prompt** | ✅ Prompt template | ⚠️ system_prompt exists | Low | Format string expansion in `pi_session_service.py` |
| **Deduplication** | ✅ Built-in | ❌ Missing | Low | One utility function (~10 lines) |
