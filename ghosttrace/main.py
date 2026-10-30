"""Application entry point and CLI architecture for GhostTrace."""

from __future__ import annotations

import contextlib
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


system_app = typer.Typer(
    name="system",
    help="Host system awareness, hardware telemetry, and diagnostics.",
    no_args_is_help=False,
)
app.add_typer(system_app, name="system")


@system_app.callback(invoke_without_command=True)
def system_default(ctx: typer.Context) -> None:
    """Show system and resource overview."""
    if ctx.invoked_subcommand is None:
        from rich.console import Console

        from ghosttrace.system.engine import SystemEngine

        engine = SystemEngine()
        snap = engine.get_snapshot()
        health = engine.check_health()
        console = Console()
        console.print(
            f"[bold #00ff66]System:[/] {snap.platform.os_name} {snap.platform.os_release} "
            f"({snap.platform.architecture}) | Python {snap.platform.python_version} | "
            f"RAM: {snap.memory.available_gb}/{snap.memory.total_gb} GB free | "
            f"Health: [bold]{health.overall_status.value}[/]"
        )


@system_app.command(name="overview")
def system_overview_cmd() -> None:
    """Display comprehensive system hardware and resource overview."""
    from rich.console import Console

    from ghosttrace.system.engine import SystemEngine

    engine = SystemEngine()
    snap = engine.get_snapshot()
    health = engine.check_health()
    console = Console()
    console.print(
        f"[bold #00ff66]OS Platform :[/] {snap.platform.os_name} {snap.platform.os_release} "
        f"({snap.platform.architecture})"
    )
    console.print(
        f"[bold #00ff66]Python      :[/] {snap.platform.python_version} "
        f"({snap.platform.python_executable_arch})"
    )
    cpu_usage_str = f"{snap.cpu.cpu_percent}%" if snap.cpu.cpu_percent is not None else "N/A"
    console.print(
        f"[bold #00ff66]Processor   :[/] {snap.cpu.model_name} "
        f"({snap.cpu.logical_cores} cores, usage: {cpu_usage_str})"
    )
    console.print(
        f"[bold #00ff66]Physical RAM:[/] {snap.memory.available_gb} GB avail / "
        f"{snap.memory.total_gb} GB total ({snap.memory.percent_used}% used)"
    )
    console.print(
        f"[bold #00ff66]Uptime      :[/] OS {snap.uptime.system_uptime_formatted} | "
        f"App {snap.uptime.app_uptime_formatted}"
    )
    console.print(
        f"[bold #00ff66]Health      :[/] {health.overall_status.value} - {health.summary}"
    )


@system_app.command(name="health")
def system_health_cmd() -> None:
    """Display health diagnostics for all GhostTrace subsystems."""
    from rich.console import Console
    from rich.table import Table

    from ghosttrace.system.engine import SystemEngine

    engine = SystemEngine()
    health = engine.check_health()
    console = Console()

    table = Table(
        title=f"SUBSYSTEM HEALTH [{health.overall_status.value}]",
        border_style="dim green",
    )
    table.add_column("Subsystem", style="bold #00ff66")
    table.add_column("Status", style="bold")
    table.add_column("Details")
    for name, sub in health.subsystems.items():
        color = (
            "#00ff66"
            if sub.status.value == "HEALTHY"
            else ("#ffaa00" if sub.status.value in ("DEGRADED", "DISABLED") else "#ff5555")
        )
        table.add_row(name, f"[{color}]{sub.status.value}[/]", sub.details)
    console.print(table)


@system_app.command(name="diagnostics")
def system_diagnostics_cmd(
    export: str | None = typer.Option(None, "--export", "-e", help="Export report to JSON file"),
) -> None:
    """Compile diagnostic report."""
    from rich.console import Console

    from ghosttrace.system.engine import SystemEngine

    engine = SystemEngine()
    rep = engine.generate_diagnostics()
    console = Console()

    if export:
        dest = engine.export_diagnostics_json(export, report=rep, overwrite=True)
        console.print(f"[bold #00ff66]Diagnostic report exported to:[/] {dest}")
        return

    console.print(f"[bold #00ff66]GhostTrace Diagnostic Report v{rep.app_version}[/]")
    console.print(f"Platform: {rep.snapshot.platform.os_name} {rep.snapshot.platform.os_release}")
    status_val = rep.snapshot.health.overall_status.value if rep.snapshot.health else "UNKNOWN"
    console.print(f"Overall Health: {status_val}")


haunt_app = typer.Typer(
    name="haunt",
    help="Haunted experience and atmospheric events.",
    no_args_is_help=False,
)
app.add_typer(haunt_app, name="haunt")


