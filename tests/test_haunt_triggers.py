"""Tests for TriggerEvaluator mapping application events to ghost reactions."""

from __future__ import annotations

from ghosttrace.haunt.event_catalog import EventCatalog
from ghosttrace.haunt.scheduler import HauntScheduler
from ghosttrace.haunt.schemas import HauntMode, TriggerContext, TriggerType
from ghosttrace.haunt.triggers import TriggerEvaluator


def test_trigger_evaluator_mode_suppression() -> None:
    """Verify NORMAL and FOCUS modes suppress unsolicited events."""
    catalog = EventCatalog()
    scheduler = HauntScheduler(base_cooldown_seconds=10.0)
    evaluator = TriggerEvaluator(catalog, scheduler)

    ctx = TriggerContext(trigger_type=TriggerType.CODING_SUCCESS)

    # NORMAL mode: suppressed
    res_normal = evaluator.evaluate(ctx, mode=HauntMode.NORMAL)
    assert res_normal.fired is False
    assert "NORMAL mode" in res_normal.reason

    # FOCUS mode: suppressed
    res_focus = evaluator.evaluate(ctx, mode=HauntMode.FOCUS)
    assert res_focus.fired is False
    assert "FOCUS mode" in res_focus.reason

    # AMBIENT mode: permitted
    res_ambient = evaluator.evaluate(ctx, mode=HauntMode.AMBIENT)
    assert res_ambient.fired is True


def test_trigger_evaluator_disabled_state() -> None:
    """Verify evaluator respects enabled=False flag."""
    catalog = EventCatalog()
    scheduler = HauntScheduler()
    evaluator = TriggerEvaluator(catalog, scheduler)

    ctx = TriggerContext(trigger_type=TriggerType.SESSION_START)
    res = evaluator.evaluate(ctx, mode=HauntMode.HAUNTED, enabled=False)
    assert res.fired is False
    assert "disabled" in res.reason


def test_trigger_evaluator_coding_reaction() -> None:
    """Verify dynamic coding success reaction composed with active profile."""
    catalog = EventCatalog()
    scheduler = HauntScheduler(base_cooldown_seconds=10.0)
    evaluator = TriggerEvaluator(catalog, scheduler)

    ctx = TriggerContext(
        trigger_type=TriggerType.CODING_SUCCESS,
        dev_intent="debug_code",
        profile_id="phantom-coder",
    )
    res = evaluator.evaluate(ctx, mode=HauntMode.HAUNTED)
    assert res.fired is True
    assert "debug code" in res.rendered_text.lower() or "clean" in res.rendered_text.lower()


def test_trigger_evaluator_guardian_reaction() -> None:
    """Verify Guardian warning trigger generates atmospheric reaction without modifying risk."""
    catalog = EventCatalog()
    scheduler = HauntScheduler(base_cooldown_seconds=10.0)
    evaluator = TriggerEvaluator(catalog, scheduler)

    ctx = TriggerContext(
        trigger_type=TriggerType.GUARDIAN_WARNING,
        command_name="rmdir /s /q test",
        risk_level="HIGH",
        profile_id="guardian-spirit",
    )
    res = evaluator.evaluate(ctx, mode=HauntMode.HAUNTED)
    assert res.fired is True
    assert "rmdir /s /q test" in res.rendered_text
    assert "safety" in res.rendered_text.lower() or "boundary" in res.rendered_text.lower()


def test_trigger_evaluator_idle_threshold() -> None:
    """Verify idle whispers trigger only when threshold is exceeded."""
    catalog = EventCatalog()
    scheduler = HauntScheduler(idle_threshold_seconds=100.0, idle_enabled=True)
    evaluator = TriggerEvaluator(catalog, scheduler)

    # Below threshold
    ctx_low = TriggerContext(trigger_type=TriggerType.IDLE_TICK, idle_seconds=50.0)
    res_low = evaluator.evaluate(ctx_low, mode=HauntMode.AMBIENT)
    assert res_low.fired is False

    # Above threshold
    ctx_high = TriggerContext(trigger_type=TriggerType.IDLE_TICK, idle_seconds=120.0)
    res_high = evaluator.evaluate(ctx_high, mode=HauntMode.AMBIENT)
    assert res_high.fired is True
    assert res_high.rendered_text is not None
