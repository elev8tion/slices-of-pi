"""
Execution Layer

Sandboxed agent execution environments and guardrail hooks
that inspect and enforce safety policies on agent actions.

Interface catalog:
  ExecutionEnvironment  — Isolated sandbox for agent processes
  GuardrailHook         — Pre/post-execution safety inspection
"""

from ._execution_environment import ExecutionEnvironment
from ._guardrail_hook import GuardrailHook

__all__ = [
    "ExecutionEnvironment",
    "GuardrailHook",
]
