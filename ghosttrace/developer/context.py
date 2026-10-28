"""Context construction and bounds enforcement for developer intelligence tasks."""

from __future__ import annotations

import re

from ghosttrace.developer.code_analysis import analyze_code_snippet
from ghosttrace.developer.intents import classify_developer_intent
from ghosttrace.developer.languages import detect_language
from ghosttrace.developer.schemas import DeveloperContext, DeveloperIntent

_CODE_FENCE_REGEX = re.compile(r"```(?:[a-zA-Z0-9_+#-]*\n)?(.*?)```", re.DOTALL)
_TRACEBACK_REGEX = re.compile(
    r"(Traceback\s+\(most\s+recent\s+call\s+last\):.*?\n[A-Za-z_]\w*(?:Error|Exception):[^\n]*)",
    re.DOTALL,
)


def extract_code_and_error(raw_text: str) -> tuple[str | None, str | None, str]:
    """Extract code blocks, tracebacks, and plain requirements from a user prompt.

    Returns: (code_snippet, error_message, remaining_query)
    """
    code_snippet: str | None = None
    error_message: str | None = None
    remaining = raw_text

    # Extract traceback if present
    tb_match = _TRACEBACK_REGEX.search(raw_text)
    if tb_match:
        error_message = tb_match.group(1).strip()
        remaining = raw_text.replace(tb_match.group(0), "").strip()

    # Extract fenced code blocks
    fence_match = _CODE_FENCE_REGEX.search(remaining)
    if fence_match:
        code_snippet = fence_match.group(1).strip()
        remaining = remaining.replace(fence_match.group(0), "").strip()

    return code_snippet, error_message, remaining


def build_developer_context(
    raw_query: str,
    code: str | None = None,
    error: str | None = None,
    language_hint: str | None = None,
    intent_override: DeveloperIntent | None = None,
    requirements: str | None = None,
    max_code_chars: int = 20000,
    max_context_chars: int = 30000,
    run_static_analysis: bool = True,
) -> DeveloperContext:
    """Build a bounded, typed DeveloperContext enforcing memory and length constraints."""
    extracted_code, extracted_err, remaining_text = extract_code_and_error(raw_query)

    active_code = code if code is not None else extracted_code
    active_err = error if error is not None else extracted_err
    active_req = requirements if requirements is not None else remaining_text

    is_truncated = False
    truncation_msg: str | None = None

    # Enforce code snippet character limit
    if active_code and len(active_code) > max_code_chars:
        original_len = len(active_code)
        active_code = active_code[:max_code_chars]
        is_truncated = True
        truncation_msg = (
            f"[NOTICE] Code snippet truncated from {original_len} to {max_code_chars} chars "
            "to prevent memory exhaustion."
        )

    # Detect language
    lang_info = detect_language(code=active_code or "", query=raw_query, hint=language_hint)
    detected_lang = (
        lang_info.id if lang_info else (language_hint.lower() if language_hint else None)
    )
    language_confirmed = language_hint is not None

    # Classify intent if not explicitly overridden
    if intent_override is not None:
        intent = intent_override
    else:
        intent = classify_developer_intent(raw_query, code=active_code)

    # Safe local static analysis
    analysis = None
    if run_static_analysis and active_code and active_code.strip():
        lang_for_analysis = detected_lang or "python"
        analysis = analyze_code_snippet(active_code, language=lang_for_analysis)

    # Enforce total context character limit
    total_len = len(raw_query) + (len(active_code) if active_code else 0)
    if total_len > max_context_chars and not is_truncated:
        is_truncated = True
        truncation_msg = (
            f"[NOTICE] Total context length {total_len} exceeds configured limit "
            f"of {max_context_chars} characters."
        )

    return DeveloperContext(
        raw_query=raw_query,
        intent=intent,
        code_snippet=active_code,
        error_message=active_err,
        detected_language=detected_lang,
        language_confirmed=language_confirmed,
        requirements=active_req,
        analysis=analysis,
        is_truncated=is_truncated,
        truncation_message=truncation_msg,
    )
