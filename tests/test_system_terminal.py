"""Tests for system terminal command handlers and subcommands."""

from __future__ import annotations

from pathlib import Path

from ghosttrace.config.settings import Settings
from ghosttrace.system.engine import SystemEngine
from ghosttrace.terminal.command_registry import CommandContext
from ghosttrace.terminal.commands import handle_system
from ghosttrace.terminal.history import SessionHistory
from rich.table import Table


def test_system_terminal_subcommands(tmp_path: Path) -> None:
    """Verify all system terminal subcommands:

    help, status, overview, cpu, ram, disk, proc, uptime, health, diagnostics.
    """
    settings = Settings()
    engine = SystemEngine(settings)
    ctx = CommandContext(
        settings=settings,
        history=SessionHistory(),
        system_engine=engine,
    )

    # 1. system help
    res_help = handle_system(["help"], ctx)
    assert res_help.success is True
    assert "SYSTEM AWARENESS & DIAGNOSTICS COMMANDS" in str(res_help.output)

    # 2. system status
    res_status = handle_system(["status"], ctx)
    assert res_status.success is True
    assert "SYSTEM AWARENESS TELEMETRY STATUS" in str(res_status.output)

    # 3. system overview
    res_overview = handle_system(["overview"], ctx)
    assert res_overview.success is True
    assert "SYSTEM & RESOURCE OVERVIEW" in str(res_overview.output)
    assert "Host Platform" in str(res_overview.output)

    # 4. system cpu
    res_cpu = handle_system(["cpu"], ctx)
    assert res_cpu.success is True
    assert "CPU HARDWARE TELEMETRY" in str(res_cpu.output)

    # 5. system memory / ram
    res_mem = handle_system(["memory"], ctx)
    assert res_mem.success is True
    assert "PHYSICAL RAM TELEMETRY" in str(res_mem.output)

    res_ram = handle_system(["ram"], ctx)
    assert res_ram.success is True
    assert "PHYSICAL RAM TELEMETRY" in str(res_ram.output)

    # 6. system disk
    res_disk = handle_system(["disk"], ctx)
    assert res_disk.success is True
    assert isinstance(res_disk.output, Table)

    # 7. system processes / proc
    res_proc = handle_system(["processes"], ctx)
    assert res_proc.success is True
    assert "PROCESS TELEMETRY & FOOTPRINT" in str(res_proc.output)

    # 8. system uptime
    res_up = handle_system(["uptime"], ctx)
    assert res_up.success is True
    assert "SYSTEM & APPLICATION UPTIME" in str(res_up.output)

    # 9. system health
    res_health = handle_system(["health"], ctx)
    assert res_health.success is True
    assert isinstance(res_health.output, Table)

    # 10. system diagnostics (in-terminal)
    res_diag = handle_system(["diagnostics"], ctx)
    assert res_diag.success is True
    assert "GHOSTTRACE DIAGNOSTIC REPORT" in str(res_diag.output)

    # 11. system diagnostics with file export
    export_file = tmp_path / "out_report.json"
    res_export = handle_system(["diagnostics", str(export_file)], ctx)
    assert res_export.success is True
    assert "exported successfully" in str(res_export.output).lower()
    assert export_file.is_file()

    # 12. unknown subcommand
    res_unknown = handle_system(["unknown_subcmd"], ctx)
    assert res_unknown.success is False
    assert "Unknown system subcommand" in str(res_unknown.output)
