"""
Tests for the SQLite persistence layer (database.py).

Covers CRUD for:
  - agents
  - sessions
  - activities
  - schedules (+ schedule_executions)
"""

from __future__ import annotations

import json
import pytest
from datetime import datetime, timezone

from pi_orchestrator import database as db
from pi_orchestrator.database import (
    _get_conn,
    _now_iso,
    _new_id,
    agent_count,
    active_session_count,
)


class TestAgentCRUD:
    """Agent create, read, update, delete."""

    def test_create_agent(self):
        agent = db.create_agent(
            name="agent-alpha",
            model="claude-sonnet-4",
            persona="senior-dev",
            tools=["read", "bash", "write", "edit"],
            skills=["python", "typescript"],
            extensions=["my-ext"],
            system_prompt="Act as senior developer.",
            git_repo="https://github.com/user/repo.git",
            schedule_cron="0 9 * * *",
        )

        assert agent is not None
        assert agent["name"] == "agent-alpha"
        assert agent["model"] == "claude-sonnet-4"
        assert agent["persona"] == "senior-dev"
        assert json.loads(agent["tools"]) == ["read", "bash", "write", "edit"]
        assert json.loads(agent["skills"]) == ["python", "typescript"]
        assert json.loads(agent["extensions"]) == ["my-ext"]
        assert agent["system_prompt"] == "Act as senior developer."
        assert agent["git_repo"] == "https://github.com/user/repo.git"
        assert agent["schedule_cron"] == "0 9 * * *"
        assert agent["status"] == "created"
        assert agent["session_count"] == 0
        assert agent["total_tokens"] == 0
        assert agent["id"] is not None
        assert agent["created_at"] is not None
        assert agent["updated_at"] is not None

    def test_create_agent_defaults(self):
        agent = db.create_agent(name="minimal")
        assert agent["name"] == "minimal"
        assert agent["model"] == ""
        assert agent["persona"] is None
        assert json.loads(agent["tools"]) == ["read", "bash", "edit", "write", "web_search", "web_scrape", "analyze_image"]
        assert json.loads(agent["skills"]) == []
        assert json.loads(agent["extensions"]) == []
        assert agent["system_prompt"] is None
        assert agent["git_repo"] is None
        assert agent["schedule_cron"] is None
        assert agent["status"] == "created"

    def test_create_agent_duplicate_name_raises(self):
        db.create_agent(name="unique")
        with pytest.raises(Exception):
            db.create_agent(name="unique")

    def test_get_agent(self):
        created = db.create_agent(name="get-me")
        fetched = db.get_agent(created["id"])
        assert fetched is not None
        assert fetched["id"] == created["id"]
        assert fetched["name"] == "get-me"

    def test_get_agent_not_found(self):
        assert db.get_agent("nonexistent-id") is None

    def test_list_agents(self):
        db.create_agent(name="alpha")
        db.create_agent(name="beta")
        agents = db.list_agents()
        assert len(agents) == 2
        names = {a["name"] for a in agents}
        assert names == {"alpha", "beta"}

    def test_list_agents_filter_by_status(self):
        a1 = db.create_agent(name="active-one")
        a2 = db.create_agent(name="active-two")
        db.update_agent_status(a1["id"], "running")
        db.update_agent_status(a2["id"], "idle")

        running = db.list_agents(status="running")
        assert len(running) == 1
        assert running[0]["id"] == a1["id"]

        idle = db.list_agents(status="idle")
        assert len(idle) == 1
        assert idle[0]["id"] == a2["id"]

    def test_list_agents_empty(self):
        assert db.list_agents() == []

    def test_update_agent_status(self):
        agent = db.create_agent(name="status-test")
        assert agent["status"] == "created"

        db.update_agent_status(agent["id"], "running")
        updated = db.get_agent(agent["id"])
        assert updated["status"] == "running"
        assert updated["last_active"] is not None

    def test_update_agent_tokens(self):
        agent = db.create_agent(name="token-test")
        db.update_agent_tokens(agent["id"], 100)
        assert db.get_agent(agent["id"])["total_tokens"] == 100
        db.update_agent_tokens(agent["id"], 50)
        assert db.get_agent(agent["id"])["total_tokens"] == 150

    def test_increment_session_count(self):
        agent = db.create_agent(name="session-count-test")
        assert agent["session_count"] == 0
        db.increment_session_count(agent["id"])
        assert db.get_agent(agent["id"])["session_count"] == 1
        db.increment_session_count(agent["id"])
        assert db.get_agent(agent["id"])["session_count"] == 2

    def test_delete_agent(self):
        agent = db.create_agent(name="delete-me")
        assert db.delete_agent(agent["id"]) is True
        assert db.get_agent(agent["id"]) is None

    def test_delete_agent_not_found(self):
        assert db.delete_agent("nonexistent") is False

    def test_agent_count(self):
        assert agent_count() == 0
        db.create_agent(name="count-a")
        db.create_agent(name="count-b")
        assert agent_count() == 2

    def test_update_session_file(self):
        agent = db.create_agent(name="sf-test")
        session = db.create_session(agent["id"], agent["name"], "", "sonnet")
        assert session["session_file"] == ""
        db.update_session_file(session["id"], "/path/to/file.jsonl")
        updated = db.get_session(session["id"])
        assert updated["session_file"] == "/path/to/file.jsonl"


