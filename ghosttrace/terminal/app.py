"""Main Textual application for GhostTrace interactive terminal."""

from __future__ import annotations

import logging
import uuid
from typing import ClassVar

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer, Input, Static

from ghosttrace.ai.engine import AIEngine
from ghosttrace.config.settings import Settings, get_settings
from ghosttrace.ghost.engine import GhostEngine
from ghosttrace.terminal.command_parser import parse_command_line
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
        ai_engine: AIEngine | None = None,
        ghost_engine: GhostEngine | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.settings = settings or get_settings()
        self.history = SessionHistory()
        self.registry = registry or create_default_registry()
        if ghost_engine is not None:
            self.ghost_engine = ghost_engine
        elif (
            ai_engine is not None
            and getattr(ai_engine, "ghost_engine", None) is not None
            and isinstance(ai_engine.ghost_engine, GhostEngine)
        ):
            self.ghost_engine = ai_engine.ghost_engine
        else:
            self.ghost_engine = GhostEngine(self.settings)

        self.ai_engine = ai_engine or AIEngine(self.settings, ghost_engine=self.ghost_engine)
        self.context = CommandContext(
            settings=self.settings,
            history=self.history,
            ai_engine=self.ai_engine,
            ghost_engine=self.ghost_engine,
        )
        self.is_generating = False

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
        """Focus the command input field upon application mount and refresh status."""
        cmd_input = self.query_one("#command-input", CommandInput)
        cmd_input.focus()
        self._refresh_subsystem_status()
        logger.info("GhostTrace terminal UI mounted successfully.")

    def on_unmount(self) -> None:
        """Release local AI resources cleanly upon shutdown."""
        self.ai_engine.unload_model()
        logger.info("GhostTrace terminal UI unmounted.")

    def _refresh_subsystem_status(self) -> None:
        """Synchronize header badge and status panel with actual AI and Ghost subsystem state."""
        try:
            status = self.ai_engine.get_status()
            header = self.query_one("#app-header", GhostTraceHeader)
            status_panel = self.query_one("#status-panel", StatusPanel)

            # Update AI engine status badges
            if not status.runtime_available:
                header.update_ai_status("NO RUNTIME", "bold #ff5555")
                status_panel.update_ai_status("RUNTIME MISSING")
            elif status.is_loaded:
                header.update_ai_status("LOADED", "bold #33ff33")
                status_panel.update_ai_status("LOADED")
            elif status.model_exists:
                header.update_ai_status("READY", "bold #00ff66")
                status_panel.update_ai_status("READY")
            else:
                header.update_ai_status("STANDBY", "bold #ffaa00")
                status_panel.update_ai_status("STANDBY")

            # Update Ghost persona and mood telemetry
            if self.ghost_engine is not None:
                header.update_ghost_status(
                    profile_name=self.ghost_engine.active_profile.name,
                    mood_name=self.ghost_engine.current_mood.value,
                    is_active=self.ghost_engine.is_enabled,
                )
                status_panel.update_ghost_status(
                    profile=self.ghost_engine.active_profile.name,
                    mood=self.ghost_engine.current_mood.value,
                    is_active=self.ghost_engine.is_enabled,
                )
        except Exception as exc:
            logger.debug("Could not refresh subsystem status: %s", exc)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle command submission or route natural-language input to AI engine."""
        raw_text = event.value.strip()
        event.input.value = ""

        if not raw_text:
            return

        conv_log = self.query_one("#conversation-log", ConversationLog)
        status_panel = self.query_one("#status-panel", StatusPanel)

        parsed = parse_command_line(raw_text)
        if parsed is not None and self.registry.get(parsed.name) is not None:
            # Route to built-in command handler
            result = self.registry.execute(raw_text, self.context)
            status_panel.update_command_count(self.history.count)
            self._refresh_subsystem_status()

            if result.should_clear:
                conv_log.clear_log()
            else:
                conv_log.add_exchange(raw_text, result)

            if result.should_exit:
                self.exit(0)
            return

        # Route natural language query to local AI engine
        self.history.add(raw_text)
        status_panel.update_command_count(self.history.count)

        if self.is_generating:
            conv_log.add_busy_warning(raw_text)
            return

        self._dispatch_ai_query(raw_text)

    @work(thread=True)
    def _dispatch_ai_query(self, query: str) -> None:
        """Execute local model inference in a background thread to prevent UI freezing."""
        self.is_generating = True
        conv_log = self.query_one("#conversation-log", ConversationLog)
        header = self.query_one("#app-header", GhostTraceHeader)

        self.call_from_thread(header.update_ai_status, "THINKING...", "bold #ffff33")

        widget_id = f"ai-resp-{uuid.uuid4().hex[:8]}"
        self.call_from_thread(conv_log.add_pending_ai_query, query, widget_id)

        try:
            status = self.ai_engine.get_status()
            if not status.runtime_available:
                msg = self.ai_engine.format_missing_runtime_message()
                self.call_from_thread(conv_log.update_ai_response, widget_id, msg, False)
                return

            if not status.model_exists:
                msg = self.ai_engine.format_missing_model_message()
                self.call_from_thread(conv_log.update_ai_response, widget_id, msg, False)
                return

            collected: list[str] = []
            for token in self.ai_engine.ask_stream(query):
                collected.append(token)
                current = "".join(collected)
                self.call_from_thread(conv_log.update_ai_stream, widget_id, current)

            final_text = "".join(collected).strip()
            self.call_from_thread(conv_log.update_ai_response, widget_id, final_text, True)
        except Exception as exc:
            logger.exception("AI query generation failed: %s", exc)
            self.call_from_thread(
                conv_log.update_ai_response, widget_id, f"Inference error: {exc}", False
            )
        finally:
            self.is_generating = False
            self.call_from_thread(self._refresh_subsystem_status)

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
        if self.is_generating:
            self.ai_engine.stop_generation()
