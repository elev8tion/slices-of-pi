"""
Core Abstractions Layer

Foundational interfaces for the agentic framework. These define the
agent lifecycle contract, composable capabilities, and credential
injection — the three pillars every agent must satisfy.

Interface catalog:
  AgentLifecycle      — State machine (CREATED → RUNNING → STOPPED)
  AgentCapability     — Composable capability injection
  CredentialProvider  — OAuth/API key/PAT injection
"""

from ._lifecycle import AgentLifecycle
from ._capability import AgentCapability
from ._credentials import CredentialProvider

__all__ = [
    "AgentLifecycle",
    "AgentCapability",
    "CredentialProvider",
]
