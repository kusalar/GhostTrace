"""Tests for GhostTrace application importability, startup, and clean shutdown."""

from pathlib import Path
from unittest.mock import patch

import ghosttrace
import ghosttrace.ai
import ghosttrace.core
import ghosttrace.ghost
import ghosttrace.memory
import ghosttrace.safety
import ghosttrace.system
import ghosttrace.terminal
import pytest
from ghosttrace.config.settings import Settings
from ghosttrace.core.logging import reset_logging_state
from ghosttrace.main import main


@pytest.fixture(autouse=True)
def cleanup_logging() -> None:
    """Reset logging state before and after each test."""
    reset_logging_state()
    yield
    reset_logging_state()


def test_package_importability() -> None:
    """Verify root package metadata and subpackage importability."""
    assert ghosttrace.__version__ == "0.6.0"
    assert ghosttrace.__app_name__ == "GhostTrace"

    # Confirm all planned architectural submodules import cleanly
    assert ghosttrace.core is not None
    assert ghosttrace.ai is not None
    assert ghosttrace.ghost is not None
    assert ghosttrace.developer is not None
    assert ghosttrace.guardian is not None
    assert ghosttrace.terminal is not None
    assert ghosttrace.safety is not None
    assert ghosttrace.memory is not None
    assert ghosttrace.system is not None


def test_main_startup_and_clean_exit(tmp_path: Path) -> None:
    """Verify main() launches the terminal app cleanly and returns 0."""
    temp_settings = Settings(
        app_data_dir=tmp_path / "app_data",
        log_dir=tmp_path / "logs",
    )

    with (
        patch("ghosttrace.main.get_settings", return_value=temp_settings),
        patch("ghosttrace.main.run_terminal_app", return_value=0) as mock_run,
    ):
        exit_code = main([])

    assert exit_code == 0
    mock_run.assert_called_once()


def test_main_handles_exception_cleanly(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify main() catches unexpected exceptions and returns error exit code 1."""
    with patch(
        "ghosttrace.main.run_terminal_app", side_effect=RuntimeError("Simulated boot failure")
    ):
        exit_code = main([])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Fatal error during GhostTrace execution" in captured.err
    assert "Simulated boot failure" in captured.err


def test_main_cli_subprocess() -> None:
    """Verify ghosttrace can be executed directly as a module via subprocess with --version."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "ghosttrace.main", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "GhostTrace v0.6.0" in result.stdout
