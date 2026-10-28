"""System and application uptime calculation and formatting."""

from __future__ import annotations

import ctypes
import logging
import sys
import time

from ghosttrace.system.schemas import UptimeInfo

logger = logging.getLogger(__name__)

# Module-level recording of GhostTrace process initialization time
APP_START_TIME: float = time.time()


def format_duration(seconds: float) -> str:
    """Format duration in seconds into a human-readable string (e.g., '2d 4h 15m 30s')."""
    if seconds < 0:
        return "0s"

    total_secs = int(seconds)
    days, rem = divmod(total_secs, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)

    parts: list[str] = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")

    return " ".join(parts)


def get_system_uptime_seconds() -> float | None:
    """Retrieve OS uptime in seconds via GetTickCount64 on Windows."""
    if sys.platform == "win32":
        try:
            kernel32 = ctypes.windll.kernel32
            kernel32.GetTickCount64.restype = ctypes.c_ulonglong
            ms = kernel32.GetTickCount64()
            return float(ms) / 1000.0
        except Exception as err:
            logger.debug("GetTickCount64 failed: %s", err)
    return None


def get_uptime_info(app_start_time: float | None = None) -> UptimeInfo:
    """Calculate operating system uptime and GhostTrace application uptime."""
    start = app_start_time if app_start_time is not None else APP_START_TIME
    app_uptime = max(0.0, time.time() - start)
    app_formatted = format_duration(app_uptime)

    sys_uptime = get_system_uptime_seconds()
    sys_hours = round(sys_uptime / 3600.0, 2) if sys_uptime is not None else None
    sys_formatted = format_duration(sys_uptime) if sys_uptime is not None else "Unavailable"

    return UptimeInfo(
        system_uptime_seconds=sys_uptime,
        system_uptime_hours=sys_hours,
        system_uptime_formatted=sys_formatted,
        app_uptime_seconds=round(app_uptime, 1),
        app_uptime_formatted=app_formatted,
        timestamp=time.time(),
    )
