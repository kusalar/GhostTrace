"""Tests for platform metadata collection."""

from __future__ import annotations

from unittest.mock import patch

from ghosttrace.system.platform_info import get_platform_info


def test_platform_info_windows_live() -> None:
    """Verify live platform info collection on host machine."""
    info = get_platform_info(include_hostname=False)
    assert info.os_name != ""
    assert info.architecture != ""
    assert info.python_version.startswith("3.")
    assert info.hostname is None


def test_platform_info_with_hostname() -> None:
    """Verify hostname inclusion when requested."""
    info = get_platform_info(include_hostname=True)
    assert info.hostname is not None
    assert len(info.hostname) > 0


def test_platform_info_error_handling() -> None:
    """Verify graceful handling when platform calls raise unexpected errors."""
    with patch("socket.gethostname", side_effect=OSError("Network failure")):
        info = get_platform_info(include_hostname=True)
        assert info.hostname == "Unavailable"
