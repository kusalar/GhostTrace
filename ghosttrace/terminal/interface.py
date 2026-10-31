"""Terminal entry point and non-interactive CLI presentation for GhostTrace."""

from __future__ import annotations

import logging

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ghosttrace.config.settings import Settings, get_settings
from ghosttrace.core.logging import disable_console_logging, setup_logging

logger = logging.getLogger("ghosttrace.terminal.interface")


def configure_terminal_console() -> None:
    """Configure Windows console code pages, standard stream encodings, and robust writer thread."""
    import contextlib
    import sys

    if sys.platform == "win32":
        with contextlib.suppress(Exception):
            import ctypes

            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
            ctypes.windll.kernel32.SetConsoleCP(65001)

    for stream_name in ("stdout", "stderr", "__stdout__", "__stderr__", "stdin", "__stdin__"):
        stream = getattr(sys, stream_name, None)
        if stream is not None and hasattr(stream, "reconfigure"):
            with contextlib.suppress(Exception):
                stream.reconfigure(encoding="utf-8", errors="replace")

    with contextlib.suppress(Exception):
        from textual.drivers._writer_thread import WriterThread

        if not getattr(WriterThread, "_ghosttrace_safe_writer", False):

            def _safe_writer_thread_run(self: WriterThread) -> None:
                write = self._file.write
                flush = self._file.flush
                get = self._queue.get
                qsize = self._queue.qsize
                while True:
                    text: str | None = get()
                    if text is None:
                        break
                    try:
                        write(text)
                    except Exception:
                        try:
                            safe_text = text.encode("utf-8", errors="replace").decode(
                                "utf-8", errors="replace"
                            )
                            write(safe_text)
                        except Exception:
                            pass
                    try:
                        if qsize() == 0:
                            flush()
                    except Exception:
                        pass
                with contextlib.suppress(Exception):
                    flush()

            WriterThread.run = _safe_writer_thread_run
            WriterThread._ghosttrace_safe_writer = True


def run_terminal_app(settings: Settings | None = None) -> int:
    """Launch the interactive Textual terminal application."""
    configure_terminal_console()
    from ghosttrace.terminal.app import GhostTraceApp

    if settings is None:
        settings = get_settings()

    setup_logging(settings, enable_console=False)
    disable_console_logging()
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

    from ghosttrace.ai.engine import AIEngine

    ai_engine = AIEngine(settings)
    ai_status = ai_engine.get_status()

    if not ai_status.runtime_available:
        ai_state_badge = "[dim #ff5555]RUNTIME MISSING[/]"
    elif ai_status.is_loaded:
        ai_state_badge = "[bold #00ff66]LOADED[/]"
    elif ai_status.model_exists:
        ai_state_badge = "[bold #00ff66]READY[/]"
    else:
        ai_state_badge = "[bold #33ff33]STANDBY (NO WEIGHTS)[/]"

    subsystem_table.add_row("01", "Foundation & Configuration", "[bold #00ff66]IMPLEMENTED[/]")
    subsystem_table.add_row("02", "Interactive Terminal & CLI", "[bold #00ff66]ACTIVE[/]")
    subsystem_table.add_row("03", "Local AI Integration (llama.cpp)", ai_state_badge)
    subsystem_table.add_row(
        "04", "Ghost Persona & Behaviour Engine", "[bold #00ff66]IMPLEMENTED[/]"
    )
    subsystem_table.add_row("05", "Developer Intel & Coding Assist", "[bold #00ff66]ACTIVE[/]")
    subsystem_table.add_row(
        "06",
        "Command Guardian & Safety",
        "[bold #00ff66]ACTIVE[/]" if settings.guard_enabled else "[dim #ff5555]DISABLED[/]",
    )
    subsystem_table.add_row(
        "07",
        "Persistent Memory & SQLite",
        "[bold #00ff66]ACTIVE[/]" if settings.memory_enabled else "[dim #ff5555]DISABLED[/]",
    )
    subsystem_table.add_row(
        "08",
        "System Diagnostics & Telemetry",
        "[bold #00ff66]ACTIVE[/]" if settings.system_enabled else "[dim #ff5555]DISABLED[/]",
    )
    subsystem_table.add_row(
        "09",
        "Haunted Experience & Events",
        "[bold #00ff66]ACTIVE[/]" if settings.haunt_enabled else "[dim #ff5555]DISABLED[/]",
    )
    subsystem_table.add_row(
        "10", "Packaging, Hardening & Release", "[bold #00ff66]PRODUCTION READY[/]"
    )

    console.print(subsystem_table)
