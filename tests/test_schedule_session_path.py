"""Track C3 — scheduler uses managed stream_chat path (not ad-hoc pi --print)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from pi_orchestrator import database as db
from pi_orchestrator.services.schedule_service import PiScheduler


@pytest.mark.asyncio
async def test_execute_schedule_uses_stream_chat(clear_db):
    agent = db.create_agent("sched-path-agent", model="", tools=["read", "bash"])
    db.update_agent_status(agent["id"], "idle")
    schedule = db.create_schedule(
        agent_id=agent["id"],
        cron_expression="0 9 * * *",
        message="say hello from schedule",
    )

    async def fake_stream(**kwargs):
        assert kwargs["agent_id"] == agent["id"]
        assert kwargs["prompt"] == "say hello from schedule"
        # Simulate session creation as stream_chat would
        s = db.create_session(
            agent_id=agent["id"],
            agent_name=agent["name"],
            session_file=f"/tmp/managed/{agent['name']}/sess.jsonl",
            model="",
        )
        yield {"type": "text_delta", "content": "hello"}
        yield {"type": "turn_end", "tokens_used": 3}
        # Keep session id for assertion
        fake_stream.session_id = s["id"]

    sched = PiScheduler()
    with patch(
        "pi_orchestrator.services.pi_session_service.stream_chat",
        new=fake_stream,
    ):
        await sched._execute_schedule(schedule["id"])

    executions = db.list_schedule_executions(schedule["id"])
    assert len(executions) >= 1
    assert executions[0]["status"] == "success"
    assert executions[0].get("session_id")
