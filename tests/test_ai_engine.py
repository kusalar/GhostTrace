"""Tests for the high-level AIEngine facade."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from ghosttrace.ai.engine import AIEngine
from ghosttrace.ai.schemas import ChatRole, InferenceResult, ModelStatus
from ghosttrace.config.settings import Settings


def test_ai_engine_initialization_and_status(tmp_path: Path) -> None:
    """Verify engine initializes subcomponents and provides complete status."""
    dummy_model = tmp_path / "model.gguf"
    dummy_model.write_bytes(b"GGUF")

    settings = Settings(
        model_path=dummy_model,
        ai_context_size=1024,
        ai_max_tokens=256,
        ai_threads=2,
    )
    engine = AIEngine(settings)

    status = engine.get_status()
    assert status.model_path == dummy_model.resolve()
    assert status.model_exists is True
    assert status.model_status == ModelStatus.UNLOADED
    assert status.is_loaded is False
    assert status.is_busy is False
    assert status.history_count == 0
    assert status.context_size == 1024
    assert status.max_tokens == 256
    assert status.threads == 2


def test_ai_engine_ask_end_to_end(tmp_path: Path) -> None:
    """Verify ask() loads model, appends messages, invokes inference, and saves response."""
    dummy_model = tmp_path / "test.gguf"
    dummy_model.write_bytes(b"GGUF")
    engine = AIEngine(Settings(model_path=dummy_model))

    mock_llama = MagicMock()
    mock_llama.create_chat_completion.return_value = {
        "choices": [
            {"message": {"content": "This is a local AI answer."}, "finish_reason": "stop"}
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 7, "total_tokens": 17},
    }

    with patch.object(engine.model_manager, "load_model", return_value=mock_llama):
        result = engine.ask("What is GhostTrace?")
        assert isinstance(result, InferenceResult)
        assert result.text == "This is a local AI answer."

        # Check conversation history
        msgs = engine.conversation.get_messages()
        assert len(msgs) == 3
        assert msgs[1].role == ChatRole.USER
        assert msgs[1].content == "What is GhostTrace?"
        assert msgs[2].role == ChatRole.ASSISTANT
        assert msgs[2].content == "This is a local AI answer."


def test_ai_engine_ask_stream_end_to_end(tmp_path: Path) -> None:
    """Verify ask_stream() yields tokens and records the full response into conversation."""
    dummy_model = tmp_path / "test.gguf"
    dummy_model.write_bytes(b"GGUF")
    engine = AIEngine(Settings(model_path=dummy_model))

    chunks = [
        {"choices": [{"delta": {"content": "Local "}}]},
        {"choices": [{"delta": {"content": "AI"}}]},
    ]
    mock_llama = MagicMock()
    mock_llama.create_chat_completion.return_value = iter(chunks)

    with patch.object(engine.model_manager, "load_model", return_value=mock_llama):
        tokens = list(engine.ask_stream("Tell me"))
        assert tokens == ["Local ", "AI"]

        msgs = engine.conversation.get_messages()
        assert msgs[-1].role == ChatRole.ASSISTANT
        assert msgs[-1].content == "Local AI"


def test_ai_engine_clear_conversation() -> None:
    """Verify clear_conversation resets conversation history."""
    engine = AIEngine(Settings())
    engine.conversation.add_user_message("Test")
    assert engine.conversation.exchange_count == 1

    engine.clear_conversation()
    assert engine.conversation.exchange_count == 0


def test_ai_engine_format_messages() -> None:
    """Verify missing model and missing runtime instructional messages."""
    engine = AIEngine(Settings())
    missing_model_msg = engine.format_missing_model_message()
    assert "LOCAL AI: MODEL NOT FOUND" in missing_model_msg
    assert "Expected:" in missing_model_msg
    assert "GHOSTTRACE_MODEL_PATH" in missing_model_msg

    missing_runtime_msg = engine.format_missing_runtime_message()
    assert "LOCAL AI: RUNTIME UNAVAILABLE" in missing_runtime_msg
    assert "pip install llama-cpp-python" in missing_runtime_msg


def test_ai_engine_load_unload_and_stop() -> None:
    """Verify load, unload, and stop methods delegate to appropriate managers."""
    engine = AIEngine(Settings())
    with patch.object(engine.model_manager, "load_model") as mock_load:
        engine.load_model()
        mock_load.assert_called_once()

    with patch.object(engine.model_manager, "unload_model", return_value=True) as mock_unload:
        assert engine.unload_model() is True
        mock_unload.assert_called_once()

    with patch.object(engine.inference_engine, "stop") as mock_stop:
        engine.stop_generation()
        mock_stop.assert_called_once()
