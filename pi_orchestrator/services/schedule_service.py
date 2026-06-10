"""
Pi Scheduler Service — cron-based recurring pi session execution.

Uses APScheduler for cron parsing. Single-instance — no Redis distributed
locking needed. Each schedule spawns a pi subprocess via the session service.

Design:
  - APScheduler with MemoryJobStore
  - Loads enabled schedules from SQLite at startup
  - Re-evaluates schedules every POLL_INTERVAL seconds
  - Each execution runs pi --mode json --print "<message>"
  - Execution results tracked in schedule_executions table
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

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

            trigger = CronTrigger.from_crontab(schedule["cron_expression"])

            if job_id in existing_jobs:
                self._scheduler.reschedule_job(job_id, trigger=trigger)
            else:
                self._scheduler.add_job(
                    self._execute_schedule,
                    trigger=trigger,
                    args=[schedule],
                    id=job_id,
                    replace_existing=True,
                )

    async def _execute_schedule(self, schedule: dict) -> None:
        """Execute a scheduled pi session asynchronously."""
        execution_id = db.record_schedule_execution_start(schedule["id"])
        logger.info(f"Schedule {schedule['id'][:12]} executing: {schedule['message'][:60]}")

        try:
            # Build pi command
            cmd = ["pi", "--mode", "json", "--print"]

            agent = db.get_agent(schedule["agent_id"])
            if agent:
                tools = agent.get("tools", "[]")
                if isinstance(tools, str):
                    import json
                    tools = json.loads(tools)
                cmd.extend(["--tools", ",".join(tools)])

            model = schedule.get("model") or (agent["model"] if agent else "claude-sonnet-4-5")
            cmd.extend(["--model", model, schedule["message"]])

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=schedule.get("timeout_seconds", 900),
                )

                if proc.returncode == 0:
                    db.record_schedule_execution_end(
                        execution_id, "success",
                        exit_code=proc.returncode,
                    )
                else:
                    stderr_text = stderr.decode()[:500] if stderr else ""
                    db.record_schedule_execution_end(
                        execution_id, "failed",
                        exit_code=proc.returncode,
                        error_message=stderr_text,
                    )

            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                db.record_schedule_execution_end(
                    execution_id, "timeout",
                    error_message="Execution timed out",
                )

        except Exception as e:
            db.record_schedule_execution_end(
                execution_id, "failed",
                error_message=str(e)[:500],
            )


# Singleton
scheduler = PiScheduler()
