"""Unit tests for ghost terminal commands and Textual integration."""

import pytest
from ghosttrace.config.settings import Settings
from ghosttrace.ghost.engine import GhostEngine
from ghosttrace.ghost.schemas import GhostProfileId
from ghosttrace.terminal.app import GhostTraceApp
from ghosttrace.terminal.command_registry import CommandContext
from ghosttrace.terminal.commands import (
    handle_about,
    handle_ghost,
    handle_status,
)
from ghosttrace.terminal.history import SessionHistory
from ghosttrace.terminal.widgets.header import GhostTraceHeader
from ghosttrace.terminal.widgets.status_panel import StatusPanel


@pytest.fixture
def sample_context():
    settings = Settings(ghost_enabled=True, ghost_profile="forgotten-machine")
    ghost_engine = GhostEngine(settings)
    history = SessionHistory()
    return CommandContext(
        settings=settings,
        history=history,
        ghost_engine=ghost_engine,
    )


def test_ghost_command_no_args(sample_context):
    result = handle_ghost([], sample_context)
    assert result.success is True
    assert "Forgotten Machine" in str(result.output)
    assert "DORMANT" in str(result.output)


def test_ghost_command_status(sample_context):
    result = handle_ghost(["status"], sample_context)
    assert result.success is True
    output_str = str(result.output)
    assert "GHOST PERSONALITY SUBSYSTEM STATUS" in output_str
    assert "forgotten-machine" in output_str
    assert "Curiosity" in output_str


def test_ghost_command_profiles(sample_context):
    result = handle_ghost(["profiles"], sample_context)
    assert result.success is True
    output_str = str(result.output)
    assert "Forgotten Machine" in output_str
    assert "Phantom Coder" in output_str
    assert "Guardian Spirit" in output_str
    assert "* [ACTIVE]" in output_str


def test_ghost_command_set(sample_context):
    # Missing profile argument
    res_err = handle_ghost(["set"], sample_context)
    assert res_err.success is False
    assert "Usage: ghost set" in str(res_err.output)

    # Invalid profile
    res_inv = handle_ghost(["set", "invalid-profile"], sample_context)
    assert res_inv.success is False
    assert "Unknown personality profile" in str(res_inv.output)

    # Valid profile switch
    res_ok = handle_ghost(["set", "phantom-coder"], sample_context)
    assert res_ok.success is True
    assert "Phantom Coder" in str(res_ok.output)
    assert sample_context.ghost_engine.active_profile.id == GhostProfileId.PHANTOM_CODER


def test_ghost_command_traits(sample_context):
    result = handle_ghost(["traits"], sample_context)
    assert result.success is True
    assert "PERSONALITY TRAITS" in str(result.output)
    assert "Curiosity" in str(result.output)


def test_ghost_command_reset(sample_context):
    sample_context.ghost_engine.set_profile("guardian-spirit")
    assert sample_context.ghost_engine.active_profile.id == GhostProfileId.GUARDIAN_SPIRIT

    result = handle_ghost(["reset"], sample_context)
    assert result.success is True
    assert "Forgotten Machine" in str(result.output)
    assert sample_context.ghost_engine.active_profile.id == GhostProfileId.FORGOTTEN_MACHINE


def test_ghost_command_enable_disable(sample_context):
    res_dis = handle_ghost(["disable"], sample_context)
    assert res_dis.success is True
    assert sample_context.ghost_engine.is_enabled is False

    res_en = handle_ghost(["enable"], sample_context)
    assert res_en.success is True
    assert sample_context.ghost_engine.is_enabled is True


def test_ghost_command_unknown_subcommand(sample_context):
    res = handle_ghost(["nonexistent"], sample_context)
    assert res.success is False
    assert "Unknown ghost subcommand" in str(res.output)


def test_step_04_status_and_about_commands(sample_context):
    about_res = handle_about([], sample_context)
    assert "Step 05 / 10 — Developer Intelligence & Coding Assistance" in str(about_res.output)

    status_res = handle_status([], sample_context)
    assert "Ghost Persona (Step 04)     : [OK] ACTIVE" in str(status_res.output)


@pytest.mark.asyncio
async def test_ghost_app_ui_refresh():
    settings = Settings(ghost_enabled=True, ghost_profile="forgotten-machine")
    app = GhostTraceApp(settings=settings)

    async with app.run_test() as pilot:
        await pilot.pause()

        header = app.query_one("#app-header", GhostTraceHeader)
        status_panel = app.query_one("#status-panel", StatusPanel)

        # Header and status panel reflect initial personality
        header_text = str(getattr(header.query_one("#entity-status"), "renderable", ""))
        assert "FORGOTTEN MACHINE" in header_text

        # Switch personality via command registry
        app.registry.execute("ghost set phantom-coder", app.context)
        app._refresh_subsystem_status()
        await pilot.pause()

        header_text2 = str(getattr(header.query_one("#entity-status"), "renderable", ""))
        assert "PHANTOM CODER" in header_text2

        body_text = str(getattr(status_panel.query_one("#status-body"), "renderable", ""))
        assert "Phantom Coder" in body_text
