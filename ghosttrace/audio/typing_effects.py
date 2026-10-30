"""Haunted keystrokes and context-aware typing audio effects for GhostTrace.

This module provides subtle, non-intrusive typing audio manifestations
triggered by user keyboard activity inside GhostTrace's own interactive
Textual terminal interface.

Strict Privacy Guarantees:
- Never inspects, captures, logs, or stores actual typed characters or command text.
- Never installs global OS keyboard hooks; listens strictly within Textual's input widget.
- Never monitors external applications or clipboard contents.
- Operates entirely on aggregate metadata: event counts, intervals, and activity rates.
- Zero network egress, zero disk writes per keystroke, and zero AI inference overhead.
"""

from __future__ import annotations

import collections
import logging
import random
import threading
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Final

from ghosttrace.audio.schemas import AudioEventId

if TYPE_CHECKING:
    from ghosttrace.audio.adapter import AudioEventAdapter
    from ghosttrace.audio.manager import AudioManager

logger = logging.getLogger("ghosttrace.audio.typing_effects")


# Default tuning parameters per experience mode
TYPING_MODE_PROFILES: Final[dict[str, dict[str, Any]]] = {
    "normal": {
        "enabled_by_default": False,
        "base_probability": 0.06,
        "burst_probability": 0.08,
        "min_keystrokes_before_effect": 5,
        "cooldown_seconds": 4.0,
        "max_effects_per_minute": 4,
        "volume_scale": 0.20,
        "allowed_events": [AudioEventId.KEYSTROKE_HAUNT, AudioEventId.GLITCH_DIGITAL],
        "burst_events": [AudioEventId.GLITCH_DIGITAL, AudioEventId.KEYSTROKE_HAUNT],
    },
    "ambient": {
        "enabled_by_default": False,
        "base_probability": 0.08,
        "burst_probability": 0.12,
        "min_keystrokes_before_effect": 4,
        "cooldown_seconds": 3.0,
        "max_effects_per_minute": 6,
        "volume_scale": 0.25,
        "allowed_events": [AudioEventId.KEYSTROKE_HAUNT, AudioEventId.GLITCH_STATIC],
        "burst_events": [AudioEventId.GLITCH_STATIC, AudioEventId.KEYSTROKE_HAUNT],
    },
    "haunted": {
        "enabled_by_default": False,
        "base_probability": 0.12,
        "burst_probability": 0.22,
        "min_keystrokes_before_effect": 3,
        "cooldown_seconds": 2.0,
        "max_effects_per_minute": 8,
        "volume_scale": 0.35,
        "allowed_events": [
            AudioEventId.KEYSTROKE_HAUNT,
            AudioEventId.GLITCH_DIGITAL,
            AudioEventId.GLITCH_STATIC,
        ],
        "burst_events": [
            AudioEventId.GLITCH_CORRUPTION,
            AudioEventId.KEYSTROKE_HAUNT,
            AudioEventId.GLITCH_STATIC,
        ],
    },
    "focus": {
        "suppressed": True,
    },
}


