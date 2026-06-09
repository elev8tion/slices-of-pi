# Slice Of Pi — Architecture

## Decision: Extracted Interface Contract Layer

**Date**: 2026-06-09
**Status**: Proposed

**Context**: The trinity-toolchest contains a fully implemented agent orchestration platform with ~1,500 source files across 12 modules. The STUBS.md master index defines 22+ abstract interfaces that form the architectural contract. We need to extract these interfaces into a standalone, minimal package so the new "Slice Of Pi" framework can be built against a clean contract — not against a specific implementation.

**Decision**: Extract every interface as either a Python Protocol/ABC or a TypeScript `interface`, organized into mirroring layers. No implementation logic.

**Consequences**:
- *Positive*: Clean dependency — implementations depend on interfaces, not on each other
- *Positive*: Framework-agnostic — can swap Docker for K8s, SQLite for Postgres without changing consumers
- *Positive*: Testable — mock implementations satisfy the same contracts
- *Negative*: Maintaining interface parity with implementations requires discipline
- *Negative*: Protocol/ABC split creates two patterns to learn


## Layer Architecture

### Layer Dependency Rules

```
specification  ──►  (leaf — depends on nothing)
    │
    ▼
core  ──►  shared
    │
    ▼
execution  ──►  shared
    │
    ▼
orchestration  ──►  shared, core
    │
    ▼
infra  ──►  shared, specification
    │
    ▼
testing  ──►  shared
```

- `shared`: Zero-dependency dataclasses and enums — the leaf types every interface uses
- `core`: Agent lifecycle contracts — depends on `shared`
- `execution`: Sandbox and guardrail contracts — depends on `shared`
- `orchestration`: Runtime, workflow, event, skill, channel contracts — depends on `shared` and `core`
- `specification`: Manifest dataclasses — depends on `shared` (pure data, no behavior interfaces)
- `infra`: Template, schedule, deployment contracts — depends on `shared` and `specification`
- `testing`: Fixture and scenario contracts — depends on `shared`

### TypeScript Layer

```
interfaces/
├── frontend.ts  — UIPlugin, DashboardWidget, AgentAction, MCPTransport, ToolRegistry
└── index.ts     — Re-exports
```

TypeScript interfaces are self-contained (no Python dependency). They define the contracts for the Vue.js frontend and MCP server. These live alongside the Python package for discoverability but are consumed separately by the frontend build.


## Interface Design Rationale

### Protocol vs ABC

| Use Case | Pattern | Reason |
|----------|---------|--------|
| AgentLifecycle | Protocol (`@runtime_checkable`) | Duck-typing: any object with right methods IS an agent |
| AgentCapability | ABC | Explicit inheritance, shared `validate()` default |
| AgentRuntime | ABC | Shared default hook methods (`pre_create`, `post_destroy`) |
| ExecutionEnvironment | ABC | Shared default methods (`rollback`, `list_all`) |
| GuardrailHook | ABC | Shared default `on_network` hook |
| TemplateEngine | ABC | Shared optional `register`/`unregister` |
| ScheduleEngine | ABC | Shared `start`/`stop`/`stats` lifecycle |

**Rule**: Use Protocol when the contract is purely structural (method signatures only). Use ABC when there are default method implementations to share.

### Dataclass vs Class

Specification types (`AgentManifest`, `SystemManifest`, `PlatformDeployment`) are dataclasses, not ABCs/Protocols. They are **data contracts**, not behavior contracts. They carry configuration, not logic. This distinction keeps the specification layer dependency-free and serializable.

### TypeScript Interfaces

TypeScript interfaces mirror the Python contracts for the frontend and MCP server. They use `export interface` rather than abstract classes because TypeScript interfaces are structural (like Python Protocols), fully erasable at compile time, and produce zero runtime overhead.


## Interface Catalog (Complete)

### Core Abstractions (3 interfaces)

