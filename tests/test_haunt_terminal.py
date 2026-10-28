"""Tests for interactive terminal commands (handle_haunt)."""

from __future__ import annotations

from ghosttrace.config.settings import Settings
from ghosttrace.haunt.engine import HauntEngine
from ghosttrace.haunt.schemas import HauntIntensity, HauntMode
from ghosttrace.terminal.command_registry import CommandContext
from ghosttrace.terminal.commands import handle_haunt
from ghosttrace.terminal.history import SessionHistory
from rich.table import Table


def test_handle_haunt_subcommands() -> None:
    """Verify all subcommands of handle_haunt."""
    settings = Settings()
    engine = HauntEngine(settings)
    ctx = CommandContext(settings=settings, history=SessionHistory(), haunt_engine=engine)

    # 1. haunt help
    help_res = handle_haunt(["help"], ctx)
    assert help_res.success is True
    assert "HAUNTED EXPERIENCE & ATMOSPHERIC EVENTS COMMANDS" in str(help_res.output)

    # 2. haunt status
    status_res = handle_haunt(["status"], ctx)
    assert status_res.success is True
    assert "HAUNTED EXPERIENCE STATUS" in str(status_res.output)

    # 3. haunt mode
    mode_show = handle_haunt(["mode"], ctx)
    assert mode_show.success is True
    assert "Current experience mode" in str(mode_show.output)

    mode_set = handle_haunt(["mode", "haunted"], ctx)
    assert mode_set.success is True
    assert "HAUNTED" in str(mode_set.output)
    assert engine.mode == HauntMode.HAUNTED

    mode_invalid = handle_haunt(["mode", "invalid_mode"], ctx)
    assert mode_invalid.success is False
    assert "Invalid experience mode" in str(mode_invalid.output)

    # 4. haunt intensity
    int_show = handle_haunt(["intensity"], ctx)
    assert int_show.success is True
    assert "Current event intensity" in str(int_show.output)

    int_set = handle_haunt(["intensity", "high"], ctx)
    assert int_set.success is True
    assert "HIGH" in str(int_set.output)
    assert engine.intensity == HauntIntensity.HIGH

    # 5. haunt events
    events_res = handle_haunt(["events"], ctx)
    assert events_res.success is True
    assert isinstance(events_res.output, Table)

    # 6. haunt idle
    idle_on = handle_haunt(["idle", "on"], ctx)
    assert idle_on.success is True
    assert "ENABLED" in str(idle_on.output)
    assert engine.scheduler.idle_enabled is True

    idle_off = handle_haunt(["idle", "off"], ctx)
    assert idle_off.success is True
    assert "DISABLED" in str(idle_off.output)
    assert engine.scheduler.idle_enabled is False

    # 7. haunt preview
    prev_res = handle_haunt(["preview"], ctx)
    assert prev_res.success is True
    assert "PREVIEW RESONANCE" in str(prev_res.output)

    # 8. haunt history & clear
    hist_empty = handle_haunt(["history"], ctx)
    assert hist_empty.success is True
    assert "No atmospheric events" in str(hist_empty.output)

    clear_res = handle_haunt(["clear"], ctx)
    assert clear_res.success is True
    assert "cleared" in str(clear_res.output)

    # 9. haunt disable & enable
    dis_res = handle_haunt(["disable"], ctx)
    assert dis_res.success is True
    assert "disabled" in str(dis_res.output)
    assert engine.is_enabled is False

    en_res = handle_haunt(["enable"], ctx)
    assert en_res.success is True
    assert "enabled" in str(en_res.output)
    assert engine.is_enabled is True
