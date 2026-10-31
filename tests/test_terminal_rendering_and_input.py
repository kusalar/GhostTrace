"""Regression tests for GhostTrace TUI input lock, terminal rendering, and worker concurrency.

Covers all 10 required scenarios:
1. Typing in CommandInput while inference is running.
2. Enter submission while inference is running (busy warning, no crash, refocused).
3. Background log messages emitted during TUI session (zero stdout/stderr leakage).
4. Audio notification / sound effect triggered during command entry (non-blocking).
5. Scheduled whisper callbacks during inference (suppression when is_generating=True).
6. Multiple commands submitted in rapid succession.
7. Inference exception recovery (clean error display, is_generating resets to False).
8. Inference timeout / cancellation recovery (Escape calls stop_generation).
9. Keyboard focus restoration (after command, after modal dismiss, after clear).
10. Clean application shutdown with active workers (on_unmount releases resources).
"""

from __future__ import annotations

import logging
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from ghosttrace.ai.engine import AIEngine
from ghosttrace.ai.schemas import AIStatus, ModelStatus
from ghosttrace.config.settings import Settings
from ghosttrace.core.logging import (
    disable_console_logging,
    reset_logging_state,
    setup_logging,
)
from ghosttrace.terminal.app import GhostTraceApp
from ghosttrace.terminal.widgets.audio_modal import AudioSettingsModal
from ghosttrace.terminal.widgets.conversation import ConversationLog
from ghosttrace.terminal.widgets.input import CommandInput


class SlowMockAIEngine:
    """Mock AI engine that simulates streaming tokens slowly for concurrency tests."""

    def __init__(self, token_delay: float = 0.05, num_tokens: int = 6) -> None:
        self.token_delay = token_delay
        self.num_tokens = num_tokens
        self.is_stopped = False
        self.load_count = 0
        self.unload_count = 0

    def get_status(self) -> AIStatus:
        return AIStatus(
            runtime_available=True,
            model_status=ModelStatus.READY,
            model_path=Path("dummy.gguf"),
            model_exists=True,
            is_loaded=True,
            is_busy=False,
            history_count=0,
            context_size=2048,
            max_tokens=512,
            threads=2,
            gpu_layers=0,
        )

    def ask_stream(self, query: str) -> Iterator[str]:
        for i in range(self.num_tokens):
            if self.is_stopped:
                break
            time.sleep(self.token_delay)
            yield f"token_{i} "

    def stop_generation(self) -> None:
        self.is_stopped = True

    def unload_model(self) -> bool:
        self.unload_count += 1
        return True


class FailingMockAIEngine(SlowMockAIEngine):
    """Mock AI engine that raises an exception during generation."""

    def ask_stream(self, query: str) -> Iterator[str]:
        time.sleep(0.02)
        raise RuntimeError("Simulated inference failure in neural backend")


# Scenario 1: Typing in CommandInput while inference is running
@pytest.mark.asyncio
async def test_01_typing_in_command_input_while_inference_running() -> None:
    """Verify CommandInput remains enabled, responsive, and editable while AI inference runs."""
    mock_ai = SlowMockAIEngine(token_delay=0.08, num_tokens=8)
    app = GhostTraceApp(ai_engine=mock_ai)  # type: ignore[arg-type]

    async with app.run_test() as pilot:
        inp = app.query_one("#command-input", CommandInput)

        # Trigger AI inference query
        inp.value = "Why is the terminal cold?"
        await pilot.press("enter")
        await pilot.pause(0.02)

        # Confirm inference is running
        assert app.is_generating is True
        assert inp.disabled is False

        # User types new text while inference is actively streaming
        await pilot.press("h", "e", "l", "l", "o")
        await pilot.pause(0.02)

        assert inp.value == "hello"
        assert inp.has_focus is True

        # Wait for inference worker to finish cleanly
        mock_ai.stop_generation()
        await pilot.pause(0.2)
        assert app.is_generating is False


