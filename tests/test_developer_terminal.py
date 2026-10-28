"""Unit tests for the dev terminal command family and integration."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from ghosttrace.ai.schemas import AIStatus, InferenceResult, ModelStatus
from ghosttrace.config.settings import Settings
from ghosttrace.developer.engine import DeveloperEngine
from ghosttrace.ghost.engine import GhostEngine
from ghosttrace.terminal.command_registry import CommandContext
from ghosttrace.terminal.commands import handle_about, handle_dev, handle_status
from ghosttrace.terminal.history import SessionHistory


@pytest.fixture
def test_settings() -> Settings:
    return Settings()


def create_mock_context(
    settings: Settings,
    runtime_available: bool = True,
    model_exists: bool = True,
) -> CommandContext:
    history = SessionHistory()
    ghost_engine = GhostEngine(settings)
    dev_engine = DeveloperEngine(settings, ghost_engine=ghost_engine)

    mock_ai = MagicMock()
    mock_ai.ghost_engine = ghost_engine
    mock_ai.developer_engine = dev_engine
    mock_ai.get_status.return_value = AIStatus(
        runtime_available=runtime_available,
        runtime_version="0.3.7" if runtime_available else None,
        model_status=ModelStatus.READY if model_exists else ModelStatus.NOT_FOUND,
        model_path="models/test.gguf",
        model_exists=model_exists,
        is_loaded=False,
        is_busy=False,
        history_count=0,
        context_size=2048,
        max_tokens=512,
        threads=2,
        gpu_layers=0,
    )
    mock_ai.format_missing_runtime_message.return_value = "RUNTIME MISSING MESSAGE"
    mock_ai.format_missing_model_message.return_value = "MODEL MISSING MESSAGE"
    mock_ai.inference_engine.generate.return_value = InferenceResult(
        text="Mocked developer assistant response.",
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30,
        elapsed_seconds=0.1,
        tokens_per_second=200.0,
    )

    return CommandContext(
        settings=settings,
        history=history,
        ai_engine=mock_ai,
        ghost_engine=ghost_engine,
        dev_engine=dev_engine,
    )


def test_handle_dev_summary(test_settings: Settings) -> None:
    ctx = create_mock_context(test_settings)
    res = handle_dev([], ctx)
    assert res.success is True
    assert "DEVELOPER ASSISTANT SUBSYSTEM" in str(res.output)
    assert "Status          : ACTIVE" in str(res.output)


def test_handle_dev_help(test_settings: Settings) -> None:
    ctx = create_mock_context(test_settings)
    res = handle_dev(["help"], ctx)
    assert res.success is True
    assert "GHOSTTRACE DEVELOPER INTELLIGENCE" in str(res.output)


def test_handle_dev_enable_disable(test_settings: Settings) -> None:
    ctx = create_mock_context(test_settings)
    res_dis = handle_dev(["disable"], ctx)
    assert res_dis.success is True
    assert "disabled" in str(res_dis.output)
    assert ctx.dev_engine.is_enabled is False

    res_en = handle_dev(["enable"], ctx)
    assert res_en.success is True
    assert "enabled" in str(res_en.output)
    assert ctx.dev_engine.is_enabled is True


def test_handle_dev_language(test_settings: Settings) -> None:
    ctx = create_mock_context(test_settings)
    res_list = handle_dev(["language"], ctx)
    assert res_list.success is True
    assert "SUPPORTED PROGRAMMING LANGUAGES" in str(res_list.output)

    res_detect = handle_dev(["language", "def foo(): pass"], ctx)
    assert res_detect.success is True
    assert "DETECTED LANGUAGE: Python" in str(res_detect.output)

    res_unknown = handle_dev(["language", "zz_not_a_lang_12345"], ctx)
    assert res_unknown.success is True
    assert "Could not identify language" in str(res_unknown.output)


def test_handle_dev_analyze(test_settings: Settings) -> None:
    ctx = create_mock_context(test_settings)
    res_empty = handle_dev(["analyze"], ctx)
    assert res_empty.success is False
    assert "Usage: dev analyze" in str(res_empty.output)

    snippet = "def factorial(n): return 1 if n <= 1 else n * factorial(n-1)"
    res = handle_dev(["analyze", snippet], ctx)
    assert res.success is True
    assert "LOCAL STATIC ANALYSIS REPORT" in str(res.output)
    assert "factorial" in str(res.output)


def test_handle_dev_workflow_missing_args(test_settings: Settings) -> None:
    ctx = create_mock_context(test_settings)
    for sub in ("explain", "debug", "review", "generate", "refactor", "tests"):
        res = handle_dev([sub], ctx)
        assert res.success is False
        assert f"Usage: dev {sub}" in str(res.output)


def test_handle_dev_workflow_missing_runtime(test_settings: Settings) -> None:
    ctx = create_mock_context(test_settings, runtime_available=False)
    res = handle_dev(["explain", "def foo(): pass"], ctx)
    assert res.success is False
    assert "RUNTIME MISSING MESSAGE" in str(res.output)


def test_handle_dev_workflow_missing_model(test_settings: Settings) -> None:
    ctx = create_mock_context(test_settings, runtime_available=True, model_exists=False)
    res = handle_dev(["explain", "def foo(): pass"], ctx)
    assert res.success is False
    assert "MODEL MISSING MESSAGE" in str(res.output)


def test_handle_dev_workflow_success(test_settings: Settings) -> None:
    ctx = create_mock_context(test_settings, runtime_available=True, model_exists=True)
    res = handle_dev(["explain", "def add(a, b): return a + b"], ctx)
    assert res.success is True
    assert "[CODE EXPLANATION (PYTHON)]" in str(res.output)
    assert "Mocked developer assistant response" in str(res.output)


def test_handle_dev_unknown_subcommand(test_settings: Settings) -> None:
    ctx = create_mock_context(test_settings)
    res = handle_dev(["foobar"], ctx)
    assert res.success is False
    assert "Unknown dev subcommand 'foobar'" in str(res.output)


def test_handle_status_and_about_step05(test_settings: Settings) -> None:
    ctx = create_mock_context(test_settings)
    about_res = handle_about([], ctx)
    assert "Step 07 / 10 — Persistent Memory & Project Context" in str(about_res.output)

    status_res = handle_status([], ctx)
    assert "Developer Intel (Step 05)   : [OK] ACTIVE" in str(status_res.output)
    assert "Command Guardian (Step 06)" in str(status_res.output)
    assert "Persistent Memory (Step 07)" in str(status_res.output)
