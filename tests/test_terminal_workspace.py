"""Track B2 — terminal workspace uses agent name (same as chat/files)."""

from __future__ import annotations

from pi_orchestrator import database as db
from pi_orchestrator.config import PI_MANAGED_SESSIONS_DIR
from pi_orchestrator.routers.terminal import _agent_workspace


class TestTerminalWorkspace:
    def test_workspace_uses_agent_name(self):
        agent = db.create_agent("term-ws-agent", model="", tools=["read"])
        path = _agent_workspace(agent["id"])
        assert path == PI_MANAGED_SESSIONS_DIR / "term-ws-agent"
        assert agent["id"] not in str(path) or path.name == "term-ws-agent"

    def test_missing_agent_falls_back_to_id(self):
        path = _agent_workspace("nonexistent-agent-id-xyz")
        assert path == PI_MANAGED_SESSIONS_DIR / "nonexistent-agent-id-xyz"
