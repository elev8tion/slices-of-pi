"""
Agent Runtime Interface

Abstract agent execution environment. Agents run in isolated
environments — Docker containers, Kubernetes pods, Firecracker
microVMs, serverless functions, etc.

This interface lets the orchestrator manage agents without
knowing where they execute. Implementations provide the
runtime-specific glue.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional

from ..shared import AgentStatus, ResourceLimits, SandboxHandle


class AgentRuntime(ABC):
    """Abstract agent execution environment.

    The runtime is responsible for the full lifecycle of agent
    sandboxes: creation, destruction, health checks, file operations,
    and streaming execution.

    Implementations:
      - DockerRuntime:   Docker containers (via docker-py)
      - K8sRuntime:      Kubernetes pods (via kubernetes-asyncio)
      - FirecrackerRuntime: Firecracker microVMs
      - MockRuntime:     In-process for testing
    """

    # ------------------------------------------------------------------ create / destroy

    @abstractmethod
    async def create(self, config: dict) -> str:
        """Provision a new agent environment.

        Args:
            config: Agent configuration dict (image, resources, mounts, env, etc.)

        Returns:
            agent_id — a unique identifier for the new agent.

        Raises:
            RuntimeProvisionError: If the environment cannot be created.
        """
        ...

    @abstractmethod
    async def destroy(self, agent_id: str) -> None:
        """Tear down agent environment and release all resources.

        Must be idempotent — destroying an already-destroyed agent
        is a no-op.
        """
        ...

    # ------------------------------------------------------------------ execute

    @abstractmethod
    async def execute(
        self,
        agent_id: str,
        prompt: str,
        context: dict,
    ) -> AsyncIterator[str]:
        """Run an agent prompt, yielding streaming output chunks.

        This is the primary interaction point. The runtime sends the
        prompt to the agent process and streams back the response
        token-by-token (or chunk-by-chunk for non-LLM agents).

        Args:
            agent_id: Target agent.
            prompt: The message to send.
            context: Execution context (model, tools, system prompt, etc.).

        Yields:
            String chunks of the agent's response.
        """
        ...

    # ------------------------------------------------------------------ status

    @abstractmethod
    async def status(self, agent_id: str) -> AgentStatus:
        """Get detailed status of a single agent."""
        ...

    @abstractmethod
    async def list_all(self) -> list[dict]:
        """List all agents managed by this runtime."""
        ...

    # ------------------------------------------------------------------ file operations

    @abstractmethod
    async def inject_file(
        self,
        agent_id: str,
        path: str,
        content: bytes,
    ) -> None:
        """Write a file into the agent's sandbox.

        Used for credential injection, skill installation, and
        configuration updates.
        """
        ...

    @abstractmethod
    async def read_file(
        self,
        agent_id: str,
        path: str,
    ) -> bytes:
        """Read a file from the agent's sandbox."""
        ...

    # ------------------------------------------------------------------ lifecycle hooks

    async def pre_create(self, config: dict) -> dict:
        """Hook called before create(). Can modify config.

        Optional. Default is identity.
        """
        return config

    async def post_destroy(self, agent_id: str) -> None:
        """Hook called after destroy(). For cleanup logging, etc.

        Optional. Default is no-op.
        """
        return None
