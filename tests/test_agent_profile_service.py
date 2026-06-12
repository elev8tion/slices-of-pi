"""
Tests for agent profile service.
"""

from __future__ import annotations

from pi_orchestrator import database as db
from pi_orchestrator.services.agent_profile_service import (
    format_profile_as_prompt,
    extract_session_summary,
)


class TestFormatProfileAsPrompt:
    """format_profile_as_prompt() formats agent profiles for prompt injection."""

    def test_empty_for_nonexistent_agent(self):
        result = format_profile_as_prompt("nonexistent")
        assert result == ""

    def test_empty_for_no_profile_data(self):
        agent = db.create_agent("test-empty-profile")
        try:
            result = format_profile_as_prompt(agent["id"])
            assert result == ""
        finally:
            db.delete_agent(agent["id"])

    def test_includes_static_facts(self):
        agent = db.create_agent("test-static-profile")
        try:
            profile = db.get_agent_profile(agent["id"])
            profile["static"] = {"role": "code reviewer", "lang": "Python"}
            db.update_agent_profile(agent["id"], profile)
            result = format_profile_as_prompt(agent["id"])
            assert "code reviewer" in result
            assert "Python" in result
        finally:
            db.delete_agent(agent["id"])

    def test_includes_dynamic_facts(self):
        agent = db.create_agent("test-dynamic-profile")
        try:
            db.append_agent_memory(agent["id"], "Working on auth middleware")
            result = format_profile_as_prompt(agent["id"])
            assert "auth middleware" in result
        finally:
            db.delete_agent(agent["id"])

    def test_caps_dynamic_at_5_entries(self):
        agent = db.create_agent("test-cap-profile")
        try:
            for i in range(10):
                db.append_agent_memory(agent["id"], f"Fact number {i}")
            profile = db.get_agent_profile(agent["id"])
            assert len(profile["dynamic"]) == 10, "Should store up to 50"
            result = format_profile_as_prompt(agent["id"])
            assert "Fact number 9" in result
        finally:
            db.delete_agent(agent["id"])


class TestExtractSessionSummary:
    """extract_session_summary() creates summary facts from sessions."""

    def test_creates_summary_with_session_prefix(self):
        summary = extract_session_summary("agent-1", "Fix the auth middleware", "sess_abc123")
        assert "Session sess_abc" in summary
        assert "auth" in summary

    def test_truncates_long_prompts(self):
        long_prompt = "x" * 200
        summary = extract_session_summary("agent-1", long_prompt, "sess_abc")
        assert len(summary) < 150  # Truncated
