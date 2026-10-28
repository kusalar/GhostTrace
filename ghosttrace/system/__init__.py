"""GhostTrace System Awareness & Diagnostics subsystem."""

from __future__ import annotations

from ghosttrace.system.collector import SystemCollector
from ghosttrace.system.cpu import CpuCollector, get_cpu_info
from ghosttrace.system.diagnostics import DiagnosticsGenerator
from ghosttrace.system.disk import get_disk_info
from ghosttrace.system.engine import SystemEngine
from ghosttrace.system.health import HealthRegistry
from ghosttrace.system.memory import get_memory_info
from ghosttrace.system.platform_info import get_platform_info
from ghosttrace.system.processes import get_process_info
from ghosttrace.system.schemas import (
    CpuInfo,
    DiagnosticReport,
    DiskDrive,
    DiskInfo,
    HealthStatus,
    MemoryInfo,
    PlatformInfo,
    ProcessInfo,
    SubsystemHealth,
    SystemHealthReport,
    SystemSnapshot,
    UptimeInfo,
)
from ghosttrace.system.uptime import get_uptime_info

__all__ = [
    "CpuCollector",
    "CpuInfo",
    "DiagnosticReport",
    "DiagnosticsGenerator",
    "DiskDrive",
    "DiskInfo",
    "HealthRegistry",
    "HealthStatus",
    "MemoryInfo",
    "PlatformInfo",
    "ProcessInfo",
    "SubsystemHealth",
    "SystemCollector",
    "SystemEngine",
    "SystemHealthReport",
    "SystemSnapshot",
    "UptimeInfo",
    "get_cpu_info",
    "get_disk_info",
    "get_memory_info",
    "get_platform_info",
    "get_process_info",
    "get_uptime_info",
]
