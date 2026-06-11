"""
Shared test fixtures for Pi Orchestrator tests.

Sets up:
  - Temporary SQLite database for each test session
  - Mocked pi binary (no real subprocess calls)
  - FastAPI test app with all routers registered
  - httpx.AsyncClient for API testing
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Optional
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

# ── Override paths BEFORE any pi_orchestrator imports ────────────
# We patch at the module level so database.py uses a temp DB.
# This must happen before pi_orchestrator is imported.

_tmpdir = tempfile.mkdtemp(prefix="pi_orch_test_")
os.environ["PI_ORCHESTRATOR_HOST"] = "127.0.0.1"
os.environ["PI_ORCHESTRATOR_PORT"] = "0"  # random port for tests

_test_db_path = Path(_tmpdir) / "test_orchestrator.db"
_test_sessions_dir = Path(_tmpdir) / "sessions" / "managed"
_test_sessions_dir.mkdir(parents=True, exist_ok=True)
_test_scheduled_sessions_dir = Path(_tmpdir) / "sessions" / "scheduled"
_test_scheduled_sessions_dir.mkdir(parents=True, exist_ok=True)

# Patch config paths before any module imports them
import pi_orchestrator.config as cfg_mod

cfg_mod.DATABASE_PATH = _test_db_path
cfg_mod.PI_MANAGED_SESSIONS_DIR = _test_sessions_dir
cfg_mod.PI_SCHEDULED_SESSIONS_DIR = _test_scheduled_sessions_dir
cfg_mod.PI_AGENT_DIR = Path(_tmpdir)
cfg_mod.PI_AGENTS_CONFIG_DIR = Path(_tmpdir) / "agents"
cfg_mod.PI_AGENTS_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
cfg_mod.PI_SKILLS_DIR = Path(_tmpdir) / "skills"
cfg_mod.PI_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
cfg_mod.PI_EXTENSIONS_DIR = Path(_tmpdir) / "extensions"
cfg_mod.PI_EXTENSIONS_DIR.mkdir(parents=True, exist_ok=True)
cfg_mod.PI_SESSIONS_DIR = Path(_tmpdir) / "sessions"
cfg_mod.PI_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
cfg_mod.PI_HOME = Path(_tmpdir)

# Now it's safe to import the rest
from pi_orchestrator import database as db
from pi_orchestrator.database import init_db, _local, _get_conn, close_connections
from pi_orchestrator.services.event_bus import event_bus
from pi_orchestrator.services.pi_session_service import (
    _running as _proc_registry,
    _session_dir as _svc_session_dir,
)


# ═══════════════════════════════════════════════════════════════════
# Session-scoped: DB + event bus setup/teardown
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """Initialize the test database once per session."""
    # Reset thread-local connection so it picks up the test DB path
    if hasattr(_local, "conn") and _local.conn is not None:
        _local.conn.close()
        _local.conn = None
    init_db()
    yield
    close_connections()


@pytest.fixture(autouse=True)
def clear_db():
    """Clear all tables between tests and clean up test directories."""
    conn = _get_conn()
    tables = ["schedule_executions", "schedules", "activities", "sessions", "agents", "mcp_keys", "settings"]
    for table in tables:
        conn.execute(f"DELETE FROM {table}")
    conn.commit()
    # Clear process registry
    _proc_registry.clear()
    # Clean up filesystem test artifacts
    import shutil
    for d in [cfg_mod.PI_SKILLS_DIR, cfg_mod.PI_EXTENSIONS_DIR, cfg_mod.PI_AGENTS_CONFIG_DIR]:
        if d.exists():
            for child in list(d.iterdir()):
                if child.is_file():
                    child.unlink()
                elif child.is_dir():
                    shutil.rmtree(str(child))
    yield


@pytest.fixture(autouse=True)
def clear_event_bus():
    """Remove all subscribers between tests and ensure the bus is running."""
    event_bus._subscribers.clear()
    event_bus._queues.clear()
    event_bus._running = True
    yield


# ═══════════════════════════════════════════════════════════════════
# Mock pi binary — never actually invoke pi
# ═══════════════════════════════════════════════════════════════════


class _MockStreamReader:
    """Simulates an asyncio StreamReader for a single stream (stdout or stderr)."""

    def __init__(self, lines: list[str]):
        self._buffer = b"".join(f"{l}\n".encode() for l in lines)
        self._pos = 0
        self._eof = False
        self._killed = False

    async def readline(self) -> bytes:
        if self._killed:
            return b""
        if self._pos >= len(self._buffer):
            self._eof = True
            return b""
        end = self._buffer.find(b"\n", self._pos)
        if end == -1:
            line = self._buffer[self._pos:]
            self._pos = len(self._buffer)
        else:
            line = self._buffer[self._pos : end + 1]
            self._pos = end + 1
        return line

    def at_eof(self):
        return self._eof

    def kill(self):
        self._killed = True


class MockPiProcess:
    """Simulates an asyncio subprocess for the pi binary."""

    def __init__(self, returncode: int = 0, stdout_lines: list[str] | None = None):
        self.returncode = returncode
        self._stdout = _MockStreamReader(stdout_lines or [])
        self._stderr = _MockStreamReader([])
        self._killed = False

    @property
    def stdout(self):
        return self._stdout

    @property
    def stderr(self):
        return self._stderr

    def terminate(self):
        self._killed = True
        self._stdout.kill()
        self._stderr.kill()

    def kill(self):
        self._killed = True
        self._stdout.kill()
        self._stderr.kill()

    async def wait(self):
        return self.returncode

    async def communicate(self):
        return self._stdout._buffer, self._stderr._buffer


@pytest.fixture
def mock_pi_binary():
    """Fixture that patches asyncio.create_subprocess_exec to return MockPiProcess.

    The default mock returns a valid JSONL response for a simple chat turn.
    Override with `mock_pi_binary.return_value` for custom responses.
    """
    default_jsonl = [
        json.dumps({"type": "turn_end"}),
        json.dumps({"type": "message_end", "message": {"role": "assistant", "usage": {"input": 10, "output": 50}}}),
    ]

    mock_process = MockPiProcess(returncode=0, stdout_lines=default_jsonl)

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock:
        mock.return_value = mock_process
        yield mock


@pytest.fixture
def mock_pi_binary_stream():
    """Mock pi binary that streams text_delta chunks then completes."""
    lines = [
        json.dumps({"type": "message_start", "message": {"role": "assistant", "content": [{"type": "text", "text": ""}]}}),
        json.dumps({"type": "message_update", "assistantMessageEvent": {"type": "text_delta", "delta": "Hello"}}),
        json.dumps({"type": "message_update", "assistantMessageEvent": {"type": "text_delta", "delta": " world"}}),
        json.dumps({"type": "turn_end"}),
        json.dumps({"type": "message_end", "message": {"role": "assistant", "usage": {"input": 10, "output": 50}}}),
    ]
    mock_process = MockPiProcess(returncode=0, stdout_lines=lines)
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock:
        mock.return_value = mock_process
        yield mock


@pytest.fixture
def mock_pi_binary_tool_call():
    """Mock pi binary that issues a tool call then responds."""
    lines = [
        json.dumps({"type": "message_start", "message": {"role": "assistant", "content": [{"type": "text", "text": ""}]}}),
        json.dumps({"type": "tool_call", "tool_name": "read", "input": {"path": "/tmp/test.txt"}}),
        json.dumps({"type": "tool_result", "tool_name": "read", "result": "file contents"}),
        json.dumps({"type": "message_update", "assistantMessageEvent": {"type": "text_delta", "delta": "Here's the file"}}),
        json.dumps({"type": "turn_end"}),
        json.dumps({"type": "message_end", "message": {"role": "assistant", "usage": {"input": 20, "output": 80}}}),
    ]
    mock_process = MockPiProcess(returncode=0, stdout_lines=lines)
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock:
        mock.return_value = mock_process
        yield mock


@pytest.fixture
def mock_pi_binary_timeout():
    """Mock pi binary that hangs to test timeouts."""
    mock_process = MockPiProcess(returncode=0, stdout_lines=[])

    async def _slow_readline():
        await asyncio.sleep(999)  # Simulate hang
        return b""

    mock_process._stdout.readline = _slow_readline

    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock:
        mock.return_value = mock_process
        yield mock


# ═══════════════════════════════════════════════════════════════════
# Test FastAPI App
# ═══════════════════════════════════════════════════════════════════


@asynccontextmanager
async def test_lifespan(app: FastAPI):
    """No-op lifespan for testing — no scheduler, no event bus start."""
    # Don't start the real event bus or scheduler
    # Just make sure directories exist
    yield


def _build_test_app() -> FastAPI:
    """Build a FastAPI app identical to the real one but with test lifespan."""
    from fastapi.middleware.cors import CORSMiddleware

    from pi_orchestrator.config import CORS_ORIGINS

    app = FastAPI(
        title="Pi Orchestrator — Test",
        description="Test instance",
        version="0.1.0",
        lifespan=test_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register all routers
    from pi_orchestrator.routers.events import router as events_router
    from pi_orchestrator.routers.agents import router as agents_router
    from pi_orchestrator.routers.chat import router as chat_router
    from pi_orchestrator.routers.sessions import router as sessions_router
    from pi_orchestrator.routers.activities import router as activities_router
    from pi_orchestrator.routers.skills import router as skills_router
    from pi_orchestrator.routers.extensions import router as extensions_router
    from pi_orchestrator.routers.schedules import router as schedules_router
    from pi_orchestrator.routers.templates import router as templates_router
    from pi_orchestrator.routers.coms import router as coms_router
    from pi_orchestrator.routers.teams import router as teams_router

    app.include_router(events_router)
    app.include_router(agents_router)
    app.include_router(chat_router)
    app.include_router(sessions_router)
    app.include_router(activities_router)
    app.include_router(skills_router)
    app.include_router(extensions_router)
    app.include_router(schedules_router)
    app.include_router(templates_router)
    app.include_router(coms_router)
    app.include_router(teams_router)

    # Health endpoint
    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "version": "0.1.0",
            "agent_count": db.agent_count(),
            "active_session_count": db.active_session_count(),
        }

    return app


@pytest.fixture(scope="session")
def test_app():
    """Build the test FastAPI application once."""
    return _build_test_app()


@pytest.fixture
async def async_client(test_app) -> AsyncIterator[AsyncClient]:
    """Provide an httpx AsyncClient connected to the test app."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ═══════════════════════════════════════════════════════════════════
# Helper: create a test agent in the DB
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def test_agent() -> dict:
    """Create a basic agent in the database for testing."""
    agent = db.create_agent(
        name="test-agent",
        model="sonnet",
        persona="developer",
        tools=["read", "bash", "write"],
        skills=["python", "shell"],
        system_prompt="You are a helpful coding assistant.",
    )
    return agent


@pytest.fixture
def test_session(test_agent) -> dict:
    """Create a test session in the database."""
    session = db.create_session(
        agent_id=test_agent["id"],
        agent_name=test_agent["name"],
        session_file=str(_test_sessions_dir / f"{test_agent['name']}_test.jsonl"),
        model="sonnet",
    )
    return session
