"""Application entry point and CLI architecture for GhostTrace."""

from __future__ import annotations

import sys

import typer

from ghosttrace.config.settings import get_settings
from ghosttrace.terminal.interface import render_cli_status, run_terminal_app

app = typer.Typer(
    name="ghosttrace",
    help="GhostTrace — The AI That Haunts Your Terminal.",
    add_completion=False,
    no_args_is_help=False,
)


def version_callback(value: bool) -> None:
    """Print GhostTrace version and exit cleanly."""
    if value:
        settings = get_settings()
        print(f"{settings.app_name} v{settings.app_version}")
        raise typer.Exit(0)


@app.callback(invoke_without_command=True)
def default_entry(
    ctx: typer.Context,
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        help="Show GhostTrace version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """GhostTrace default entry point: launches the interactive terminal."""
    if ctx.invoked_subcommand is None:
        run_terminal_app()


@app.command(name="status", help="Display GhostTrace configuration and subsystem status.")
def status_command() -> None:
    """Display system status non-interactively via Rich."""
    render_cli_status()


def main(args: list[str] | None = None) -> int:
    """Standard CLI entry point returning exit code."""
    try:
        app(args=args, standalone_mode=False)
        return 0
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 0
    except Exception as exc:
        print(f"Fatal error during GhostTrace execution: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
