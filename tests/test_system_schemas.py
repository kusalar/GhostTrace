"""Tests for system awareness schemas and typed models."""

from __future__ import annotations

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


def test_platform_info_schema() -> None:
    """Verify PlatformInfo instantiation and field serialization."""
    info = PlatformInfo(
        os_name="Windows",
        os_release="10",
        os_version="10.0.19045",
        architecture="AMD64",
        python_version="3.11.9",
        python_compiler="MSC v.1939 64 bit",
        python_executable_arch="64bit",
        hostname=None,
    )
    assert info.os_name == "Windows"
    assert info.architecture == "AMD64"
    assert info.hostname is None
    dump = info.model_dump()
    assert dump["python_version"] == "3.11.9"


def test_cpu_and_memory_schemas() -> None:
    """Verify CpuInfo and MemoryInfo calculations and schema constraints."""
    cpu = CpuInfo(
        logical_cores=4,
        physical_cores=2,
        cpu_percent=15.5,
        model_name="Intel Core i3-1115G4",
    )
    assert cpu.logical_cores == 4
    assert cpu.cpu_percent == 15.5

    mem = MemoryInfo(
        total_bytes=12884901888,
        available_bytes=4294967296,
        used_bytes=8589934592,
        percent_used=66.7,
        total_gb=12.0,
        available_gb=4.0,
        used_gb=8.0,
        pagefile_total_bytes=16106127360,
        pagefile_available_bytes=8053063680,
    )
    assert mem.percent_used == 66.7
    assert mem.total_gb == 12.0


def test_disk_and_process_schemas() -> None:
    """Verify DiskInfo, DiskDrive, and ProcessInfo schemas."""
    drive = DiskDrive(
        path="C:\\",
        total_bytes=500000000000,
        used_bytes=200000000000,
        free_bytes=300000000000,
        percent_used=40.0,
        total_gb=465.7,
        free_gb=279.4,
    )
    disk_info = DiskInfo(drives=[drive])
    assert len(disk_info.drives) == 1
    assert disk_info.drives[0].path == "C:\\"

    proc = ProcessInfo(
        total_processes=185,
        ghosttrace_pid=12345,
        ghosttrace_working_set_bytes=41943040,
        ghosttrace_working_set_mb=40.0,
        ghosttrace_uptime_seconds=120.5,
    )
    assert proc.total_processes == 185
    assert proc.ghosttrace_pid == 12345
    assert proc.ghosttrace_working_set_mb == 40.0


def test_health_report_and_snapshot_schemas() -> None:
    """Verify composite SystemHealthReport, SubsystemHealth, and SystemSnapshot."""
    sub = SubsystemHealth(
        name="test_sub",
        status=HealthStatus.HEALTHY,
        details="Operating normally",
    )
    report = SystemHealthReport(
        overall_status=HealthStatus.HEALTHY,
        subsystems={"test_sub": sub},
        summary="All good",
    )
    assert report.overall_status == HealthStatus.HEALTHY
    assert "test_sub" in report.subsystems

    plat = PlatformInfo(
        os_name="Windows",
        os_release="10",
        os_version="10.0",
        architecture="x64",
        python_version="3.11",
        python_compiler="MSC",
        python_executable_arch="64bit",
    )
    cpu = CpuInfo(logical_cores=4, cpu_percent=10.0, model_name="i3")
    mem = MemoryInfo(
        total_bytes=1000,
        available_bytes=500,
        used_bytes=500,
        percent_used=50.0,
        total_gb=1.0,
        available_gb=0.5,
        used_gb=0.5,
    )
    disk = DiskInfo()
    proc = ProcessInfo(ghosttrace_pid=1)
    uptime = UptimeInfo(app_uptime_seconds=10.0, app_uptime_formatted="10s")

    snap = SystemSnapshot(
        platform=plat,
        cpu=cpu,
        memory=mem,
        disk=disk,
        processes=proc,
        uptime=uptime,
        health=report,
    )
    assert snap.platform.os_name == "Windows"

    diag = DiagnosticReport(
        app_version="0.9.0",
        python_version="3.11.9",
        snapshot=snap,
        warnings=["Test warning"],
    )
    assert diag.app_version == "0.9.0"
    assert len(diag.warnings) == 1
