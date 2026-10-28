"""Tests for Haunt schemas, enums, and data validation."""

from __future__ import annotations

import time

from ghosttrace.haunt.schemas import (
    EventCategory,
    HauntEvent,
    HauntHistoryEntry,
    HauntIntensity,
    HauntMode,
    HauntStatus,
    TriggerContext,
    TriggerResult,
    TriggerType,
)


def test_haunt_enums() -> None:
    """Verify enum members and values."""
    assert HauntMode.NORMAL.value == "normal"
    assert HauntMode.AMBIENT.value == "ambient"
    assert HauntMode.HAUNTED.value == "haunted"
    assert HauntMode.FOCUS.value == "focus"

    assert HauntIntensity.LOW.value == "low"
    assert HauntIntensity.MEDIUM.value == "medium"
    assert HauntIntensity.HIGH.value == "high"

    assert EventCategory.GHOST_GREETING.value == "ghost_greeting"
    assert EventCategory.IDLE_WHISPER.value == "idle_whisper"
    assert EventCategory.CODING_REACTION.value == "coding_reaction"
    assert EventCategory.ERROR_REACTION.value == "error_reaction"
    assert EventCategory.GUARDIAN_REACTION.value == "guardian_reaction"
    assert EventCategory.MOOD_SHIFT.value == "mood_shift"
    assert EventCategory.SESSION_EVENT.value == "session_event"
    assert EventCategory.DISCOVERY_EVENT.value == "discovery_event"
    assert EventCategory.SPECIAL_EVENT.value == "special_event"

    assert TriggerType.SESSION_START.value == "session_start"
    assert TriggerType.COMMAND_DISCOVERY.value == "command_discovery"
    assert TriggerType.CODING_SUCCESS.value == "coding_success"
    assert TriggerType.APP_ERROR.value == "app_error"
    assert TriggerType.GUARDIAN_WARNING.value == "guardian_warning"
    assert TriggerType.MOOD_TRANSITION.value == "mood_transition"
    assert TriggerType.IDLE_TICK.value == "idle_tick"
    assert TriggerType.MANUAL_PREVIEW.value == "manual_preview"


def test_haunt_event_model() -> None:
    """Verify HauntEvent schema defaults and validation."""
    ev = HauntEvent(
        id="test_ev",
        category=EventCategory.GHOST_GREETING,
        name="Test Greeting",
        description="A test greeting",
        templates={"default": ["Hello from the shell."]},
    )
    assert ev.id == "test_ev"
    assert ev.priority == 1
    assert ev.cooldown_seconds == 60.0
    assert HauntMode.AMBIENT in ev.eligible_modes
    assert HauntMode.HAUNTED in ev.eligible_modes


def test_trigger_context_and_result() -> None:
    """Verify TriggerContext creation and TriggerResult reporting."""
    ctx = TriggerContext(
        trigger_type=TriggerType.CODING_SUCCESS,
        dev_intent="explain_code",
        profile_id="phantom-coder",
    )
    assert ctx.trigger_type == TriggerType.CODING_SUCCESS
    assert ctx.dev_intent == "explain_code"
    assert ctx.profile_id == "phantom-coder"

    res = TriggerResult(
        fired=True,
        reason="Triggered",
        rendered_text="Ghost text",
        category=EventCategory.CODING_REACTION,
    )
    assert res.fired is True
    assert res.rendered_text == "Ghost text"
    assert res.category == EventCategory.CODING_REACTION


def test_haunt_status_and_history_models() -> None:
    """Verify HauntStatus snapshot and HauntHistoryEntry records."""
    entry = HauntHistoryEntry(
        id="h1",
        timestamp=time.time(),
        event_id="test_ev",
        category=EventCategory.SPECIAL_EVENT,
        mode=HauntMode.HAUNTED,
        profile_id="forgotten-machine",
        rendered_text="A special echo.",
        trigger_type=TriggerType.MANUAL_PREVIEW,
    )
    assert entry.id == "h1"
    assert entry.category == EventCategory.SPECIAL_EVENT

    status = HauntStatus(
        enabled=True,
        mode=HauntMode.HAUNTED,
        intensity=HauntIntensity.MEDIUM,
        active_profile="Forgotten Machine",
        current_mood="DORMANT",
        total_events_triggered=1,
        session_events_remaining=29,
        max_events_per_session=30,
        cooldown_seconds=60.0,
        last_event_time=time.time(),
        idle_enabled=False,
        idle_threshold_seconds=120.0,
        reduced_motion=False,
    )
    assert status.enabled is True
    assert status.session_events_remaining == 29
