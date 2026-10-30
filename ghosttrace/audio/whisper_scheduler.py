"""Scheduled whisper audio manifestations for GhostTrace dark horror audio (v1.2.0 Step 08).

This module manages rare, unpredictable, atmospheric whisper-like sound effects
using procedural audio assets (spectral_whisper, chilling_breath, eerie_murmur).

Strict Privacy & Safety Guarantees:
- Purely synthetic/procedural sound effects; zero spoken words, speech, or TTS.
- Zero AI-generated dialogue, zero cloud synthesis, and zero network calls.
- Zero microphone access, capture buffers, or recording APIs.
- Operates on Textual's event-loop timer; spawns zero persistent Python worker threads.
- Context-aware suppression: immediately silenced during Focus mode, Guardian
  prompts, active command generation, or error conditions.
- Strict opt-in preference: disabled by default (OFF).
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

logger = logging.getLogger("ghosttrace.audio.whispers")


# Declarative tuning profiles per experience mode
WHISPER_MODE_PROFILES: Final[dict[str, dict[str, Any]]] = {
    "normal": {
        "min_interval_seconds": 180.0,  # 3 minutes
        "max_interval_seconds": 360.0,  # 6 minutes
        "cooldown_seconds": 120.0,  # 2 minutes
        "max_per_hour": 3,
        "volume_scale": 0.20,
        "allowed_events": [AudioEventId.WHISPER_BREATH],
    },
    "ambient": {
        "min_interval_seconds": 90.0,  # 1.5 minutes
        "max_interval_seconds": 210.0,  # 3.5 minutes
        "cooldown_seconds": 60.0,  # 1 minute
        "max_per_hour": 6,
        "volume_scale": 0.25,
        "allowed_events": [AudioEventId.WHISPER_BREATH, AudioEventId.WHISPER_SPECTRAL],
    },
    "haunted": {
        "min_interval_seconds": 45.0,  # 45 seconds
        "max_interval_seconds": 120.0,  # 2 minutes
        "cooldown_seconds": 30.0,  # 30 seconds
        "max_per_hour": 12,
        "volume_scale": 0.35,
        "allowed_events": [
            AudioEventId.WHISPER_BREATH,
            AudioEventId.WHISPER_SPECTRAL,
            AudioEventId.WHISPER_MURMUR,
        ],
    },
    "focus": {
        "suppressed": True,
    },
}


class WhisperScheduler:
    """Event-driven scheduler for subtle, unpredictable horror whisper effects.

    Integrates with Textual's timer loop without spawning persistent worker threads.
    Supports deterministic clock and random injections for testing.
    """

    def __init__(
        self,
        audio_manager: AudioManager | None = None,
        audio_adapter: AudioEventAdapter | None = None,
        random_func: Callable[[], float] | None = None,
        time_func: Callable[[], float] | None = None,
        schedule_timer_func: Callable[[float, Callable[[], None]], Any] | None = None,
        cancel_timer_func: Callable[[Any], None] | None = None,
        context_check_func: Callable[[], bool] | None = None,
    ) -> None:
        self.audio_manager = audio_manager
        self.audio_adapter = audio_adapter
        self.random_func = random_func or random.random
        self.time_func = time_func or time.monotonic
        self.schedule_timer_func = schedule_timer_func
        self.cancel_timer_func = cancel_timer_func
        self.context_check_func = context_check_func

        self._lock = threading.Lock()
        self._last_whisper_time: float = 0.0
        self._recent_whisper_timestamps: collections.deque[float] = collections.deque()
        self._active_timer: Any | None = None
        self._active_mode_override: str | None = None
        self._is_shutdown = False
        self._is_whisper_playing = False

    @property
    def is_enabled(self) -> bool:
        """Return True if master audio and scheduled whispers setting are both active."""
        if self._is_shutdown or self.audio_manager is None:
            return False
        return (
            self.audio_manager.settings.audio_enabled
            and self.audio_manager.settings.audio_scheduled_whispers_enabled
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
        """Synchronize scheduling policy with experience mode changes."""
        norm_mode = str(mode).strip().lower()
        with self._lock:
            self._active_mode_override = norm_mode

        logger.debug("WhisperScheduler mode updated to '%s'.", norm_mode)

        if norm_mode == "focus":
            # Focus mode suppresses all whispers immediately and cancels pending timer
            self.cancel()

    def calculate_next_interval(self, mode: str | None = None) -> float:
        """Calculate next randomized delay within the mode's configured boundaries."""
        target_mode = (mode or self.experience_mode).lower()
        profile = WHISPER_MODE_PROFILES.get(target_mode, WHISPER_MODE_PROFILES["normal"])

        if profile.get("suppressed", False):
            return 300.0  # Safe default if evaluated

        min_sec = float(profile.get("min_interval_seconds", 120.0))
        max_sec = float(profile.get("max_interval_seconds", 300.0))

        # Uniform randomized interpolation between min and max
        rand_val = self.random_func()
        return round(min_sec + (rand_val * (max_sec - min_sec)), 2)

    def can_play_whisper(self, now: float | None = None) -> bool:
        """Check all safety, context, cooldown, and limit constraints."""
        if not self.is_enabled:
            return False

        mode = self.experience_mode.lower()
        if mode == "focus":
            return False

        profile = WHISPER_MODE_PROFILES.get(mode, WHISPER_MODE_PROFILES["normal"])
        if profile.get("suppressed", False):
            return False

        # Context-aware check: suppress during Guardian approvals, LLM generation, etc.
        if self.context_check_func is not None:
            try:
                if not self.context_check_func():
                    logger.debug("Context check active: suppressing whisper opportunity.")
                    return False
            except Exception as exc:
                logger.debug("Context check failed (%s); safe suppression.", exc)
                return False

        current_time = now if now is not None else self.time_func()

        with self._lock:
            if self._is_whisper_playing:
                return False

            # Cooldown check since last played whisper
            cooldown = profile.get("cooldown_seconds", 60.0)
            time_since_whisper = current_time - self._last_whisper_time
            if self._last_whisper_time > 0.0 and time_since_whisper < cooldown:
                logger.debug("Whisper suppressed by active cooldown period.")
                return False

            # Purge timestamps older than 1 hour (3600.0s)
            hour_cutoff = current_time - 3600.0
            while (
                self._recent_whisper_timestamps and self._recent_whisper_timestamps[0] < hour_cutoff
            ):
                self._recent_whisper_timestamps.popleft()

            # Rolling window hourly ceiling check
            max_per_hour = profile.get("max_per_hour", 6)
            if len(self._recent_whisper_timestamps) >= max_per_hour:
                logger.debug("Whisper suppressed by hourly frequency limit (%d).", max_per_hour)
                return False

        return True

    def trigger_whisper(
        self,
        event_id: AudioEventId | None = None,
        now: float | None = None,
    ) -> AudioEventId | None:
        """Trigger a whisper manifestation immediately if all policy checks pass."""
        if not self.can_play_whisper(now=now):
            return None

        current_time = now if now is not None else self.time_func()
        mode = self.experience_mode.lower()
        profile = WHISPER_MODE_PROFILES.get(mode, WHISPER_MODE_PROFILES["normal"])
        allowed = profile.get("allowed_events", [AudioEventId.WHISPER_BREATH])

        # Pick event
        if event_id is not None and event_id in allowed:
            chosen_event = event_id
        else:
            rand_pick = self.random_func()
            idx = int(rand_pick * len(allowed)) % len(allowed)
            chosen_event = allowed[idx]

        volume_scale = profile.get("volume_scale", 0.25)

        with self._lock:
            self._last_whisper_time = current_time
            self._recent_whisper_timestamps.append(current_time)
            self._is_whisper_playing = True

        # Dispatch playback
        success = False
        if self.audio_manager is not None:
            try:
                success = bool(self.audio_manager.play(chosen_event, volume_scale=volume_scale))
                logger.debug("Scheduled whisper triggered: %s (success=%s)", chosen_event, success)
            except Exception as exc:
                logger.debug("Scheduled whisper playback error (%s). Non-blocking.", exc)
            finally:
                with self._lock:
                    self._is_whisper_playing = False

        return chosen_event if success else None

    def tick(self, now: float | None = None) -> AudioEventId | None:
        """Timer callback tick evaluating whether a scheduled whisper should play."""
        return self.trigger_whisper(now=now)

    def schedule_next(self, delay: float | None = None) -> None:
        """Schedule the next randomized timer tick via Textual event loop."""
        with self._lock:
            if self._is_shutdown or not self.is_enabled or self.experience_mode == "focus":
                self._cancel_active_timer()
                return

            if self.schedule_timer_func is None:
                return

            next_delay = delay if delay is not None else self.calculate_next_interval()
            self._cancel_active_timer()

            try:
                self._active_timer = self.schedule_timer_func(
                    next_delay, self._on_scheduled_timer_tick
                )
                logger.debug("Scheduled next whisper in %.2f seconds.", next_delay)
            except Exception as exc:
                logger.debug("Failed to schedule whisper timer: %s", exc)

    def _on_scheduled_timer_tick(self) -> None:
        """Internal callback invoked when Textual's timer fires."""
        if self._is_shutdown:
            return

        try:
            self.tick()
        finally:
            # Always schedule next opportunity if still active
            self.schedule_next()

    def _cancel_active_timer(self) -> None:
        """Internal helper to cancel any existing pending timer."""
        if self._active_timer is not None:
            if self.cancel_timer_func is not None:
                try:
                    self.cancel_timer_func(self._active_timer)
                except Exception as exc:
                    logger.debug("Error canceling whisper timer: %s", exc)
            elif hasattr(self._active_timer, "stop"):
                try:
                    self._active_timer.stop()
                except Exception as exc:
                    logger.debug("Error stopping timer object: %s", exc)
            self._active_timer = None

    def cancel(self) -> None:
        """Cancel pending scheduled whisper timer."""
        with self._lock:
            self._cancel_active_timer()

    def start(self) -> None:
        """Start or restart the randomized scheduler loop."""
        with self._lock:
            self._is_shutdown = False
        self.schedule_next()

    def shutdown(self) -> None:
        """Safely shut down the scheduler and release timer handles."""
        with self._lock:
            self._is_shutdown = True
            self._cancel_active_timer()
            self._recent_whisper_timestamps.clear()
            self._is_whisper_playing = False
        logger.debug("WhisperScheduler shut down cleanly.")