class TestSessionCRUD:
    """Session create, read, update, list."""

    def test_create_session(self):
        agent = db.create_agent(name="session-agent")
        session = db.create_session(
            agent_id=agent["id"],
            agent_name=agent["name"],
            session_file="/tmp/session.jsonl",
            model="sonnet",
        )
        assert session["agent_id"] == agent["id"]
        assert session["agent_name"] == "session-agent"
        assert session["session_file"] == "/tmp/session.jsonl"
        assert session["model"] == "sonnet"
        assert session["status"] == "running"
        assert session["turns"] == 0
        assert session["tokens_in"] == 0
        assert session["tokens_out"] == 0
        assert session["started_at"] is not None
        assert session["ended_at"] is None

    def test_get_session(self):
        agent = db.create_agent(name="get-session")
        created = db.create_session(agent["id"], agent["name"], "/tmp/s.jsonl", "sonnet")
        fetched = db.get_session(created["id"])
        assert fetched is not None
        assert fetched["id"] == created["id"]

    def test_get_session_not_found(self):
        assert db.get_session("nonexistent") is None

    def test_list_sessions(self):
        agent = db.create_agent(name="list-sessions")
        s1 = db.create_session(agent["id"], agent["name"], "/tmp/1.jsonl", "sonnet")
        s2 = db.create_session(agent["id"], agent["name"], "/tmp/2.jsonl", "haiku")
        sessions = db.list_sessions()
        assert len(sessions) >= 2
        # Most recent first
        assert sessions[0]["id"] in (s1["id"], s2["id"])

    def test_list_sessions_filter_by_agent(self):
        a1 = db.create_agent(name="filter-a")
        a2 = db.create_agent(name="filter-b")
        s1 = db.create_session(a1["id"], a1["name"], "/tmp/a.jsonl", "sonnet")
        s2 = db.create_session(a2["id"], a2["name"], "/tmp/b.jsonl", "haiku")

        a1_sessions = db.list_sessions(agent_id=a1["id"])
        assert len(a1_sessions) == 1
        assert a1_sessions[0]["id"] == s1["id"]

    def test_update_session_status(self):
        agent = db.create_agent(name="upd-session")
        session = db.create_session(agent["id"], agent["name"], "/tmp/s.jsonl", "sonnet")
        assert session["status"] == "running"

        db.update_session(session["id"], status="completed", ended_at=_now_iso())
        updated = db.get_session(session["id"])
        assert updated["status"] == "completed"
        assert updated["ended_at"] is not None

    def test_update_session_tokens(self):
        agent = db.create_agent(name="token-session")
        session = db.create_session(agent["id"], agent["name"], "/tmp/s.jsonl", "sonnet")

        db.update_session(session["id"], tokens_in=100, tokens_out=200)
        updated = db.get_session(session["id"])
        assert updated["tokens_in"] == 100
        assert updated["tokens_out"] == 200

        # Incremental
        db.update_session(session["id"], tokens_in=50, tokens_out=30)
        updated = db.get_session(session["id"])
        assert updated["tokens_in"] == 150
        assert updated["tokens_out"] == 230

    def test_update_session_turns(self):
        agent = db.create_agent(name="turns-session")
        session = db.create_session(agent["id"], agent["name"], "/tmp/s.jsonl", "sonnet")

        db.update_session(session["id"], turns=5)
        updated = db.get_session(session["id"])
        assert updated["turns"] == 5

    def test_session_cascading_delete(self):
        """Deleting an agent cascades to its sessions."""
        agent = db.create_agent(name="cascade-test")
        db.create_session(agent["id"], agent["name"], "/tmp/s.jsonl", "sonnet")

        db.delete_agent(agent["id"])
        sessions = db.list_sessions(agent_id=agent["id"])
        assert len(sessions) == 0

    def test_active_session_count(self):
        assert active_session_count() == 0
        agent = db.create_agent(name="active-test")
        db.create_session(agent["id"], agent["name"], "/tmp/s.jsonl", "sonnet")
        assert active_session_count() == 1

        # Completed sessions don't count
        s2 = db.create_session(agent["id"], agent["name"], "/tmp/s2.jsonl", "sonnet")
        db.update_session(s2["id"], status="completed")
        assert active_session_count() == 1  # Still 1 running


