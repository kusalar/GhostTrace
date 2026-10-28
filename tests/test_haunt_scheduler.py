"""Tests for HauntScheduler cooldowns, session caps, and duplicate suppression."""

from __future__ import annotations

from ghosttrace.haunt.scheduler import HauntScheduler
from ghosttrace.haunt.schemas import HauntIntensity


def test_scheduler_cooldown_and_trigger_flow() -> None:
    """Verify cooldown tracking and trigger recording."""
    sched = HauntScheduler(base_cooldown_seconds=60.0, max_events_per_session=10)
    now = 1000.0

    # 1. Initial trigger permitted
    ok, _ = sched.can_trigger("ev1", event_cooldown=60.0, now=now)
    assert ok is True

    sched.record_trigger("ev1", event_cooldown=60.0, now=now)
    assert sched.total_events == 1
    assert sched.remaining_events == 9

    # 2. Duplicate immediate trigger rejected
    ok_dup, reason_dup = sched.can_trigger("ev1", event_cooldown=60.0, now=now + 5.0)
    assert ok_dup is False
    assert "duplicate" in reason_dup.lower() or "cooldown" in reason_dup.lower()

    # 3. Another event on global cooldown rejected
    ok_diff, reason_diff = sched.can_trigger("ev2", event_cooldown=60.0, now=now + 5.0)
    assert ok_diff is False
    assert "global cooldown" in reason_diff.lower()

    # 4. After global cooldown, different event permitted
    ok_after, _ = sched.can_trigger("ev2", event_cooldown=60.0, now=now + 25.0)
    assert ok_after is True


def test_scheduler_session_quota() -> None:
    """Verify session max events cap."""
    sched = HauntScheduler(base_cooldown_seconds=10.0, max_events_per_session=2)
    now = 1000.0

    sched.record_trigger("ev1", event_cooldown=10.0, now=now)
    sched.record_trigger("ev2", event_cooldown=10.0, now=now + 20.0)

    assert sched.remaining_events == 0
    ok, reason = sched.can_trigger("ev3", event_cooldown=10.0, now=now + 40.0)
    assert ok is False
    assert "cap reached" in reason.lower()


def test_scheduler_intensity_scaling() -> None:
    """Verify intensity multipliers affect effective cooldowns."""
    sched_low = HauntScheduler(base_cooldown_seconds=60.0, intensity=HauntIntensity.LOW)
    sched_med = HauntScheduler(base_cooldown_seconds=60.0, intensity=HauntIntensity.MEDIUM)
    sched_high = HauntScheduler(base_cooldown_seconds=60.0, intensity=HauntIntensity.HIGH)

    assert sched_low.get_intensity_multiplier() == 1.5
    assert sched_med.get_intensity_multiplier() == 1.0
    assert sched_high.get_intensity_multiplier() == 0.6

    assert sched_low.get_effective_cooldown(60.0) == 90.0
    assert sched_high.get_effective_cooldown(60.0) == 36.0


def test_scheduler_idle_whisper_checks() -> None:
    """Verify idle whisper triggers and threshold validation."""
    sched = HauntScheduler(idle_threshold_seconds=120.0, idle_enabled=True)
    now = 1000.0

    # 1. Idle seconds below threshold rejected
    assert sched.can_trigger_idle(idle_seconds=50.0, now=now) is False

    # 2. Idle seconds above threshold permitted
    assert sched.can_trigger_idle(idle_seconds=130.0, now=now) is True

    sched.record_idle_trigger(now=now)

    # 3. Immediate subsequent idle rejected due to cooldown
    assert sched.can_trigger_idle(idle_seconds=130.0, now=now + 10.0) is False

    # 4. If idle_enabled is False, rejected regardless of seconds
    sched.idle_enabled = False
    assert sched.can_trigger_idle(idle_seconds=300.0, now=now + 500.0) is False


def test_scheduler_preview_bypasses_cooldowns() -> None:
    """Verify preview mode is exempt from session quotas and cooldowns."""
    sched = HauntScheduler(max_events_per_session=0)
    ok, _ = sched.can_trigger("ev1", event_cooldown=100.0, is_preview=True)
    assert ok is True