@haunt_app.callback(invoke_without_command=True)
def haunt_default(ctx: typer.Context) -> None:
    """Show haunted experience status summary."""
    if ctx.invoked_subcommand is None:
        from rich.console import Console

        from ghosttrace.haunt.engine import HauntEngine

        engine = HauntEngine()
        st = engine.get_status()
        console = Console()
        console.print(
            f"[bold #00ff66]Haunted Experience:[/] "
            f"{'ACTIVE' if st.enabled else 'DISABLED'} | "
            f"Mode: {st.mode.value.upper()} | "
            f"Intensity: {st.intensity.value.upper()} | "
            f"Budget: {st.total_events_triggered}/{st.max_events_per_session}"
        )


@haunt_app.command(name="status")
def haunt_status_cmd() -> None:
    """Display comprehensive haunted experience status and configuration."""
    from rich.console import Console

    from ghosttrace.haunt.engine import HauntEngine

    engine = HauntEngine()
    st = engine.get_status()
    console = Console()
    console.print("HAUNTED EXPERIENCE STATUS")
    console.print("==================================================")
    console.print(f"  Subsystem State    : {'ACTIVE' if st.enabled else 'DISABLED'}")
    console.print(f"  Experience Mode    : {st.mode.value.upper()}")
    console.print(f"  Event Intensity    : {st.intensity.value.upper()}")
    console.print(f"  Active Profile     : {st.active_profile}")
    console.print(f"  Current Mood       : {st.current_mood.upper()}")
    console.print(f"  Session Budget     : {st.total_events_triggered}/{st.max_events_per_session}")
    console.print(f"  Base Cooldown      : {st.cooldown_seconds}s")
    console.print(f"  Idle Whispers      : {'ENABLED' if st.idle_enabled else 'DISABLED'}")
    console.print(f"  Reduced Motion     : {'ON' if st.reduced_motion else 'OFF'}")


@haunt_app.command(name="preview")
def haunt_preview_cmd(
    category: str | None = typer.Argument(None, help="Event category to preview"),
) -> None:
    """Preview an atmospheric event manifestation harmlessly."""
    from rich.console import Console

    from ghosttrace.haunt.atmosphere import format_haunt_banner
    from ghosttrace.haunt.engine import HauntEngine

    engine = HauntEngine()
    res = engine.preview_event(category=category)
    console = Console()
    if res.fired and res.rendered_text:
        banner = format_haunt_banner(
            title="PREVIEW RESONANCE",
            text=res.rendered_text,
            glyph=True,
        )
        console.print(banner)
    else:
        console.print(f"[dim #ff5555]Preview failed: {res.reason}[/]")


audio_app = typer.Typer(
    name="audio",
    help="Horror sound effects, volume control, and audio subsystem management.",
    no_args_is_help=False,
)
app.add_typer(audio_app, name="audio")


@audio_app.callback(invoke_without_command=True)
def audio_default(ctx: typer.Context) -> None:
    """Show audio subsystem status summary."""
    if ctx.invoked_subcommand is None:
        audio_status_cmd()


@audio_app.command(name="status")
def audio_status_cmd() -> None:
    """Display audio subsystem configuration, volume levels, and device status."""
    from rich.console import Console

    from ghosttrace.audio.manager import AudioManager
    from ghosttrace.config.settings import get_settings
    from ghosttrace.haunt.engine import HauntEngine

    settings = get_settings()
    mgr = AudioManager(settings=settings)
    try:
        st = mgr.get_status()
        haunt = HauntEngine(settings=settings)

        console = Console()
        console.print("GHOSTTRACE AUDIO SUBSYSTEM")
        console.print("==================================================")
        state_badge = "[bold #00ff66]ENABLED[/]" if st.enabled else "[dim #ff5555]DISABLED[/]"
        console.print(f"  Subsystem State    : {state_badge}")
        console.print(f"  Backend Type       : {st.backend_type.upper()}")
        if not st.enabled:
            device_avail = "[dim]OFFLINE (AUDIO DISABLED)[/]"
        else:
            device_avail = (
                "[bold #00ff66]AVAILABLE[/]"
                if st.backend_available
                else "[dim #ffaa00]UNAVAILABLE[/]"
            )
        console.print(f"  Playback Device    : {device_avail}")
        console.print(f"  Master Volume      : {int(st.volume * 100)}% ({st.volume:.2f})")
        amb_pct = int(st.ambient_volume * 100)
        console.print(f"  Ambient Volume     : {amb_pct}% ({st.ambient_volume:.2f})")
        mute_badge = "[bold #ffaa00]MUTED[/]" if st.is_muted else "[bold #00ff66]UNMUTED[/]"
        console.print(f"  Mute State         : {mute_badge}")
        console.print(f"  Active Voices      : {st.active_voices_count}")
        amb_playing = "[bold #00ff66]STREAMING[/]" if st.ambient_playing else "[dim]INACTIVE[/]"
        console.print(f"  Ambient Loop       : {amb_playing}")
        keystrokes_badge = (
            "[bold #00ff66]ENABLED[/]"
            if st.haunted_keystrokes_enabled
            else "[dim #ff5555]DISABLED[/]"
        )
        console.print(f"  Haunted Keystrokes : {keystrokes_badge}")
        whispers_badge = (
            "[bold #00ff66]ENABLED[/]"
            if st.scheduled_whispers_enabled
            else "[dim #ff5555]DISABLED[/]"
        )
        console.print(f"  Scheduled Whispers : {whispers_badge}")
        console.print(f"  Experience Mode    : [bold #00ff66]{haunt.mode.value.upper()}[/]")
        console.print("==================================================")
    finally:
        mgr.shutdown()