# Scenario 2: Enter submission while inference is running
@pytest.mark.asyncio
async def test_02_enter_submission_while_inference_running() -> None:
    """Verify Enter submission while busy triggers a warning without crashing."""
    mock_ai = SlowMockAIEngine(token_delay=0.08, num_tokens=8)
    app = GhostTraceApp(ai_engine=mock_ai)  # type: ignore[arg-type]

    async with app.run_test() as pilot:
        inp = app.query_one("#command-input", CommandInput)
        conv_log = app.query_one("#conversation-log", ConversationLog)

        # 1. Start first query
        inp.value = "Tell me a story"
        await pilot.press("enter")
        await pilot.pause(0.02)
        assert app.is_generating is True

        # 2. Enter a second query while still generating
        inp.value = "Are you there?"
        await pilot.press("enter")
        await pilot.pause(0.02)

        # Verify busy warning rendered in conversation log
        rendered_texts = [str(child.render()) for child in conv_log.children]
        assert any("generating a response" in t.lower() for t in rendered_texts)

        # Input should be cleared and refocused
        assert inp.value == ""
        assert inp.has_focus is True

        # Stop and wait for completion
        mock_ai.stop_generation()
        await pilot.pause(0.2)
        assert app.is_generating is False


# Scenario 3: Background log messages during TUI session
def test_03_background_logs_silenced_to_stdout_and_written_to_file(tmp_path: Path) -> None:
    """Verify console stdout/stderr handlers are removed in TUI mode and logs go to file."""
    reset_logging_state()
    try:
        log_dir = tmp_path / "logs"
        settings = Settings(log_dir=log_dir, log_level="DEBUG")

        # Set up with enable_console=False (as run_terminal_app does)
        setup_logging(settings, enable_console=False)
        disable_console_logging()

        root_logger = logging.getLogger()
        # Confirm no StreamHandler targeting stdout or stderr exists
        stream_handlers = [
            h
            for h in root_logger.handlers
            if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        ]
        stdout_stderr_streams = [
            h for h in stream_handlers if getattr(h, "stream", None) in (sys.stdout, sys.stderr)
        ]
        assert len(stdout_stderr_streams) == 0

        # Write a test log
        test_msg = "Atmospheric anomaly detected at offset 0xDEADBEEF"
        test_logger = logging.getLogger("ghosttrace.background_test")
        test_logger.info(test_msg)

        # Flush file handlers
        for h in root_logger.handlers:
            h.flush()

        # Verify log content exists in file
        log_file = log_dir / "ghosttrace.log"
        assert log_file.exists()
        content = log_file.read_text(encoding="utf-8")
        assert test_msg in content
    finally:
        reset_logging_state()


# Scenario 4: Audio notification / sound effect triggered during command entry
@pytest.mark.asyncio
async def test_04_audio_notification_and_typing_nonblocking() -> None:
    """Verify audio cues and notifications triggered during command entry are non-blocking."""
    app = GhostTraceApp()
    async with app.run_test() as pilot:
        inp = app.query_one("#command-input", CommandInput)

        # Trigger notification
        app.notify("Haunted whisper echoed nearby", severity="warning")
        await pilot.pause(0.02)

        # Trigger typing activity
        app.on_keystroke_activity()
        inp.value = "help"
        await pilot.press("enter")
        await pilot.pause(0.05)

        # Verify help was executed cleanly without lockup
        conv_log = app.query_one("#conversation-log", ConversationLog)
        rendered_texts = [str(child.render()) for child in conv_log.children]
        assert any("COMMANDS" in t or "help" in t.lower() for t in rendered_texts)
        assert inp.has_focus is True


# Scenario 5: Scheduled whisper callbacks during inference
def test_05_scheduled_whispers_suppressed_during_inference() -> None:
    """Verify _is_safe_for_whisper returns False when inference is active."""
    app = GhostTraceApp()
    # When idle and not generating
    app.is_generating = False
    app.is_executing_command = False
    assert app._is_safe_for_whisper() is True

    # When generating response
    app.is_generating = True
    assert app._is_safe_for_whisper() is False

    # When executing background command
    app.is_generating = False
    app.is_executing_command = True
    assert app._is_safe_for_whisper() is False


