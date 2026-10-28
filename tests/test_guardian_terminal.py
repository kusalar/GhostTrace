"""Unit tests for the guard terminal command family and Textual UI integration."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest
from ghosttrace.config.settings import Settings
from ghosttrace.developer.engine import DeveloperEngine
from ghosttrace.ghost.engine import GhostEngine
from ghosttrace.guardian.engine import GuardianEngine
from ghosttrace.guardian.schemas import ExecutionStatus
from ghosttrace.terminal.app import GhostTraceApp
from ghosttrace.terminal.command_registry import CommandContext
from ghosttrace.terminal.commands import handle_guard
from ghosttrace.terminal.history import SessionHistory
from ghosttrace.terminal.widgets.approval_modal import CommandApprovalModal
from ghosttrace.terminal.widgets.conversation import ConversationLog
from ghosttrace.terminal.widgets.input import CommandInput
from ghosttrace.terminal.widgets.status_panel import StatusPanel


@pytest.fixture
def test_settings() -> Settings:
    return Settings()


def create_terminal_context(settings: Settings) -> CommandContext:
    history = SessionHistory()
    ghost_engine = GhostEngine(settings)
    dev_engine = DeveloperEngine(settings, ghost_engine=ghost_engine)
    guard_engine = GuardianEngine(settings)

    mock_ai = MagicMock()
    mock_ai.ghost_engine = ghost_engine
    mock_ai.developer_engine = dev_engine
    mock_ai.guardian_engine = guard_engine

    return CommandContext(
        settings=settings,
        history=history,
        ai_engine=mock_ai,
        ghost_engine=ghost_engine,
        dev_engine=dev_engine,
        guardian_engine=guard_engine,
    )


def test_guard_status_and_summary(test_settings: Settings) -> None:
    """Verify 'guard' and 'guard status' display telemetry snapshot."""
    ctx = create_terminal_context(test_settings)
    res = handle_guard([], ctx)
    assert res.success is True
    assert "COMMAND GUARDIAN & EXECUTION SAFETY STATUS" in str(res.output)
    assert "Guardian Subsystem : ACTIVE" in str(res.output)

    res_status = handle_guard(["status"], ctx)
    assert res_status.success is True
    assert "Approval Enforced  : YES" in str(res_status.output)


def test_guard_help(test_settings: Settings) -> None:
    """Verify 'guard help' displays command reference and examples."""
    ctx = create_terminal_context(test_settings)
    res = handle_guard(["help"], ctx)
    assert res.success is True
    assert "GHOSTTRACE COMMAND GUARDIAN" in str(res.output)
    assert "guard analyze" in str(res.output)
    assert "guard run" in str(res.output)


def test_guard_enable_and_disable(test_settings: Settings) -> None:
    """Verify toggling Guardian subsystem via terminal commands."""
    ctx = create_terminal_context(test_settings)

    res_disable = handle_guard(["disable"], ctx)
    assert res_disable.success is True
    assert ctx.guardian_engine.is_enabled is False

    res_enable = handle_guard(["enable"], ctx)
    assert res_enable.success is True
    assert ctx.guardian_engine.is_enabled is True


def test_guard_analyze_command(test_settings: Settings) -> None:
    """Verify 'guard analyze' outputs static analysis reports."""
    ctx = create_terminal_context(test_settings)

    # Missing command
    res_err = handle_guard(["analyze"], ctx)
    assert res_err.success is False
    assert "Usage: guard analyze" in str(res_err.output)

    # Harmless command
    res_safe = handle_guard(["analyze", "python", "--version"], ctx)
    assert res_safe.success is True
    assert "STATIC ANALYSIS REPORT" in str(res_safe.output)
    assert "SAFE" in str(res_safe.output)

    # Destructive command
    res_blocked = handle_guard(["analyze", "format", "C:"], ctx)
    assert res_blocked.success is True
    assert "BLOCKED" in str(res_blocked.output)


def test_guard_explain_command(test_settings: Settings) -> None:
    """Verify 'guard explain' outputs human-readable purpose and risks."""
    ctx = create_terminal_context(test_settings)

    res_err = handle_guard(["explain"], ctx)
    assert res_err.success is False
    assert "Usage: guard explain" in str(res_err.output)

    res_explain = handle_guard(["explain", "git", "reset", "--hard"], ctx)
    assert res_explain.success is True
    assert "COMMAND EXPLANATION & PURPOSE" in str(res_explain.output)
    assert "HIGH RISK" in str(res_explain.output)


def test_guard_run_and_approve_flow(test_settings: Settings) -> None:
    """Verify 'guard run' generates approval preview and 'guard approve' executes."""
    ctx = create_terminal_context(test_settings)

    # 1. guard run with harmless command
    res_run = handle_guard(["run", sys.executable, "--version"], ctx)
    assert res_run.success is True
    assert "COMMAND EXECUTION APPROVAL PREVIEW" in str(res_run.output)
    assert "Approval Token :" in str(res_run.output)
    assert ctx.guardian_engine.approval_mgr.pending_count == 1

    # 2. guard approve (uses latest pending)
    res_approve = handle_guard(["approve"], ctx)
    assert res_approve.success is True
    assert "EXECUTION RESULT" in str(res_approve.output)
    assert "[SUCCESS]" in str(res_approve.output)

    # Pending count is now 0
    assert ctx.guardian_engine.approval_mgr.pending_count == 0


def test_guard_run_blocked_command(test_settings: Settings) -> None:
    """Verify 'guard run' rejects BLOCKED commands immediately."""
    ctx = create_terminal_context(test_settings)

    res_blocked = handle_guard(["run", "format", "C:"], ctx)
    assert res_blocked.success is False
    assert "Execution request rejected" in str(res_blocked.output)
    assert "BLOCKED" in str(res_blocked.output)


def test_guard_approve_without_pending(test_settings: Settings) -> None:
    """Verify 'guard approve' without pending request returns clear error."""
    ctx = create_terminal_context(test_settings)

    res = handle_guard(["approve"], ctx)
    assert res.success is False
    assert "No pending approval request found" in str(res.output)


def test_guard_cancel_and_history(test_settings: Settings) -> None:
    """Verify cancelling approval and viewing/clearing session history."""
    ctx = create_terminal_context(test_settings)

    # Run command to stage approval
    handle_guard(["run", sys.executable, "--version"], ctx)
    assert ctx.guardian_engine.approval_mgr.pending_count == 1

    # Cancel approval
    res_cancel = handle_guard(["cancel"], ctx)
    assert res_cancel.success is True
    assert ctx.guardian_engine.approval_mgr.pending_count == 0

    # History shows cancelled request
    res_hist = handle_guard(["history"], ctx)
    assert res_hist.success is True
    from rich.table import Table

    assert isinstance(res_hist.output, Table)
    assert any(
        e.execution_status == ExecutionStatus.CANCELLED for e in ctx.guardian_engine.get_history()
    )

    # Clear history
    res_clear = handle_guard(["clear"], ctx)
    assert res_clear.success is True
    assert "cleared" in str(res_clear.output).lower()

    res_empty_hist = handle_guard(["history"], ctx)
    assert "No commands executed" in str(res_empty_hist.output)


def test_guard_unknown_subcommand(test_settings: Settings) -> None:
    """Verify unknown subcommand returns helpful error."""
    ctx = create_terminal_context(test_settings)
    res = handle_guard(["nonexistent_subcmd"], ctx)
    assert res.success is False
    assert "Unknown guard subcommand" in str(res.output)


@pytest.mark.asyncio
async def test_app_guard_run_triggers_approval_modal() -> None:
    """Verify 'guard run' in Textual UI presents CommandApprovalModal dialog."""
    app = GhostTraceApp()
    async with app.run_test() as pilot:
        cmd_input = app.query_one("#command-input", CommandInput)

        # Submit 'guard run python --version'
        cmd_input.value = "guard run python --version"
        await pilot.press("enter")
        await pilot.pause()

        # Approval modal must be pushed and active on the screen stack
        assert len(app.screen_stack) > 1
        modal = app.screen_stack[-1]
        assert isinstance(modal, CommandApprovalModal)
        assert "python --version" in modal.request.analysis.original_command

        # Press 'y' to confirm execution
        await pilot.press("y")
        await pilot.pause()

        # Modal should be dismissed
        assert len(app.screen_stack) == 1

        conv_log = app.query_one("#conversation-log", ConversationLog)
        assert any("EXECUTION RESULT" in str(child.render()) for child in conv_log.children)


@pytest.mark.asyncio
async def test_app_guard_run_modal_cancellation() -> None:
    """Verify pressing 'n' cancels the execution in CommandApprovalModal."""
    app = GhostTraceApp()
    async with app.run_test() as pilot:
        cmd_input = app.query_one("#command-input", CommandInput)

        # Submit 'guard run python --version'
        cmd_input.value = "guard run python --version"
        await pilot.press("enter")
        await pilot.pause()

        assert isinstance(app.screen_stack[-1], CommandApprovalModal)

        # Press 'n' to cancel
        await pilot.press("n")
        await pilot.pause()

        # Modal dismissed and cancel notice logged
        assert len(app.screen_stack) == 1
        conv_log = app.query_one("#conversation-log", ConversationLog)
        assert any("cancelled" in str(child.render()).lower() for child in conv_log.children)


@pytest.mark.asyncio
async def test_app_status_panel_shows_guardian() -> None:
    """Verify StatusPanel displays accurate Guardian telemetry row."""
    app = GhostTraceApp()
    async with app.run_test() as pilot:
        status_panel = app.query_one("#status-panel", StatusPanel)
        rendered = str(status_panel._build_content())
        assert "Guardian" in rendered
        assert "ACTIVE (APPROVAL REQUIRED)" in rendered

        # Submit guard disable
        cmd_input = app.query_one("#command-input", CommandInput)
        cmd_input.value = "guard disable"
        await pilot.press("enter")
        await pilot.pause()

        rendered_disabled = str(status_panel._build_content())
        assert "DISABLED" in rendered_disabled
