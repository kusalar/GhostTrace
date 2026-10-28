"""Presentation and formatting helpers for developer assistance outputs and analysis."""

from __future__ import annotations

from ghosttrace.developer.schemas import CodeAnalysisResult, DeveloperIntent


def format_analysis_result(analysis: CodeAnalysisResult) -> str:
    """Format safe local static analysis findings into a clean terminal report."""
    syntax_status = (
        "[OK] Valid Syntax"
        if analysis.is_valid_syntax is True
        else (
            f"[X] Syntax Error (line {analysis.error_line}, col {analysis.error_column}): "
            f"{analysis.error_message}"
            if analysis.is_valid_syntax is False
            else "Not parsed (non-Python / generic)"
        )
    )

    lines: list[str] = [
        "LOCAL STATIC ANALYSIS REPORT",
        "==================================================",
        f"  Language     : {analysis.language.upper()}",
        f"  Syntax State : {syntax_status}",
        f"  Line Count   : {analysis.line_count}",
        f"  Char Count   : {analysis.char_count}",
    ]

    if analysis.functions:
        funcs = ", ".join(analysis.functions)
        lines.append(f"  Functions    : {funcs}")

    if analysis.classes:
        classes = ", ".join(analysis.classes)
        lines.append(f"  Classes      : {classes}")

    if analysis.imports:
        imports = ", ".join(analysis.imports)
        lines.append(f"  Imports      : {imports}")

    if analysis.observations:
        lines.append("  Observations :")
        for obs in analysis.observations:
            lines.append(f"    • {obs}")

    lines.append("==================================================")
    lines.append("Note: Static analysis performed locally without executing code.")
    return "\n".join(lines)


def format_developer_help() -> str:
    """Format help text for developer intelligence capabilities and commands."""
    return (
        "GHOSTTRACE DEVELOPER INTELLIGENCE & CODING ASSISTANCE\n"
        "======================================================================\n"
        "GhostTrace assists with coding tasks directly in your terminal using\n"
        "the local Qwen2.5 language model and local static analysis.\n\n"
        "CAPABILITIES:\n"
        "  1. Code Explanation   : Step-by-step logic, concepts, and complexity.\n"
        "  2. Debugging Assist   : Root cause analysis, minimal fix, verification.\n"
        "  3. Code Review        : Strict severity ratings (CRITICAL, HIGH, etc.).\n"
        "  4. Code Generation    : Clean, typed, idiomatic functions and modules.\n"
        "  5. Refactoring        : Readability, simplicity, and risk analysis.\n"
        "  6. Test Generation    : Comprehensive tests (pytest default for Python).\n"
        "  7. Safe Code Analysis : Local Python AST & structural checks (no execution).\n\n"
        "COMMAND USAGE:\n"
        "  dev                   : Show developer assistant summary.\n"
        "  dev help              : Display this help message.\n"
        "  dev explain <code>    : Request step-by-step code explanation.\n"
        "  dev debug <err/code>  : Debug an error, traceback, or broken code.\n"
        "  dev review <code>     : Perform structured code review with severities.\n"
        "  dev generate <spec>   : Generate code from requirements.\n"
        "  dev refactor <code>   : Propose refactored code with change rationale.\n"
        "  dev tests <code>      : Generate unit tests for supplied code.\n"
        "  dev language [hint]   : List supported languages or detect language.\n"
        "  dev analyze <code>    : Run safe local static analysis on snippet.\n\n"
        "NATURAL LANGUAGE ROUTING:\n"
        "  You can also type natural requests directly without the 'dev' prefix:\n"
        "    ghost> Explain this Python code: def fib(n): ...\n"
        "    ghost> Debug this traceback: Traceback (most recent call last): ...\n"
        "    ghost> Review this JavaScript function: const add = (a, b) => a + b;\n"
        "======================================================================"
    )


def format_task_headline(intent: DeveloperIntent, language: str | None) -> str:
    """Return a concise headline for the completed developer turn."""
    lang_str = f" ({language.upper()})" if language else ""
    mapping = {
        DeveloperIntent.EXPLAIN_CODE: f"CODE EXPLANATION{lang_str}",
        DeveloperIntent.DEBUG_CODE: f"DEBUGGING ASSISTANCE{lang_str}",
        DeveloperIntent.REVIEW_CODE: f"CODE REVIEW{lang_str}",
        DeveloperIntent.GENERATE_CODE: f"CODE GENERATION{lang_str}",
        DeveloperIntent.REFACTOR_CODE: f"CODE REFACTORING{lang_str}",
        DeveloperIntent.GENERATE_TESTS: f"TEST GENERATION{lang_str}",
        DeveloperIntent.OPTIMIZE_CODE: f"CODE OPTIMIZATION{lang_str}",
        DeveloperIntent.GENERAL_PROGRAMMING: f"PROGRAMMING GUIDANCE{lang_str}",
        DeveloperIntent.UNKNOWN: "DEVELOPER ASSISTANCE",
    }
    return mapping.get(intent, "DEVELOPER ASSISTANCE")