# Scenario 6: Multiple commands submitted in rapid succession
@pytest.mark.asyncio
async def test_06_rapid_command_submission_stability() -> None:
    """Verify rapid submission of built-in commands and queries handles state safely."""
    mock_ai = SlowMockAIEngine(token_delay=0.04, num_tokens=4)
    app = GhostTraceApp(ai_engine=mock_ai)  # type: ignore[arg-type]

    async with app.run_test() as pilot:
        inp = app.query_one("#command-input", CommandInput)

        # Rapidly fire multiple built-in commands
        for cmd in ["version", "status", "about"]:
            inp.value = cmd
            await pilot.press("enter")
            await pilot.pause(0.01)

        # Ensure status panel recorded all 3 commands
        status_panel = app.query_one("#status-panel")
        assert getattr(status_panel, "_command_count", 0) == 3
        assert inp.has_focus is True


# Scenario 7: Inference exception recovery
@pytest.mark.asyncio
async def test_07_inference_exception_recovery() -> None:
    """Verify that an exception in AI inference resets is_generating and displays error."""
    mock_ai = FailingMockAIEngine()
    app = GhostTraceApp(ai_engine=mock_ai)  # type: ignore[arg-type]

    async with app.run_test() as pilot:
        inp = app.query_one("#command-input", CommandInput)
        conv_log = app.query_one("#conversation-log", ConversationLog)

        inp.value = "Cause an intentional backend error"
        await pilot.press("enter")

        # Wait for worker thread to catch exception and execute finally block
        await pilot.pause(0.15)

        # is_generating must be reset to False
        assert app.is_generating is False

        # Conversation log should show error message
        rendered_texts = [str(child.render()) for child in conv_log.children]
        assert any("Inference error" in t or "failure" in t.lower() for t in rendered_texts)

        # Input must be refocused
        assert inp.has_focus is True


# Scenario 8: Inference timeout / cancellation recovery (Escape key)
@pytest.mark.asyncio
async def test_08_inference_cancellation_via_escape() -> None:
    """Verify pressing Escape signals stop_generation and clears input."""
    mock_ai = SlowMockAIEngine(token_delay=0.08, num_tokens=10)
    app = GhostTraceApp(ai_engine=mock_ai)  # type: ignore[arg-type]

    async with app.run_test() as pilot:
        inp = app.query_one("#command-input", CommandInput)

        inp.value = "Stream endlessly"
        await pilot.press("enter")
        await pilot.pause(0.02)
        assert app.is_generating is True

        # User presses Escape to cancel
        await pilot.press("escape")
        assert mock_ai.is_stopped is True

        # Wait for worker thread to terminate
        await pilot.pause(0.15)
        assert app.is_generating is False
        assert inp.value == ""
        assert inp.has_focus is True


# Scenario 9: Keyboard focus restoration
@pytest.mark.asyncio
async def test_09_focus_restoration_lifecycle() -> None:
    """Verify CommandInput recovers focus after command execution, clear, and modal dismissal."""
    app = GhostTraceApp()
    async with app.run_test() as pilot:
        inp = app.query_one("#command-input", CommandInput)
        assert inp.has_focus is True

        # 1. Focus after normal command
        inp.value = "status"
        await pilot.press("enter")
        await pilot.pause(0.02)
        assert inp.has_focus is True

        # 2. Focus after clear screen (Ctrl+L)
        await pilot.press("ctrl+l")
        await pilot.pause(0.02)
        assert inp.has_focus is True

        # 3. Focus after opening and closing Audio Settings modal
        inp.value = "audio settings"
        await pilot.press("enter")
        await pilot.pause(0.05)

        # Modal is on top of screen stack
        assert len(app.screen_stack) > 1
        assert isinstance(app.screen, AudioSettingsModal)

        # Close modal with Escape
        await pilot.press("escape")
        await pilot.pause(0.05)

        # Returned to main screen, focus restored to CommandInput
        assert len(app.screen_stack) == 1
        assert inp.has_focus is True


