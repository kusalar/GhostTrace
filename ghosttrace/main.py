"""Application entry point for GhostTrace."""

import sys

from ghosttrace.config.settings import get_settings
from ghosttrace.core.logging import get_logger, setup_logging


def main() -> int:
    """Initialize configuration, set up logging, display status, and exit cleanly."""
    try:
        settings = get_settings()
        setup_logging(settings)
        logger = get_logger("ghosttrace.main")

        logger.info("Initializing GhostTrace foundation...")

        print("==================================================")
        print(f" {settings.app_name} v{settings.app_version}")
        print(f" {settings.app_description}")
        print("==================================================")
        print(f"Environment : {settings.env}")
        print(f"Log Level   : {settings.log_level}")
        print(f"App Data    : {settings.app_data_dir}")
        print(f"Logs        : {settings.log_dir}")
        print("--------------------------------------------------")
        print("Foundation initialized successfully. Ready for Step 02.")
        print("==================================================")

        logger.info("GhostTrace foundation initialized cleanly.")
        return 0
    except Exception as exc:
        print(f"Fatal error during GhostTrace initialization: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
