"""
Agent Manifest

Declarative specification for a single agent.

An AgentManifest fully describes an agent's configuration,
capabilities, dependencies, and runtime constraints. It is
the single source of truth — version-controlled, shareable,
and reproducible.

Example YAML:
  name: research-agent
  version: "1.0"
  runtime: docker
  image: agent-base:latest
  resources:
    cpu: "2"
    memory: "4Gi"
  tools:
    - web_search
    - filesystem
    - code_execution
  skills:
    - academic-research
    - citation-manager
  guardrails:
    - no-network-egress
    - read-only-filesystem
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..shared import (
    ChannelConfig,
    CredentialRef,
    GitConfig,
    MCPConfig,
    ResourceLimits,
    ScheduleDef,
)


@dataclass
class AgentManifest:
    """Declarative specification for an agent.

    This is the contract: any system that can read an AgentManifest
    and provision the described agent is a valid implementation of
    the agentic framework.
    """

    # ------------------------------------------------------------------ identity

    name: str
    version: str
    description: str = ""

    # ------------------------------------------------------------------ runtime

    runtime: str = "docker"       # "docker", "kubernetes", "wasm", "firecracker"
    image: str = "agent-base:latest"
    resources: ResourceLimits = field(default_factory=ResourceLimits)

    # ------------------------------------------------------------------ capabilities

    tools: list[str] = field(default_factory=list)           # Tool names
    skills: list[str] = field(default_factory=list)          # Skill IDs
    mcp_servers: list[MCPConfig] = field(default_factory=list)  # MCP server configs

    # ------------------------------------------------------------------ integrations

    channels: list[ChannelConfig] = field(default_factory=list)
    credentials: list[CredentialRef] = field(default_factory=list)
    git: Optional[GitConfig] = None

    # ------------------------------------------------------------------ scheduling

    schedules: list[ScheduleDef] = field(default_factory=list)

    # ------------------------------------------------------------------ guardrails

    guardrails: list[str] = field(default_factory=list)  # Guardrail hook names

    # ------------------------------------------------------------------ instructions

    system_prompt: Optional[str] = None
    custom_instructions: Optional[str] = None

    # ------------------------------------------------------------------ metadata

    tags: list[str] = field(default_factory=list)
    labels: dict[str, str] = field(default_factory=dict)
