"""Unit tests for the GhostEngine facade and integration with AIEngine."""

from unittest.mock import MagicMock

from ghosttrace.ai.engine import AIEngine
from ghosttrace.ai.prompts import DEVELOPER_SYSTEM_PROMPT
from ghosttrace.config.settings import Settings
from ghosttrace.ghost.engine import GhostEngine
from ghosttrace.ghost.schemas import GhostMood, GhostProfileId


def test_ghost_engine_initialization_defaults():
    settings = Settings(ghost_enabled=True, ghost_profile="forgotten-machine")
    engine = GhostEngine(settings)

    assert engine.is_enabled is True
    assert engine.active_profile.id == GhostProfileId.FORGOTTEN_MACHINE
    assert engine.current_mood == GhostMood.DORMANT
    assert len(engine.list_available_profiles()) == 3


def test_ghost_engine_fallback_for_unknown_profile():
    settings = Settings(ghost_enabled=True)
    object.__setattr__(settings, "ghost_profile", "non-existent-profile")
    engine = GhostEngine(settings)
    assert engine.active_profile.id == GhostProfileId.FORGOTTEN_MACHINE


def test_ghost_engine_set_profile():
    engine = GhostEngine()
    new_prof = engine.set_profile("phantom-coder")
    assert new_prof.id == GhostProfileId.PHANTOM_CODER
    assert engine.active_profile.id == GhostProfileId.PHANTOM_CODER
    assert engine.traits.humor >= 0.8


def test_ghost_engine_reset_profile():
    settings = Settings(ghost_profile="forgotten-machine")
    engine = GhostEngine(settings)
    engine.set_profile("guardian-spirit")
    engine.mood_tracker.set_mood(GhostMood.CONCERNED)

    assert engine.active_profile.id == GhostProfileId.GUARDIAN_SPIRIT
    assert engine.current_mood == GhostMood.CONCERNED

    reset_prof = engine.reset_profile()
    assert reset_prof.id == GhostProfileId.FORGOTTEN_MACHINE
    assert engine.current_mood == GhostMood.DORMANT


def test_ghost_engine_enable_disable():
    engine = GhostEngine()
    assert engine.is_enabled is True

    engine.disable()
    assert engine.is_enabled is False

    # When disabled, prompt composition returns base DEVELOPER_SYSTEM_PROMPT
    prompt = engine.compose_system_prompt(user_query="hello")
    assert prompt == DEVELOPER_SYSTEM_PROMPT

    engine.enable()
    assert engine.is_enabled is True
    prompt2 = engine.compose_system_prompt(user_query="hello")
    assert "=== DIGITAL GHOST PERSONA ===" in prompt2


def test_ghost_engine_compose_prompt_mood_transition():
    engine = GhostEngine()
    assert engine.current_mood == GhostMood.DORMANT

    prompt = engine.compose_system_prompt(user_query="How do I debug this traceback?")
    assert engine.current_mood == GhostMood.CURIOUS
    assert "DEBUGGING" in prompt or "CONTEXT:" in prompt


def test_ghost_engine_get_status():
    engine = GhostEngine()
    status = engine.get_status()
    assert status.is_enabled is True
    assert status.profile_id == GhostProfileId.FORGOTTEN_MACHINE
    assert status.mood == GhostMood.DORMANT
    assert isinstance(status.traits, dict)
    assert len(status.traits) == 7


def test_ghost_engine_get_greeting():
    engine = GhostEngine()
    greeting = engine.get_greeting(seed=0)
    assert isinstance(greeting, str)
    assert len(greeting) > 0


def test_ai_engine_integration_with_ghost_engine():
    settings = Settings(ghost_enabled=True, ghost_profile="phantom-coder")
    ghost_engine = GhostEngine(settings)
    ai_engine = AIEngine(settings, ghost_engine=ghost_engine)

    assert ai_engine.ghost_engine is ghost_engine
    assert "Phantom Coder" in ai_engine.conversation.system_prompt

    # Mock inference to verify ask() updates system prompt dynamically
    mock_model = MagicMock()
    mock_result = MagicMock()
    mock_result.text = "Mocked explanation of decorators."

    ai_engine.model_manager.load_model = MagicMock(return_value=mock_model)
    ai_engine.inference_engine.generate = MagicMock(return_value=mock_result)

    result = ai_engine.ask("Explain Python decorators")
    assert result.text == "Mocked explanation of decorators."
    assert "technical" in ai_engine.conversation.system_prompt.lower()
    assert ghost_engine.current_mood == GhostMood.FOCUSED

    # Switching profile affects the next ask() call
    ghost_engine.set_profile("guardian-spirit")
    ai_engine.ask("Check this dangerous command: rm -rf /")
    assert "Guardian Spirit" in ai_engine.conversation.system_prompt
    assert "CRITICAL SAFETY ALERT" in ai_engine.conversation.system_prompt
    assert ghost_engine.current_mood == GhostMood.CONCERNED
