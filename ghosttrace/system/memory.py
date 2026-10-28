"""Physical system RAM and page-file memory collection."""

from __future__ import annotations

import ctypes
import logging
import sys
import time

from ghosttrace.system.schemas import MemoryInfo

logger = logging.getLogger(__name__)


class _MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def get_memory_info() -> MemoryInfo:
    """Collect physical RAM metrics using Win32 GlobalMemoryStatusEx or platform fallback."""
    if sys.platform == "win32":
        try:
            stat = _MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(_MEMORYSTATUSEX)
            kernel32 = ctypes.windll.kernel32

            if kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                total_bytes = stat.ullTotalPhys
                avail_bytes = stat.ullAvailPhys
                used_bytes = max(0, total_bytes - avail_bytes)
                percent = round((used_bytes / total_bytes) * 100.0, 1) if total_bytes > 0 else 0.0

                total_gb = round(total_bytes / (1024**3), 2)
                avail_gb = round(avail_bytes / (1024**3), 2)
                used_gb = round(used_bytes / (1024**3), 2)

                return MemoryInfo(
                    total_bytes=total_bytes,
                    available_bytes=avail_bytes,
                    used_bytes=used_bytes,
                    percent_used=percent,
                    total_gb=total_gb,
                    available_gb=avail_gb,
                    used_gb=used_gb,
                    pagefile_total_bytes=stat.ullTotalPageFile,
                    pagefile_available_bytes=stat.ullAvailPageFile,
                    timestamp=time.time(),
                )
        except Exception as err:
            logger.debug("Failed querying GlobalMemoryStatusEx: %s", err)

    # Fallback when Win32 API is not available or fails
    return MemoryInfo(
        total_bytes=0,
        available_bytes=0,
        used_bytes=0,
        percent_used=0.0,
        total_gb=0.0,
        available_gb=0.0,
        used_gb=0.0,
        pagefile_total_bytes=None,
        pagefile_available_bytes=None,
        timestamp=time.time(),
    )
