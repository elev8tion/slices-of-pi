# Slice Of Pi

> Architectural contract layer for a new agentic framework.

**Slice Of Pi** provides clean, minimal abstract interfaces (ABCs, Protocols, dataclasses, TypeScript interfaces) that define the contracts for building agent orchestration systems. No implementation — just structure.

## What This Is

A set of 22 abstract interfaces organized across 4 architecture layers:

```
┌───────────────────────────────────────────────────────────┐
│               Plugin / Extension Layer                      │
│  UIPlugin  │  CLIPlugin  │  ChannelAdapter  │  GuardrailHook│
├───────────────────────────────────────────────────────────┤
│               Orchestration Layer                           │
│  AgentRuntime  │  WorkflowEngine  │  ScheduleEngine        │
│  EventBus  │  SkillProvider  │  TemplateEngine             │
├───────────────────────────────────────────────────────────┤
│               Execution Layer                               │
│  ExecutionEnvironment  │  AgentLifecycle                    │
│  CredentialProvider  │  AgentCapability                     │
├───────────────────────────────────────────────────────────┤
│               Specification Layer                           │
│  AgentManifest  │  SystemManifest  │  PlatformDeployment   │
└───────────────────────────────────────────────────────────┘
```

## Installation

```bash
pip install -e /Users/kc/slice-of-pi
```

## Quick Start

```python
from slice_of_pi.core import AgentLifecycle, AgentCapability, CredentialProvider
from slice_of_pi.orchestration import AgentRuntime, WorkflowEngine, EventBus
from slice_of_pi.specification import AgentManifest, SystemManifest

# All interfaces are abstract — implement them:
class MyRuntime(AgentRuntime):
    async def create(self, config): ...
    # ... implement remaining methods
```

## Package Structure

```
slice_of_pi/
├── __init__.py          # Package root
├── shared.py            # Shared types, dataclasses, enums
├── core/                # AgentLifecycle, AgentCapability, CredentialProvider
├── orchestration/       # AgentRuntime, WorkflowEngine, EventBus, SkillProvider, ChannelAdapter, CLIPlugin, AgentClient
├── execution/           # ExecutionEnvironment, GuardrailHook
├── specification/       # AgentManifest, SystemManifest
├── infra/               # TemplateEngine, ScheduleEngine, PlatformDeployment
├── testing/             # TestFixtureFactory, ScenarioRunner
└── interfaces/          # TypeScript interfaces (UIPlugin, DashboardWidget, ToolRegistry, MCPTransport)
```

## Interface Catalog

| # | Interface | Layer | Language | Purpose |
|---|-----------|-------|----------|---------|
| 1 | `AgentLifecycle` | Core | Python | Agent state machine (CREATED → RUNNING → STOPPED) |
| 2 | `AgentCapability` | Core | Python | Composable agent capabilities |
| 3 | `CredentialProvider` | Core | Python | OAuth/API key/PAT injection |
| 4 | `AgentRuntime` | Orchestration | Python | Abstract execution environment |
| 5 | `WorkflowEngine` | Orchestration | Python | Multi-step workflow execution |
| 6 | `EventBus` | Orchestration | Python | Real-time pub/sub |
| 7 | `SkillProvider` | Orchestration | Python | Skill injection and marketplace |
| 8 | `ChannelAdapter` | Orchestration | Python | External message channels |
| 9 | `CLIPlugin` | Orchestration | Python | CLI command extension |
| 10 | `AgentClient` | Orchestration | Python | Programmatic agent interaction |
| 11 | `ExecutionEnvironment` | Execution | Python | Sandboxed execution |
| 12 | `GuardrailHook` | Execution | Python | Pre/post-execution safety hooks |
| 13 | `AgentManifest` | Specification | Python | Single agent specification |
| 14 | `SystemManifest` | Specification | Python | Multi-agent system specification |
| 15 | `TemplateEngine` | Infrastructure | Python | Agent template instantiation |
| 16 | `ScheduleEngine` | Infrastructure | Python | Cron-based recurring execution |
| 17 | `PlatformDeployment` | Infrastructure | Python | Declarative platform deployment |
| 18 | `TestFixtureFactory` | Testing | Python | Deterministic test fixtures |
| 19 | `ScenarioRunner` | Testing | Python | End-to-end scenario testing |
| 20 | `UIPlugin` | Plugin | TypeScript | Dashboard extension system |
| 21 | `DashboardWidget` | Plugin | TypeScript | Pluggable dashboard widgets |
| 22 | `ToolRegistry` | Plugin | TypeScript | MCP tool registry |
| 23 | `MCPTransport` | Plugin | TypeScript | MCP protocol transport layer |
| 24 | `ToolDefinition` | Plugin | TypeScript | MCP tool definition |

## Architecture Decision Record

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full rationale:
- Why Protocols over ABCs where possible
- Why dataclasses for specification types
- Layer dependency rules
- TypeScript interface strategy

## License

MIT
