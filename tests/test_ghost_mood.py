"""Unit tests for GhostTrace session mood tracker."""

from ghosttrace.ghost.mood import SessionMoodTracker
from ghosttrace.ghost.schemas import GhostMood, InteractionContext


def test_mood_tracker_initial_state():
    tracker = SessionMoodTracker(enabled=True)
    assert tracker.is_enabled is True
    assert tracker.current_mood == GhostMood.DORMANT
    assert "dormant" in tracker.last_reason.lower()


def test_mood_transitions_for_contexts():
    tracker = SessionMoodTracker(enabled=True)

    # Greeting wakes from dormant to curious
    mood1 = tracker.transition_for_context(InteractionContext.GREETING)
    assert mood1 == GhostMood.CURIOUS

    # Another greeting makes it amused
    mood2 = tracker.transition_for_context(InteractionContext.GREETING)
    assert mood2 == GhostMood.AMUSED

    # Technical question makes it focused
    mood3 = tracker.transition_for_context(InteractionContext.TECHNICAL_QUESTION)
    assert mood3 == GhostMood.FOCUSED

    # Debugging makes it curious
    mood4 = tracker.transition_for_context(InteractionContext.DEBUGGING)
    assert mood4 == GhostMood.CURIOUS

    # Error encountered makes it concerned
    mood5 = tracker.transition_for_context(InteractionContext.ERROR_ENCOUNTERED)
    assert mood5 == GhostMood.CONCERNED

    # Dangerous command makes it concerned
    mood6 = tracker.transition_for_context(InteractionContext.POTENTIALLY_DANGEROUS_INSTRUCTION)
    assert mood6 == GhostMood.CONCERNED

    # Successful operation makes it satisfied
    mood7 = tracker.transition_for_context(InteractionContext.SUCCESSFUL_OPERATION)
    assert mood7 == GhostMood.SATISFIED

    # Model unavailable makes it concerned
    mood8 = tracker.transition_for_context(InteractionContext.MODEL_UNAVAILABLE)
    assert mood8 == GhostMood.CONCERNED

    # Repeated question makes it focused
    mood9 = tracker.transition_for_context(InteractionContext.REPEATED_QUESTION)
    assert mood9 == GhostMood.FOCUSED

    # Long idle gap returns to dormant
    mood10 = tracker.transition_for_context(InteractionContext.LONG_IDLE_GAP)
    assert mood10 == GhostMood.DORMANT

    # Ordinary conversation from dormant makes it curious
    mood11 = tracker.transition_for_context(InteractionContext.ORDINARY_CONVERSATION)
    assert mood11 == GhostMood.CURIOUS


def test_mood_tracker_explicit_set_and_reset():
    tracker = SessionMoodTracker(enabled=True)
    tracker.set_mood(GhostMood.SATISFIED, "Custom test rationale")
    assert tracker.current_mood == GhostMood.SATISFIED
    assert tracker.last_reason == "Custom test rationale"

    tracker.reset()
    assert tracker.current_mood == GhostMood.DORMANT
    assert "reset" in tracker.last_reason.lower()


def test_mood_tracker_disabled():
    tracker = SessionMoodTracker(enabled=False)
    assert tracker.is_enabled is False
    assert tracker.current_mood == GhostMood.DORMANT

    # When disabled, transition returns dormant and does not change
    res = tracker.transition_for_context(InteractionContext.TECHNICAL_QUESTION)
    assert res == GhostMood.DORMANT
    assert tracker.current_mood == GhostMood.DORMANT

    # set_mood does nothing when disabled
    tracker.set_mood(GhostMood.FOCUSED)
    assert tracker.current_mood == GhostMood.DORMANT

    # Dynamically toggling enabled property
    tracker.is_enabled = True
    assert tracker.is_enabled is True
    tracker.set_mood(GhostMood.AMUSED)
    assert tracker.current_mood == GhostMood.AMUSED

    tracker.is_enabled = False
    assert tracker.current_mood == GhostMood.DORMANT