@audio_app.command(name="enable")
def audio_enable_cmd() -> None:
    """Enable audio for the current configuration and persist preference."""
    from rich.console import Console

    from ghosttrace.audio.manager import AudioManager
    from ghosttrace.config.settings import get_settings

    settings = get_settings()
    mgr = AudioManager(settings=settings)
    try:
        success = mgr.enable(persist=True)
        console = Console()
        if success:
            console.print("[bold #00ff66]Audio subsystem enabled and hardware initialized.[/]")
        else:
            console.print(
                "[bold #ffaa00]Audio enabled in configuration, "
                "but no hardware playback device is currently available.[/]"
            )
    finally:
        mgr.shutdown()


@audio_app.command(name="disable")
def audio_disable_cmd() -> None:
    """Disable audio, stop active playback, and persist preference."""
    from rich.console import Console

    from ghosttrace.audio.manager import AudioManager
    from ghosttrace.config.settings import get_settings

    settings = get_settings()
    mgr = AudioManager(settings=settings)
    try:
        mgr.disable(persist=True)
        console = Console()
        console.print("[dim #ff5555]Audio subsystem disabled and all playback silenced.[/]")
    finally:
        mgr.shutdown()


@audio_app.command(name="volume")
def audio_volume_cmd(
    value: float = typer.Argument(..., help="Master volume between 0.0 and 1.0 (e.g. 0.7)"),
) -> None:
    """Set master output volume and persist preference."""
    from rich.console import Console

    from ghosttrace.audio.manager import AudioManager
    from ghosttrace.config.settings import get_settings

    console = Console()
    if not (0.0 <= value <= 1.0):
        console.print(
            f"[bold #ff5555]Invalid volume {value}. Value must be between 0.0 and 1.0.[/]"
        )
        raise typer.Exit(code=1)

    settings = get_settings()
    mgr = AudioManager(settings=settings)
    try:
        mgr.set_volume(value, persist=True)
        console.print(
            f"[bold #00ff66]Master audio volume set to {int(value * 100)}% ({value:.2f}).[/]"
        )
    finally:
        mgr.shutdown()


@audio_app.command(name="ambient-volume")
def audio_ambient_volume_cmd(
    value: float = typer.Argument(..., help="Ambient volume between 0.0 and 1.0 (e.g. 0.3)"),
) -> None:
    """Set ambient background loop volume independently and persist preference."""
    from rich.console import Console

    from ghosttrace.audio.manager import AudioManager
    from ghosttrace.config.settings import get_settings

    console = Console()
    if not (0.0 <= value <= 1.0):
        console.print(
            f"[bold #ff5555]Invalid ambient volume {value}. Value must be between 0.0 and 1.0.[/]"
        )
        raise typer.Exit(code=1)

    settings = get_settings()
    mgr = AudioManager(settings=settings)
    try:
        mgr.set_ambient_volume(value, persist=True)
        console.print(
            f"[bold #00ff66]Ambient loop volume set to {int(value * 100)}% ({value:.2f}).[/]"
        )
    finally:
        mgr.shutdown()


@audio_app.command(name="mute")
def audio_mute_cmd() -> None:
    """Mute audio output without resetting configured volume levels."""
    from rich.console import Console

    from ghosttrace.audio.manager import AudioManager
    from ghosttrace.config.settings import get_settings

    settings = get_settings()
    mgr = AudioManager(settings=settings)
    try:
        mgr.mute(persist=True)
        console = Console()
        console.print("[bold #ffaa00]Audio output muted.[/]")
    finally:
        mgr.shutdown()


