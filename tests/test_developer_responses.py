"""Unit tests for response presentation and terminal formatting."""

from __future__ import annotations

from ghosttrace.developer.code_analysis import analyze_code_snippet
from ghosttrace.developer.responses import (
    format_analysis_result,
    format_developer_help,
    format_task_headline,
)
from ghosttrace.developer.schemas import DeveloperIntent


def test_format_analysis_result_valid() -> None:
    code = (
        "import json\n\n"
        "class ConfigLoader:\n"
        "    def load(self):\n"
        "        try:\n"
        "            return json.loads('{}')\n"
        "        except:\n"
        "            pass\n"
    )
    analysis = analyze_code_snippet(code, language="python")
    formatted = format_analysis_result(analysis)

    assert "LOCAL STATIC ANALYSIS REPORT" in formatted
    assert "Language     : PYTHON" in formatted
    assert "[OK] Valid Syntax" in formatted
    assert "Functions    : load" in formatted
    assert "Classes      : ConfigLoader" in formatted
    assert "Imports      : json" in formatted
    assert "Observations :" in formatted


def test_format_analysis_result_error() -> None:
    code = "def error(\n  pass"
    analysis = analyze_code_snippet(code, language="python")
    formatted = format_analysis_result(analysis)

    assert "[X] Syntax Error" in formatted
    assert "without executing code" in formatted


def test_format_developer_help() -> None:
    help_text = format_developer_help()
    assert "GHOSTTRACE DEVELOPER INTELLIGENCE" in help_text
    assert "dev explain" in help_text
    assert "dev debug" in help_text
    assert "dev review" in help_text
    assert "dev analyze" in help_text


def test_format_task_headline() -> None:
    assert (
        format_task_headline(DeveloperIntent.EXPLAIN_CODE, "python") == "CODE EXPLANATION (PYTHON)"
    )
    assert format_task_headline(DeveloperIntent.DEBUG_CODE, None) == "DEBUGGING ASSISTANCE"
    assert format_task_headline(DeveloperIntent.REVIEW_CODE, "rust") == "CODE REVIEW (RUST)"
    assert format_task_headline(DeveloperIntent.GENERATE_CODE, "go") == "CODE GENERATION (GO)"
    assert format_task_headline(DeveloperIntent.REFACTOR_CODE, "java") == "CODE REFACTORING (JAVA)"
    assert (
        format_task_headline(DeveloperIntent.GENERATE_TESTS, "python") == "TEST GENERATION (PYTHON)"
    )
    assert format_task_headline(DeveloperIntent.OPTIMIZE_CODE, "c") == "CODE OPTIMIZATION (C)"
    assert format_task_headline(DeveloperIntent.UNKNOWN, None) == "DEVELOPER ASSISTANCE"