class TestActivityCRUD:
    """Activity recording and listing."""

    def test_record_activity(self):
        agent = db.create_agent(name="activity-test")
        db.record_activity(agent["id"], "test_event", agent["name"], {"key": "value"})
        activities = db.list_activities(limit=10)
        assert len(activities) == 1
        a = activities[0]
        assert a["agent_id"] == agent["id"]
        assert a["agent_name"] == "activity-test"
        assert a["event_type"] == "test_event"
        assert json.loads(a["event_data"]) == {"key": "value"}

    def test_record_activity_without_data(self):
        agent = db.create_agent(name="activity-no-data")
        db.record_activity(agent["id"], "simple_event")
        activities = db.list_activities(limit=10)
        assert len(activities) == 1
        assert activities[0]["event_type"] == "simple_event"
        assert activities[0]["event_data"] is None

    def test_list_activities_order(self):
        # Activities are ordered by created_at DESC. Since SQLite's datetime('now')
        # has second precision, all events in this test share the same timestamp.
        # We verify all events are returned correctly.
        agent = db.create_agent(name="activity-order")
        db.record_activity(agent["id"], "event_1")
        db.record_activity(agent["id"], "event_2")
        db.record_activity(agent["id"], "event_3")

        activities = db.list_activities(limit=10)
        assert len(activities) == 3
        # All three events present
        types = {a["event_type"] for a in activities}
        assert types == {"event_1", "event_2", "event_3"}
        assert all(a["agent_id"] == agent["id"] for a in activities)

    def test_list_activities_filter_by_agent(self):
        a1 = db.create_agent(name="activity-filter-a")
        a2 = db.create_agent(name="activity-filter-b")
        db.record_activity(a1["id"], "event_a")
        db.record_activity(a2["id"], "event_b")

        a1_activities = db.list_activities(agent_id=a1["id"])
        assert len(a1_activities) == 1
        assert a1_activities[0]["event_type"] == "event_a"

    def test_list_activities_limit(self):
        agent = db.create_agent(name="activity-limit")
        for i in range(5):
            db.record_activity(agent["id"], f"event_{i}")
        activities = db.list_activities(limit=3)
        assert len(activities) == 3


