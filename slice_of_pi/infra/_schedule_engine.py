"""
Schedule Engine Interface

Abstract scheduled task execution engine. Supports cron expressions,
one-shot timers, and interval-based recurring execution with
pre-check validation.

The schedule engine is a background service that evaluates
schedules and dispatches tasks to agents. It does NOT execute
tasks itself — it calls AgentRuntime.execute().
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Awaitable, Callable, Optional

from ..shared import ScheduleDef

# Task callback: async callable receiving a ScheduleDef
TaskCallback = Callable[[ScheduleDef], Awaitable[None]]


class ScheduleEngine(ABC):
    """Abstract scheduled task execution engine.

    Evaluates cron expressions, fires tasks at the right time,
    and handles missed executions (catch-up). Supports pre-check
    validation: before executing a task, the engine can verify
    that the target agent is healthy and not already busy.

    Implementations:
      - CronScheduleEngine:   Traditional cron-based scheduling
      - QuartzScheduleEngine:  Richer scheduling (intervals, calendars)
      - TemporalScheduleEngine: Durable execution with workflows
    """

    @abstractmethod
    async def register(
        self,
        schedule: ScheduleDef,
        task: TaskCallback,
    ) -> str:
        """Register a recurring task.

        Args:
            schedule: Cron expression, agent target, prompt, etc.
            task:     Async callback invoked when the schedule fires.

        Returns:
            schedule_id — used for cancel/list/get_next_run.
        """
        ...

    @abstractmethod
    async def run_once(
        self,
        at: datetime,
        task: TaskCallback,
    ) -> str:
        """Schedule a one-shot execution at a specific time.

        Args:
            at:   When to fire (UTC).
            task: Async callback.

        Returns:
            schedule_id — can be used to cancel before firing.
        """
        ...

    @abstractmethod
    async def cancel(self, schedule_id: str) -> None:
        """Cancel a schedule.

        Must be idempotent. If the task is currently executing,
        implementations should either allow it to complete or
        interrupt it (behavior is implementation-defined).
        """
        ...

    @abstractmethod
    async def list_schedules(self) -> list[ScheduleDef]:
        """List all registered schedules with their current state."""
        ...

    @abstractmethod
    async def get_next_run(self, schedule_id: str) -> Optional[datetime]:
        """Get the next scheduled execution time, or None if cancelled."""
        ...

    # ------------------------------------------------------------------ optional

    async def start(self) -> None:
        """Start the schedule engine (begin evaluating schedules).

        Optional. Default no-op.
        """
        return None

    async def stop(self) -> None:
        """Stop the schedule engine (drain in-flight tasks).

        Optional. Default no-op.
        """
        return None

    async def stats(self) -> dict:
        """Return operational statistics.

        Optional. Default returns empty dict.
        """
        return {}
