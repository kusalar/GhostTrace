"""Event scheduling, cooldown enforcement, and frequency management for the haunted experience."""

from __future__ import annotations

import logging
import time

from ghosttrace.haunt.schemas import HauntIntensity

logger = logging.getLogger("ghosttrace.haunt.scheduler")


class HauntScheduler:
    """Manages cooldowns, session quotas, duplicate suppression, and intensity scaling."""

    def __init__(
        self,
        base_cooldown_seconds: float = 60.0,
        max_events_per_session: int = 30,
        intensity: HauntIntensity = HauntIntensity.MEDIUM,
        idle_threshold_seconds: float = 120.0,
        idle_enabled: bool = False,
    ) -> None:
        self.base_cooldown_seconds = base_cooldown_seconds
        self.max_events_per_session = max_events_per_session
        self.intensity = intensity
        self.idle_threshold_seconds = idle_threshold_seconds
        self.idle_enabled = idle_enabled

        self._event_cooldowns: dict[str, float] = {}
        self._last_event_time: float | None = None
        self._last_event_id: str | None = None
        self._total_events_triggered: int = 0
        self._last_idle_event_time: float = 0.0

    @property
    def total_events(self) -> int:
        """Total number of atmospheric events triggered in this session."""
        return self._total_events_triggered

    @property
    def remaining_events(self) -> int:
        """Number of remaining allowed events in the session budget."""
        return max(0, self.max_events_per_session - self._total_events_triggered)

    @property
    def last_event_time(self) -> float | None:
        """Timestamp of the most recently triggered event."""
        return self._last_event_time

    def get_intensity_multiplier(self) -> float:
        """Return cooldown scaling multiplier based on intensity setting."""
        if self.intensity == HauntIntensity.LOW:
            return 1.5
        if self.intensity == HauntIntensity.HIGH:
            return 0.6
        return 1.0

    def get_effective_cooldown(self, event_cooldown: float) -> float:
        """Calculate effective cooldown scaled by intensity."""
        cooldown = max(event_cooldown, self.base_cooldown_seconds)
        return cooldown * self.get_intensity_multiplier()

    def can_trigger(
        self,
        event_id: str,
        event_cooldown: float,
        now: float | None = None,
        is_preview: bool = False,
    ) -> tuple[bool, str]:
        """Check whether an event is eligible to trigger under current scheduling rules."""
        if is_preview:
            return True, "Preview mode ignores cooldowns and quotas."

        current_time = now if now is not None else time.time()

        # 1. Session event limit
        if self._total_events_triggered >= self.max_events_per_session:
            return False, f"Session event cap reached ({self.max_events_per_session})."

        # 2. Global cooldown
        global_cd = self.base_cooldown_seconds * self.get_intensity_multiplier() * 0.25
        if self._last_event_time is not None:
            time_since_last = current_time - self._last_event_time
            if time_since_last < global_cd:
                return False, f"Global cooldown active ({int(global_cd - time_since_last)}s left)."

        # 3. Specific event cooldown
        if event_id in self._event_cooldowns:
            expires_at = self._event_cooldowns[event_id]
            if current_time < expires_at:
                return (
                    False,
                    f"Event '{event_id}' cooldown active ({int(expires_at - current_time)}s left).",
                )

        # 4. Immediate duplicate suppression
        if self._last_event_id == event_id and self._total_events_triggered > 0:
            return False, f"Event '{event_id}' was just triggered (duplicate suppression)."

        return True, "Eligible to trigger."

    def record_trigger(
        self,
        event_id: str,
        event_cooldown: float,
        now: float | None = None,
        is_preview: bool = False,
    ) -> None:
        """Record that an event has fired, updating cooldowns and counters."""
        if is_preview:
            return

        current_time = now if now is not None else time.time()
        effective_cd = self.get_effective_cooldown(event_cooldown)

        self._event_cooldowns[event_id] = current_time + effective_cd
        self._last_event_time = current_time
        self._last_event_id = event_id
        self._total_events_triggered += 1

    def can_trigger_idle(self, idle_seconds: float, now: float | None = None) -> bool:
        """Check whether an idle whisper event can trigger."""
        if not self.idle_enabled:
            return False

        if idle_seconds < self.idle_threshold_seconds:
            return False

        current_time = now if now is not None else time.time()
        idle_cooldown = self.idle_threshold_seconds * self.get_intensity_multiplier()

        return (current_time - self._last_idle_event_time) >= idle_cooldown

    def record_idle_trigger(self, now: float | None = None) -> None:
        """Record that an idle whisper event fired."""
        current_time = now if now is not None else time.time()
        self._last_idle_event_time = current_time

    def reset(self) -> None:
        """Reset all cooldowns and counters for a fresh session."""
        self._event_cooldowns.clear()
        self._last_event_time = None
        self._last_event_id = None
        self._total_events_triggered = 0
        self._last_idle_event_time = 0.0