class TypingEffectsManager:
    """Manages lightweight, rate-limited horror audio manifestations while typing.

    Enforces strict rate limits, mode policies, debouncing, inactivity detection,
    and deterministic randomness for testing.
    """

    def __init__(
        self,
        audio_manager: AudioManager | None = None,
        audio_adapter: AudioEventAdapter | None = None,
        random_func: Callable[[], float] | None = None,
        time_func: Callable[[], float] | None = None,
        inactivity_threshold: float = 1.2,
        min_key_interval: float = 0.03,
    ) -> None:
        self.audio_manager = audio_manager
        self.audio_adapter = audio_adapter
        self.random_func = random_func or random.random
        self.time_func = time_func or time.monotonic
        self.inactivity_threshold = inactivity_threshold
        self.min_key_interval = min_key_interval

        self._lock = threading.Lock()
        self._last_keystroke_time: float = 0.0
        self._last_effect_time: float = 0.0
        self._consecutive_keystrokes: int = 0
        self._recent_key_timestamps: collections.deque[float] = collections.deque()
        self._recent_effect_timestamps: collections.deque[float] = collections.deque()
        self._active_mode_override: str | None = None

    @property
    def is_enabled(self) -> bool:
        """Return True if audio subsystem and haunted keystrokes setting are both active."""
        if self.audio_manager is None:
            return False
        return (
            self.audio_manager.settings.audio_enabled
            and self.audio_manager.settings.audio_haunted_keystrokes_enabled
            and not self.audio_manager._is_muted
        )

    @property
    def experience_mode(self) -> str:
        """Return the active experience mode."""
        if self._active_mode_override is not None:
            return self._active_mode_override
        if self.audio_adapter is not None:
            return self.audio_adapter.experience_mode
        return "normal"

    def set_experience_mode(self, mode: str) -> None:
        """Override or update active experience mode."""
        with self._lock:
            self._active_mode_override = str(mode).strip().lower()

    def reset(self) -> None:
        """Reset internal keystroke metrics and rate-limiting deques."""
        with self._lock:
            self._last_keystroke_time = 0.0
            self._last_effect_time = 0.0
            self._consecutive_keystrokes = 0
            self._recent_key_timestamps.clear()
            self._recent_effect_timestamps.clear()

    def is_typing_active(self, now: float | None = None) -> bool:
        """Return True if user has typed within the inactivity threshold window."""
        current_time = now if now is not None else self.time_func()
        with self._lock:
            if self._last_keystroke_time <= 0.0:
                return False
            return (current_time - self._last_keystroke_time) <= self.inactivity_threshold

    def get_typing_rate(self, now: float | None = None, window_seconds: float = 2.0) -> float:
        """Calculate average keystrokes per second over the specified window."""
        current_time = now if now is not None else self.time_func()
        with self._lock:
            cutoff = current_time - window_seconds
            count = sum(1 for t in self._recent_key_timestamps if t >= cutoff)
            return round(count / window_seconds, 2)

    def record_keystroke(self, now: float | None = None) -> AudioEventId | None:
        """Record aggregate keystroke activity and conditionally trigger an audio effect.

        Strict Privacy Notice:
        Takes no key character or text input. Only aggregate temporal metadata is tracked.

        Returns:
            AudioEventId of the triggered sound effect, or None if no effect was fired.
        """
        # Fast path check: if audio or setting is disabled or muted, immediately return None
        if not self.is_enabled:
            return None

        # Mode policy check
        mode = self.experience_mode.lower()
        if mode == "focus":
            # Focus mode strictly suppresses all non-essential typing audio manifestations
            return None

        profile = TYPING_MODE_PROFILES.get(mode, TYPING_MODE_PROFILES["normal"])
        if profile.get("suppressed", False):
            return None

        current_time = now if now is not None else self.time_func()

        with self._lock:
            # Debounce rapid key chatter (e.g. key repeats < min_key_interval)
            time_since_last_key = current_time - self._last_keystroke_time
            if self._last_keystroke_time > 0.0 and time_since_last_key < self.min_key_interval:
                return None

            # Detect typing inactivity pause: if gap exceeds threshold, reset consecutive count
            if time_since_last_key > self.inactivity_threshold:
                self._consecutive_keystrokes = 0

            self._consecutive_keystrokes += 1
            self._last_keystroke_time = current_time

            # Maintain recent keystroke timestamps (keep 5.0 seconds window)
            self._recent_key_timestamps.append(current_time)
            key_cutoff = current_time - 5.0
            while self._recent_key_timestamps and self._recent_key_timestamps[0] < key_cutoff:
                self._recent_key_timestamps.popleft()

            # Maintain recent effect timestamps (keep 60.0 seconds window)
            effect_cutoff = current_time - 60.0
            while (
                self._recent_effect_timestamps and self._recent_effect_timestamps[0] < effect_cutoff
            ):
                self._recent_effect_timestamps.popleft()

            # Rate Limiting 1: Maximum effects per minute check
            max_per_min = profile.get("max_effects_per_minute", 4)
            if len(self._recent_effect_timestamps) >= max_per_min:
                return None

            # Rate Limiting 2: Cooldown check since last effect
            cooldown = profile.get("cooldown_seconds", 3.0)
            if (current_time - self._last_effect_time) < cooldown:
                return None

            # Rate Limiting 3: Minimum typing activity before an effect can trigger
            min_keys = profile.get("min_keystrokes_before_effect", 4)
            if self._consecutive_keystrokes < min_keys:
                return None

            # Determine typing speed / burst state in the last 2 seconds
            two_sec_cutoff = current_time - 2.0
            keys_in_2s = sum(1 for t in self._recent_key_timestamps if t >= two_sec_cutoff)
            is_burst = keys_in_2s >= 8

            probability = (
                profile.get("burst_probability", 0.15)
                if is_burst
                else profile.get("base_probability", 0.08)
            )
            candidate_events = (
                profile.get("burst_events", profile["allowed_events"])
                if is_burst
                else profile.get("allowed_events", [AudioEventId.KEYSTROKE_HAUNT])
            )

            # Probability roll
            roll = self.random_func()
            if roll >= probability:
                return None

            # Select sound event deterministically from random source
            roll_sub = self.random_func()
            event_idx = int(roll_sub * len(candidate_events)) % len(candidate_events)
            chosen_event: AudioEventId = candidate_events[event_idx]

            # Mark effect timestamp and record to minute window
            self._last_effect_time = current_time
            self._recent_effect_timestamps.append(current_time)

            volume_scale = profile.get("volume_scale", 0.25)

        # Dispatch playback asynchronously through AudioManager
        if self.audio_manager is not None:
            try:
                self.audio_manager.play(chosen_event, volume_scale=volume_scale)
            except Exception as exc:
                logger.debug(
                    "Typing effect playback failed for event %s (%s). Non-blocking.",
                    chosen_event,
                    exc,
                )

        return chosen_event
