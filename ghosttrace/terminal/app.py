"""Main Textual application for GhostTrace interactive terminal."""

from __future__ import annotations

import logging
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer, Input, Static

from ghosttrace.config.settings import Settings, get_settings
from ghosttrace.terminal.command_registry import CommandContext, CommandRegistry
from ghosttrace.terminal.commands import create_default_registry
from ghosttrace.terminal.history import SessionHistory
from ghosttrace.terminal.widgets.conversation import ConversationLog
from ghosttrace.terminal.widgets.header import GhostTraceHeader
from ghosttrace.terminal.widgets.input import CommandInput
from ghosttrace.terminal.widgets.status_panel import StatusPanel

logger = logging.getLogger("ghosttrace.terminal.app")


class GhostTraceApp(App[int]):
    """Interactive haunted terminal UI powered by Textual."""

    TITLE = "GhostTrace"
    SUB_TITLE = "The AI That Haunts Your Terminal"

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("ctrl+c", "quit_app", "Quit", show=True, priority=True),
        Binding("ctrl+l", "clear_screen", "Clear", show=True),
        Binding("escape", "cancel_input", "Cancel", show=True),
    ]

    CSS = """
    Screen {
        background: #080c0a;
        color: #00ff66;
        layout: vertical;
    }
    #body-container {
        width: 100%;
        height: 1fr;
        layout: horizontal;
    }
    #input-container {
        dock: bottom;
        height: 3;
        background: #050807;
        layout: horizontal;
        padding: 0 1;
        border-top: solid #00441b;
    }
    #prompt-label {
        width: 7;
        height: 3;
        color: #00ff66;
        text-style: bold;
        content-align: center middle;
    }
    #command-input {
        width: 1fr;
        height: 3;
    }
    Footer {
        dock: bottom;
        background: #060a08;
        color: #558855;
    }
    """

    def __init__(
        self,
        settings: Settings | None = None,
        registry: CommandRegistry | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.settings = settings or get_settings()
        self.history = SessionHistory()
        self.registry = registry or create_default_registry()
        self.context = CommandContext(settings=self.settings, history=self.history)

    def compose(self) -> ComposeResult:
        """Compose interface sections: Header, Conversation + Status, Input bar, Footer."""
        yield GhostTraceHeader(self.settings, id="app-header")

        with Horizontal(id="body-container"):
            yield ConversationLog(id="conversation-log")
            yield StatusPanel(self.settings, id="status-panel")

        with Horizontal(id="input-container"):
            yield Static("ghost>", id="prompt-label")
            yield CommandInput(self.history, id="command-input")

        yield Footer()

    def on_mount(self) -> None:
        """Focus the command input field upon application mount."""
        cmd_input = self.query_one("#command-input", CommandInput)
        cmd_input.focus()
        logger.info("GhostTrace terminal UI mounted successfully.")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle command submission from the CommandInput widget."""
        raw_text = event.value.strip()
        event.input.value = ""

        if not raw_text:
            return

        conv_log = self.query_one("#conversation-log", ConversationLog)
        status_panel = self.query_one("#status-panel", StatusPanel)

        result = self.registry.execute(raw_text, self.context)
        status_panel.update_command_count(self.history.count)

        if result.should_clear:
            conv_log.clear_log()
        else:
            conv_log.add_exchange(raw_text, result)

        if result.should_exit:
            self.exit(0)

    def action_clear_screen(self) -> None:
        """Action handler to clear the conversation log (Ctrl+L)."""
        conv_log = self.query_one("#conversation-log", ConversationLog)
        conv_log.clear_log()

    def action_quit_app(self) -> None:
        """Action handler for clean shutdown (Ctrl+C)."""
        logger.info("User requested application shutdown via shortcut.")
        self.exit(0)

    def action_cancel_input(self) -> None:
        """Action handler to reset input field (Escape)."""
        cmd_input = self.query_one("#command-input", CommandInput)
        cmd_input.value = ""
        self.history.reset_cursor()
