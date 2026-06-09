"""
Guardrail Hook Interface

Pre/post-execution safety hooks that inspect and can block
agent actions before they run.

Guardrails are the safety net: they enforce file access policies,
block dangerous bash commands, restrict network egress, prevent
credential leakage, and scan outputs for PII/secrets.

Architecture:
  Agent action → [pre_exec hooks] → execute → [post_exec hooks] → result
                     ↓ reject                          ↓ reject
                  blocked                            blocked

Hooks are composable: multiple hooks can be registered and
each one gets to inspect every action.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..shared import GuardrailDecision


class GuardrailHook(ABC):
    """Pre/post-execution guardrail that can inspect and block agent actions.

    Implement one hook per safety concern:
      - FileAccessGuardrail:    Restrict which paths agents can read/write
      - CommandGuardrail:       Block dangerous shell commands
      - NetworkGuardrail:       Restrict outbound connections
      - OutputScanner:          Scan agent responses for PII/secrets
      - RateLimitGuardrail:     Throttle agent action frequency

    Hooks run in registration order. A REJECT from any hook stops
    the action immediately (short-circuit evaluation).
    """

    @property
    @abstractmethod
    def hook_name(self) -> str:
        """Unique hook identifier for logging and debugging."""
        ...

    # ------------------------------------------------------------------ pre-execution

    @abstractmethod
    async def pre_exec(
        self,
        agent_id: str,
        action: dict[str, Any],
    ) -> GuardrailDecision:
        """Inspect an action BEFORE it executes.

        Called for every agent action (tool call, file access, etc.).
        Return GuardrailDecision(allowed=False) to block the action.

        Args:
            agent_id: Which agent is acting.
            action:   The proposed action (tool name, params, etc.).
        """
        ...

    @abstractmethod
    async def post_exec(
        self,
        agent_id: str,
        action: dict[str, Any],
        result: dict[str, Any],
    ) -> GuardrailDecision:
        """Inspect the result AFTER an action executes.

        Called after every successful action. Can block the result
        from being returned to the agent (e.g., if it contains
        secrets). Can also trigger alerts for suspicious outputs.

        Args:
            agent_id: Which agent acted.
            action:   The action that was executed.
            result:   The result produced.
        """
        ...

    # ------------------------------------------------------------------ specialized hooks

    @abstractmethod
    async def on_file_access(
        self,
        agent_id: str,
        path: str,
        mode: str,
    ) -> GuardrailDecision:
        """Called when an agent attempts file I/O.

        Args:
            path: Absolute path inside the sandbox.
            mode: "read", "write", "delete", "execute".
        """
        ...

    @abstractmethod
    async def on_command(
        self,
        agent_id: str,
        command: list[str],
    ) -> GuardrailDecision:
        """Called when an agent attempts to run a command.

        Args:
            command: The command and arguments as a list.
                     Never a shell string (prevents injection).
        """
        ...

    # ------------------------------------------------------------------ optional

    async def on_network(
        self,
        agent_id: str,
        host: str,
        port: int,
    ) -> GuardrailDecision:
        """Called when an agent attempts outbound network access.

        Optional. Default ALLOW.
        """
        return GuardrailDecision(allowed=True)
