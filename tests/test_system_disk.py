"""Tests for storage volume metrics and error boundaries."""

from __future__ import annotations

from pathlib import Path

from ghosttrace.system.disk import get_disk_info


def test_disk_info_live(tmp_path: Path) -> None:
    """Verify live disk capacity collection for repository and tmp path."""
    disk = get_disk_info(paths=[tmp_path])
    assert len(disk.drives) >= 1
    d = disk.drives[0]
    assert d.total_bytes > 0
    assert d.free_bytes >= 0
    assert 0.0 <= d.percent_used <= 100.0


def test_disk_info_handles_inaccessible_paths() -> None:
    """Verify missing, invalid, or permission-denied paths are handled gracefully."""
    fake_path = "Z:\\NonExistentDrive\\GhostTrace"
    disk = get_disk_info(paths=[fake_path])
    # Must not raise an exception; returns empty list or valid drives only
    assert isinstance(disk.drives, list)
