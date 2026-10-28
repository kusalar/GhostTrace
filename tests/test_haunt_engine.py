"""Tests for HauntEngine facade methods, mode changes, triggers, and previews."""

from __future__ import annotations

from ghosttrace.config.settings import Settings
from ghosttrace.ghost.engine import GhostEngine
from ghosttrace.haunt.engine import HauntEngine
from ghosttrace.haunt.schemas import (
    EventCategory,
    HauntIntensity,
    HauntMode,
    TriggerContext,
    TriggerType,
)


def test_haunt_engine_init_and_properties() -> None:
    """Verify HauntEngine initialization with settings and ghost engine."""
    settings = Settings(
        haunt_enabled=True,
        haunt_mode="ambient",
        haunt_intensity="low",
        haunt_max_events_per_session=25,
        haunt_cooldown_seconds=45.0,
    )
    ghost = GhostEngine(settings)
    engine = HauntEngine(settings, ghost_engine=ghost)

    assert engine.is_enabled is True
    assert engine.mode == HauntMode.AMBIENT
    assert engine.intensity == HauntIntensity.LOW
    assert engine.scheduler.max_events_per_session == 25
    assert engine.scheduler.base_cooldown_seconds == 45.0


def test_haunt_engine_mode_and_intensity_switching() -> None:
    """Verify runtime mode and intensity switching."""
    engine = HauntEngine()
    assert engine.mode == HauntMode.NORMAL

    # Switch mode
    engine.set_mode(HauntMode.HAUNTED)
    assert engine.mode == HauntMode.HAUNTED
    engine.set_mode("focus")
    assert engine.mode == HauntMode.FOCUS

    # Switch intensity
    engine.set_intensity("high")
    assert engine.intensity == HauntIntensity.HIGH
    engine.set_intensity(HauntIntensity.MEDIUM)
    assert engine.intensity == HauntIntensity.MEDIUM


def test_haunt_engine_enable_disable_toggle() -> None:
    """Verify enable and disable state controls."""
    engine = HauntEngine()
    engine.disable()
    assert engine.is_enabled is False

    engine.enable()
    assert engine.is_enabled is True


def test_haunt_engine_process_trigger_flow() -> None:
    """Verify process_trigger records events into session history when fired."""
    engine = HauntEngine()
    engine.set_mode(HauntMode.HAUNTED)

    ctx = TriggerContext(
        trigger_type=TriggerType.SESSION_START,
        profile_id="phantom-coder",
    )
    res = engine.process_trigger(ctx)
    assert res.fired is True
    assert res.rendered_text is not None
    assert engine.history.count == 1

    entries = engine.get_history()
    assert len(entries) == 1
    assert entries[0].profile_id == "phantom-coder"


def test_haunt_engine_preview_event() -> None:
    """Verify preview_event generates atmospheric output without mutating history."""
    engine = HauntEngine()
    assert engine.history.count == 0

    res = engine.preview_event(category=EventCategory.SPECIAL_EVENT, profile_id="forgotten-machine")
    assert res.fired is True
    assert res.rendered_text is not None

    # History should remain 0
    assert engine.history.count == 0


def test_haunt_engine_status_snapshot() -> None:
    """Verify get_status returns an accurate snapshot."""
    engine = HauntEngine()
    st = engine.get_status()
    assert st.enabled is True
    assert st.mode == HauntMode.NORMAL
    assert st.max_events_per_session == 30
    assert st.total_events_triggered == 0
