"""
Specification Layer

Declarative configuration contracts for agents and multi-agent
systems. These are the "single source of truth" formats that can
be version-controlled, shared, and used to reproducibly deploy
agent fleets.

Interface catalog:
  AgentManifest       — Single agent specification
  SystemManifest      — Multi-agent system specification
"""

from ._agent_manifest import AgentManifest
from ._system_manifest import SystemManifest

__all__ = [
    "AgentManifest",
    "SystemManifest",
]