| # | Interface | Module | Purpose |
|---|-----------|--------|---------|
| 1 | `AgentLifecycle` | `slice_of_pi.core` | Agent state machine: CREATED → CONFIGURING → RUNNING → (STOPPED/ERROR). Defines `provision`, `start`, `stop`, `restart`, `destroy`, `health_check`. |
| 2 | `AgentCapability` | `slice_of_pi.core` | Composable capability unit. Defines `name`, `requires`, `install`, `uninstall`, `validate`. |
| 3 | `CredentialProvider` | `slice_of_pi.core` | Credential injection. Defines `inject`, `revoke`, `rotate`, `list_available`. Supports OAuth2, API keys, PATs. |

### Orchestration (7 interfaces)

| # | Interface | Module | Purpose |
|---|-----------|--------|---------|
| 4 | `AgentRuntime` | `slice_of_pi.orchestration` | Abstract execution environment. Defines `create`, `destroy`, `execute` (streaming), `status`, `list_all`, `inject_file`, `read_file`. |
| 5 | `WorkflowEngine` | `slice_of_pi.orchestration` | Multi-step workflow execution. Defines `deploy`, `execute` (streaming), `status`, `cancel`. Supports sequential, parallel, fan-out, conditional steps. |
| 6 | `EventBus` | `slice_of_pi.orchestration` | Pub/sub event system. Defines `publish`, `subscribe`, `unsubscribe`, `start`, `stop`, `stats`. |
| 7 | `SkillProvider` | `slice_of_pi.orchestration` | Skill injection. Defines `list_available`, `install`, `uninstall`, `get_marketplace`, `search`, `get_skill`. |
| 8 | `ChannelAdapter` | `slice_of_pi.orchestration` | Message channel adapter. Defines `channel_type`, `connect`, `disconnect`, `send_message`, `on_message`, `send_file`, `typing_indicator`. |
| 9 | `CLIPlugin` | `slice_of_pi.orchestration` | CLI command extension. Defines `name`, `register_commands`, `connect`. |
| 10 | `AgentClient` | `slice_of_pi.orchestration` | Programmatic agent interaction. Defines `deploy`, `chat`, `list_agents`, `get_logs`, `exec_command`, `stop_agent`, `destroy_agent`. |

### Execution (2 interfaces)

| # | Interface | Module | Purpose |
|---|-----------|--------|---------|
| 11 | `ExecutionEnvironment` | `slice_of_pi.execution` | Sandboxed execution. Defines `create_sandbox`, `exec_command`, `stream_logs`, `snapshot`, `destroy_sandbox`, `rollback`, `list_all`. |
| 12 | `GuardrailHook` | `slice_of_pi.execution` | Safety inspection. Defines `hook_name`, `pre_exec`, `post_exec`, `on_file_access`, `on_command`, `on_network`. |

### Specification (2 interfaces)

| # | Interface | Module | Purpose |
|---|-----------|--------|---------|
| 13 | `AgentManifest` | `slice_of_pi.specification` | Single agent spec. Dataclass with `name`, `version`, `runtime`, `image`, `resources`, `tools`, `skills`, `mcp_servers`, `channels`, `credentials`, `git`, `schedules`, `guardrails`, `system_prompt`. |
| 14 | `SystemManifest` | `slice_of_pi.specification` | Multi-agent system spec. Dataclass with `name`, `agents` (dict of SystemAgentConfig), `permissions`, `workflows`, `shared`, `topology`. |

### Infrastructure (3 interfaces)

| # | Interface | Module | Purpose |
|---|-----------|--------|---------|
| 15 | `TemplateEngine` | `slice_of_pi.infra` | Template instantiation. Defines `list_templates`, `get_template`, `instantiate`, `validate`, `register`, `unregister`. |
| 16 | `ScheduleEngine` | `slice_of_pi.infra` | Cron-based scheduling. Defines `register`, `run_once`, `cancel`, `list_schedules`, `get_next_run`, `start`, `stop`, `stats`. |
| 17 | `PlatformDeployment` | `slice_of_pi.infra` | Platform deploy manifest. Dataclass with `platform`, `providers`, `services`, `agents`, `networking`. |

### Testing (2 interfaces)

