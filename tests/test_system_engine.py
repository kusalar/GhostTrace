"""Tests for SystemEngine facade and AI context integration."""

from __future__ import annotations

from ghosttrace.config.settings import Settings
from ghosttrace.system.engine import SystemEngine


def test_system_engine_facade() -> None:
    """Verify facade methods delegate cleanly and return expected schemas."""
    engine = SystemEngine()
    assert engine.is_enabled is True
    assert engine.get_platform_info().os_name != ""
    assert engine.get_cpu_info().logical_cores is not None
    assert engine.get_memory_info().total_bytes >= 0
    assert isinstance(engine.get_disk_info().drives, list)
    assert engine.get_process_info().ghosttrace_pid > 0
    assert engine.get_uptime_info().app_uptime_seconds >= 0.0
    snap = engine.get_snapshot()
    assert snap.platform.os_name != ""
    health = engine.check_health()
    assert health.overall_status.value != ""
    report = engine.generate_diagnostics()
    assert report.app_name == "GhostTrace"


def test_ai_system_context_relevance_filtering() -> None:
    """Verify AI system context is only injected for resource-relevant questions."""
    engine = SystemEngine()

    # Relevant queries must produce bounded diagnostic context
    ctx_ram = engine.build_ai_system_context("How much RAM does my computer have?")
    assert ctx_ram is not None
    assert "=== SYSTEM DIAGNOSTIC SNAPSHOT" in ctx_ram
    assert "Physical RAM:" in ctx_ram

    ctx_health = engine.build_ai_system_context("Is GhostTrace healthy right now?")
    assert ctx_health is not None
    assert "GhostTrace Overall Health:" in ctx_health

    ctx_cpu = engine.build_ai_system_context("What CPU utilization is running?")
    assert ctx_cpu is not None
    assert "CPU:" in ctx_cpu

    # Irrelevant queries must return None to avoid polluting conversation
    ctx_normal = engine.build_ai_system_context("Can you explain how async/await works in Python?")
    assert ctx_normal is None

    ctx_greeting = engine.build_ai_system_context("Hello there, good morning!")
    assert ctx_greeting is None


def test_ai_system_context_disabled_setting() -> None:
    """Disabled system subsystem returns None regardless of query."""
    settings = Settings(system_enabled=False)
    engine = SystemEngine(settings)
    assert engine.build_ai_system_context("How much RAM do I have?") is None