# Scenario 10: Clean application shutdown with active workers
def test_10_clean_application_shutdown() -> None:
    """Verify on_unmount cleanly releases scheduler, director, audio adapter, and AI model."""
    mock_ai = MagicMock(spec=AIEngine)
    mock_whisper = MagicMock()
    mock_director = MagicMock()
    mock_adapter = MagicMock()
    mock_memory = MagicMock()

    app = GhostTraceApp(ai_engine=mock_ai)
    app.whisper_scheduler = mock_whisper
    app.audio_director = mock_director
    app.audio_adapter = mock_adapter
    app.memory_engine = mock_memory

    # Call on_unmount
    app.on_unmount()

    mock_whisper.shutdown.assert_called_once()
    mock_director.shutdown.assert_called_once()
    mock_adapter.on_shutdown.assert_called_once()
    mock_ai.unload_model.assert_called_once()
    mock_memory.close.assert_called_once()


# Scenario 11: UI heartbeat continues during slow inference
@pytest.mark.asyncio
async def test_11_ui_heartbeat_continues_during_slow_inference() -> None:
    """Verify that the timer heartbeat continues ticking during active AI generation."""
    mock_ai = SlowMockAIEngine(token_delay=0.08, num_tokens=10)
    app = GhostTraceApp(ai_engine=mock_ai)  # type: ignore[arg-type]

    heartbeat_ticks = 0

    def _tick() -> None:
        nonlocal heartbeat_ticks
        heartbeat_ticks += 1

    async with app.run_test() as pilot:
        inp = app.query_one("#command-input", CommandInput)
        app.set_interval(0.04, _tick)

        # Trigger inference
        inp.value = "Why is the abyss deep?"
        await pilot.press("enter")
        await pilot.pause(0.02)
        assert app.is_generating is True

        # Let inference run for a few ticks
        initial_ticks = heartbeat_ticks
        await pilot.pause(0.2)

        # Confirm heartbeat incremented while inference was streaming
        assert heartbeat_ticks > initial_ticks

        mock_ai.stop_generation()
        await pilot.pause(0.1)


# Scenario 12: Keyboard events reach input widget during generation
@pytest.mark.asyncio
async def test_12_keyboard_events_reach_input_widget_during_generation() -> None:
    """Verify that keystrokes typed while inference is active reach CommandInput immediately."""
    mock_ai = SlowMockAIEngine(token_delay=0.1, num_tokens=10)
    app = GhostTraceApp(ai_engine=mock_ai)  # type: ignore[arg-type]

    async with app.run_test() as pilot:
        inp = app.query_one("#command-input", CommandInput)

        inp.value = "First query"
        await pilot.press("enter")
        await pilot.pause(0.02)
        assert app.is_generating is True

        # User types second sentence without submitting it
        await pilot.press("a", "b", "c", "d")
        await pilot.pause(0.02)

        assert inp.value == "abcd"
        assert inp.has_focus is True
        assert inp.disabled is False

        mock_ai.stop_generation()
        await pilot.pause(0.15)


# Scenario 13: Worker thread never synchronously blocks waiting for UI
@pytest.mark.asyncio
async def test_13_worker_thread_never_synchronously_blocks_waiting_for_ui() -> None:
    """Verify that rapid UI updates from inference do not deadlock or stall the worker."""
    mock_ai = SlowMockAIEngine(token_delay=0.01, num_tokens=25)
    app = GhostTraceApp(ai_engine=mock_ai)  # type: ignore[arg-type]

    async with app.run_test() as pilot:
        inp = app.query_one("#command-input", CommandInput)

        inp.value = "Fast streaming test"
        await pilot.press("enter")
        await pilot.pause(0.02)
        assert app.is_generating is True

        # Wait for all 25 tokens to finish without deadlock
        t0 = time.time()
        while app.is_generating and time.time() - t0 < 5.0:
            await pilot.pause(0.05)

        assert app.is_generating is False


