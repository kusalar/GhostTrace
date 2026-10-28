"""Tests for the GhostTrace Typer CLI commands."""

from unittest.mock import patch

from ghosttrace.main import app
from typer.testing import CliRunner

runner = CliRunner()


def test_cli_version() -> None:
    """Verify --version and -v return version string and code 0."""
    res1 = runner.invoke(app, ["--version"])
    assert res1.exit_code == 0
    assert "GhostTrace v0.6.0" in res1.stdout

    res2 = runner.invoke(app, ["-v"])
    assert res2.exit_code == 0
    assert "GhostTrace v0.6.0" in res2.stdout


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


def test_cli_guard_subcommands() -> None:
    """Verify 'guard', 'guard status', 'guard analyze', and 'guard explain' work via Typer."""
    # guard default callback
    res_default = runner.invoke(app, ["guard"])
    assert res_default.exit_code == 0
    assert "Guardian:" in res_default.stdout

    # guard status
    res_status = runner.invoke(app, ["guard", "status"])
    assert res_status.exit_code == 0
    assert "Guardian Subsystem :" in res_status.stdout
    assert "Execution Permitted:" in res_status.stdout

    # guard analyze
    res_analyze = runner.invoke(app, ["guard", "analyze", "--", "python", "--version"])
    assert res_analyze.exit_code == 0
    assert "STATIC ANALYSIS REPORT" in res_analyze.stdout
    assert "Risk Level  : [ SAFE ]" in res_analyze.stdout

    # guard explain
    res_explain = runner.invoke(app, ["guard", "explain", "git", "status"])
    assert res_explain.exit_code == 0
    assert "COMMAND EXPLANATION & PURPOSE" in res_explain.stdout
