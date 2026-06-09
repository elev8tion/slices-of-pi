"""
Credential Provider Interface

Abstract credential injection system. Supports multiple credential
types: OAuth2, API keys, Personal Access Tokens (PATs), and custom
credential formats.

Credentials are injected into agent sandboxes at provision time and
can be rotated without recreating the sandbox.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class CredentialProvider(ABC):
    """Abstract credential injection system.

    Credentials are secrets agents need to access external services
    (APIs, databases, git repos, etc.). This interface abstracts
    credential storage, injection, and rotation away from the agent
    runtime so the orchestrator can support multiple secret backends
    (env vars, vault, sealed secrets, cloud secret managers).

    Lifecycle:
      inject()  → called during agent provision (secrets → sandbox)
      rotate()  → called on schedule or on demand (new secret → sandbox)
      revoke()  → called when credential is removed (sandbox cleaned)
    """

    @abstractmethod
    async def inject(
        self,
        agent_id: str,
        credential_id: str,
    ) -> dict:
        """Inject a credential into an agent's sandbox.

        Args:
            agent_id: Target agent.
            credential_id: Which credential to inject.

        Returns:
            Metadata about the injection: paths written, env vars set,
            success status, etc.
        """
        ...

    @abstractmethod
    async def revoke(
        self,
        agent_id: str,
        credential_id: str,
    ) -> None:
        """Remove a credential from an agent's sandbox.

        Cleans up all files and environment variables associated
        with the credential.
        """
        ...

    @abstractmethod
    async def rotate(self, credential_id: str) -> str:
        """Rotate a credential, returning the new credential_id.

        The old credential is invalidated and the new one is injected
        into all agents currently using it. Implementations must
        handle the case where rotation fails partway through
        (old credential should remain valid until all agents are
        updated).
        """
        ...

    async def list_available(self, agent_id: str) -> list[str]:
        """List credential IDs available for an agent.

        Optional. Default returns empty list. Override if the
        credential backend supports agent-scoped visibility.
        """
        return []
