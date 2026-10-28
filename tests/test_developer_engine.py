"""Unit tests for DeveloperEngine facade and GhostEngine integration."""

import pytest
from ghosttrace.config.settings import Settings
from ghosttrace.developer.engine import DeveloperEngine
from ghosttrace.developer.schemas import DeveloperIntent
from ghosttrace.ghost.engine import GhostEngine
from ghosttrace.ghost.schemas import GhostProfileId


@pytest.fixture
def test_settings() -> Settings:
    return Settings()


def test_developer_engine_lifecycle(test_settings: Settings) -> None:
    ghost_engine = GhostEngine(test_settings)
    dev_engine = DeveloperEngine(test_settings, ghost_engine=ghost_engine)

    assert dev_engine.is_enabled is True
    dev_engine.disable()
    assert dev_engine.is_enabled is False
    dev_engine.enable()
    assert dev_engine.is_enabled is True


def test_developer_engine_analyze_code(test_settings: Settings) -> None:
    dev_engine = DeveloperEngine(test_settings)
    report = dev_engine.format_static_analysis_report("def add(a, b): return a + b")

    assert "LOCAL STATIC ANALYSIS REPORT" in report
    assert "add" in report
    assert "[OK] Valid Syntax" in report


def test_developer_engine_prepare_prompt(test_settings: Settings) -> None:
    ghost_engine = GhostEngine(test_settings)
    dev_engine = DeveloperEngine(test_settings, ghost_engine=ghost_engine)

    ctx, instructions = dev_engine.prepare_developer_prompt(
        query="Explain this Python function",
        code="def factorial(n):\n    return 1 if n <= 1 else n * factorial(n - 1)",
    )
    assert ctx.intent == DeveloperIntent.EXPLAIN_CODE
    assert "TASK MODE: CODE EXPLANATION" in instructions
    assert "factorial" in instructions

    # Test integration with GhostEngine prompt composition
    prompt = ghost_engine.compose_system_prompt(
        user_query=ctx.raw_query,
        developer_instructions=instructions,
    )
    assert "=== BASE DEVELOPER ASSISTANT IDENTITY ===" in prompt
    assert "=== DIGITAL GHOST PERSONA ===" in prompt
    assert "=== DEVELOPER TASK INSTRUCTIONS ===" in prompt
    assert "TASK MODE: CODE EXPLANATION" in prompt


def test_developer_engine_personality_profiles_integration(test_settings: Settings) -> None:
    ghost_engine = GhostEngine(test_settings)
    dev_engine = DeveloperEngine(test_settings, ghost_engine=ghost_engine)

    query = "Review this code"
    code = "def insecure():\n    pass"
    _ctx, instructions = dev_engine.prepare_developer_prompt(query, code=code)

    # 1. Test with Phantom Coder
    ghost_engine.set_profile(GhostProfileId.PHANTOM_CODER)
    p_coder_prompt = ghost_engine.compose_system_prompt(
        user_query=query,
        developer_instructions=instructions,
    )
    assert "Phantom Coder" in p_coder_prompt
    assert "=== DEVELOPER TASK INSTRUCTIONS ===" in p_coder_prompt

    # 2. Test with Guardian Spirit
    ghost_engine.set_profile(GhostProfileId.GUARDIAN_SPIRIT)
    guardian_prompt = ghost_engine.compose_system_prompt(
        user_query=query,
        developer_instructions=instructions,
    )
    assert "Guardian Spirit" in guardian_prompt
    assert "=== DEVELOPER TASK INSTRUCTIONS ===" in guardian_prompt

    # 3. Test with Personality disabled
    ghost_engine.disable()
    neutral_prompt = ghost_engine.compose_system_prompt(
        user_query=query,
        developer_instructions=instructions,
    )
    assert "=== DIGITAL GHOST PERSONA ===" not in neutral_prompt
    assert "=== DEVELOPER TASK INSTRUCTIONS ===" in neutral_prompt
    assert "TASK MODE: CODE REVIEW" in neutral_prompt


def test_developer_engine_is_developer_query(test_settings: Settings) -> None:
    dev_engine = DeveloperEngine(test_settings)
    assert dev_engine.is_developer_query("Explain this code", code="def foo(): pass") is True
    assert dev_engine.is_developer_query("Why did this traceback happen?") is True
    assert dev_engine.is_developer_query("Tell me a fairy tale") is False
    assert dev_engine.is_developer_query("ai status") is False
