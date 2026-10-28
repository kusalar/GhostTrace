"""Tests for the InferenceEngine execution wrapper."""

from unittest.mock import MagicMock

import pytest
from ghosttrace.ai.exceptions import InferenceError, ModelBusyError
from ghosttrace.ai.inference import InferenceEngine
from ghosttrace.ai.schemas import InferenceConfig


def test_inference_generate_synchronous() -> None:
    """Verify synchronous chat completion parses response and token usage."""
    config = InferenceConfig(max_tokens=256, temperature=0.5, top_p=0.95)
    engine = InferenceEngine(config)

    mock_model = MagicMock()
    mock_model.create_chat_completion.return_value = {
        "id": "chatcmpl-test",
        "choices": [
            {
                "message": {"content": "A Python decorator wraps a function."},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 15,
            "completion_tokens": 8,
            "total_tokens": 23,
        },
    }

    messages = [{"role": "user", "content": "Explain decorators"}]
    result = engine.generate(mock_model, messages)

    assert result.text == "A Python decorator wraps a function."
    assert result.finish_reason == "stop"
    assert result.prompt_tokens == 15
    assert result.completion_tokens == 8
    assert result.total_tokens == 23
    assert result.duration_seconds >= 0.0

    mock_model.create_chat_completion.assert_called_once_with(
        messages=messages,
        max_tokens=256,
        temperature=0.5,
        top_p=0.95,
        stream=False,
    )


def test_inference_generate_stream() -> None:
    """Verify streaming generation yields token deltas sequentially."""
    config = InferenceConfig(max_tokens=100)
    engine = InferenceEngine(config)

    chunks = [
        {"choices": [{"delta": {"content": "Hello"}}]},
        {"choices": [{"delta": {"content": " world"}}]},
        {"choices": [{"delta": {"content": "!"}}]},
    ]
    mock_model = MagicMock()
    mock_model.create_chat_completion.return_value = iter(chunks)

    messages = [{"role": "user", "content": "Hi"}]
    tokens = list(engine.generate_stream(mock_model, messages))

    assert tokens == ["Hello", " world", "!"]
    mock_model.create_chat_completion.assert_called_once_with(
        messages=messages,
        max_tokens=100,
        temperature=0.7,
        top_p=0.9,
        stream=True,
    )


def test_inference_streaming_stop_early() -> None:
    """Verify stop() signal interrupts streaming iteration cleanly."""
    engine = InferenceEngine()

    def stream_generator():
        yield {"choices": [{"delta": {"content": "Token1"}}]}
        engine.stop()
        yield {"choices": [{"delta": {"content": "Token2"}}]}
        yield {"choices": [{"delta": {"content": "Token3"}}]}

    mock_model = MagicMock()
    mock_model.create_chat_completion.return_value = stream_generator()

    tokens = list(engine.generate_stream(mock_model, []))
    assert tokens == ["Token1"]


def test_inference_prevents_concurrent_requests() -> None:
    """Attempting simultaneous generation raises ModelBusyError."""
    engine = InferenceEngine()
    engine._busy_lock.acquire()  # Simulate ongoing inference

    mock_model = MagicMock()
    try:
        with pytest.raises(ModelBusyError):
            engine.generate(mock_model, [])
        with pytest.raises(ModelBusyError):
            list(engine.generate_stream(mock_model, []))
    finally:
        engine._busy_lock.release()


def test_inference_handles_generation_exception() -> None:
    """Exceptions during inference are wrapped in InferenceError and release lock."""
    engine = InferenceEngine()
    mock_model = MagicMock()
    mock_model.create_chat_completion.side_effect = RuntimeError("llama_decode error")

    with pytest.raises(InferenceError) as exc_info:
        engine.generate(mock_model, [])
    assert "Model generation failed" in str(exc_info.value)
    assert engine.is_busy is False
    assert not engine._busy_lock.locked()
