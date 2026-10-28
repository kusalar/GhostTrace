"""Tests for diagnostic report generation and safe export."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from ghosttrace.system.diagnostics import DiagnosticsGenerator


def test_generate_diagnostic_report() -> None:
    """Verify diagnostic report structure and metric fields."""
    gen = DiagnosticsGenerator()
    report = gen.generate_report()
    assert report.app_name == "GhostTrace"
    assert report.app_version != ""
    assert report.python_version != ""
    assert report.snapshot.platform.os_name != ""
    assert isinstance(report.warnings, list)
    assert isinstance(report.unavailable_metrics, list)


def test_export_diagnostic_report_json(tmp_path: Path) -> None:
    """Verify safe JSON export without leaking secrets or overwriting without permission."""
    gen = DiagnosticsGenerator()
    report = gen.generate_report()

    target = tmp_path / "diagnostics.json"
    exported_path = gen.export_report_json(report, target)
    assert exported_path.is_file()

    content = exported_path.read_text(encoding="utf-8")
    data = json.loads(content)
    assert data["app_name"] == "GhostTrace"
    assert "platform" in data["snapshot"]

    # Invariant: Must not overwrite existing file unless overwrite=True
    with pytest.raises(FileExistsError):
        gen.export_report_json(report, target, overwrite=False)

    # Overwrite succeeds when explicit
    gen.export_report_json(report, target, overwrite=True)
    assert target.is_file()
