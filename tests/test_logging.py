"""Tests for the GhostTrace logging infrastructure."""

import logging
from pathlib import Path

import pytest
from ghosttrace.config.settings import Settings, get_settings
from ghosttrace.core.logging import (
    get_logger,
    reset_logging_state,
    setup_logging,
)


@pytest.fixture(autouse=True)
def cleanup_logging() -> None:
    """Reset logging state before and after each test."""
    reset_logging_state()
    yield
    reset_logging_state()


def test_logging_initialization(tmp_path: Path) -> None:
    """Verify setup_logging configures root and app loggers with handlers."""
    log_dir = tmp_path / "logs"
    settings = Settings(log_dir=log_dir, log_level="DEBUG")

    logger = setup_logging(settings)
    assert logger.name == "ghosttrace"
    assert logger.level == logging.DEBUG

    # Check root logger has handlers attached
    root_logger = logging.getLogger()
    assert len(root_logger.handlers) == 2  # Console + File handler

    # Verify log directory was automatically created
    assert log_dir.is_dir()
    log_file = log_dir / "ghosttrace.log"
    assert log_file.exists()


def test_setup_logging_with_none_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """setup_logging(None) should fall back to get_settings()."""
    log_dir = tmp_path / "default_logs"
    monkeypatch.setenv("GHOSTTRACE_LOG_DIR", str(log_dir))
    get_settings.cache_clear()

    logger = setup_logging(None)
    assert logger.name == "ghosttrace"
    assert (log_dir / "ghosttrace.log").exists()
    get_settings.cache_clear()


def test_file_logging_content(tmp_path: Path) -> None:
    """Verify that messages written to logger appear in the rotating log file."""
    log_dir = tmp_path / "logs"
    settings = Settings(log_dir=log_dir, log_level="INFO")

    logger = setup_logging(settings)
    test_message = "GhostTrace test pulse verified."
    logger.info(test_message)

    # Flush handlers
    for handler in logging.getLogger().handlers:
        handler.flush()

    log_file = log_dir / "ghosttrace.log"
    content = log_file.read_text(encoding="utf-8")
    assert test_message in content
    assert "[INFO]" in content
    assert "[ghosttrace]" in content


def test_duplicate_handler_prevention(tmp_path: Path) -> None:
    """Multiple calls to setup_logging must not accumulate duplicate handlers."""
    log_dir = tmp_path / "logs"
    settings = Settings(log_dir=log_dir, log_level="INFO")

    setup_logging(settings)
    initial_count = len(logging.getLogger().handlers)

    # Re-invoke setup_logging
    setup_logging(settings)
    reinvoked_count = len(logging.getLogger().handlers)

    assert initial_count == 2
    assert reinvoked_count == 2


def test_get_logger_namespacing() -> None:
    """get_logger should return properly namespaced logger instances."""
    custom_logger = get_logger("ghosttrace.guardian")
    assert custom_logger.name == "ghosttrace.guardian"
