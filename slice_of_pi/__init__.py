"""
Slice Of Pi — Architectural Contract Layer

A clean, minimal set of abstract interfaces for building
agentic frameworks. Each sub-package defines the contracts
that implementations must satisfy.

Architecture Layers:
  core/           — AgentLifecycle, AgentCapability, CredentialProvider
  orchestration/  — AgentRuntime, WorkflowEngine, EventBus, SkillProvider, ChannelAdapter
  execution/      — ExecutionEnvironment, GuardrailHook
  specification/  — AgentManifest, SystemManifest
  infra/          — TemplateEngine, ScheduleEngine, PlatformDeployment
  testing/        — TestFixtureFactory, ScenarioRunner
  interfaces/     — TypeScript interfaces for frontend + MCP contracts
"""

__version__ = "0.1.0"
