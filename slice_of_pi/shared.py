"""
Shared types, dataclasses, and enums used across all interface layers.

These are the "leaf-level" data types that interface methods accept and return.
They carry no implementation — just structure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


# ===========================================================================
# Resource & Infrastructure Types
# ===========================================================================


@dataclass
class ResourceLimits:
    """CPU and memory constraints for a sandbox or agent."""
    cpu: str = "2"
    memory: str = "4Gi"


@dataclass
class Mount:
    """Filesystem mount specification."""
    source: str
    target: str
    read_only: bool = False


@dataclass
class NetworkPolicy:
    """Network access policy for a sandbox."""
    allow_egress: bool = True
    allowed_domains: list[str] = field(default_factory=list)
    allow_internet: bool = False


@dataclass
class SandboxHandle:
    """Opaque handle to a running sandbox."""
    id: str
    host: str
    port: int
    status: str
    created_at: datetime


@dataclass
class ExecResult:
    """Result of a command execution inside a sandbox."""
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int


# ===========================================================================
# Guardrail Types
# ===========================================================================


@dataclass
class GuardrailDecision:
    """Result of a guardrail check."""
    allowed: bool
    reason: Optional[str] = None
    modified_action: Optional[dict[str, Any]] = None
    alert: bool = False


# ===========================================================================
# Agent Lifecycle Types
# ===========================================================================


class AgentStatus(str, Enum):
    """Canonical agent lifecycle states."""
    CREATED = "created"
    CONFIGURING = "configuring"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    DESTROYED = "destroyed"


# ===========================================================================
# Credential Types
# ===========================================================================


class CredentialType(str, Enum):
    """Supported credential kinds."""
    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    PAT = "pat"           # Personal Access Token
    CUSTOM = "custom"
    ENV = "env"           # Environment variable


@dataclass
class CredentialRef:
    """Reference to a stored credential."""
    id: str
    name: str
    type: CredentialType
    provider: str


# ===========================================================================
# Skill & Tool Types
# ===========================================================================


@dataclass
class Skill:
    """A skill that can be injected into an agent."""
    id: str
    name: str
    version: str
    description: str
    requires: list[str] = field(default_factory=list)
    category: str = "general"


# ===========================================================================
# Schedule Types
# ===========================================================================


@dataclass
class ScheduleDef:
    """Schedule definition for a recurring task."""
    id: str
    agent_id: str
    cron_expression: str
    prompt: str
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    pre_check_enabled: bool = True


# ===========================================================================
# Channel / Integration Types
# ===========================================================================


@dataclass
class ChannelConfig:
    """Configuration for a message channel."""
    type: str               # "slack", "telegram", "discord", etc.
    enabled: bool = True
    config: dict[str, Any] = field(default_factory=dict)


# ===========================================================================
# MCP / Tool Types
# ===========================================================================


@dataclass
class MCPConfig:
    """Configuration for an MCP server."""
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


@dataclass
class ToolResult:
    """Result of a tool execution."""
    content: list[dict[str, Any]]
    is_error: bool = False


# ===========================================================================
# Git Configuration
# ===========================================================================


@dataclass
class GitConfig:
    """Git integration configuration for an agent."""
    repo_url: str
    branch: str = "main"
    auto_sync: bool = False
    commit_on_change: bool = True


# ===========================================================================
# Workflow / Process Types
# ===========================================================================


class StepType(str, Enum):
    """Types of workflow steps."""
    TASK = "task"           # Send a prompt to an agent
    CONDITION = "condition"  # Branch based on output
    PARALLEL = "parallel"   # Run multiple steps concurrently
    WAIT = "wait"           # Pause for a duration
    HUMAN_INPUT = "human_input"  # Await human approval


@dataclass
class WorkflowDef:
    """Definition of a multi-step workflow."""
    name: str
    description: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    timeout_seconds: int = 3600
    on_failure: str = "stop"  # "stop", "retry", "continue"


@dataclass
class WorkflowStepResult:
    """Result of a single workflow step."""
    step_id: str
    status: str     # "success", "failed", "skipped"
    output: Optional[str] = None
    error: Optional[str] = None
    duration_ms: int = 0


# ===========================================================================
# Validation Types
# ===========================================================================


@dataclass
class ValidationResult:
    """Result of validating a template or configuration."""
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    schema_version: str = "1.0"


# ===========================================================================
# Agent Template Types
# ===========================================================================


@dataclass
class Template:
    """An agent template that can be instantiated."""
    id: str
    name: str
    description: str
    version: str
    category: str = "general"
    config: dict[str, Any] = field(default_factory=dict)


# ===========================================================================
# Topology Types
# ===========================================================================


@dataclass
class TopologyConfig:
    """How agents in a system communicate with each other."""
    mode: str = "full-mesh"  # "full-mesh", "orchestrator-workers", "none"
    explicit: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class SharedResources:
    """Resources shared across agents in a system."""
    volumes: list[Mount] = field(default_factory=list)
    secrets: list[str] = field(default_factory=list)
    network: str = "default"


# ===========================================================================
# Testing Types
# ===========================================================================


@dataclass
class Scenario:
    """An end-to-end test scenario."""
    name: str
    description: str
    steps: list[ScenarioStep] = field(default_factory=list)
    cleanup: list[ScenarioStep] = field(default_factory=list)


@dataclass
class ScenarioStep:
    """A single step in a test scenario."""
    action: str    # "create_agent", "chat", "schedule", "assert_status"
    params: dict[str, Any] = field(default_factory=dict)
    expected: Optional[dict[str, Any]] = None
    timeout: int = 60


@dataclass
class ScenarioResult:
    """Result of running a scenario."""
    name: str
    passed: bool
    steps_completed: int
    steps_total: int
    failures: list[str] = field(default_factory=list)
    duration_ms: int = 0
