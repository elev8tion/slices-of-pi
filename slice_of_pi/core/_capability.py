"""
Agent Capability Interface

Composable units of agent functionality. Capabilities are injected
at provision time and can be installed/uninstalled independently.

Examples: filesystem_access, web_browsing, code_execution,
           image_generation, voice_interface
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class AgentCapability(ABC):
    """Abstract capability that can be injected into an agent.

    Capabilities are composable — an agent's total ability set is the
    union of all installed capabilities. Each capability declares its
    dependencies so the injection system can topologically order
    installation.

    Usage:
        class FilesystemCapability(AgentCapability):
            name = "filesystem"
            requires = []
            async def install(self, agent_id): ...
            async def uninstall(self, agent_id): ...
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique capability identifier, e.g. 'filesystem', 'web_search'."""
        ...

    @property
    @abstractmethod
    def requires(self) -> list[str]:
        """Names of capabilities this one depends on.

        The injection system installs dependencies before this capability.
        """
        ...

    @abstractmethod
    async def install(self, agent_id: str) -> None:
        """Install this capability into an agent's sandbox.

        Called during provision(). Should be idempotent — calling
        install on an already-installed capability is a no-op.
        """
        ...

    @abstractmethod
    async def uninstall(self, agent_id: str) -> None:
        """Remove this capability from an agent's sandbox.

        Should be idempotent. May leave config files in place
        (they become inert without the capability active).
        """
        ...

    async def validate(self, agent_id: str) -> bool:
        """Check that the capability is functioning correctly.

        Optional. Default implementation returns True. Override
        for capabilities that need runtime verification
        (e.g., web_search checks network connectivity).
        """
        return True
