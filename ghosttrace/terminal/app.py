"""Main Textual application for GhostTrace interactive terminal."""

from __future__ import annotations

import logging
import time
import uuid
from typing import ClassVar

from rich.console import RenderableType
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.notifications import SeverityLevel
from textual.widgets import Footer, Input, Static

from ghosttrace.ai.engine import AIEngine
from ghosttrace.audio.adapter import AudioEventAdapter
from ghosttrace.audio.manager import AudioManager
from ghosttrace.audio.typing_effects import TypingEffectsManager
from ghosttrace.config.settings import Settings, get_settings
from ghosttrace.developer.engine import DeveloperEngine
from ghosttrace.ghost.engine import GhostEngine
from ghosttrace.guardian.engine import GuardianEngine
from ghosttrace.guardian.explanations import format_execution_result
from ghosttrace.guardian.schemas import ExecutionStatus
from ghosttrace.haunt.engine import HauntEngine
from ghosttrace.haunt.schemas import TriggerContext, TriggerType
from ghosttrace.memory.engine import MemoryEngine
from ghosttrace.system.engine import SystemEngine
from ghosttrace.terminal.command_parser import parse_command_line
from ghosttrace.terminal.command_registry import CommandContext, CommandRegistry, CommandResult
from ghosttrace.terminal.commands import create_default_registry
from ghosttrace.terminal.history import SessionHistory
from ghosttrace.terminal.widgets.approval_modal import CommandApprovalModal
from ghosttrace.terminal.widgets.audio_modal import AudioSettingsModal
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
        height: auto;
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
        dev_engine: DeveloperEngine | None = None,
        guardian_engine: GuardianEngine | None = None,
        memory_engine: MemoryEngine | None = None,
        system_engine: SystemEngine | None = None,
        haunt_engine: HauntEngine | None = None,
        audio_manager: AudioManager | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.settings = settings or get_settings()
        self.session_id = uuid.uuid4().hex[:12]
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

        if dev_engine is not None:
            self.dev_engine = dev_engine
        elif (
            ai_engine is not None
            and getattr(ai_engine, "developer_engine", None) is not None
            and isinstance(ai_engine.developer_engine, DeveloperEngine)
        ):
            self.dev_engine = ai_engine.developer_engine
        else:
            self.dev_engine = DeveloperEngine(self.settings, ghost_engine=self.ghost_engine)

        if guardian_engine is not None:
            self.guardian_engine = guardian_engine
        elif (
            ai_engine is not None
            and getattr(ai_engine, "guardian_engine", None) is not None
            and isinstance(ai_engine.guardian_engine, GuardianEngine)
        ):
            self.guardian_engine = ai_engine.guardian_engine
        else:
            self.guardian_engine = GuardianEngine(self.settings)

        if memory_engine is not None:
            self.memory_engine = memory_engine
        elif (
            ai_engine is not None
            and getattr(ai_engine, "memory_engine", None) is not None
            and isinstance(ai_engine.memory_engine, MemoryEngine)
        ):
            self.memory_engine = ai_engine.memory_engine
        else:
            self.memory_engine = MemoryEngine(self.settings)

        if system_engine is not None:
            self.system_engine = system_engine
        elif (
            ai_engine is not None
            and getattr(ai_engine, "system_engine", None) is not None
            and isinstance(ai_engine.system_engine, SystemEngine)
        ):
            self.system_engine = ai_engine.system_engine
        else:
            self.system_engine = SystemEngine(self.settings)

        if haunt_engine is not None:
            self.haunt_engine = haunt_engine
        else:
            self.haunt_engine = HauntEngine(self.settings, ghost_engine=self.ghost_engine)

        if audio_manager is not None:
            self.audio_manager = audio_manager
        else:
            self.audio_manager = AudioManager(self.settings)

        self.audio_adapter = AudioEventAdapter(self.audio_manager)
        self.typing_effects = TypingEffectsManager(
            audio_manager=self.audio_manager,
            audio_adapter=self.audio_adapter,
        )
        self.audio_adapter._typing_effects = self.typing_effects
        self._last_observed_mood: str | None = None
        self._last_observed_haunt_mode: str | None = None
        self.last_user_activity = time.time()

        self.ai_engine = ai_engine or AIEngine(
            self.settings,
            ghost_engine=self.ghost_engine,
            developer_engine=self.dev_engine,
            guardian_engine=self.guardian_engine,
            memory_engine=self.memory_engine,
            system_engine=self.system_engine,
        )
        self.context = CommandContext(
            settings=self.settings,
            history=self.history,
            ai_engine=self.ai_engine,
            ghost_engine=self.ghost_engine,
            dev_engine=self.dev_engine,
            guardian_engine=self.guardian_engine,
            memory_engine=self.memory_engine,
            system_engine=self.system_engine,
            haunt_engine=self.haunt_engine,
            audio_manager=self.audio_manager,
            audio_adapter=self.audio_adapter,
        )
        self.is_generating = False
        self.is_executing_command = False

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

        # Trigger session start atmospheric event if eligible
        start_res = self.haunt_engine.process_trigger(
            TriggerContext(trigger_type=TriggerType.SESSION_START)
        )
        if start_res.fired and start_res.rendered_text:
            conv_log = self.query_one("#conversation-log", ConversationLog)
            conv_log.add_haunt_event(start_res.rendered_text)

        # Periodic lightweight idle check
        self.set_interval(15.0, self._check_idle_whisper)
        logger.info("GhostTrace terminal UI mounted successfully.")

        # Dispatch application startup sound effect
        self.audio_adapter.on_startup()

    def on_unmount(self) -> None:
        """Release local AI and audio resources cleanly upon shutdown."""
        self.audio_adapter.on_shutdown()
        self.ai_engine.unload_model()
        if self.memory_engine is not None:
            self.memory_engine.close()
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
            if self.ghost_engine is not None and isinstance(self.ghost_engine, GhostEngine):
                curr_mood = self.ghost_engine.current_mood.value
                if self._last_observed_mood is not None and self._last_observed_mood != curr_mood:
                    self.audio_adapter.on_mood_shift(self._last_observed_mood, curr_mood)
                self._last_observed_mood = curr_mood

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

            # Update Developer Assistant telemetry
            if self.dev_engine is not None and isinstance(self.dev_engine, DeveloperEngine):
                status_panel.update_dev_status(
                    is_active=self.dev_engine.is_enabled,
                    static_analysis=self.dev_engine._static_analysis_enabled,
                )

            # Update Command Guardian telemetry
            if self.guardian_engine is not None and isinstance(
                self.guardian_engine, GuardianEngine
            ):
                status_panel.update_guardian_status(
                    is_active=self.guardian_engine.is_enabled,
                    execution_enabled=self.guardian_engine.is_execution_enabled,
                    require_approval=self.guardian_engine.policy.require_approval,
                )

            # Update Persistent Memory & Project telemetry
            if self.memory_engine is not None and isinstance(self.memory_engine, MemoryEngine):
                active_proj = self.memory_engine.get_active_project()
                proj_name = active_proj.name if active_proj else None
                status_panel.update_memory_status(
                    is_active=self.memory_engine.is_enabled,
                    project_name=proj_name,
                )

            # Update System telemetry
            if self.system_engine is not None and isinstance(self.system_engine, SystemEngine):
                status_panel.update_system_status(
                    is_active=self.system_engine.is_enabled,
                )

            # Update Haunted Experience telemetry
            if self.haunt_engine is not None and isinstance(self.haunt_engine, HauntEngine):
                curr_haunt_mode = self.haunt_engine.mode.value
                if (
                    self._last_observed_haunt_mode is not None
                    and self._last_observed_haunt_mode != curr_haunt_mode
                ):
                    self.audio_adapter.set_experience_mode(curr_haunt_mode)
                self._last_observed_haunt_mode = curr_haunt_mode

                status_panel.update_haunt_status(
                    is_active=self.haunt_engine.is_enabled,
                    mode=self.haunt_engine.mode.value,
                    intensity=self.haunt_engine.intensity.value,
                )
        except Exception as exc:
            logger.debug("Could not refresh subsystem status: %s", exc)

    def on_keystroke_activity(self) -> None:
        """Handle aggregate typing activity signal from the input widget.

        Strict Privacy Notice:
        No keystroke character, keycode, or text content is ever accepted or inspected.
        """
        if hasattr(self, "typing_effects") and self.typing_effects is not None:
            self.typing_effects.record_keystroke()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle command submission or route natural-language input to AI engine."""
        raw_text = event.value.strip()
        event.input.value = ""

        if not raw_text:
            return

        self.last_user_activity = time.time()
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

            if (
                result.command_name
                and result.command_name not in ("clear", "exit", "help")
                and not result.should_clear
            ):
                disc_res = self.haunt_engine.process_trigger(
                    TriggerContext(
                        trigger_type=TriggerType.COMMAND_DISCOVERY,
                        command_name=result.command_name,
                    )
                )
                if disc_res.fired and disc_res.rendered_text:
                    conv_log.add_haunt_event(disc_res.rendered_text)

            if result.command_name == "guard_run":
                if result.success:
                    latest_req = self.guardian_engine.approval_mgr.get_latest_pending()
                    if latest_req is not None:
                        self.audio_adapter.on_guardian_intercept(
                            latest_req.analysis.original_command
                        )

                        def _on_approval_decision(approved: bool) -> None:
                            if approved:
                                self.audio_adapter.on_guardian_approved(latest_req.token)
                                self._dispatch_approved_execution(
                                    latest_req.token,
                                    latest_req.analysis.original_command,
                                )
                            else:
                                self.audio_adapter.on_guardian_blocked(
                                    latest_req.token, "Cancelled by user"
                                )
                                self.guardian_engine.cancel_approval(latest_req.token)
                                output = (
                                    f"Execution of '{latest_req.analysis.original_command}' "
                                    "was cancelled."
                                )
                                conv_log.add_exchange(
                                    f"guard cancel {latest_req.token}",
                                    CommandResult(
                                        success=True,
                                        output=output,
                                    ),
                                )
                                self._refresh_subsystem_status()

                        self.push_screen(
                            CommandApprovalModal(
                                request=latest_req,
                                timeout_seconds=self.guardian_engine.policy.timeout_seconds,
                                max_output_chars=self.guardian_engine.policy.max_output_chars,
                            ),
                            _on_approval_decision,
                        )
                else:
                    self.audio_adapter.on_guardian_blocked(reason="Execution request rejected")

            if result.command_name == "audio_settings":
                exp_mode = (
                    self.haunt_engine.mode.value
                    if self.haunt_engine is not None and isinstance(self.haunt_engine, HauntEngine)
                    else "normal"
                )
                self.push_screen(
                    AudioSettingsModal(
                        audio_manager=self.audio_manager,
                        audio_adapter=self.audio_adapter,
                        experience_mode=exp_mode,
                    )
                )

            if result.should_exit:
                self.exit(0)
            return

        # Route natural language query to local AI engine
        self.history.add(raw_text)
        status_panel.update_command_count(self.history.count)

        if self.memory_engine is not None and self.memory_engine.is_enabled:
            try:
                self.memory_engine.persist_user_message(self.session_id, raw_text)
            except Exception as exc:
                logger.debug("Failed to persist user message: %s", exc)

        if self.is_generating:
            conv_log.add_busy_warning(raw_text)
            return

        self._dispatch_ai_query(raw_text)

    @work(thread=True)
    def _dispatch_approved_execution(self, token: str, command: str) -> None:
        """Execute approved command in a background worker thread."""
        self.is_executing_command = True
        conv_log = self.query_one("#conversation-log", ConversationLog)

        try:
            exec_res = self.guardian_engine.execute_approved(token=token, command=command)
            formatted = format_execution_result(exec_res)
            self.call_from_thread(
                conv_log.add_exchange,
                f"guard approve {token}",
                CommandResult(
                    success=(exec_res.status == ExecutionStatus.SUCCESS),
                    output=formatted,
                ),
            )
        except Exception as exc:
            logger.exception("Error during approved command background execution: %s", exc)
            self.call_from_thread(
                conv_log.add_exchange,
                f"guard approve {token}",
                CommandResult(
                    success=False,
                    output=f"Execution failed: {exc}",
                ),
            )
        finally:
            self.is_executing_command = False
            self.call_from_thread(self._refresh_subsystem_status)

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
            if self.memory_engine is not None and self.memory_engine.is_enabled and final_text:
                try:
                    self.memory_engine.persist_assistant_message(self.session_id, final_text)
                except Exception as exc:
                    logger.debug("Failed to persist assistant message: %s", exc)

            is_coding = (
                self.dev_engine is not None
                and self.dev_engine.is_enabled
                and self.dev_engine.is_developer_query(query)
            )
            if is_coding:
                self.audio_adapter.on_coding_success("ai_developer_query")

            coding_res = self.haunt_engine.process_trigger(
                TriggerContext(
                    trigger_type=TriggerType.CODING_SUCCESS,
                    dev_intent="general_programming",
                )
            )
            if coding_res.fired and coding_res.rendered_text:
                self.call_from_thread(conv_log.add_haunt_event, coding_res.rendered_text)
        except Exception as exc:
            logger.exception("AI query generation failed: %s", exc)
            self.audio_adapter.on_app_error(exc)
            self.call_from_thread(
                conv_log.update_ai_response, widget_id, f"Inference error: {exc}", False
            )
            err_res = self.haunt_engine.process_trigger(
                TriggerContext(
                    trigger_type=TriggerType.APP_ERROR,
                    error_message=str(exc),
                )
            )
            if err_res.fired and err_res.rendered_text:
                self.call_from_thread(conv_log.add_haunt_event, err_res.rendered_text)
        finally:
            self.is_generating = False
            self.call_from_thread(self._refresh_subsystem_status)

    def _check_idle_whisper(self) -> None:
        """Check for genuine terminal idle whisper events."""
        if self.is_generating or self.is_executing_command:
            return

        idle_secs = time.time() - self.last_user_activity
        res = self.haunt_engine.process_trigger(
            TriggerContext(
                trigger_type=TriggerType.IDLE_TICK,
                idle_seconds=idle_secs,
            )
        )
        if res.fired and res.rendered_text:
            conv_log = self.query_one("#conversation-log", ConversationLog)
            conv_log.add_haunt_event(res.rendered_text)

    def action_clear_screen(self) -> None:
        """Action handler to clear the conversation log (Ctrl+L)."""
        conv_log = self.query_one("#conversation-log", ConversationLog)
        conv_log.clear_log()

    def notify(
        self,
        message: RenderableType | str,
        *,
        title: RenderableType | str = "",
        severity: SeverityLevel = "information",
        timeout: float | None = None,
    ) -> None:
        """Post notification and dispatch corresponding audio sound cue."""
        super().notify(message, title=title, severity=severity, timeout=timeout)
        if hasattr(self, "audio_adapter") and self.audio_adapter is not None:
            self.audio_adapter.on_notification(message=str(message), severity=str(severity))

    def action_quit_app(self) -> None:
        """Action handler for clean shutdown (Ctrl+C)."""
        logger.info("User requested application shutdown via shortcut.")
        self.audio_adapter.on_shutdown()
        self.exit(0)

    def action_cancel_input(self) -> None:
        """Action handler to reset input field (Escape)."""
        cmd_input = self.query_one("#command-input", CommandInput)
        cmd_input.value = ""
        self.history.reset_cursor()
        if self.is_generating:
            self.ai_engine.stop_generation()
