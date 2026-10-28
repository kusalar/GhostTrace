"""Lightweight intent classification for developer tasks and programming queries."""

from __future__ import annotations

import re

from ghosttrace.developer.schemas import DeveloperIntent

_RESERVED_CLI_COMMANDS: frozenset[str] = frozenset(
    {
        "ai",
        "ghost",
        "help",
        "status",
        "about",
        "version",
        "clear",
        "history",
        "exit",
        "quit",
        "cls",
        "info",
        "hist",
        "?",
    }
)

_DEBUG_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:debug|traceback|fix(?:\s+this)?\s+error|broken|segfault)\b", re.I),
    re.compile(r"\b(?:exception|nullpointer|zerodivision|syntaxerror|typeerror)\b", re.I),
    re.compile(r"\b(?:why\s+does\s+this\s+fail|not\s+working|panicked\s+at)\b", re.I),
    re.compile(r"Traceback\s+\(most\s+recent\s+call\s+last\):", re.I),
)

_REVIEW_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:review(?:\s+this)?(?:\s+code)?|code\s+review|audit|critique)\b", re.I),
    re.compile(r"\b(?:code\s+smell|best\s+practices|find\s+bugs|flaws)\b", re.I),
)

_EXPLAIN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:explain(?:\s+this)?(?:\s+code|\s+function|\s+method|\s+algorithm|\s+snippet)?)\b",
        re.I,
    ),
    re.compile(r"\b(?:how\s+does\s+(?:this\s+)?(?:\w+\s+)?work)\b", re.I),
    re.compile(
        r"\b(?:what\s+does\s+this\s+(?:code|function|do)|walk\s+(?:me\s+)?through)\b",
        re.I,
    ),
    re.compile(r"\b(?:break\s+down\s+this\s+code|understand\s+this)\b", re.I),
)

_REFACTOR_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:refactor|clean\s+up(?:\s+this)?|simplify(?:\s+this)?)\b", re.I),
    re.compile(r"\b(?:improve\s+readability|reduce\s+duplication|modernize)\b", re.I),
    re.compile(r"\b(?:decouple|extract\s+function|dry\s+principle)\b", re.I),
)

_TEST_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:write\s+tests?|generate\s+tests?|unit\s+tests?|test\s+cases?)\b", re.I),
    re.compile(r"\b(?:pytest|unittest|test\s+suite|mock\s+tests?)\b", re.I),
)

_OPTIMIZE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:optimize(?:\s+this)?|speed\s+up|make\s+faster|bottleneck)\b", re.I),
    re.compile(r"\b(?:reduce\s+memory|time\s+complexity|big\s+o|performance)\b", re.I),
)

_GENERATE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:generate(?:\s+a|\s+code)?|write\s+a\s+(?:function|class|script|program))\b",
        re.I,
    ),
    re.compile(
        r"\b(?:create\s+a\s+(?:function|class|script|module)|implement\s+(?:an?|a))\b",
        re.I,
    ),
    re.compile(r"\b(?:code\s+for|build\s+a\s+cli|snippet\s+to)\b", re.I),
)

_PROGRAMMING_KEYWORD_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:recursion|polymorphism|asyncio|concurrency|multiprocessing)\b", re.I),
    re.compile(
        r"\b(?:memoization|dependency\s+injection|rest\s+api|(?:database\s+|sql\s+)?indexing)\b",
        re.I,
    ),
    re.compile(r"\b(?:linked\s+list|binary\s+tree|graph\s+algorithm|regex)\b", re.I),
)


def classify_developer_intent(query: str, code: str | None = None) -> DeveloperIntent:
    """Classify user query into a DeveloperIntent using deterministic rule heuristics.

    Returns UNKNOWN if the query is not a programming-related task.
    """
    cleaned = query.strip()
    has_code = bool(code and code.strip())
    if not cleaned:
        if has_code:
            return DeveloperIntent.EXPLAIN_CODE
        return DeveloperIntent.UNKNOWN

    # First check if the first token is a reserved GhostTrace CLI command
    first_token = cleaned.split()[0].lower()
    if first_token in _RESERVED_CLI_COMMANDS:
        return DeveloperIntent.UNKNOWN

    combined = f"{cleaned}\n{code.strip()}" if code else cleaned

    # Order of evaluation: Debugging errors takes high priority
    for pattern in _DEBUG_PATTERNS:
        if pattern.search(combined):
            return DeveloperIntent.DEBUG_CODE

    # Code review checks
    for pattern in _REVIEW_PATTERNS:
        if pattern.search(cleaned):
            return DeveloperIntent.REVIEW_CODE

    # Test generation checks
    for pattern in _TEST_PATTERNS:
        if pattern.search(cleaned):
            return DeveloperIntent.GENERATE_TESTS

    # Refactoring checks
    for pattern in _REFACTOR_PATTERNS:
        if pattern.search(cleaned):
            return DeveloperIntent.REFACTOR_CODE

    # Code optimization checks
    for pattern in _OPTIMIZE_PATTERNS:
        if pattern.search(cleaned):
            return DeveloperIntent.OPTIMIZE_CODE

    # If no explicit code is provided, check general programming concepts before explain
    if not has_code:
        for pattern in _PROGRAMMING_KEYWORD_PATTERNS:
            if pattern.search(cleaned):
                return DeveloperIntent.GENERAL_PROGRAMMING

    # Code explanation checks
    for pattern in _EXPLAIN_PATTERNS:
        if pattern.search(cleaned):
            return DeveloperIntent.EXPLAIN_CODE

    # Code generation checks
    for pattern in _GENERATE_PATTERNS:
        if pattern.search(cleaned):
            return DeveloperIntent.GENERATE_CODE

    # General programming concept checks (if code was present but didn't match explain)
    for pattern in _PROGRAMMING_KEYWORD_PATTERNS:
        if pattern.search(cleaned):
            return DeveloperIntent.GENERAL_PROGRAMMING

    # If code is supplied with no obvious intent, default to explaining the code
    if has_code:
        return DeveloperIntent.EXPLAIN_CODE

    return DeveloperIntent.UNKNOWN
