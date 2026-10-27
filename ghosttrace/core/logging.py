"""Application logging infrastructure for GhostTrace."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from ghosttrace.config.settings import Settings, get_settings

DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_LOGGING_INITIALIZED = False


def setup_logging(settings: Settings | None = None) -> logging.Logger:
    """Initialize application-wide logging with console and rotating file handlers.

    Safe against duplicate handler registration.
    """
    global _LOGGING_INITIALIZED

    if settings is None:
        settings = get_settings()

    target_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    app_logger = logging.getLogger("ghosttrace")

    # If already initialized, update levels and return existing logger
    if _LOGGING_INITIALIZED:
        root_logger.setLevel(target_level)
        app_logger.setLevel(target_level)
        return app_logger

    # Ensure log directory exists
    log_dir: Path = settings.log_dir or (settings.app_data_dir / "logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file_path = log_dir / "ghosttrace.log"

    formatter = logging.Formatter(fmt=DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)

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
    # Remove any pre-existing default handlers to prevent duplication
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    app_logger.setLevel(target_level)
    _LOGGING_INITIALIZED = True

    app_logger.debug(
        "Logging initialized. Level: %s, Log file: %s",
        settings.log_level,
        log_file_path,
    )

    return app_logger


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
