"""Application logging infrastructure for GhostTrace."""

from __future__ import annotations

import contextlib
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from ghosttrace.config.settings import Settings, get_settings

DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_LOGGING_INITIALIZED = False


def setup_logging(
    settings: Settings | None = None,
    enable_console: bool = True,
) -> logging.Logger:
    """Initialize application-wide logging with file and optional console handlers.

    When enable_console is False (e.g. during interactive Textual TUI execution),
    logs are written strictly to the rotating log file to prevent terminal screen
    corruption and input widget overwrites. Safe against duplicate handler registration.
    """
    global _LOGGING_INITIALIZED

    if settings is None:
        settings = get_settings()

    target_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    app_logger = logging.getLogger("ghosttrace")

    formatter = logging.Formatter(fmt=DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)

    # Ensure log directory exists
    log_dir: Path = settings.log_dir or (settings.app_data_dir / "logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file_path = log_dir / "ghosttrace.log"

    # If already initialized, reconcile console handler and levels
    if _LOGGING_INITIALIZED:
        root_logger.setLevel(target_level)
        app_logger.setLevel(target_level)

        if not enable_console:
            disable_console_logging()
        else:
            _ensure_console_handler(root_logger, formatter, target_level)

        return app_logger

    # Console Handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(target_level)
    console_handler.setFormatter(formatter)

    # Rotating File Handler (10 MB per file, max 5 backups)
    file_handler = RotatingFileHandler(
        filename=log_file_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(target_level)
    file_handler.setFormatter(formatter)

    # Attach handlers to root logger so all subsystem loggers inherit them cleanly
    root_logger.setLevel(target_level)
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    if enable_console:
        root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    app_logger.setLevel(target_level)
    _LOGGING_INITIALIZED = True

    app_logger.debug(
        "Logging initialized. Level: %s, Console: %s, Log file: %s",
        settings.log_level,
        enable_console,
        log_file_path,
    )

    return app_logger


def disable_console_logging() -> None:
    """Detach any stdout/stderr StreamHandlers to prevent terminal screen corruption in TUI."""
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        if (
            isinstance(handler, logging.StreamHandler)
            and not isinstance(handler, RotatingFileHandler)
            and getattr(handler, "stream", None) in (sys.stdout, sys.stderr)
        ):
            root_logger.removeHandler(handler)
            with contextlib.suppress(Exception):
                handler.close()


def enable_console_logging(settings: Settings | None = None) -> None:
    """Attach stdout StreamHandler if not already present."""
    if settings is None:
        settings = get_settings()
    target_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    formatter = logging.Formatter(fmt=DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)
    _ensure_console_handler(root_logger, formatter, target_level)


def _ensure_console_handler(
    logger: logging.Logger, formatter: logging.Formatter, level: int
) -> None:
    """Internal helper to attach stdout StreamHandler if absent."""
    has_console = any(
        isinstance(h, logging.StreamHandler)
        and not isinstance(h, RotatingFileHandler)
        and getattr(h, "stream", None) == sys.stdout
        for h in logger.handlers
    )
    if not has_console:
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(level)
        ch.setFormatter(formatter)
        logger.addHandler(ch)


def get_logger(name: str = "ghosttrace") -> logging.Logger:
    """Return a scoped logger instance for the given module or component."""
    return logging.getLogger(name)


def reset_logging_state() -> None:
    """Reset initialization state and detach handlers (primarily for testing)."""
    global _LOGGING_INITIALIZED
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        handler.close()
        root_logger.removeHandler(handler)
    _LOGGING_INITIALIZED = False
