"""Task-specific developer prompt instructions and static analysis integration."""

from __future__ import annotations

from ghosttrace.developer.schemas import DeveloperContext, DeveloperIntent

_INTENT_INSTRUCTIONS: dict[DeveloperIntent, str] = {
    DeveloperIntent.EXPLAIN_CODE: (
        "TASK MODE: CODE EXPLANATION\n"
        "1. High-level Summary: Explain what the supplied code achieves in plain terms.\n"
        "2. Step-by-Step Logic: Trace the execution flow, control branches, and transformations.\n"
        "3. Key Symbols: Detail important functions, classes, and variables.\n"
        "4. Concepts: Highlight relevant design patterns or core language mechanics.\n"
        "5. I/O & Edge Cases: Identify inputs, outputs, preconditions, and potential boundaries.\n"
        "6. Complexity: Note time and space complexity when meaningful."
    ),
    DeveloperIntent.DEBUG_CODE: (
        "TASK MODE: DEBUGGING ASSISTANCE\n"
        "1. Observed Problem: State the reported error or failure precisely.\n"
        "2. Root Cause Analysis: Distinguish confirmed facts from working hypotheses.\n"
        "3. Minimal Proposed Fix: Present the smallest necessary correction.\n"
        "4. Corrected Implementation: Provide the clean, fixed code snippet with language fence.\n"
        "5. Verification Procedure: Provide concrete steps for the user to test the fix locally.\n"
        "If crucial context or reproduction details are missing, ask a focused clarifying question."
    ),
    DeveloperIntent.REVIEW_CODE: (
        "TASK MODE: CODE REVIEW\n"
        "Review the supplied code for correctness, readability, maintainability, and safety.\n"
        "Categorize each finding using strict severity tags:\n"
        "  - [CRITICAL] Severe logic error, data loss risk, or blatant security vulnerability.\n"
        "  - [HIGH] Significant bug, concurrency defect, or resource leak.\n"
        "  - [MEDIUM] Maintainability issue, anti-pattern, or performance bottleneck.\n"
        "  - [LOW] Minor code smell, naming issue, or missing documentation.\n"
        "  - [INFO] Idiomatic suggestion or style polish.\n"
        "For each issue include: Location, Description, Why it matters, and Suggested fix.\n"
        "If the code has no meaningful defects, explicitly confirm that it looks clean."
    ),
    DeveloperIntent.GENERATE_CODE: (
        "TASK MODE: CODE GENERATION\n"
        "Generate clean, maintainable, production-ready code fulfilling the user requirements.\n"
        "1. Respect requested language, version, and framework (default to standard libraries).\n"
        "2. Include necessary imports, type annotations, and error handling.\n"
        "3. Explain architectural assumptions and trade-offs.\n"
        "4. Provide a brief usage or demonstration example.\n"
        "Clearly label the code as a proposed implementation."
    ),
    DeveloperIntent.REFACTOR_CODE: (
        "TASK MODE: CODE REFACTORING\n"
        "1. Current Shortcomings: Explain readability, complexity, or duplication issues.\n"
        "2. Refactored Implementation: Provide the modernized, cleaned-up code.\n"
        "3. Key Improvements: Detail what changed and why it is better.\n"
        "4. Behavioral Risks: Note any subtle edge-case differences or migration cautions."
    ),
    DeveloperIntent.GENERATE_TESTS: (
        "TASK MODE: TEST GENERATION\n"
        "Generate comprehensive unit tests for the supplied code using standard frameworks\n"
        "(pytest for Python, vitest/jest for JS/TS, JUnit 5 for Java, cargo test for Rust).\n"
        "Cover:\n"
        "  - Normal/Happy path cases\n"
        "  - Boundary and edge cases\n"
        "  - Invalid inputs and type errors\n"
        "  - Exception handling and error assertions\n"
        "Provide clear test names and concise fixtures. Label tests as proposed code."
    ),
    DeveloperIntent.OPTIMIZE_CODE: (
        "TASK MODE: CODE OPTIMIZATION\n"
        "1. Analyze algorithmic complexity (Big-O time and space).\n"
        "2. Identify bottlenecks or unnecessary allocations.\n"
        "3. Present optimized code implementation.\n"
        "4. Explain the performance gain and any trade-offs made."
    ),
    DeveloperIntent.GENERAL_PROGRAMMING: (
        "TASK MODE: GENERAL PROGRAMMING GUIDANCE\n"
        "Provide accurate, idiomatic explanations, architectural trade-offs, and concrete examples."
    ),
    DeveloperIntent.UNKNOWN: (
        "TASK MODE: DEVELOPER ASSISTANT\n"
        "Provide helpful, accurate programming assistance grounded strictly in user requirements."
    ),
}

_ACCURACY_DIRECTIVES: str = (
    "STRICT DEVELOPER ACCURACY DIRECTIVES:\n"
    "- Never invent function names, standard library APIs, or CLI flags.\n"
    "- Never claim code was executed, compiled, or tested by you.\n"
    "- Never claim a bug was reproduced without actual local execution.\n"
    "- Clearly distinguish assumptions from confirmed facts.\n"
    "- If supplied information is insufficient to solve the problem, "
    "ask focused follow-up questions.\n"
    "- Prefer minimal, surgical, explainable fixes over sweeping rewrites."
)


def build_developer_instructions(context: DeveloperContext) -> str:
    """Build task-specific instructions combining intent directives and static analysis."""
    lines: list[str] = [
        _INTENT_INSTRUCTIONS.get(context.intent, _INTENT_INSTRUCTIONS[DeveloperIntent.UNKNOWN]),
        "",
        _ACCURACY_DIRECTIVES,
    ]

    # Incorporate static analysis observations if present
    if context.analysis is not None:
        lines.append("")
        lines.append("LOCAL STATIC ANALYSIS FINDINGS (Ground Truth):")
        lines.append(f"• Language: {context.analysis.language.upper()}")
        lines.append(
            f"• Lines: {context.analysis.line_count}, Chars: {context.analysis.char_count}"
        )

        if context.analysis.is_valid_syntax is False:
            lines.append(
                f"• SYNTAX ERROR: Line {context.analysis.error_line}, "
                f"Col {context.analysis.error_column}: {context.analysis.error_message}"
            )
        elif context.analysis.is_valid_syntax is True:
            lines.append("• Syntax: Valid local parse.")

        if context.analysis.functions:
            funcs_str = ", ".join(context.analysis.functions[:8])
            lines.append(f"• Identified Functions: {funcs_str}")

        if context.analysis.classes:
            classes_str = ", ".join(context.analysis.classes[:5])
            lines.append(f"• Identified Classes: {classes_str}")

        if context.analysis.imports:
            imports_str = ", ".join(context.analysis.imports[:8])
            lines.append(f"• Imported Modules: {imports_str}")

        for obs in context.analysis.observations:
            lines.append(f"• Observation: {obs}")

    if context.is_truncated and context.truncation_message:
        lines.append("")
        lines.append(f"NOTE: {context.truncation_message}")

    return "\n".join(lines)
