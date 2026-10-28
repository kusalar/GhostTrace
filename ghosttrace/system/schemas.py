"""Pydantic schemas and typed models for the GhostTrace system awareness subsystem."""

from __future__ import annotations

import time
from enum import StrEnum

from pydantic import BaseModel, Field


class HealthStatus(StrEnum):
    """Subsystem operational health states."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    DISABLED = "DISABLED"
    ERROR = "ERROR"


class PlatformInfo(BaseModel):
    """Host operating system, architecture, and Python runtime metadata."""

    os_name: str
    os_release: str
    os_version: str
    architecture: str
    python_version: str
    python_compiler: str
    python_executable_arch: str
    hostname: str | None = None


class CpuInfo(BaseModel):
    """Processor counts, model identification, and utilization."""

    logical_cores: int | None = None
    physical_cores: int | None = None
    cpu_percent: float | None = None
    model_name: str = "Unknown CPU"
    timestamp: float = Field(default_factory=time.time)


class MemoryInfo(BaseModel):
    """Physical system RAM and optional page-file statistics."""

    total_bytes: int
    available_bytes: int
    used_bytes: int
    percent_used: float
    total_gb: float
    available_gb: float
    used_gb: float
    pagefile_total_bytes: int | None = None
    pagefile_available_bytes: int | None = None
    timestamp: float = Field(default_factory=time.time)


class DiskDrive(BaseModel):
    """Disk space metrics for an individual drive or volume."""

    path: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    percent_used: float
    total_gb: float
    free_gb: float


class DiskInfo(BaseModel):
    """Disk volume metrics across inspected directories."""

    drives: list[DiskDrive] = Field(default_factory=list)
    timestamp: float = Field(default_factory=time.time)


class ProcessInfo(BaseModel):
    """Aggregate system process metrics and GhostTrace process footprint."""

    total_processes: int | None = None
    ghosttrace_pid: int
    ghosttrace_working_set_bytes: int | None = None
    ghosttrace_working_set_mb: float | None = None
    ghosttrace_uptime_seconds: float | None = None
    timestamp: float = Field(default_factory=time.time)


class UptimeInfo(BaseModel):
    """Operating system and application uptime metrics."""

    system_uptime_seconds: float | None = None
    system_uptime_hours: float | None = None
    system_uptime_formatted: str = "Unavailable"
    app_uptime_seconds: float
    app_uptime_formatted: str
    timestamp: float = Field(default_factory=time.time)


class SubsystemHealth(BaseModel):
    """Individual GhostTrace subsystem diagnostic state."""

    name: str
    status: HealthStatus
    details: str
    checked_at: float = Field(default_factory=time.time)


class SystemHealthReport(BaseModel):
    """Composite health report across all application subsystems."""

    overall_status: HealthStatus
    subsystems: dict[str, SubsystemHealth] = Field(default_factory=dict)
    summary: str = ""
    timestamp: float = Field(default_factory=time.time)


class SystemSnapshot(BaseModel):
    """Complete, unified point-in-time system telemetry snapshot."""

    platform: PlatformInfo
    cpu: CpuInfo
    memory: MemoryInfo
    disk: DiskInfo
    processes: ProcessInfo
    uptime: UptimeInfo
    health: SystemHealthReport | None = None
    collected_at: float = Field(default_factory=time.time)


class DiagnosticReport(BaseModel):
    """Comprehensive diagnostic report for terminal display or sanitised export."""

    app_name: str = "GhostTrace"
    app_version: str
    python_version: str
    snapshot: SystemSnapshot
    warnings: list[str] = Field(default_factory=list)
    unavailable_metrics: list[str] = Field(default_factory=list)
    generated_at: float = Field(default_factory=time.time)
