"""Terminal entry point and non-interactive CLI presentation for GhostTrace."""

from __future__ import annotations

import logging

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ghosttrace.config.settings import Settings, get_settings
from ghosttrace.core.logging import setup_logging
from ghosttrace.terminal.app import GhostTraceApp

logger = logging.getLogger("ghosttrace.terminal.interface")


def run_terminal_app(settings: Settings | None = None) -> int:
    """Launch the interactive Textual terminal application."""
    if settings is None:
        settings = get_settings()

    setup_logging(settings)
    logger.info("Starting GhostTrace interactive terminal session...")

    app = GhostTraceApp(settings=settings)
    app.run()
    logger.info("GhostTrace terminal session completed cleanly.")
    return 0


def render_cli_status(settings: Settings | None = None) -> None:
    """Render a Rich non-interactive status report to stdout for the CLI 'status' command."""
    if settings is None:
        settings = get_settings()

    console = Console()

    # System Overview Table
    overview_table = Table(box=None, show_header=False, pad_edge=False)
    overview_table.add_column("Key", style="bold #55aa66", width=18)
    overview_table.add_column("Value", style="#bbddbb")

    overview_table.add_row("Application", f"{settings.app_name} v{settings.app_version}")
    overview_table.add_row("Tagline", settings.app_description)
    overview_table.add_row("Environment", settings.env)
    overview_table.add_row("Debug Mode", str(settings.debug))
    overview_table.add_row("Log Level", settings.log_level)
    overview_table.add_row("App Data Dir", str(settings.app_data_dir))
    overview_table.add_row("Log Dir", str(settings.log_dir))

    console.print(
        Panel(
            overview_table,
            title="[bold #00ff66]GHOSTTRACE CONFIGURATION & TELEMETRY[/]",
            border_style="#005522",
        )
    )

    # Roadmap / Subsystems Table
    subsystem_table = Table(title="ROADMAP & SUBSYSTEM STATUS", border_style="#005522")
    subsystem_table.add_column("Step", style="bold #00ff66", width=8)
    subsystem_table.add_column("Subsystem", style="#ffffff", width=34)
    subsystem_table.add_column("State", style="bold", width=16)

    subsystem_table.add_row("01", "Foundation & Configuration", "[bold #00ff66]IMPLEMENTED[/]")
    subsystem_table.add_row("02", "Interactive Terminal & CLI", "[bold #00ff66]ACTIVE[/]")
    subsystem_table.add_row(
        "03", "Local AI Integration (llama.cpp)", "[dim #ff5555]NOT CONNECTED[/]"
    )
    subsystem_table.add_row(
        "04", "Ghost Persona & Behaviour Engine", "[dim #778877]NOT IMPLEMENTED[/]"
    )
    subsystem_table.add_row(
        "05", "Developer Intel & Coding Assist", "[dim #778877]NOT IMPLEMENTED[/]"
    )
    subsystem_table.add_row("06", "Command Guardian & Safety", "[dim #778877]NOT IMPLEMENTED[/]")
    subsystem_table.add_row("07", "Persistent Memory & SQLite", "[dim #778877]NOT IMPLEMENTED[/]")
    subsystem_table.add_row(
        "08", "System Diagnostics & Telemetry", "[dim #778877]NOT IMPLEMENTED[/]"
    )
    subsystem_table.add_row("09", "Haunted Events Engine", "[dim #778877]NOT IMPLEMENTED[/]")
    subsystem_table.add_row(
        "10", "Packaging, Hardening & Release", "[dim #778877]NOT IMPLEMENTED[/]"
    )

    console.print(subsystem_table)
