"""Tests for the GhostTrace Typer CLI commands."""

from unittest.mock import patch

from ghosttrace.main import app
from typer.testing import CliRunner

runner = CliRunner()


def test_cli_version() -> None:
    """Verify --version and -v return version string and code 0."""
    res1 = runner.invoke(app, ["--version"])
    assert res1.exit_code == 0
    assert "GhostTrace v0.5.0" in res1.stdout

    res2 = runner.invoke(app, ["-v"])
    assert res2.exit_code == 0
    assert "GhostTrace v0.5.0" in res2.stdout


def test_cli_help() -> None:
    """Verify --help outputs usage, options, and available subcommands."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "GhostTrace" in result.stdout
    assert "status" in result.stdout
    assert "--version" in result.stdout


def test_cli_status_subcommand() -> None:
    """Verify 'ghosttrace status' prints configuration and roadmap overview."""
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "GHOSTTRACE CONFIGURATION & TELEMETRY" in result.stdout
    assert "ROADMAP & SUBSYSTEM STATUS" in result.stdout
    assert "Foundation & Configuration" in result.stdout


def test_cli_default_invocation_launches_terminal() -> None:
    """Running ghosttrace without arguments routes to run_terminal_app."""
    with patch("ghosttrace.main.run_terminal_app", return_value=0) as mock_run:
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        mock_run.assert_called_once()


def test_main_function_direct_invocation() -> None:
    """Verify main() function handles arguments directly and returns exit code."""
    from ghosttrace.main import main

    with patch("ghosttrace.main.run_terminal_app", return_value=0) as mock_run:
        code = main([])
        assert code == 0
        mock_run.assert_called_once()

    # Calling with --version raises Exit(0), returning 0
    exit_code = main(["--version"])
    assert exit_code == 0
