"""
Pi Orchestrator — manage multiple pi coding agents.

FastAPI application with lifespan management. No Docker, no Redis,
no multi-tenant auth. Single-user, bound to localhost.
"""

from __future__ import annotations

import logging
import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .config import (
    CORS_ORIGINS, HOST, PORT, PI_BINARY,
    PI_AGENT_DIR, PI_SESSIONS_DIR, PI_MANAGED_SESSIONS_DIR,
    PI_SKILLS_DIR, PI_EXTENSIONS_DIR, PI_AGENTS_CONFIG_DIR,
    ensure_directories,
)
from .database import init_db, agent_count, active_session_count, close_connections
from .logging_config import setup_logging
from .services.event_bus import event_bus
from .services.pi_session_service import kill_all

try:
    from .services.schedule_service import scheduler
except ImportError:
    scheduler = None

try:
    from .services.cleanup_service import cleanup
except ImportError:
    cleanup = None

# Routers
from .routers.events import router as events_router
from .routers.agents import router as agents_router
from .routers.chat import router as chat_router
from .routers.sessions import router as sessions_router
from .routers.activities import router as activities_router
from .routers.skills import router as skills_router
from .routers.extensions import router as extensions_router
from .routers.schedules import router as schedules_router
from .routers.templates import router as templates_router
from .routers.coms import router as coms_router
from .routers.connectors import router as connectors_router
from .routers.teams import router as teams_router
from .routers.system import router as system_router
from .routers.terminal import router as terminal_router
from .routers.console import router as console_router
from .routers.tags import router as tags_router
from .routers.telemetry import router as telemetry_router
from .routers.credentials import router as credentials_router
from .routers.operator_queue import router as operator_queue_router
from .routers.files import router as files_router
from .routers.git import router as git_router
from .routers.voice import router as voice_router
from .routers.settings_router import router as settings_router
from .routers.auth import router as auth_router
from .routers.sharing import router as sharing_router
from .routers.users import router as users_router
from .routers.ws_tickets import router as ws_tickets_router
from .routers.audit_log import router as audit_log_router
from .routers.ops import router as ops_router
from .routers.mcp_keys import router as mcp_keys_router

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Lifespan
# ═══════════════════════════════════════════════════════════════════


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown."""
    # ── Startup ──────────────────────────────────────────────────
    setup_logging()
    ensure_directories()

    # Check pi binary
    pi_path = shutil.which(PI_BINARY)
    if pi_path:
        logger.info(f"Pi binary found: {pi_path}")
    else:
        if Path(PI_BINARY).exists():
            logger.info(f"Pi binary found at explicit path: {PI_BINARY}")
        else:
            logger.warning(f"PI_BINARY '{PI_BINARY}' not found — session creation will fail")

    _check_dir(PI_AGENT_DIR, "agent directory")
    _check_dir(PI_SESSIONS_DIR, "sessions directory")
    _check_dir(PI_MANAGED_SESSIONS_DIR, "managed sessions")
    _check_dir(PI_SKILLS_DIR, "skills directory")
    _check_dir(PI_EXTENSIONS_DIR, "extensions directory")
    _check_dir(PI_AGENTS_CONFIG_DIR, "agents config")

    init_db()

    await event_bus.start()
    logger.info("Event bus started (in-process)")

    if scheduler:
        await scheduler.start()
        logger.info("Scheduler started")
    else:
        logger.info("Scheduler disabled (apscheduler not installed)")

    if cleanup:
        await cleanup.start()
        logger.info("Cleanup service started")
    else:
        logger.info("Cleanup service disabled")

    logger.info(f"Pi Orchestrator starting on {HOST}:{PORT}")

    yield

    # ── Shutdown ─────────────────────────────────────────────────
    logger.info("Pi Orchestrator shutting down...")
    await kill_all()
    if scheduler:
        await scheduler.stop()
    if cleanup:
        await cleanup.stop()
    await event_bus.stop()
    close_connections()
    logger.info("Pi Orchestrator stopped")


# ═══════════════════════════════════════════════════════════════════
# App
# ═══════════════════════════════════════════════════════════════════

app = FastAPI(
    title="Pi Orchestrator",
    description="Manage multiple pi coding agents — API server and dashboard backend",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow dashboard dev server on port 5173
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
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
app.include_router(connectors_router)
app.include_router(teams_router)
app.include_router(system_router)
app.include_router(terminal_router)
app.include_router(console_router)
app.include_router(tags_router)
app.include_router(telemetry_router)
app.include_router(credentials_router)
app.include_router(operator_queue_router)
app.include_router(files_router)
app.include_router(git_router)
app.include_router(voice_router)
app.include_router(settings_router)
app.include_router(auth_router)
app.include_router(sharing_router)
app.include_router(users_router)
app.include_router(ws_tickets_router)
app.include_router(audit_log_router)
app.include_router(ops_router)
app.include_router(mcp_keys_router)

# ── Dashboard serving (production mode) ──────────────────────────

DASHBOARD_DIST = Path(__file__).resolve().parent.parent / "dashboard" / "dist"
_serve_dashboard = False


def enable_dashboard_serve() -> None:
    """Serve the built dashboard alongside the API.

    Static assets are mounted at /assets/. A catch-all route serves
    index.html for SPA client-side routing. The catch-all is registered
    LAST so API routes take precedence.
    """
    global _serve_dashboard
    _serve_dashboard = True

    assets_dir = DASHBOARD_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="dashboard_assets")

    # Catch-all for SPA routing — registered last, lowest priority
    @app.get("/{path:path}")
    async def spa_fallback(request: Request, path: str):
        file_path = DASHBOARD_DIST / path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(DASHBOARD_DIST / "index.html")

    # Root route
    @app.get("/")
    async def dashboard_root():
        return FileResponse(DASHBOARD_DIST / "index.html")

# ── Health ───────────────────────────────────────────────────────


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "0.1.0",
        "agent_count": agent_count(),
        "active_session_count": active_session_count(),
    }


# ═══════════════════════════════════════════════════════════════════
# Entry Point
# ═══════════════════════════════════════════════════════════════════

def _check_dir(path: Path, label: str) -> None:
    if not path.exists():
        logger.warning(f"{label} not found: {path}")


if __name__ == "__main__":
    import sys, uvicorn

    if "--serve-dashboard" in sys.argv and DASHBOARD_DIST.exists():
        enable_dashboard_serve()
        print(f"Serving dashboard from {DASHBOARD_DIST}")

    uvicorn.run(
        "pi_orchestrator.main:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info",
    )
