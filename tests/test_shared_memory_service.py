"""
Tests for shared memory service (knowledge pool).
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile

from pi_orchestrator.services.shared_memory_service import (
    SHARED_MEMORY_DIR,
    write_fact,
    read_context,
    deduplicate_facts,
    cleanup_expired_facts,
    delete_agent_facts,
)


class TestWriteAndRead:
    """Write facts and read them back."""

    def setup_method(self):
        self._orig_dir = str(SHARED_MEMORY_DIR)
        self._tmp_dir = tempfile.mkdtemp(prefix="sop-shared-mem-test-")
        import pi_orchestrator.services.shared_memory_service as sms
        sms.SHARED_MEMORY_DIR = type(SHARED_MEMORY_DIR)(self._tmp_dir)

    def teardown_method(self):
        import pi_orchestrator.services.shared_memory_service as sms
        sms.SHARED_MEMORY_DIR = type(SHARED_MEMORY_DIR)(self._orig_dir)
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def test_write_and_read_back(self):
        write_fact("agent-a", "test-tag", "Database has users table", "static")
        context = read_context(["test-tag"], max_age_hours=9999)
        assert "users table" in context.lower()

    def test_multiple_tags(self):
        write_fact("agent-a", "frontend", "React 18 features", "dynamic")
        write_fact("agent-b", "backend", "FastAPI routes", "dynamic")
        context = read_context(["frontend", "backend"], max_age_hours=9999)
        assert "React" in context
        assert "FastAPI" in context

    def test_no_match_returns_empty(self):
        context = read_context(["nonexistent-tag"], max_age_hours=9999)
        assert context == ""


class TestDeduplication:
    """Facts should be deduplicated: static wins over dynamic."""

    def setup_method(self):
        self._orig_dir = str(SHARED_MEMORY_DIR)
        self._tmp_dir = tempfile.mkdtemp(prefix="sop-dedup-test-")
        import pi_orchestrator.services.shared_memory_service as sms
        sms.SHARED_MEMORY_DIR = type(SHARED_MEMORY_DIR)(self._tmp_dir)

    def teardown_method(self):
        import pi_orchestrator.services.shared_memory_service as sms
        sms.SHARED_MEMORY_DIR = type(SHARED_MEMORY_DIR)(self._orig_dir)
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def test_dedup_same_fact(self):
        write_fact("agent-a", "dedup-test", "Same fact", "static")
        write_fact("agent-b", "dedup-test", "Same fact", "dynamic")
        context = read_context(["dedup-test"], max_age_hours=9999)
        assert context.lower().count("same fact") == 1

    def test_dedup_preserves_unique(self):
        write_fact("agent-a", "dedup-test", "Fact A", "static")
        write_fact("agent-b", "dedup-test", "Fact B", "dynamic")
        context = read_context(["dedup-test"], max_age_hours=9999)
        assert "Fact A" in context
        assert "Fact B" in context


class TestCleanup:
    """Expired facts should be removable."""

    def setup_method(self):
        self._orig_dir = str(SHARED_MEMORY_DIR)
        self._tmp_dir = tempfile.mkdtemp(prefix="sop-cleanup-test-")
        import pi_orchestrator.services.shared_memory_service as sms
        sms.SHARED_MEMORY_DIR = type(SHARED_MEMORY_DIR)(self._tmp_dir)

    def teardown_method(self):
        import pi_orchestrator.services.shared_memory_service as sms
        sms.SHARED_MEMORY_DIR = type(SHARED_MEMORY_DIR)(self._orig_dir)
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def test_cleanup_expired(self):
        write_fact("agent-a", "cleanup-test", "Fresh fact", "dynamic")
        context_before = read_context(["cleanup-test"], max_age_hours=9999)
        assert "Fresh fact" in context_before
        purged = cleanup_expired_facts(max_age_days=0)  # Everything expired
        assert purged >= 1
        context_after = read_context(["cleanup-test"], max_age_hours=9999)
        assert "Fresh fact" not in context_after

    def test_delete_agent_facts(self):
        write_fact("agent-to-delete", "del-test", "Fact from agent", "dynamic")
        deleted = delete_agent_facts("agent-to-delete")
        assert deleted >= 1
        context = read_context(["del-test"], max_age_hours=9999)
        assert "Fact from agent" not in context