@audio_app.command(name="unmute")
def audio_unmute_cmd() -> None:
    """Unmute audio output and restore previous configured volume."""
    from rich.console import Console

    from ghosttrace.audio.manager import AudioManager
    from ghosttrace.config.settings import get_settings

    settings = get_settings()
    mgr = AudioManager(settings=settings)
    try:
        mgr.unmute(persist=True)
        console = Console()
        console.print(f"[bold #00ff66]Audio output unmuted. Volume: {int(mgr._volume * 100)}%.[/]")
    finally:
        mgr.shutdown()


@audio_app.command(name="keystrokes")
def audio_keystrokes_cmd(
    state: str = typer.Argument(
        ...,
        help="Desired state: 'on', 'enable', 'off', or 'disable'.",
    ),
) -> None:
    """Enable or disable subtle haunted keystroke typing audio effects."""
    from rich.console import Console

    from ghosttrace.audio.manager import AudioManager
    from ghosttrace.config.settings import get_settings

    norm = state.strip().lower()
    console = Console()
    if norm in ("on", "enable", "1", "true"):
        enable_val = True
    elif norm in ("off", "disable", "0", "false"):
        enable_val = False
    else:
        console.print(f"[bold #ff5555]Invalid state '{state}'. Use 'on' or 'off'.[/]")
        raise typer.Exit(code=1)

    settings = get_settings()
    mgr = AudioManager(settings=settings)
    try:
        mgr.set_haunted_keystrokes(enable_val, persist=True)
        if enable_val:
            console.print(
                "[bold #00ff66]Haunted keystrokes ENABLED. Subtle typing manifestations active.[/]"
            )
        else:
            console.print("[bold #ffaa00]Haunted keystrokes DISABLED.[/]")
    finally:
        mgr.shutdown()


@audio_app.command(name="whispers")
def audio_whispers_cmd(
    state: str = typer.Argument(
        ...,
        help="Desired state: 'on', 'enable', 'off', or 'disable'.",
    ),
) -> None:
    """Enable or disable subtle scheduled whisper sound effects."""
    from rich.console import Console

    from ghosttrace.audio.manager import AudioManager
    from ghosttrace.config.settings import get_settings

    norm = state.strip().lower()
    console = Console()
    if norm in ("on", "enable", "1", "true"):
        enable_val = True
    elif norm in ("off", "disable", "0", "false"):
        enable_val = False
    else:
        console.print(f"[bold #ff5555]Invalid state '{state}'. Use 'on' or 'off'.[/]")
        raise typer.Exit(code=1)

    settings = get_settings()
    mgr = AudioManager(settings=settings)
    try:
        mgr.set_scheduled_whispers(enable_val, persist=True)
        if enable_val:
            console.print("[bold #00ff66]Scheduled whispers ENABLED. Atmospheric cues active.[/]")
        else:
            console.print("[bold #ffaa00]Scheduled whispers DISABLED.[/]")
    finally:
        mgr.shutdown()


@audio_app.command(name="test")
def audio_test_cmd() -> None:
    """Play a short verification sound effect to test playback output."""
    from rich.console import Console

    from ghosttrace.audio.manager import AudioManager
    from ghosttrace.config.settings import get_settings

    settings = get_settings()
    mgr = AudioManager(settings=settings)
    console = Console()
    try:
        if not mgr.settings.audio_enabled:
            console.print(
                "[dim #ffaa00]Cannot test audio: audio subsystem is currently DISABLED. "
                "Use 'ghosttrace audio enable' first.[/]"
            )
            return

        if mgr._is_muted:
            console.print(
                "[dim #ffaa00]Cannot test audio: audio is currently MUTED. "
                "Use 'ghosttrace audio unmute' first.[/]"
            )
            return

        if not mgr.backend.is_available():
            console.print("[bold #ff5555]Audio playback hardware is UNAVAILABLE on this host.[/]")
            return

        dispatched = mgr.play_test_sound()
        if dispatched:
            import time

            console.print("[bold #00ff66]Dispatched test sound effect (notification ping).[/]")
            time.sleep(1.2)
        else:
            console.print("[bold #ff5555]Failed to dispatch test sound.[/]")
    finally:
        mgr.shutdown()


def main(args: list[str] | None = None) -> int:
    """Standard CLI entry point returning exit code."""
    if hasattr(sys.stdout, "reconfigure"):
        with contextlib.suppress(Exception):
            sys.stdout.reconfigure(errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        with contextlib.suppress(Exception):
            sys.stderr.reconfigure(errors="replace")
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
