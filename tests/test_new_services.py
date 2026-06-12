"""
Tests for agent_profile_service, shared_memory_service, and connector services.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from datetime import datetime, timezone

import pytest

from pi_orchestrator import database as db
from pi_orchestrator.database import _get_conn


# ═══════════════════════════════════════════════════════════════════
# Agent Profile Service
# ═══════════════════════════════════════════════════════════════════


class TestAgentProfileService:
    """Tests for agent_profile_service.py."""

    def test_format_profile_empty(self):
        from pi_orchestrator.services.agent_profile_service import format_profile_as_prompt
        result = format_profile_as_prompt("nonexistent")
        assert result == "", f"Expected empty string for nonexistent agent, got {repr(result)}"

    def test_format_profile_with_data(self):
        from pi_orchestrator.services.agent_profile_service import format_profile_as_prompt
        conn = _get_conn()
        conn.execute("DELETE FROM agents WHERE name = 'prof-test'")
        conn.commit()
        agent = db.create_agent("prof-test")
        db.append_agent_memory(agent["id"], "Working on auth", "dynamic")
        result = format_profile_as_prompt(agent["id"])
        assert "Working on auth" in result, f"Expected fact in profile, got: {result}"
        assert "## Recent Context" in result, f"Expected section header, got: {result}"
        db.delete_agent(agent["id"])
        conn.commit()

    def test_extract_session_summary(self):
        from pi_orchestrator.services.agent_profile_service import extract_session_summary
        result = extract_session_summary("test-agent", "Fix the authentication middleware", "sess_abc123")
        assert "authentication" in result, f"Expected summary to contain auth text, got: {result}"
        assert "Session" in result and "authentication" in result, f"Expected summary with Session prefix, got: {result}"

    def test_append_agent_memory_dedup(self):
        conn = _get_conn()
        conn.execute("DELETE FROM agents WHERE name = 'dedup-test'")
        conn.commit()
        agent = db.create_agent("dedup-test")
        db.append_agent_memory(agent["id"], "Same fact", "dynamic")
        db.append_agent_memory(agent["id"], "Same fact", "dynamic")  # duplicate
        profile = db.get_agent_profile(agent["id"])
        assert len(profile["dynamic"]) == 1, f"Expected 1 (deduped), got {len(profile['dynamic'])}"
        db.delete_agent(agent["id"])
        conn.commit()

    def test_append_agent_memory_cap(self):
        conn = _get_conn()
        conn.execute("DELETE FROM agents WHERE name = 'cap-test'")
        conn.commit()
        agent = db.create_agent("cap-test")
        for i in range(55):
            db.append_agent_memory(agent["id"], f"Fact #{i}", "dynamic")
        profile = db.get_agent_profile(agent["id"])
        assert len(profile["dynamic"]) == 50, f"Expected cap at 50, got {len(profile['dynamic'])}"
        assert "Fact #0" not in profile["dynamic"], "Oldest should be rotated out"
        assert "Fact #54" in profile["dynamic"], "Newest should be present"
        db.delete_agent(agent["id"])
        conn.commit()


# ═══════════════════════════════════════════════════════════════════
# Shared Memory Service
# ═══════════════════════════════════════════════════════════════════


class TestSharedMemoryService:
    """Tests for shared_memory_service.py."""

    def setup_method(self):
        from pi_orchestrator.services.shared_memory_service import SHARED_MEMORY_DIR
        self.test_tag = "test-tag-" + datetime.now().strftime("%s")
        self.test_dir = SHARED_MEMORY_DIR / self.test_tag

    def teardown_method(self):
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(str(self.test_dir))

    def test_write_and_read_fact(self):
        from pi_orchestrator.services.shared_memory_service import write_fact, read_context
        write_fact("agent-a", self.test_tag, "Database has users table", "static")
        context = read_context([self.test_tag], max_age_hours=9999)
        assert "users table" in context.lower(), f"Expected fact in context, got: {context}"
        assert "agent-a" in context, f"Expected agent prefix, got: {context}"

    def test_deduplicate_facts(self):
        from pi_orchestrator.services.shared_memory_service import write_fact, read_context
        write_fact("agent-a", self.test_tag, "Duplicate fact", "static")
        write_fact("agent-b", self.test_tag, "Duplicate fact", "dynamic")
        context = read_context([self.test_tag], max_age_hours=9999)
        assert context.lower().count("duplicate fact") == 1, "Dedup should collapse to 1"

    def test_empty_tag_returns_empty(self):
        from pi_orchestrator.services.shared_memory_service import read_context
        context = read_context(["nonexistent-tag-xyz"], max_age_hours=9999)
        assert context == "", f"Expected empty for nonexistent tag, got: {repr(context)}"

    def test_cleanup_expired_facts(self):
        from pi_orchestrator.services.shared_memory_service import write_fact, cleanup_expired_facts, SHARED_MEMORY_DIR
        write_fact("agent-a", self.test_tag, "Old fact", "dynamic")
        purged = cleanup_expired_facts(max_age_days=0)  # 0 days = everything expired
        assert purged > 0, f"Expected >0 purged, got {purged}"

    def test_delete_agent_facts(self):
        from pi_orchestrator.services.shared_memory_service import write_fact, delete_agent_facts, read_context
        write_fact("delete-me-agent", self.test_tag, "To be deleted", "dynamic")
        deleted = delete_agent_facts("delete-me-agent")
        assert deleted > 0, f"Expected >0 deleted, got {deleted}"
        context = read_context([self.test_tag], max_age_hours=9999)
        assert "To be deleted" not in context, "Deleted fact should not appear"


# ═══════════════════════════════════════════════════════════════════
# Connector Registry
# ═══════════════════════════════════════════════════════════════════


class TestConnectorRegistry:
    """Tests for connector registry and plugins."""

    def test_webhook_connector_loaded(self):
        from pi_orchestrator.services.connectors.registry import get, list_available
        webhook = get("webhook")
        assert webhook is not None, "Webhook connector should be available"
        assert webhook.provider == "webhook"
        assert webhook.display_name == "Incoming Webhook"

    def test_webhook_authorize_valid(self):
        from pi_orchestrator.services.connectors.registry import get
        import asyncio
        webhook = get("webhook")
        result = asyncio.run(webhook.authorize({"token": "valid-token-123"}))
        assert result == {"token": "valid-token-123"}

    def test_webhook_authorize_short_token(self):
        from pi_orchestrator.services.connectors.registry import get
        import asyncio
        webhook = get("webhook")
        with pytest.raises(ValueError, match="at least 8 characters"):
            asyncio.run(webhook.authorize({"token": "short"}))

    def test_webhook_verify_valid(self):
        from pi_orchestrator.services.connectors.registry import get
        import asyncio
        webhook = get("webhook")
        assert asyncio.run(webhook.verify({"token": "valid"}))

    def test_webhook_verify_empty(self):
        from pi_orchestrator.services.connectors.registry import get
        import asyncio
        webhook = get("webhook")
        assert not asyncio.run(webhook.verify({}))

    def test_list_available(self):
        from pi_orchestrator.services.connectors.registry import list_available
        available = list_available()
        assert "webhook" in available, "Webhook should be in available list"
        assert available["webhook"]["display_name"] == "Incoming Webhook"


# ═══════════════════════════════════════════════════════════════════
# Connector CRUD
# ═══════════════════════════════════════════════════════════════════


class TestConnectorDB:
    """Tests for connector database CRUD."""

    def setup_method(self):
        conn = _get_conn()
        conn.execute("DELETE FROM agents WHERE name LIKE 'conn-test-%'")
        conn.execute("DELETE FROM connectors WHERE provider = 'webhook'")
        conn.commit()
        self.agent = db.create_agent("conn-test-agent")

    def teardown_method(self):
        conn = _get_conn()
        if self.agent:
            db.delete_agent(self.agent["id"])
        conn.commit()

    def test_create_connector(self):
        c = db.create_connector(self.agent["id"], "webhook", "Test Connector", {"token": "secret-12345"}, ["default"])
        assert c is not None
        assert c["provider"] == "webhook"
        assert c["label"] == "Test Connector"
        assert c["auth_state"] == "••••••••"
        db.delete_connector(c["id"])

    def test_get_connector(self):
        c = db.create_connector(self.agent["id"], "webhook", "Get Test", {"token": "get-secret"}, ["default"])
        fetched = db.get_connector(c["id"])
        assert fetched is not None
        assert fetched["auth_state"] == {"token": "get-secret"}
        db.delete_connector(c["id"])

    def test_list_connectors(self):
        c1 = db.create_connector(self.agent["id"], "webhook", "List Test 1", {"token": "t1"}, ["default"])
        c2 = db.create_connector(self.agent["id"], "webhook", "List Test 2", {"token": "t2"}, ["default"])
        all_c = db.list_connectors()
        assert len(all_c) >= 2
        agent_c = db.list_connectors(agent_id=self.agent["id"])
        assert len(agent_c) >= 2
        db.delete_connector(c1["id"])
        db.delete_connector(c2["id"])

    def test_delete_connector(self):
        c = db.create_connector(self.agent["id"], "webhook", "Delete Test", {"token": "del"}, ["default"])
        assert db.delete_connector(c["id"])
        assert db.get_connector(c["id"]) is None