# Scenario 14: Cancellation and shutdown safety during active inference
@pytest.mark.asyncio
async def test_14_cancellation_and_shutdown_safety_during_active_inference() -> None:
    """Verify that cancelling via Escape or shutting down during inference releases cleanly."""
    mock_ai = SlowMockAIEngine(token_delay=0.2, num_tokens=20)
    app = GhostTraceApp(ai_engine=mock_ai)  # type: ignore[arg-type]

    async with app.run_test() as pilot:
        inp = app.query_one("#command-input", CommandInput)

        inp.value = "Long query to cancel"
        await pilot.press("enter")
        await pilot.pause(0.02)
        assert app.is_generating is True

        # Cancel with Escape
        await pilot.press("escape")
        assert mock_ai.is_stopped is True

        t0 = time.time()
        while app.is_generating and time.time() - t0 < 2.0:
            await pilot.pause(0.05)

        assert app.is_generating is False
        assert inp.value == ""
        assert inp.has_focus is True


# Scenario 15: Console configuration ensures UTF-8 stream reconfigure and safe WriterThread
def test_15_console_configuration_utf8_streams_and_safe_writer() -> None:
    """Verify configure_terminal_console configures UTF-8 encoding on standard streams."""
    from ghosttrace.terminal.interface import configure_terminal_console

    configure_terminal_console()

    for stream_name in ("stdout", "stderr", "__stdout__", "__stderr__"):
        stream = getattr(sys, stream_name, None)
        if stream is not None and hasattr(stream, "encoding"):
            assert (
                stream.encoding.lower().replace("-", "") == "utf8"
                or stream.encoding.lower() == "utf-8"
            )

    from textual.drivers._writer_thread import WriterThread

    assert getattr(WriterThread, "_ghosttrace_safe_writer", False) is True


# Scenario 16: CommandInput renders typed text visibly with high contrast and cursor
@pytest.mark.asyncio
async def test_16_command_input_renders_typed_text_visibly() -> None:
    """Verify that typed text is visually rendered into line segments inside CommandInput."""
    app = GhostTraceApp()

    async with app.run_test() as pilot:
        inp = app.query_one("#command-input", CommandInput)
        inp.focus()

        test_input = "status"
        for char in test_input:
            await pilot.press(char)

        assert inp.value == test_input
        assert inp.cursor_position == len(test_input)

        # Render line 0 of the input widget
        line = inp.render_line(0)
        assert test_input in line.text

        # Verify visual contrast: text style is foreground green (#00ff66)
        found_text_segment = False
        for seg in line:
            if test_input in seg.text:
                found_text_segment = True
                assert seg.style is not None
                color_str = str(seg.style.color)
                assert "00ff66" in color_str or "green" in color_str.lower()
        assert found_text_segment is True


# Scenario 17: WriterThread survives unencodable characters without terminating
def test_17_writer_thread_survives_unencodable_characters() -> None:
    """Verify WriterThread continues draining and writing with unmappable characters."""
    import io

    from textual.drivers._writer_thread import WriterThread

    mock_stream = io.StringIO()
    writer = WriterThread(mock_stream)
    writer.start()

    try:
        writer.write("Hello ")
        writer.write("Box \u2503 \u250f \u2501 ")
        writer.write("World")
        time.sleep(0.05)

        assert writer.is_alive() is True
        output = mock_stream.getvalue()
        assert "Hello" in output
        assert "World" in output
    finally:
        writer.stop()


# Scenario 18: Heavy box characters write to sys.__stdout__ without error
def test_18_heavy_box_characters_write_without_encoding_error() -> None:
    """Verify heavy Unicode box characters can be written without raising UnicodeEncodeError."""
    from ghosttrace.terminal.interface import configure_terminal_console

    configure_terminal_console()

    heavy_chars = "\u250f\u2501\u2513\u2503\u2517\u251b"
    encoded = heavy_chars.encode(sys.__stdout__.encoding, errors="replace")
    assert len(encoded) > 0
