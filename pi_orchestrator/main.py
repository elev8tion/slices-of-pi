"""
Pi Orchestrator — manage multiple pi coding agents.

FastAPI application with lifespan management. No Docker, no Redis,
no multi-tenant auth. Single-user, bound to localhost.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from .config import CORS_ORIGINS, HOST, PORT, ensure_directories
from .database import init_db, agent_count, active_session_count, close_connections
from .services.event_bus import event_bus
from .services.pi_session_service import kill_all

try:
    from .services.schedule_service import scheduler
except ImportError:
    scheduler = None

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
from .routers.teams import router as teams_router

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Lifespan
# ═══════════════════════════════════════════════════════════════════


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown."""
    # ── Startup ──────────────────────────────────────────────────
    ensure_directories()
    init_db()

    await event_bus.start()
    logger.info("Event bus started (in-process)")

    if scheduler:
        await scheduler.start()
        logger.info("Scheduler started")
    else:
        logger.info("Scheduler disabled (apscheduler not installed)")

    logger.info(f"Pi Orchestrator starting on {HOST}:{PORT}")

    yield  # App runs here ────────────────────────────────────────

    # ── Shutdown ─────────────────────────────────────────────────
    logger.info("Pi Orchestrator shutting down...")
    await kill_all()
    if scheduler:
        await scheduler.stop()
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
app.include_router(teams_router)

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
