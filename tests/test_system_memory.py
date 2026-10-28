"""Tests for physical RAM and page-file memory metrics."""

from __future__ import annotations

import sys
from unittest.mock import patch

from ghosttrace.system.memory import get_memory_info


def test_memory_info_live() -> None:
    """Verify live physical RAM metrics on host machine."""
    mem = get_memory_info()
    assert mem.timestamp > 0
    if sys.platform == "win32":
        assert mem.total_bytes > 0
        assert mem.available_bytes > 0
        assert mem.total_gb > 0.0
        assert 0.0 <= mem.percent_used <= 100.0
        assert mem.used_bytes == mem.total_bytes - mem.available_bytes


def test_memory_info_fallback_on_error() -> None:
    """Verify fallback values when memory query fails."""
    with patch("ctypes.windll.kernel32.GlobalMemoryStatusEx", side_effect=OSError("API Error")):
        mem = get_memory_info()
        assert mem.total_bytes == 0
        assert mem.percent_used == 0.0
