"""
Skill Provider Interface

Abstract skill injection and marketplace system.

Skills are capabilities injected into agents at provision time.
They can be MCP server configs, environment variables, workspace
files, or any combination thereof.

The SkillProvider abstracts skill storage (local files, git repos,
marketplace API), discovery, and injection so the orchestrator
doesn't care where skills come from.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..shared import Skill


class SkillProvider(ABC):
    """Abstract skill injection system.

    Skills extend agent capabilities. They are discovered from a
    marketplace (or local catalog), installed into agent sandboxes,
    and can be updated independently of the agent image.
    """

    @abstractmethod
    async def list_available(self) -> list[Skill]:
        """List all skills available for installation.

        This is the catalog — it includes skills from all sources
        (built-in, marketplace, custom).
        """
        ...

    @abstractmethod
    async def install(self, agent_id: str, skill_id: str) -> None:
        """Install a skill into an agent's sandbox.

        May write files, set environment variables, configure MCP
        servers, or run setup scripts. Should be idempotent.
        """
        ...

    @abstractmethod
    async def uninstall(self, agent_id: str, skill_id: str) -> None:
        """Remove a skill from an agent's sandbox.

        Should be idempotent. May leave inert files in place.
        """
        ...

    @abstractmethod
    async def get_marketplace(self) -> list[Skill]:
        """List skills available from the remote marketplace.

        Different from list_available() — this only returns skills
        from the remote marketplace, not locally installed ones.
        """
        ...

    async def search(self, query: str) -> list[Skill]:
        """Search the marketplace for skills matching a query.

        Optional. Default returns empty list.
        """
        return []

    async def get_skill(self, skill_id: str) -> Skill | None:
        """Get detailed information about a single skill.

        Optional. Default returns None.
        """
        return None
