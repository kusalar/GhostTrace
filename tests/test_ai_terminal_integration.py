"""Tests for Textual terminal integration with local AI inference."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from ghosttrace.ai.engine import AIEngine
from ghosttrace.ai.schemas import AIStatus, ModelStatus
from ghosttrace.config.settings import Settings
from ghosttrace.terminal.app import GhostTraceApp
from ghosttrace.terminal.widgets.conversation import ConversationLog
from ghosttrace.terminal.widgets.header import GhostTraceHeader
from ghosttrace.terminal.widgets.input import CommandInput
from ghosttrace.terminal.widgets.status_panel import StatusPanel


@pytest.mark.asyncio
async def test_terminal_natural_language_missing_model(tmp_path: Path) -> None:
    """When user types query and model is missing, display clear model-not-found advice."""
    missing_model = tmp_path / "nonexistent.gguf"
    settings = Settings(model_path=missing_model)
    app = GhostTraceApp(settings=settings)

    async with app.run_test() as pilot:
        cmd_input = app.query_one("#command-input", CommandInput)
        cmd_input.value = "Explain what a decorator is in Python"
        await pilot.press("enter")

        # Allow background thread/worker to complete
        await pilot.pause()

        conv_log = app.query_one("#conversation-log", ConversationLog)
        rendered_text = "\n".join(
            str(getattr(c, "renderable", c.render())) for c in conv_log.children
        )
        assert "LOCAL AI: MODEL NOT FOUND" in rendered_text
        assert "nonexistent.gguf" in rendered_text
        assert str(app.ai_engine.model_manager.model_path) in rendered_text
        assert "GHOSTTRACE_MODEL_PATH" in rendered_text


@pytest.mark.asyncio
async def test_terminal_natural_language_missing_runtime() -> None:
    """When runtime is missing, natural language query displays runtime unavailable guidance."""
    settings = Settings()
    mock_engine = MagicMock(spec=AIEngine)
    mock_engine.get_status.return_value = AIStatus(
        runtime_available=False,
        runtime_version=None,
        model_status=ModelStatus.UNAVAILABLE,
        model_path=settings.model_path,
        model_exists=False,
        is_loaded=False,
        is_busy=False,
        history_count=0,
        context_size=2048,
        max_tokens=512,
        threads=2,
        gpu_layers=0,
    )
    mock_engine.format_missing_runtime_message.return_value = (
        "LOCAL AI: RUNTIME UNAVAILABLE\n\nllama-cpp-python is not installed."
    )

    app = GhostTraceApp(settings=settings, ai_engine=mock_engine)

    async with app.run_test() as pilot:
        cmd_input = app.query_one("#command-input", CommandInput)
        cmd_input.value = "Hello GhostTrace"
        await pilot.press("enter")
        await pilot.pause()

        conv_log = app.query_one("#conversation-log", ConversationLog)
        rendered = "\n".join(str(getattr(c, "renderable", c.render())) for c in conv_log.children)
        assert "LOCAL AI: RUNTIME UNAVAILABLE" in rendered


@pytest.mark.asyncio
async def test_terminal_natural_language_successful_streaming(tmp_path: Path) -> None:
    """When model and runtime exist, query streams assistant tokens into conversation log."""
    dummy_model = tmp_path / "model.gguf"
    dummy_model.write_bytes(b"GGUF")
    settings = Settings(model_path=dummy_model)

    mock_engine = AIEngine(settings)
    with (
        patch.object(mock_engine, "get_status") as mock_status,
        patch.object(mock_engine, "ask_stream") as mock_stream,
    ):
        mock_status.return_value = AIStatus(
            runtime_available=True,
            runtime_version="0.3.36",
            model_status=ModelStatus.READY,
            model_path=dummy_model,
            model_exists=True,
            is_loaded=True,
            is_busy=False,
            history_count=0,
            context_size=2048,
            max_tokens=512,
            threads=2,
            gpu_layers=0,
        )
        mock_stream.return_value = iter(["A decorator ", "wraps a function."])

        app = GhostTraceApp(settings=settings, ai_engine=mock_engine)

        async with app.run_test() as pilot:
            cmd_input = app.query_one("#command-input", CommandInput)
            cmd_input.value = "What is a decorator?"
            await pilot.press("enter")
            await pilot.pause()

            conv_log = app.query_one("#conversation-log", ConversationLog)
            rendered = "\n".join(
                str(getattr(c, "renderable", c.render())) for c in conv_log.children
            )
            assert "A decorator wraps a function." in rendered
            assert "GHOSTTRACE:" in rendered


@pytest.mark.asyncio
async def test_terminal_busy_state_warning() -> None:
    """When already generating, subsequent query triggers busy warning."""
    app = GhostTraceApp()
    async with app.run_test() as pilot:
        app.is_generating = True
        cmd_input = app.query_one("#command-input", CommandInput)
        cmd_input.value = "Are you busy?"
        await pilot.press("enter")

        conv_log = app.query_one("#conversation-log", ConversationLog)
        rendered = "\n".join(str(getattr(c, "renderable", c.render())) for c in conv_log.children)
        assert "currently generating a response" in rendered


@pytest.mark.asyncio
async def test_terminal_header_and_status_panel_sync(tmp_path: Path) -> None:
    """Header and status panel accurately reflect AI subsystem readiness."""
    dummy_model = tmp_path / "ready.gguf"
    dummy_model.write_bytes(b"GGUF")
    settings = Settings(model_path=dummy_model)

    app = GhostTraceApp(settings=settings)
    async with app.run_test():
        header = app.query_one("#app-header", GhostTraceHeader)
        status_panel = app.query_one("#status-panel", StatusPanel)

        assert header is not None
        assert status_panel._ai_status_text in ("READY", "STANDBY", "LOADED")
