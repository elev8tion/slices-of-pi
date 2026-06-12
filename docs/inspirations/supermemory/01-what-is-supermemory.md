# What is Supermemory — A Simple Breakdown

> Extracted from [github.com/supermemoryai/supermemory](https://github.com/supermemoryai/supermemory)
> Full toolchest at `~/supermemory-toolchest/`

## The Problem It Solves

Every time you talk to an AI (ChatGPT, Claude, etc.), **it forgets everything** once the conversation ends. You tell it your name, your preferences, what you're working on — and the next chat, it's a stranger again.

Supermemory **fixes that permanently**.

## How It Works

### 1. It listens and learns

When you talk to an AI, Supermemory picks out facts worth keeping:

- *"I'm a software engineer in Tokyo"* → **Static memory** (stable fact)
- *"I'm working on a React dashboard this week"* → **Dynamic memory** (current context)
- *"Here's a link to my design doc"* → **Document** (stored content)

### 2. It organizes what it knows

Memories are split into three buckets:

| Type | What it is | Example |
|------|-----------|---------|
| **Static** | Permanent facts | Name, job, long-term preferences |
| **Dynamic** | Recent context | Current projects, recent interests |
| **Searchable** | Document content | PDFs, web pages, notes you've saved |

### 3. It serves the right memory at the right time

When you start a new conversation, Supermemory automatically injects relevant context into the AI's system prompt — so the AI remembers who you are without you repeating yourself.

## Architecture (High Level)

```
You (chat) → AI Assistant
                  │
            ┌─────▼─────┐
            │  MCP Tool  │  ← "memory" & "recall" tools
            └─────┬─────┘
                  │
            ┌─────▼─────┐
            │SuperMemory │  ← The brain: stores, searches, profiles
            │   API      │
            └─────┬─────┘
                  │
     ┌────────────┼────────────┐
     │            │            │
  Google Drive  Notion    GitHub
  Gmail         OneDrive  (connectors auto-sync)
```

## Key Components

- **MCP Server** — The doorway. AI assistants talk to it using a standard protocol (Model Context Protocol). Has tools like `memory` (save/forget facts) and `recall` (search memories).
- **API Client** — The engine under the hood. Talks to Supermemory's cloud API to store, search, and retrieve memories.
- **SDK Integrations** — Plugins for different AI frameworks (OpenAI, Claude, Vercel AI SDK, etc.) so any AI can use it.

## What Makes It Special

- **#1 on all three major AI memory benchmarks** — Research-grade, not cobbled together
- **Handles contradictions** — If you change your mind, it updates gracefully
- **Auto-forgets** — Expired information cleans itself up
- **Connectors** — Syncs with Google Drive, Notion, GitHub, Gmail
- **50ms profile lookups** — Retrieving your context is nearly instant

## The Core Pattern: Profile + Search

The most important design pattern is the **dual model**:

```
Every request to Supermemory returns:
  1. A PROFILE  — stable facts + recent activity about the user
  2. SEARCH RESULTS — semantically relevant documents/memories for the current query

These get merged, deduplicated, and injected into the AI's system prompt.
```

This means **every conversation starts with context from all past conversations** — not blank.
