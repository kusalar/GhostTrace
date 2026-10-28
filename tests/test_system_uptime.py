"""Tests for operating system and application uptime calculation."""

from __future__ import annotations

import time

from ghosttrace.system.uptime import format_duration, get_uptime_info


def test_format_duration() -> None:
    """Verify human-readable duration formatting."""
    assert format_duration(0) == "0s"
    assert format_duration(45) == "45s"
    assert format_duration(125) == "2m 5s"
    assert format_duration(3665) == "1h 1m 5s"
    assert format_duration(90065) == "1d 1h 1m 5s"
    assert format_duration(-10) == "0s"


def test_uptime_info_live() -> None:
    """Verify live uptime info collection."""
    start = time.time() - 100.0
    info = get_uptime_info(app_start_time=start)
    assert info.app_uptime_seconds >= 100.0
    assert "m" in info.app_uptime_formatted or "s" in info.app_uptime_formatted
    assert info.timestamp > 0
