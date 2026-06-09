"""
Agent Client Interface

Abstract client for interacting with the agent platform
programmatically. This is the API surface that CLI tools,
SDKs, and other automation consume.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator


class AgentClient(ABC):
    """Abstract client for the agent platform.

    This is the primary programmatic interface. CLI tools, CI/CD
    pipelines, and custom integrations all use this client to
    deploy agents, send messages, and manage infrastructure.

    Implementations:
      - HttpAgentClient:    REST/WebSocket client to backend API
      - GrpcAgentClient:    gRPC client (high-throughput)
      - LocalAgentClient:   Direct in-process client (testing)
      - MCPAgentClient:     MCP protocol client
    """

    @abstractmethod
    async def deploy(self, config: dict) -> str:
        """Deploy a new agent from a configuration dict.

        Returns:
            agent_id of the newly deployed agent.
        """
        ...

    @abstractmethod
    async def chat(
        self,
        agent_id: str,
        message: str,
        stream: bool = True,
    ) -> AsyncIterator[str]:
        """Send a message to an agent and stream the response.

        Args:
            agent_id: Target agent.
            message:  The message to send.
            stream:   If True, yield tokens as they arrive.
                      If False, yield the complete response once.

        Yields:
            Response chunks (tokens or complete message).
        """
        ...

    @abstractmethod
    async def list_agents(self) -> list[dict]:
        """List all agents visible to this client."""
        ...

    @abstractmethod
    async def get_logs(self, agent_id: str) -> str:
        """Get recent logs from an agent."""
        ...

    @abstractmethod
    async def exec_command(
        self,
        agent_id: str,
        command: str,
    ) -> str:
        """Execute a command inside an agent's sandbox.

        Use sparingly — this is for debugging, not for automation.
        """
        ...

    async def stop_agent(self, agent_id: str) -> None:
        """Stop a running agent.

        Optional. Default raises NotImplementedError.
        """
        raise NotImplementedError

    async def destroy_agent(self, agent_id: str) -> None:
        """Destroy an agent and release its resources.

        Optional. Default raises NotImplementedError.
        """
        raise NotImplementedError
