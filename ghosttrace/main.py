"""Application entry point and CLI architecture for GhostTrace."""

from __future__ import annotations

import sys
from typing import Annotated

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


guard_app = typer.Typer(
    name="guard",
    help="Command Guardian & execution safety subsystem.",
    no_args_is_help=False,
)
app.add_typer(guard_app, name="guard")


@guard_app.callback(invoke_without_command=True)
def guard_default(ctx: typer.Context) -> None:
    """Show Guardian status and quick help."""
    if ctx.invoked_subcommand is None:
        from rich.console import Console

        from ghosttrace.guardian.engine import GuardianEngine

        engine = GuardianEngine()
        status = engine.get_status()
        console = Console()
        console.print(
            f"[bold #00ff66]Guardian:[/] {'ACTIVE' if status.is_enabled else 'DISABLED'} | "
            f"Risk block high: {status.block_high_risk} | Timeout: {status.timeout_seconds}s"
        )


@guard_app.command(name="status")
def guard_status() -> None:
    """Display active Guardian policy and execution configuration."""
    from rich.console import Console

    from ghosttrace.guardian.engine import GuardianEngine

    engine = GuardianEngine()
    status = engine.get_status()
    console = Console()
    console.print(f"Guardian Subsystem : {'ACTIVE' if status.is_enabled else 'DISABLED'}")
    console.print(
        f"Execution Permitted: {'YES' if status.is_execution_enabled else 'NO (ANALYSIS ONLY)'}"
    )
    console.print(f"Approval Enforced  : {'YES (STRICT)' if status.requires_approval else 'NO'}")
    console.print(f"Block High Risk    : {'YES' if status.block_high_risk else 'NO'}")
    console.print(
        f"Default Timeout    : {status.timeout_seconds}s (max: {status.max_timeout_seconds}s)"
    )


@guard_app.command(name="analyze")
def guard_analyze(
    command: Annotated[list[str], typer.Argument(help="Command string to analyze.")],
) -> None:
    """Statically analyze command risk without execution."""
    from rich.console import Console

    from ghosttrace.guardian.engine import GuardianEngine
    from ghosttrace.guardian.explanations import format_command_analysis

    cmd_str = " ".join(command)
    engine = GuardianEngine()
    analysis = engine.analyze(cmd_str)
    console = Console()
    console.print(format_command_analysis(analysis))


@guard_app.command(name="explain")
def guard_explain(
    command: Annotated[list[str], typer.Argument(help="Command string to explain.")],
) -> None:
    """Explain command purpose, side effects, and risk warnings."""
    from rich.console import Console

    from ghosttrace.guardian.engine import GuardianEngine

    cmd_str = " ".join(command)
    engine = GuardianEngine()
    console = Console()
    console.print(engine.explain(cmd_str))


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
