"""Tests for non-interactive haunt Typer CLI subcommands."""

from __future__ import annotations

from ghosttrace.main import app
from typer.testing import CliRunner

runner = CliRunner()


def test_cli_haunt_default() -> None:
    """Verify 'ghosttrace haunt' shows status summary."""
    result = runner.invoke(app, ["haunt"])
    assert result.exit_code == 0
    assert "Haunted Experience:" in result.stdout
    assert "Mode:" in result.stdout


def test_cli_haunt_status() -> None:
    """Verify 'ghosttrace haunt status' displays full status."""
    result = runner.invoke(app, ["haunt", "status"])
    assert result.exit_code == 0
    assert "HAUNTED EXPERIENCE STATUS" in result.stdout
    assert "Experience Mode" in result.stdout
    assert "Event Intensity" in result.stdout


def test_cli_haunt_preview() -> None:
    """Verify 'ghosttrace haunt preview' outputs atmospheric manifestation."""
    result = runner.invoke(app, ["haunt", "preview"])
    assert result.exit_code == 0
    assert "PREVIEW RESONANCE" in result.stdout
