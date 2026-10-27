"""Core foundation utilities and shared infrastructure for GhostTrace."""

from ghosttrace.core.logging import (
    get_logger,
    reset_logging_state,
    setup_logging,
)

__all__ = [
    "get_logger",
    "reset_logging_state",
    "setup_logging",
]
