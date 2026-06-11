"""
Logging configuration for Pi Orchestrator.

Two handlers:
  - Console (stream) handler     → INFO+
  - Rotating file handler         → DEBUG+  at ~/.pi/agent/orchestrator.log
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

_LOG_DIR = Path.home() / ".pi" / "agent"
_LOG_FILE = _LOG_DIR / "orchestrator.log"
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
_BACKUP_COUNT = 3

_initialised = False


def setup_logging() -> None:
    """Configure the root logger with console (INFO) and file (DEBUG) handlers.

    Safe to call multiple times — only configures on the first invocation.
    """
    global _initialised
    if _initialised:
        return
    _initialised = True

    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()

    # ── Console handler ──────────────────────────────────────────
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root.addHandler(console)

    # ── Rotating file handler ────────────────────────────────────
    file_handler = logging.handlers.RotatingFileHandler(
        filename=str(_LOG_FILE),
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root.addHandler(file_handler)

    root.setLevel(logging.DEBUG)  # Root at DEBUG so both handlers get their level's feed

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)  # quieter access logs
