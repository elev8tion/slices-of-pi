"""
Test Fixture Factory

Factory for creating deterministic test fixtures: pre-configured
agents, multi-agent systems, schedules, and credentials.

Fixtures are isolated — they don't interfere with each other or
with live infrastructure. The factory cleans up after itself
(optionally, via cleanup()) so test suites leave no trace.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class TestFixtureFactory(ABC):
    """Factory for creating test fixtures.

    Provides pre-configured agents, systems, schedules, and
    credentials for deterministic testing. All fixtures are
    ephemeral — use cleanup() to destroy them after tests.

    Implementations:
      - DockerTestFactory:    Real Docker containers (integration tests)
      - MockTestFactory:      In-memory mocks (unit tests)
      - HybridTestFactory:    Real services, mock agents
    """

    @abstractmethod
    async def create_test_agent(
        self,
        template: str = "echo",
        runtime: str = "mock",
    ) -> str:
        """Create a test agent that echoes back prompts.

        The "echo" template creates an agent that returns whatever
        prompt it receives. Perfect for testing orchestration logic
        without needing a real LLM.

        Args:
            template: Agent template to use ("echo", "error", "slow", etc.).
            runtime:  Runtime backend ("mock", "docker", "process").

        Returns:
            agent_id for use in test assertions.
        """
        ...

    @abstractmethod
    async def create_test_system(
        self,
        agent_ids: list[str],
    ) -> str:
        """Create a multi-agent test system.

        Args:
            agent_ids: Pre-created test agent IDs to include.

        Returns:
            system_id for use in test assertions.
        """
        ...

    @abstractmethod
    async def create_test_credential(
        self,
        credential_type: str,
    ) -> str:
        """Create a test credential (fake API key, mock OAuth token, etc.).

        Args:
            credential_type: "api_key", "oauth2", "pat", "env".

        Returns:
            credential_id.
        """
        ...

    @abstractmethod
    async def cleanup(self) -> None:
        """Destroy all test fixtures created by this factory.

        Must be idempotent. Call in test teardown.
        """
        ...

    async def create_test_schedule(
        self,
        agent_id: str,
        cron: str = "0 0 * * *",
    ) -> str:
        """Create a test schedule.

        Optional. Default raises NotImplementedError.
        """
        raise NotImplementedError
