"""Process enumeration aggregates and GhostTrace process metrics."""

from __future__ import annotations

import logging
import os
import sys
import time
from ctypes import Structure, byref, c_size_t, c_ulong, c_void_p, sizeof, windll, wintypes

from ghosttrace.system.schemas import ProcessInfo

logger = logging.getLogger(__name__)


class _PROCESS_MEMORY_COUNTERS_EX(Structure):  # noqa: N801
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", c_size_t),
        ("WorkingSetSize", c_size_t),
        ("QuotaPeakPagedPoolUsage", c_size_t),
        ("QuotaPagedPoolUsage", c_size_t),
        ("QuotaPeakNonPagedPoolUsage", c_size_t),
        ("QuotaNonPagedPoolUsage", c_size_t),
        ("PagefileUsage", c_size_t),
        ("PeakPagefileUsage", c_size_t),
        ("PrivateUsage", c_size_t),
    ]


class _FILETIME(Structure):
    _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]


def _get_process_count_windows() -> int | None:
    """Enumerate running processes count using Win32 EnumProcesses.

    Collects aggregate count only. Does not inspect command lines, environment
    variables, or memory of other processes.
    """
    try:
        psapi = windll.psapi
        max_pids = 4096
        pids_array = (c_ulong * max_pids)()
        cb_needed = c_ulong()

        if psapi.EnumProcesses(byref(pids_array), sizeof(pids_array), byref(cb_needed)):
            return cb_needed.value // sizeof(c_ulong)
    except Exception as err:
        logger.debug("EnumProcesses failed: %s", err)
    return None


def _get_ghosttrace_memory_windows() -> int | None:
    """Query current process resident working set memory."""
    try:
        kernel32 = windll.kernel32
        psapi = windll.psapi

        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, c_void_p, wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL

        h_proc = kernel32.GetCurrentProcess()
        pmc = _PROCESS_MEMORY_COUNTERS_EX()
        pmc.cb = sizeof(_PROCESS_MEMORY_COUNTERS_EX)

        if psapi.GetProcessMemoryInfo(h_proc, byref(pmc), pmc.cb):
            return int(pmc.WorkingSetSize)
    except Exception as err:
        logger.debug("GetProcessMemoryInfo failed: %s", err)
    return None


def _get_ghosttrace_uptime_windows() -> float | None:
    """Determine application process running time via GetProcessTimes."""
    try:
        kernel32 = windll.kernel32
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        kernel32.GetProcessTimes.argtypes = [
            wintypes.HANDLE,
            c_void_p,
            c_void_p,
            c_void_p,
            c_void_p,
        ]

        creation = _FILETIME()
        exit_time = _FILETIME()
        kernel_time = _FILETIME()
        user_time = _FILETIME()
        h_proc = kernel32.GetCurrentProcess()

        if kernel32.GetProcessTimes(
            h_proc,
            byref(creation),
            byref(exit_time),
            byref(kernel_time),
            byref(user_time),
        ):
            ft_val = (creation.dwHighDateTime << 32) + creation.dwLowDateTime
            # Windows FILETIME epoch to Unix epoch: 116444736000000000 in 100ns units
            epoch_sec = (ft_val - 116444736000000000) / 10000000.0
            return max(0.0, time.time() - epoch_sec)
    except Exception as err:
        logger.debug("GetProcessTimes failed: %s", err)
    return None


def get_process_info() -> ProcessInfo:
    """Collect aggregate process count and GhostTrace process footprint."""
    pid = os.getpid()
    proc_count: int | None = None
    working_set_bytes: int | None = None
    proc_uptime: float | None = None

    if sys.platform == "win32":
        proc_count = _get_process_count_windows()
        working_set_bytes = _get_ghosttrace_memory_windows()
        proc_uptime = _get_ghosttrace_uptime_windows()

    working_set_mb = (
        round(working_set_bytes / (1024 * 1024), 2) if working_set_bytes is not None else None
    )

    return ProcessInfo(
        total_processes=proc_count,
        ghosttrace_pid=pid,
        ghosttrace_working_set_bytes=working_set_bytes,
        ghosttrace_working_set_mb=working_set_mb,
        ghosttrace_uptime_seconds=proc_uptime,
        timestamp=time.time(),
    )
