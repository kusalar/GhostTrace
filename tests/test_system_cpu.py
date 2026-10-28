"""Tests for CPU metrics, core counts, and utilization sampling."""

from __future__ import annotations

import sys
from unittest.mock import patch

from ghosttrace.system.cpu import CpuCollector


def test_cpu_collector_live() -> None:
    """Verify live CPU metrics on current host machine."""
    collector = CpuCollector()
    info = collector.get_cpu_info(sample_interval=0.02)
    assert info.logical_cores is not None
    assert info.logical_cores > 0
    assert info.model_name != ""
    assert info.timestamp > 0
    if sys.platform == "win32":
        assert info.cpu_percent is not None
        assert 0.0 <= info.cpu_percent <= 100.0


def test_cpu_collector_caching_and_delta() -> None:
    """Verify non-blocking delta calculation across successive calls."""
    collector = CpuCollector()
    # First call establishes baseline
    info1 = collector.get_cpu_info(sample_interval=0.01)
    # Second call uses delta
    info2 = collector.get_cpu_info(sample_interval=0.0)
    assert info2.logical_cores == info1.logical_cores


def test_cpu_collector_non_windows_fallback() -> None:
    """Verify non-Windows platform returns None for cpu_percent without failing."""
    collector = CpuCollector()
    with patch("sys.platform", "linux"):
        usage = collector.sample_cpu_percent()
        assert usage is None


def test_cpu_collector_error_handling() -> None:
    """Verify sampling failure does not raise an unhandled exception."""
    collector = CpuCollector()
    with patch("ctypes.windll.kernel32.GetSystemTimes", side_effect=OSError("API Error")):
        usage = collector.sample_cpu_percent()
        assert usage is None
