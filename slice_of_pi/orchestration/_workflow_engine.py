"""
Workflow Engine Interface

Abstract multi-step workflow/process execution engine.

Workflows are YAML-defined sequences that orchestrate multiple agents
through structured pipelines: perception → analysis → synthesis →
publish. Supports sequential, parallel, fan-out, and conditional steps.

Design principle:
  The workflow engine coordinates agents but does NOT execute steps
  itself — it delegates to the AgentRuntime.execute() method.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator

from ..shared import WorkflowDef, WorkflowStepResult


class WorkflowEngine(ABC):
    """Abstract workflow/process execution engine.

    Deploy a YAML workflow definition, then execute it with inputs.
    The engine handles step ordering, parallelism, error handling,
    and retry logic. Each step dispatches to the appropriate agent.

    Supported step types:
      task         — Send a prompt to an agent
      condition    — Branch based on previous step output
      parallel     — Run multiple steps concurrently
      wait         — Pause for a duration
      human_input  — Await human approval before continuing
    """

    # ------------------------------------------------------------------ lifecycle

    @abstractmethod
    async def deploy(self, workflow_yaml: str) -> str:
        """Validate and deploy a workflow.

        Parses the YAML, validates the DAG (no cycles), resolves
        agent references, and stores the workflow for execution.

        Returns:
            workflow_id — used for subsequent execute/status/cancel calls.
        """
        ...

    @abstractmethod
    async def execute(
        self,
        workflow_id: str,
        inputs: dict,
    ) -> AsyncIterator[WorkflowStepResult]:
        """Execute a workflow, yielding step results as they complete.

        Steps are yielded in completion order (not definition order).
        For parallel steps, results are yielded as each child finishes.
        """
        ...

    @abstractmethod
    async def status(self, workflow_id: str) -> dict:
        """Get current status of a workflow execution.

        Returns:
            {
                "workflow_id": str,
                "state": "running" | "completed" | "failed" | "cancelled",
                "steps_completed": int,
                "steps_total": int,
                "current_step": Optional[str],
                "started_at": ISO8601,
                "errors": [...]
            }
        """
        ...

    @abstractmethod
    async def cancel(self, workflow_id: str) -> None:
        """Cancel a running workflow.

        Running steps are allowed to complete; pending steps are
        skipped. Partial results are preserved for inspection.
        """
        ...

    # ------------------------------------------------------------------ optional

    async def validate(self, workflow_yaml: str) -> list[str]:
        """Validate a workflow YAML without deploying.

        Returns list of validation errors (empty = valid).
        Optional. Default raises NotImplementedError.
        """
        raise NotImplementedError
