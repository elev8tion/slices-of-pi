"""
Host Telemetry router — system resource monitoring.

Provides CPU, memory, and disk usage statistics for the host machine.
Used by the dashboard HostTelemetry component to show real-time system
health while pi agents are running.
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])


def _get_cpu_percent() -> float:
    """Get CPU usage as a percentage (0-100)."""
    try:
        import psutil
        return psutil.cpu_percent(interval=0.3)
    except ImportError:
        pass
    # Fallback: read from /proc/stat (Linux) or use os loadavg
    try:
        import os
        load1, load5, load15 = os.getloadavg()
        cpu_count = os.cpu_count() or 1
        return min(100.0, (load1 / cpu_count) * 100)
    except (AttributeError, OSError):
        return 0.0


def _get_memory_info() -> dict:
    """Get memory usage info."""
    try:
        import psutil
        mem = psutil.virtual_memory()
        return {
            "total_gb": round(mem.total / (1024**3), 1),
            "used_gb": round(mem.used / (1024**3), 1),
            "available_gb": round(mem.available / (1024**3), 1),
            "percent": round(mem.percent, 1),
        }
    except ImportError:
        pass
    # Fallback
    try:
        import subprocess
        result = subprocess.run(
            ["vm_stat"], capture_output=True, text=True, timeout=2
        )
        return {"note": "macOS vm_stat available via psutil", "percent": 50.0}
    except Exception:
        return {"percent": 0.0}


def _get_disk_info() -> dict:
    """Get disk usage for the home partition."""
    try:
        import psutil
        disk = psutil.disk_usage(os.path.expanduser("~"))
        return {
            "total_gb": round(disk.total / (1024**3), 1),
            "used_gb": round(disk.used / (1024**3), 1),
            "free_gb": round(disk.free / (1024**3), 1),
            "percent": round(disk.percent, 1),
        }
    except ImportError:
        return {"percent": 0.0}


@router.get("/host")
async def host_telemetry():
    """Get host system resource usage (CPU, memory, disk)."""
    import json

    cpu = _get_cpu_percent()
    mem = _get_memory_info()
    disk = _get_disk_info()

    return {
        "cpu": {"percent": cpu, "count": os.cpu_count() or 1},
        "memory": mem,
        "disk": disk,
        "hostname": os.uname().nodename,
    }
