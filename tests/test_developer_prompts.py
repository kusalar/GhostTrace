"""Unit tests for task-specific developer prompt construction."""

from __future__ import annotations

import pytest
from ghosttrace.developer.code_analysis import analyze_code_snippet
from ghosttrace.developer.prompts import build_developer_instructions
from ghosttrace.developer.schemas import DeveloperContext, DeveloperIntent


@pytest.mark.parametrize(
    ("intent", "expected_phrase"),
    [
        (DeveloperIntent.EXPLAIN_CODE, "TASK MODE: CODE EXPLANATION"),
        (DeveloperIntent.DEBUG_CODE, "TASK MODE: DEBUGGING ASSISTANCE"),
        (DeveloperIntent.REVIEW_CODE, "TASK MODE: CODE REVIEW"),
        (DeveloperIntent.GENERATE_CODE, "TASK MODE: CODE GENERATION"),
        (DeveloperIntent.REFACTOR_CODE, "TASK MODE: CODE REFACTORING"),
        (DeveloperIntent.GENERATE_TESTS, "TASK MODE: TEST GENERATION"),
        (DeveloperIntent.OPTIMIZE_CODE, "TASK MODE: CODE OPTIMIZATION"),
        (DeveloperIntent.GENERAL_PROGRAMMING, "TASK MODE: GENERAL PROGRAMMING GUIDANCE"),
        (DeveloperIntent.UNKNOWN, "TASK MODE: DEVELOPER ASSISTANT"),
    ],
)
def test_build_developer_instructions_intent_modes(
    intent: DeveloperIntent,
    expected_phrase: str,
) -> None:
    ctx = DeveloperContext(raw_query="test query", intent=intent)
    instructions = build_developer_instructions(ctx)
    assert expected_phrase in instructions
    assert "STRICT DEVELOPER ACCURACY DIRECTIVES:" in instructions
    assert "Never claim code was executed" in instructions


def test_build_developer_instructions_with_static_analysis() -> None:
    code = "def parse_data(raw: str):\n    return raw.strip()\n"
    analysis = analyze_code_snippet(code, language="python")
    ctx = DeveloperContext(
        raw_query="Explain this function",
        intent=DeveloperIntent.EXPLAIN_CODE,
        code_snippet=code,
        analysis=analysis,
    )
    instructions = build_developer_instructions(ctx)

    assert "LOCAL STATIC ANALYSIS FINDINGS (Ground Truth):" in instructions
    assert "Language: PYTHON" in instructions
    assert "parse_data" in instructions
    assert "Syntax: Valid local parse." in instructions


def test_build_developer_instructions_with_syntax_error() -> None:
    code = "def bad_syntax(:\n    pass"
    analysis = analyze_code_snippet(code, language="python")
    ctx = DeveloperContext(
        raw_query="Why does this fail?",
        intent=DeveloperIntent.DEBUG_CODE,
        code_snippet=code,
        analysis=analysis,
    )
    instructions = build_developer_instructions(ctx)

    assert "SYNTAX ERROR:" in instructions
    assert "SyntaxError" in instructions


def test_build_developer_instructions_classes_imports_truncation() -> None:
    code = "import math\n\nclass Calculator:\n    def run(self):\n        pass\n"
    analysis = analyze_code_snippet(code, language="python")
    ctx = DeveloperContext(
        raw_query="Refactor this class",
        intent=DeveloperIntent.REFACTOR_CODE,
        code_snippet=code,
        analysis=analysis,
        is_truncated=True,
        truncation_message="Code truncated for testing.",
    )
    instructions = build_developer_instructions(ctx)

    assert "Identified Classes: Calculator" in instructions
    assert "Imported Modules: math" in instructions
    assert "NOTE: Code truncated for testing." in instructions
