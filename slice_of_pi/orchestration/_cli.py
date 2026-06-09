"""
CLI Plugin & Agent Client Interfaces

These are kept in a sub-module of orchestration since they
represent the CLI integration surface. They define how CLI
tools extend the platform and how clients interact with
agents programmatically.
"""

from ._cli_plugin import CLIPlugin
from ._agent_client import AgentClient

__all__ = [
    "CLIPlugin",
    "AgentClient",
]
