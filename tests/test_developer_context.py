"""Unit tests for developer context extraction and bounds enforcement."""

from __future__ import annotations

from ghosttrace.developer.context import (
    build_developer_context,
    extract_code_and_error,
)
from ghosttrace.developer.schemas import DeveloperIntent


def test_extract_code_and_error() -> None:
    prompt = (
        "Why does this fail?\n"
        "Traceback (most recent call last):\n"
        "  File 'test.py', line 5, in <module>\n"
        "ZeroDivisionError: division by zero\n\n"
        "Here is the code:\n"
        "```python\n"
        "def div(a, b):\n"
        "    return a / b\n"
        "```"
    )
    code, error, remaining = extract_code_and_error(prompt)
    assert code is not None
    assert "def div(a, b):" in code
    assert error is not None
    assert "ZeroDivisionError" in error
    assert "Why does this fail?" in remaining


def test_build_developer_context_basic() -> None:
    query = "Explain this code:\n```python\ndef square(n):\n    return n * n\n```"
    ctx = build_developer_context(raw_query=query)

    assert ctx.intent == DeveloperIntent.EXPLAIN_CODE
    assert ctx.detected_language == "python"
    assert ctx.code_snippet is not None
    assert "def square(n):" in ctx.code_snippet
    assert ctx.analysis is not None
    assert ctx.analysis.is_valid_syntax is True
    assert "square" in ctx.analysis.functions
    assert not ctx.is_truncated


def test_build_developer_context_truncation() -> None:
    huge_code = "x = 1\n" * 500  # 3000 chars
    ctx = build_developer_context(
        raw_query="Review this code",
        code=huge_code,
        max_code_chars=100,
    )
    assert ctx.is_truncated is True
    assert ctx.truncation_message is not None
    assert "[NOTICE]" in ctx.truncation_message
    assert len(ctx.code_snippet) == 100


def test_build_developer_context_explicit_overrides() -> None:
    ctx = build_developer_context(
        raw_query="something random",
        code="let x: number = 42;",
        language_hint="typescript",
        intent_override=DeveloperIntent.REFACTOR_CODE,
        run_static_analysis=False,
    )
    assert ctx.intent == DeveloperIntent.REFACTOR_CODE
    assert ctx.detected_language == "typescript"
    assert ctx.language_confirmed is True
    assert ctx.analysis is None
