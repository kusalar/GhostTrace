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


memory_app = typer.Typer(
    name="memory",
    help="Persistent conversation and developer memory subsystem.",
    no_args_is_help=False,
)
app.add_typer(memory_app, name="memory")


@memory_app.callback(invoke_without_command=True)
def memory_default(ctx: typer.Context) -> None:
    """Show Memory status and item counts."""
    if ctx.invoked_subcommand is None:
        from rich.console import Console

        from ghosttrace.memory.engine import MemoryEngine

        engine = MemoryEngine()
        status = engine.get_status()
        console = Console()
        fts_str = "YES" if status.fts5_available else "LIKE"
        console.print(
            f"[bold #00ff66]Memory:[/] {'ACTIVE' if status.is_enabled else 'DISABLED'} | "
            f"Memories: {status.total_memories} | FTS5: {fts_str}"
        )


@memory_app.command(name="status")
def memory_status() -> None:
    """Display memory subsystem database telemetry and statistics."""
    from rich.console import Console

    from ghosttrace.memory.engine import MemoryEngine

    engine = MemoryEngine()
    status = engine.get_status()
    console = Console()
    console.print(f"Memory Subsystem : {'ACTIVE' if status.is_enabled else 'DISABLED'}")
    console.print(f"Database Path    : {status.database_path}")
    console.print(f"Database Size    : {status.database_size_bytes:,} bytes")
    console.print(f"WAL Mode         : {status.wal_mode}")
    console.print(f"FTS5 Search      : {'ACTIVE' if status.fts5_available else 'FALLBACK (LIKE)'}")
    console.print(f"Total Memories   : {status.total_memories}")
    console.print(f"Conversations    : {status.total_conversations}")
    console.print(f"Messages Stored  : {status.total_messages}")


@memory_app.command(name="list")
def memory_list(
    category: Annotated[str | None, typer.Option(help="Filter by category.")] = None,
) -> None:
    """List stored memories."""
    from rich.console import Console
    from rich.table import Table

    from ghosttrace.memory.engine import MemoryEngine

    engine = MemoryEngine()
    memories = engine.list_memories(category=category, limit=50)
    console = Console()
    if not memories:
        console.print("No memories found.")
        return

    table = Table(title="STORED MEMORIES", border_style="dim green")
    table.add_column("ID", style="bold #00ff66")
    table.add_column("Category", style="cyan")
    table.add_column("Imp", style="yellow")
    table.add_column("Content")
    for m in memories:
        snippet = m.content[:50] + "..." if len(m.content) > 50 else m.content
        table.add_row(str(m.id), m.category.value, str(m.importance), snippet)
    console.print(table)


project_app = typer.Typer(
    name="project",
    help="Project context discovery, registration, and indexing subsystem.",
    no_args_is_help=False,
)
app.add_typer(project_app, name="project")


@project_app.callback(invoke_without_command=True)
def project_default(ctx: typer.Context) -> None:
    """Show active project status."""
    if ctx.invoked_subcommand is None:
        from rich.console import Console

        from ghosttrace.memory.engine import MemoryEngine

        engine = MemoryEngine()
        active = engine.get_active_project()
        console = Console()
        if active:
            console.print(f"[bold #00ff66]Active Project:[/] {active.name} ({active.root_path})")
        else:
            console.print("[dim]No active project selected.[/]")


@project_app.command(name="list")
def project_list() -> None:
    """List registered projects."""
    from rich.console import Console
    from rich.table import Table

    from ghosttrace.memory.engine import MemoryEngine

    engine = MemoryEngine()
    projects = engine.list_projects()
    active = engine.get_active_project()
    console = Console()
    if not projects:
        console.print("No registered projects.")
        return

    table = Table(title="REGISTERED PROJECTS", border_style="dim green")
    table.add_column("Active", style="bold #00ff66")
    table.add_column("Name", style="cyan")
    table.add_column("Root Path")
    for p in projects:
        is_active = "*" if (active and active.id == p.id) else ""
        table.add_row(is_active, p.name, p.root_path)
    console.print(table)


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
