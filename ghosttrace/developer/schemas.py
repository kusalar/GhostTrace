"""Data schemas, enums, and typed models for developer intelligence and coding assistance."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class DeveloperIntent(StrEnum):
    """Categorized programming tasks recognized by the developer assistant."""

    EXPLAIN_CODE = "explain_code"
    DEBUG_CODE = "debug_code"
    REVIEW_CODE = "review_code"
    GENERATE_CODE = "generate_code"
    REFACTOR_CODE = "refactor_code"
    GENERATE_TESTS = "generate_tests"
    OPTIMIZE_CODE = "optimize_code"
    GENERAL_PROGRAMMING = "general_programming"
    UNKNOWN = "unknown"


class ReviewSeverity(StrEnum):
    """Severity ratings for code review findings."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class ReviewFinding(BaseModel):
    """Individual code review observation with severity and suggested resolution."""

    location: str = Field(description="Line number, function name, or code fragment reference.")
    severity: ReviewSeverity = Field(description="Severity classification.")
    description: str = Field(description="Clear explanation of the finding.")
    why_it_matters: str = Field(description="Impact on correctness, security, or maintainability.")
    suggested_fix: str = Field(description="Actionable recommendation or replacement snippet.")


class CodeAnalysisResult(BaseModel):
    """Safe, local static analysis observations of explicitly supplied code snippets."""

    language: str = Field(description="Detected or inferred programming language.")
    is_valid_syntax: bool | None = Field(
        default=None,
        description=(
            "Whether syntax is valid according to local parser (e.g. ast.parse for Python)."
        ),
    )
    error_message: str | None = Field(
        default=None,
        description="Syntax error message if code fails local parsing.",
    )
    error_line: int | None = Field(
        default=None,
        description="Line number where syntax error occurred.",
    )
    error_column: int | None = Field(
        default=None,
        description="Column offset where syntax error occurred.",
    )
    functions: list[str] = Field(
        default_factory=list,
        description="Discovered function and method identifiers.",
    )
    classes: list[str] = Field(
        default_factory=list,
        description="Discovered class identifiers.",
    )
    imports: list[str] = Field(
        default_factory=list,
        description="Discovered imported module names.",
    )
    line_count: int = Field(default=0, description="Total line count of the snippet.")
    char_count: int = Field(default=0, description="Total character count of the snippet.")
    observations: list[str] = Field(
        default_factory=list,
        description="Lightweight heuristic or structural observations.",
    )


class DeveloperContext(BaseModel):
    """Bounded, parsed contextual payload built from user query and supplied code."""

    raw_query: str = Field(description="Original user prompt or command.")
    intent: DeveloperIntent = Field(description="Classified or overridden developer intent.")
    code_snippet: str | None = Field(
        default=None,
        description="Extracted or explicitly provided code snippet.",
    )
    error_message: str | None = Field(
        default=None,
        description="Extracted or explicitly provided traceback or compiler error.",
    )
    detected_language: str | None = Field(
        default=None,
        description="Programming language identifier detected or supplied.",
    )
    language_confirmed: bool = Field(
        default=False,
        description="True if language was explicitly specified by the user.",
    )
    requirements: str | None = Field(
        default=None,
        description="Specific coding requirements or instructions extracted from query.",
    )
    analysis: CodeAnalysisResult | None = Field(
        default=None,
        description="Static analysis result if analysis was executed.",
    )
    is_truncated: bool = Field(
        default=False,
        description="True if snippet was truncated due to configured size limits.",
    )
    truncation_message: str | None = Field(
        default=None,
        description="Notice regarding truncated context if applicable.",
    )


class DeveloperTaskRequest(BaseModel):
    """Explicit developer task request submitted via terminal command or API."""

    intent: DeveloperIntent = Field(description="Requested developer task mode.")
    query: str = Field(description="Full user query or command argument.")
    code: str | None = Field(default=None, description="Explicit code payload.")
    error: str | None = Field(default=None, description="Explicit error payload.")
    language: str | None = Field(default=None, description="Optional explicit language hint.")
    requirements: str | None = Field(default=None, description="Optional explicit requirements.")


class DeveloperTaskResult(BaseModel):
    """Structured result of a completed developer assistance turn."""

    intent: DeveloperIntent = Field(description="Executed intent.")
    language: str | None = Field(default=None, description="Active programming language.")
    task_summary: str = Field(description="Brief headline summarizing the task performed.")
    content: str = Field(description="AI response content or static analysis report.")
    analysis: CodeAnalysisResult | None = Field(
        default=None,
        description="Static analysis findings if available.",
    )
    formatted_output: str = Field(
        description="Ready-to-render presentation string for the terminal interface.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional diagnostic metadata.",
    )
