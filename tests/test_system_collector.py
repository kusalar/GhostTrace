"""Tests for the central SystemCollector and caching behavior."""

from __future__ import annotations

from ghosttrace.config.settings import Settings
from ghosttrace.system.collector import SystemCollector


def test_collector_snapshot_caching() -> None:
    """Verify collector caches snapshot within TTL window."""
    settings = Settings(system_cache_seconds=2.0)
    collector = SystemCollector(settings)

    snap1 = collector.get_snapshot()
    snap2 = collector.get_snapshot()
    # Same cached instance
    assert snap1.collected_at == snap2.collected_at

    # Forced refresh bypasses cache
    snap3 = collector.get_snapshot(force_refresh=True)
    assert snap3.collected_at >= snap1.collected_at


def test_collector_individual_providers() -> None:
    """Verify all individual collector methods return typed schemas."""
    collector = SystemCollector()
    assert collector.get_platform().os_name != ""
    assert collector.get_cpu().logical_cores is not None
    assert collector.get_memory().total_bytes >= 0
    assert isinstance(collector.get_disk().drives, list)
    assert collector.get_processes().ghosttrace_pid > 0
    assert collector.get_uptime().app_uptime_seconds >= 0.0
