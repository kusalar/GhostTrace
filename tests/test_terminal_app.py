"""Tests for the GhostTrace Textual interactive terminal application."""

from unittest.mock import patch

import pytest
from ghosttrace.config.settings import Settings
from ghosttrace.terminal.app import GhostTraceApp
from ghosttrace.terminal.interface import run_terminal_app
from ghosttrace.terminal.widgets.conversation import ConversationLog
from ghosttrace.terminal.widgets.header import GhostTraceHeader
from ghosttrace.terminal.widgets.input import CommandInput
from ghosttrace.terminal.widgets.status_panel import StatusPanel
from textual.widgets import Static


@pytest.mark.asyncio
async def test_app_mounting_and_welcome_screen() -> None:
    """Verify all widgets mount properly and welcome message is displayed."""
    app = GhostTraceApp()
    async with app.run_test():
        # Verify core widgets exist
        assert app.query_one(GhostTraceHeader) is not None
        assert app.query_one(StatusPanel) is not None
        assert app.query_one(CommandInput) is not None
        assert app.query_one(ConversationLog) is not None

        # Verify welcome message in conversation log
        welcome_widget = app.query_one("#welcome-message", Static)
        assert "Something has awakened" in str(welcome_widget.render())


@pytest.mark.asyncio
async def test_app_command_submission_and_response() -> None:
    """Verify submitting commands renders command and response, and updates status."""
    app = GhostTraceApp()
    async with app.run_test() as pilot:
        cmd_input = app.query_one("#command-input", CommandInput)

        # Submit 'ai' command
        cmd_input.value = "ai"
        await pilot.press("enter")

        conv_log = app.query_one("#conversation-log", ConversationLog)
        assert any("AI ENGINE: NOT CONNECTED" in str(child.render()) for child in conv_log.children)

        # Status panel should reflect 1 command executed
        status_panel = app.query_one("#status-panel", StatusPanel)
        assert status_panel._command_count == 1

        # Submit empty input - should be ignored
        cmd_input.value = "   "
        await pilot.press("enter")
        assert status_panel._command_count == 1


@pytest.mark.asyncio
async def test_app_clear_action_and_command() -> None:
    """Verify conversation buffer clearing via Ctrl+L and 'clear' command."""
    app = GhostTraceApp()
    async with app.run_test() as pilot:
        cmd_input = app.query_one("#command-input", CommandInput)

        cmd_input.value = "status"
        await pilot.press("enter")

        conv_log = app.query_one("#conversation-log", ConversationLog)
        assert len(conv_log.children) > 1

        # Trigger clear command
        cmd_input.value = "clear"
        await pilot.press("enter")

        # Log should now only contain the cleared note
        assert any("cleared" in str(child.render()).lower() for child in conv_log.children)

        # Trigger Ctrl+L shortcut
        await pilot.press("ctrl+l")
        assert any("cleared" in str(child.render()).lower() for child in conv_log.children)


@pytest.mark.asyncio
async def test_app_history_navigation_keys() -> None:
    """Verify Up and Down arrow keys navigate command history."""
    app = GhostTraceApp()
    async with app.run_test() as pilot:
        cmd_input = app.query_one("#command-input", CommandInput)

        # Submit two commands
        cmd_input.value = "version"
        await pilot.press("enter")

        cmd_input.value = "about"
        await pilot.press("enter")

        # Press Up arrow
        await pilot.press("up")
        assert cmd_input.value == "about"

        # Press Up arrow again
        await pilot.press("up")
        assert cmd_input.value == "version"

        # Press Down arrow
        await pilot.press("down")
        assert cmd_input.value == "about"

        # Escape clears input
        await pilot.press("escape")
        assert cmd_input.value == ""


@pytest.mark.asyncio
async def test_app_action_quit_app() -> None:
    """Verify action_quit_app triggers exit cleanly."""
    app = GhostTraceApp()
    async with app.run_test() as pilot:
        await pilot.press("ctrl+c")
        assert app.return_value == 0


@pytest.mark.asyncio
async def test_app_exit_command_submission() -> None:
    """Verify submitting exit command terminates the app cleanly."""
    app = GhostTraceApp()
    async with app.run_test() as pilot:
        cmd_input = app.query_one("#command-input", CommandInput)
        cmd_input.value = "exit"
        await pilot.press("enter")
        assert app.return_value == 0


def test_run_terminal_app_wrapper() -> None:
    """Verify run_terminal_app helper instantiates GhostTraceApp and runs it."""
    with patch.object(GhostTraceApp, "run", return_value=0) as mock_run:
        exit_code = run_terminal_app(Settings())
        assert exit_code == 0
        mock_run.assert_called_once()

    with patch.object(GhostTraceApp, "run", return_value=0) as mock_run_default:
        exit_code_default = run_terminal_app(None)
        assert exit_code_default == 0
        mock_run_default.assert_called_once()
