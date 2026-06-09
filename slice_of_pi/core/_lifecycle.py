"""
Agent Lifecycle Interface

Defines the canonical agent state machine. Every agent implementation
MUST transition through these states in order:

  CREATED → CONFIGURING → RUNNING → (STOPPED | ERROR)

Sub-states (PAUSED, RESTARTING) are managed by the runtime, not
by this interface — they are transient and resolve to RUNNING.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Protocol, runtime_checkable


# ===========================================================================
# Protocol (structural) form — recommended for duck-typing
# ===========================================================================


@runtime_checkable
class AgentLifecycle(Protocol):
    """Protocol defining the agent lifecycle contract.

    Agents MUST implement all methods. The state machine defines the
    valid transitions; implementations MUST enforce them.

    Valid transitions:
      CREATED     → CONFIGURING (provision called)
      CONFIGURING → RUNNING      (start called, health_check passes)
      RUNNING     → STOPPED      (stop called)
      RUNNING     → ERROR        (health_check fails or crash)
      STOPPED     → CREATED      (destroy called)
      ERROR       → CREATED      (destroy called)

    Invalid transitions (implementations MUST reject):
      RUNNING → CREATED (cannot create a running agent)
      STOPPED → RUNNING (use restart, not start)
    """

    @property
    def agent_id(self) -> str: ...

    @property
    def status(self) -> str: ...

    @property
    def created_at(self) -> datetime: ...

    async def provision(self, config: dict) -> None:
        """Transition CREATED → CONFIGURING.

        Provision resources for the agent: allocate sandbox, set up
        networking, mount volumes, inject credentials.
        """
        ...

    async def start(self) -> None:
        """Transition CONFIGURING → RUNNING.

        Start the agent process inside the sandbox. After this call,
        the agent should respond to execute() requests.
        """
        ...

    async def stop(self) -> None:
        """Transition RUNNING → STOPPED.

        Gracefully stop the agent process. Resources are preserved
        so restart() can be called.
        """
        ...

    async def restart(self) -> None:
        """Transition STOPPED → RUNNING.

        Restart a stopped agent. Equivalent to stop() then start()
        but preserves configuration and credentials.
        """
        ...

    async def destroy(self) -> None:
        """Transition (any) → CREATED.

        Tear down all resources. After destruction, the agent_id
        should be reusable.
        """
        ...

    async def health_check(self) -> bool:
        """Return True if the agent is responsive and healthy."""
        ...


# ===========================================================================
# ABC (nominal) form — use when explicit inheritance is preferred
# ===========================================================================


class AbstractAgentLifecycle(ABC):
    """Abstract base class for agent lifecycle implementations.

    Use this when you want explicit inheritance and shared utility
    methods. Prefer AgentLifecycle Protocol for duck-typing
    compatibility.
    """

    @property
    @abstractmethod
    def agent_id(self) -> str: ...

    @property
    @abstractmethod
    def status(self) -> str: ...

    @property
    @abstractmethod
    def created_at(self) -> datetime: ...

    @abstractmethod
    async def provision(self, config: dict) -> None: ...

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    @abstractmethod
    async def restart(self) -> None: ...

    @abstractmethod
    async def destroy(self) -> None: ...

    @abstractmethod
    async def health_check(self) -> bool: ...
