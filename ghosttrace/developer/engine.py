"""Developer intelligence facade engine coordinating parsing, analysis, and prompt generation."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ghosttrace.developer.code_analysis import analyze_code_snippet
from ghosttrace.developer.context import build_developer_context
from ghosttrace.developer.prompts import build_developer_instructions
from ghosttrace.developer.responses import format_analysis_result
from ghosttrace.developer.schemas import CodeAnalysisResult, DeveloperContext, DeveloperIntent

if TYPE_CHECKING:
    from ghosttrace.config.settings import Settings
    from ghosttrace.ghost.engine import GhostEngine

logger = logging.getLogger("ghosttrace.developer.engine")


class DeveloperEngine:
    """Central facade for developer intelligence, code analysis, and task orchestration."""

    def __init__(
        self,
        settings: Settings | None = None,
        ghost_engine: GhostEngine | None = None,
    ) -> None:
        self.settings = settings
        self.ghost_engine = ghost_engine
        self._enabled = getattr(settings, "dev_enabled", True) if settings else True
        self._static_analysis_enabled = (
            getattr(settings, "dev_static_analysis", True) if settings else True
        )
        self._max_code_chars = getattr(settings, "dev_max_code_chars", 20000) if settings else 20000
        self._max_context_chars = (
            getattr(settings, "dev_max_context_chars", 30000) if settings else 30000
        )

    @property
    def is_enabled(self) -> bool:
        """Return whether developer intelligence is active."""
        return self._enabled

    def enable(self) -> None:
        """Enable the developer intelligence subsystem."""
        self._enabled = True
        logger.info("Developer intelligence subsystem enabled.")

    def disable(self) -> None:
        """Disable the developer intelligence subsystem."""
        self._enabled = False
        logger.info("Developer intelligence subsystem disabled.")

    def build_context(
        self,
        raw_query: str,
        code: str | None = None,
        error: str | None = None,
        language_hint: str | None = None,
        intent_override: DeveloperIntent | None = None,
        requirements: str | None = None,
        run_static_analysis: bool | None = None,
    ) -> DeveloperContext:
        """Construct bounded DeveloperContext using configured size limits."""
        static_analysis_flag = (
            run_static_analysis
            if run_static_analysis is not None
            else self._static_analysis_enabled
        )
        return build_developer_context(
            raw_query=raw_query,
            code=code,
            error=error,
            language_hint=language_hint,
            intent_override=intent_override,
            requirements=requirements,
            max_code_chars=self._max_code_chars,
            max_context_chars=self._max_context_chars,
            run_static_analysis=static_analysis_flag,
        )

    def analyze_code(self, code: str, language_hint: str | None = None) -> CodeAnalysisResult:
        """Execute safe local static analysis on explicitly supplied code without execution."""
        lang = language_hint or "python"
        return analyze_code_snippet(code, language=lang)

    def format_static_analysis_report(
        self,
        code: str,
        language_hint: str | None = None,
    ) -> str:
        """Perform static analysis and return a formatted human-readable report."""
        result = self.analyze_code(code, language_hint=language_hint)
        return format_analysis_result(result)

    def prepare_developer_prompt(
        self,
        query: str,
        code: str | None = None,
        error: str | None = None,
        language_hint: str | None = None,
        intent_override: DeveloperIntent | None = None,
    ) -> tuple[DeveloperContext, str]:
        """Classify query, build context, and generate task instructions for LLM prompt.

        Returns (DeveloperContext, task_instructions_str).
        """
        context = self.build_context(
            raw_query=query,
            code=code,
            error=error,
            language_hint=language_hint,
            intent_override=intent_override,
        )
        instructions = build_developer_instructions(context)
        return context, instructions

    def is_developer_query(self, query: str, code: str | None = None) -> bool:
        """Check if a query should be handled as a developer programming task."""
        if not self._enabled:
            return False
        context = self.build_context(query, code=code, run_static_analysis=False)
        return context.intent != DeveloperIntent.UNKNOWN
