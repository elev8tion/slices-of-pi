"""
Pi Scheduler Service — cron-based recurring pi session execution.

Uses APScheduler for cron parsing. Single-instance — no Redis distributed
locking needed. Each schedule runs through pi_session_service.stream_chat
so sessions land in the same managed layout as interactive chat:

  ~/.pi/agent/sessions/managed/<agent_name>/<session_id>.jsonl
"""

from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore

from .. import database as db
from ..config import SCHEDULE_POLL_INTERVAL

logger = logging.getLogger(__name__)


class PiScheduler:
    """Single-instance scheduler for recurring pi sessions."""

    def __init__(self):
        self._scheduler: AsyncIOScheduler | None = None
        self._running = False

    async def start(self) -> None:
        """Start the scheduler and load enabled schedules."""
        self._scheduler = AsyncIOScheduler(
            jobstores={"default": MemoryJobStore()},
            timezone="UTC",
        )
        await self._reload_schedules()
        self._scheduler.start()
        self._running = True
        logger.info("Scheduler started")

        # Periodic reload for new/updated schedules
        asyncio.create_task(self._reload_loop())

    async def stop(self) -> None:
        """Graceful shutdown."""
        self._running = False
        if self._scheduler:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None
        logger.info("Scheduler stopped")

    async def _reload_loop(self) -> None:
        """Periodically reload schedules from the database."""
        while self._running:
            await asyncio.sleep(SCHEDULE_POLL_INTERVAL)
            try:
                await self._reload_schedules()
            except Exception:
                logger.exception("Schedule reload failed")

    async def _reload_schedules(self) -> None:
        """Sync APScheduler jobs with enabled schedules in the database."""
        if not self._scheduler:
            return

        schedules = db.list_schedules()
        existing_jobs = {job.id for job in self._scheduler.get_jobs()}

        for schedule in schedules:
            job_id = schedule["id"]

            if not schedule["enabled"]:
                if job_id in existing_jobs:
                    self._scheduler.remove_job(job_id)
                continue

            try:
                trigger = CronTrigger.from_crontab(schedule["cron_expression"])
            except Exception:
                logger.exception("Invalid cron for schedule %s", job_id[:12])
                continue

            if job_id in existing_jobs:
                self._scheduler.reschedule_job(job_id, trigger=trigger)
            else:
                self._scheduler.add_job(
                    self._execute_schedule,
                    trigger=trigger,
                    args=[schedule["id"]],
                    id=job_id,
                    replace_existing=True,
                )

    async def _execute_schedule(self, schedule_id: str) -> None:
        """Execute a scheduled run via the same stream_chat path as the UI."""
        schedule = db.get_schedule(schedule_id)
        if not schedule or not schedule.get("enabled"):
            return

        execution_id = db.record_schedule_execution_start(schedule["id"])
        agent_id = schedule["agent_id"]
        agent = db.get_agent(agent_id)
        if not agent:
            db.record_schedule_execution_end(
                execution_id, "failed", error_message="Agent not found"
            )
            return

        logger.info(
            "Schedule %s executing for agent %s: %s",
            schedule["id"][:12],
            agent.get("name"),
            (schedule.get("message") or "")[:60],
        )

        try:
            # Import here to avoid circular import at module load
            from ..services.pi_session_service import stream_chat

            had_error = False
            error_msg = None
            async for chunk in stream_chat(
                agent_id=agent_id,
                prompt=schedule["message"],
                model=schedule.get("model") or agent.get("model") or None,
                timeout_seconds=schedule.get("timeout_seconds") or 900,
            ):
                if chunk.get("type") == "error":
                    had_error = True
                    error_msg = (chunk.get("content") or "stream error")[:500]

            # Latest session for this agent is the one stream_chat just created
            sessions = db.list_sessions(agent_id=agent_id, limit=1)
            session_id = sessions[0]["id"] if sessions else None

            if had_error:
                db.record_schedule_execution_end(
                    execution_id,
                    "failed",
                    session_id=session_id,
                    error_message=error_msg,
                )
            else:
                db.record_schedule_execution_end(
                    execution_id,
                    "success",
                    session_id=session_id,
                    exit_code=0,
                )

        except asyncio.TimeoutError:
            db.record_schedule_execution_end(
                execution_id, "timeout", error_message="Execution timed out"
            )
        except Exception as e:
            logger.exception("Schedule %s failed", schedule_id[:12])
            db.record_schedule_execution_end(
                execution_id, "failed", error_message=str(e)[:500]
            )


# Singleton
scheduler = PiScheduler()