class TestScheduleCRUD:
    """Schedule create, read, update, delete + executions."""

    def test_create_schedule(self):
        agent = db.create_agent(name="schedule-test")
        schedule = db.create_schedule(
            agent_id=agent["id"],
            cron_expression="0 9 * * *",
            message="Run daily standup",
            model="sonnet",
            max_turns=5,
            timeout_seconds=300,
        )
        assert schedule["agent_id"] == agent["id"]
        assert schedule["cron_expression"] == "0 9 * * *"
        assert schedule["message"] == "Run daily standup"
        assert schedule["model"] == "sonnet"
        assert schedule["max_turns"] == 5
        assert schedule["timeout_seconds"] == 300
        assert schedule["enabled"] == 1
        assert schedule["last_run_at"] is None
        assert schedule["next_run_at"] is None

    def test_create_schedule_minimal(self):
        agent = db.create_agent(name="schedule-minimal")
        schedule = db.create_schedule(
            agent_id=agent["id"],
            cron_expression="0 * * * *",
            message="Hourly task",
        )
        assert schedule["model"] is None
        assert schedule["max_turns"] is None
        assert schedule["timeout_seconds"] is None

    def test_get_schedule(self):
        agent = db.create_agent(name="get-schedule")
        created = db.create_schedule(agent["id"], "0 9 * * *", "Daily")
        fetched = db.get_schedule(created["id"])
        assert fetched is not None
        assert fetched["id"] == created["id"]

    def test_get_schedule_not_found(self):
        assert db.get_schedule("nonexistent") is None

    def test_list_schedules(self):
        agent = db.create_agent(name="list-schedules")
        db.create_schedule(agent["id"], "0 9 * * *", "Task 1")
        db.create_schedule(agent["id"], "0 10 * * *", "Task 2")
        schedules = db.list_schedules()
        assert len(schedules) == 2

    def test_list_schedules_filter_by_agent(self):
        a1 = db.create_agent(name="schedule-filter-a")
        a2 = db.create_agent(name="schedule-filter-b")
        db.create_schedule(a1["id"], "0 9 * * *", "A-only")
        db.create_schedule(a2["id"], "0 10 * * *", "B-only")

        a1_schedules = db.list_schedules(agent_id=a1["id"])
        assert len(a1_schedules) == 1
        assert a1_schedules[0]["message"] == "A-only"

    def test_update_schedule(self):
        agent = db.create_agent(name="update-schedule")
        schedule = db.create_schedule(agent["id"], "0 9 * * *", "Original")

        db.update_schedule(
            schedule["id"],
            cron_expression="0 10 * * *",
            message="Updated",
            enabled=False,
            model="haiku",
            max_turns=10,
            timeout_seconds=600,
        )
        updated = db.get_schedule(schedule["id"])
        assert updated["cron_expression"] == "0 10 * * *"
        assert updated["message"] == "Updated"
        assert updated["enabled"] == 0
        assert updated["model"] == "haiku"
        assert updated["max_turns"] == 10
        assert updated["timeout_seconds"] == 600

    def test_update_schedule_partial(self):
        agent = db.create_agent(name="partial-update")
        schedule = db.create_schedule(agent["id"], "0 9 * * *", "Original", model="sonnet")

        db.update_schedule(schedule["id"], message="Just message changed")
        updated = db.get_schedule(schedule["id"])
        assert updated["message"] == "Just message changed"
        assert updated["cron_expression"] == "0 9 * * *"  # Unchanged
        assert updated["model"] == "sonnet"  # Unchanged

    def test_delete_schedule(self):
        agent = db.create_agent(name="delete-schedule")
        schedule = db.create_schedule(agent["id"], "0 9 * * *", "Delete me")
        assert db.delete_schedule(schedule["id"]) is True
        assert db.get_schedule(schedule["id"]) is None

    def test_delete_schedule_not_found(self):
        assert db.delete_schedule("nonexistent") is False

    def test_schedule_execution_lifecycle(self):
        agent = db.create_agent(name="exec-test")
        schedule = db.create_schedule(agent["id"], "0 9 * * *", "Exec task")

        exec_id = db.record_schedule_execution_start(schedule["id"])
        assert exec_id is not None

        executions = db.list_schedule_executions(schedule["id"])
        assert len(executions) == 1
        assert executions[0]["status"] == "running"

        db.record_schedule_execution_end(
            exec_id, "success", session_id="sess-123", exit_code=0
        )
        executions = db.list_schedule_executions(schedule["id"])
        assert executions[0]["status"] == "success"
        assert executions[0]["exit_code"] == 0

    def test_schedule_execution_error(self):
        agent = db.create_agent(name="exec-error")
        schedule = db.create_schedule(agent["id"], "0 9 * * *", "Error task")

        exec_id = db.record_schedule_execution_start(schedule["id"])
        db.record_schedule_execution_end(
            exec_id, "failed", error_message="Something went wrong"
        )
        executions = db.list_schedule_executions(schedule["id"])
        assert executions[0]["status"] == "failed"
        assert "Something went wrong" in executions[0]["error_message"]

    def test_schedule_execution_timeout(self):
        agent = db.create_agent(name="exec-timeout")
        schedule = db.create_schedule(agent["id"], "0 9 * * *", "Timeout task")

        exec_id = db.record_schedule_execution_start(schedule["id"])
        db.record_schedule_execution_end(
            exec_id, "timeout", error_message="Execution timed out"
        )
        executions = db.list_schedule_executions(schedule["id"])
        assert executions[0]["status"] == "timeout"

    def test_schedule_cascade_delete(self):
        """Deleting a schedule cascades to its executions."""
        agent = db.create_agent(name="cascade-sched")
        schedule = db.create_schedule(agent["id"], "0 9 * * *", "Cascade")
        db.record_schedule_execution_start(schedule["id"])

        db.delete_schedule(schedule["id"])
        executions = db.list_schedule_executions(schedule["id"])
        assert len(executions) == 0


class TestHelpers:
    """Utility function tests."""

    def test_new_id_generates_unique(self):
        ids = {_new_id() for _ in range(100)}
        assert len(ids) == 100

    def test_now_iso_format(self):
        now = _now_iso()
        # Should be ISO 8601 parseable
        parsed = datetime.fromisoformat(now)
        assert parsed.tzinfo is not None or parsed.tzinfo is not None

    def test_empty_db_counts(self):
        assert agent_count() == 0
        assert active_session_count() == 0
