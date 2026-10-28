"""Developer intelligence and coding assistance subsystem for GhostTrace."""

from __future__ import annotations

from ghosttrace.developer.code_analysis import (
    analyze_code_snippet,
    analyze_python_code,
)
from ghosttrace.developer.context import (
    build_developer_context,
    extract_code_and_error,
)
from ghosttrace.developer.engine import DeveloperEngine
from ghosttrace.developer.intents import classify_developer_intent
from ghosttrace.developer.languages import (
    LanguageInfo,
    detect_language,
    get_language,
    list_supported_languages,
)
from ghosttrace.developer.prompts import build_developer_instructions
from ghosttrace.developer.responses import (
    format_analysis_result,
    format_developer_help,
)
from ghosttrace.developer.schemas import (
    CodeAnalysisResult,
    DeveloperContext,
    DeveloperIntent,
    DeveloperTaskRequest,
    DeveloperTaskResult,
    ReviewFinding,
    ReviewSeverity,
)

__all__ = [
    "CodeAnalysisResult",
    "DeveloperContext",
    "DeveloperEngine",
    "DeveloperIntent",
    "DeveloperTaskRequest",
    "DeveloperTaskResult",
    "LanguageInfo",
    "ReviewFinding",
    "ReviewSeverity",
    "analyze_code_snippet",
    "analyze_python_code",
    "build_developer_context",
    "build_developer_instructions",
    "classify_developer_intent",
    "detect_language",
    "extract_code_and_error",
    "format_analysis_result",
    "format_developer_help",
    "get_language",
    "list_supported_languages",
]
