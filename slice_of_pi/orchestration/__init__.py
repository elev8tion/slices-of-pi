"""
Orchestration Layer

Interfaces for agent execution environments, workflow engines,
real-time event distribution, skill injection, and message
channel integration.

Interface catalog:
  AgentRuntime      — Abstract execution environment (Docker, K8s, serverless)
  WorkflowEngine     — Multi-step YAML-defined workflow execution
  EventBus           — Pub/sub for real-time updates
  SkillProvider      — Skill injection and marketplace
  ChannelAdapter     — External message channel integration
"""

from ._agent_runtime import AgentRuntime
from ._workflow_engine import WorkflowEngine
from ._event_bus import EventBus
from ._skill_provider import SkillProvider
from ._channel_adapter import ChannelAdapter
from ._cli_plugin import CLIPlugin
from ._agent_client import AgentClient

__all__ = [
    "AgentRuntime",
    "WorkflowEngine",
    "EventBus",
    "SkillProvider",
    "ChannelAdapter",
    "CLIPlugin",
    "AgentClient",
]