| # | Interface | Module | Purpose |
|---|-----------|--------|---------|
| 18 | `TestFixtureFactory` | `slice_of_pi.testing` | Test fixtures. Defines `create_test_agent`, `create_test_system`, `create_test_credential`, `create_test_schedule`, `cleanup`. |
| 19 | `ScenarioRunner` | `slice_of_pi.testing` | E2E scenarios. Defines `run`. Consumes `Scenario`, `ScenarioStep`, `ScenarioResult` from `shared`. |

### Plugin Layer — TypeScript (5 interfaces)

| # | Interface | Module | Purpose |
|---|-----------|--------|---------|
| 20 | `UIPlugin` | `slice_of_pi/interfaces/frontend.ts` | Dashboard extension. Defines `registerRoutes`, `registerSettingsTabs`, `registerWidgets`, `registerAgentActions`, `init`. |
| 21 | `DashboardWidget` | `slice_of_pi/interfaces/frontend.ts` | Pluggable widget. Properties: `id`, `title`, `component`, `defaultSize`, `minSize`, `refreshInterval`. |
| 22 | `ToolDefinition` | `slice_of_pi/interfaces/frontend.ts` | MCP tool spec. Properties: `name`, `description`, `inputSchema`, `handler`. |
| 23 | `ToolRegistry` | `slice_of_pi/interfaces/frontend.ts` | Tool management. Defines `register`, `unregister`, `list`, `execute`, `search`, `get`. |
| 24 | `MCPTransport` | `slice_of_pi/interfaces/frontend.ts` | Protocol transport. Defines `start`, `onRequest`, `notify`, `stop`, `metadata`. |


## Shared Types

The `shared.py` module provides the leaf-level data types used across all interfaces:

| Type | Kind | Used By |
|------|------|---------|
| `ResourceLimits` | dataclass | AgentManifest, ExecutionEnvironment, PlatformDeployment |
| `Mount` | dataclass | ExecutionEnvironment, SharedResources |
| `NetworkPolicy` | dataclass | ExecutionEnvironment |
| `SandboxHandle` | dataclass | ExecutionEnvironment, AgentRuntime |
| `ExecResult` | dataclass | ExecutionEnvironment |
| `GuardrailDecision` | dataclass | GuardrailHook |
| `AgentStatus` | Enum | AgentLifecycle |
| `CredentialType` | Enum | CredentialProvider |
| `CredentialRef` | dataclass | AgentManifest |
| `Skill` | dataclass | SkillProvider |
| `ScheduleDef` | dataclass | ScheduleEngine, AgentManifest |
| `ChannelConfig` | dataclass | AgentManifest |
| `MCPConfig` | dataclass | AgentManifest |
| `ToolResult` | dataclass | ToolRegistry (TS equivalent) |
| `GitConfig` | dataclass | AgentManifest |
| `StepType` | Enum | WorkflowEngine |
| `WorkflowDef` | dataclass | WorkflowEngine, SystemManifest |
| `WorkflowStepResult` | dataclass | WorkflowEngine |
| `ValidationResult` | dataclass | TemplateEngine |
| `Template` | dataclass | TemplateEngine |
| `TopologyConfig` | dataclass | SystemManifest |
| `SharedResources` | dataclass | SystemManifest |
| `Scenario` | dataclass | ScenarioRunner |
| `ScenarioStep` | dataclass | ScenarioRunner |
| `ScenarioResult` | dataclass | ScenarioRunner |


## Design Principles

1. **Interfaces over implementations** — Every consumer depends on an ABC or Protocol, never a concrete class
2. **Shared types are leaf nodes** — `shared.py` depends on nothing; everything depends on it
3. **Protocols for structural typing** — Any object with the right methods IS an agent lifecycle
4. **ABCs for shared defaults** — When interfaces share utility methods, use ABCs
5. **Dataclasses for data** — Specification types carry config, not behavior
6. **TypeScript mirrors Python** — Same contracts, different language, same semantics
7. **No framework coupling** — Interfaces don't know about FastAPI, Docker, Vue, or React
