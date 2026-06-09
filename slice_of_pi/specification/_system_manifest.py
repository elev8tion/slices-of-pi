"""
System Manifest

Declarative specification for a system of collaborating agents.

A SystemManifest defines multiple agents and how they communicate,
share resources, and execute workflows together. Deploying a system
manifest creates all agents, configures permissions, and sets up
cross-agent communication channels.

Example YAML:
  name: research-pipeline
  description: "Research → Analysis → Report pipeline"
  agents:
    researcher:
      template: github:org/research-agent
      resources: {cpu: "4", memory: "8Gi"}
    analyst:
      template: github:org/analysis-agent
      resources: {cpu: "2", memory: "4Gi"}
    writer:
      template: local:report-writer
      resources: {cpu: "1", memory: "2Gi"}
  permissions:
    preset: orchestrator-workers
  workflows:
    - name: weekly-report
      description: "Generate weekly research report"
  topology:
    mode: orchestrator-workers
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..shared import (
    ResourceLimits,
    SharedResources,
    TopologyConfig,
    WorkflowDef,
)
from ._agent_manifest import AgentManifest


@dataclass
class SystemAgentConfig:
    """Configuration for a single agent within a system manifest.

    This is a lighter-weight spec than AgentManifest — it references
    a template and applies overrides rather than duplicating the full
    agent manifest.
    """
    template: str                                    # e.g., "github:Org/repo" or "local:business-assistant"
    resources: Optional[ResourceLimits] = None       # Override resource limits
    folders: Optional[dict[str, bool]] = None         # {"expose": True, "consume": False}
    schedules: list[dict] = field(default_factory=list)  # [{name, cron, message}]
    tags: list[str] = field(default_factory=list)


@dataclass
class SystemPermissions:
    """Permission configuration for agents in a system."""
    preset: Optional[str] = None                     # "full-mesh", "orchestrator-workers", "none"
    explicit: dict[str, list[str]] = field(default_factory=dict)  # {"agent-a": ["agent-b"]}


@dataclass
class SystemManifest:
    """Declarative specification for a multi-agent system.

    This is the top-level contract for deploying a fleet of
    collaborating agents from a single YAML file. Deploying
    a system manifest is the recommended way to bootstrap
    a multi-agent workflow.
    """

    name: str
    description: str = ""
    agents: dict[str, SystemAgentConfig] = field(default_factory=dict)
    permissions: Optional[SystemPermissions] = None
    workflows: list[WorkflowDef] = field(default_factory=list)
    shared: SharedResources = field(default_factory=SharedResources)
    topology: TopologyConfig = field(default_factory=TopologyConfig)

    # System-wide tags applied to all agents
    default_tags: list[str] = field(default_factory=list)
