"""Tests for aggregate process metrics and GhostTrace footprint."""

from __future__ import annotations

import os
import sys
from unittest.mock import patch

from ghosttrace.system.processes import get_process_info


def test_process_info_live() -> None:
    """Verify live process count and GhostTrace PID."""
    proc = get_process_info()
    assert proc.ghosttrace_pid == os.getpid()
    assert proc.timestamp > 0
    if sys.platform == "win32":
        assert proc.total_processes is not None
        assert proc.total_processes > 0
        assert proc.ghosttrace_working_set_bytes is not None
        assert proc.ghosttrace_working_set_bytes > 0


def test_process_info_error_handling() -> None:
    """Verify process collection returns None for aggregates on error."""
    with patch("ghosttrace.system.processes._get_process_count_windows", return_value=None):
        proc = get_process_info()
        assert proc.total_processes is None
        assert proc.ghosttrace_pid == os.getpid()
