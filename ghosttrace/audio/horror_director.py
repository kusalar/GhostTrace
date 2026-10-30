"""Centralized dynamic horror event orchestration and adaptive audio director.

GhostTrace v1.2.0 Step 09: Centralized HorrorAudioDirector coordinating
haunted keystrokes, scheduled whispers, application events, glitches, and ambient loops.

Strict Privacy & Safety Guarantees:
- Zero raw keyboard capture; never accepts, inspects, or logs keystrokes or command contents.
- Zero microphone access, clipboard inspection, or operating-system monitoring.
- Zero AI/LLM inference for audio orchestration; entirely deterministic state machine.
- Spawns zero persistent Python worker threads and zero busy polling loops.
- Guardian security decisions, approvals, and error alerts take absolute precedence.
- Strictly opt-in: disabled by default (OFF).
"""

from __future__ import annotations

import collections
import logging
import random
import threading
import time
from collections.abc import Callable
from enum import IntEnum, StrEnum
from typing import TYPE_CHECKING, Any, Final

from ghosttrace.audio.schemas import AudioEventId

if TYPE_CHECKING:
    from ghosttrace.audio.manager import AudioManager
    from ghosttrace.config.settings import Settings

logger = logging.getLogger("ghosttrace.audio.horror_director")


class AudioPriority(IntEnum):
    """Explicit hierarchical priority classification for audio playback events."""

    CRITICAL = 1  # Guardian security decisions, critical errors (never blocked)
    IMPORTANT = 2  # Startup, shutdown, notifications, coding success
    ATMOSPHERIC = 3  # Keystrokes, scheduled whispers, glitches, mood shifts
    AMBIENT = 4  # Background ambient loops


class HorrorIntensity(StrEnum):
    """Deterministic intensity state governing atmospheric audio manifestations."""

    DORMANT = "dormant"  # Atmospheric effects suppressed (Focus mode, quiet/idle)
    SUBTLE = "subtle"  # Light manifestations (Normal mode active, Ambient mode base)
    UNSETTLING = "unsettling"  # Moderate effects (Ambient active, Haunted mode base)
    HAUNTED = "haunted"  # Maximum atmospheric richness (Haunted mode peak activity)


class SuppressionReason(StrEnum):
    """Machine-readable diagnostic reason for suppressed atmospheric audio events."""

    DIRECTOR_DISABLED = "director_disabled"
    AUDIO_DISABLED = "audio_disabled"
    AUDIO_MUTED = "audio_muted"
    FOCUS_MODE = "focus_mode"
    AI_GENERATING = "ai_generating"
    GUARDIAN_ACTIVE = "guardian_active"
    COMMAND_EXECUTING = "command_executing"
    INTENSITY_DORMANT = "intensity_dormant"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    COOLDOWN_ACTIVE = "cooldown_active"
    WHISPER_COLLISION = "whisper_collision"
    TYPING_COLLISION = "typing_collision"
    GLITCH_BURST = "glitch_burst"
    DUPLICATE_EVENT = "duplicate_event"


# Canonical mapping from sound event to priority tier
EVENT_PRIORITIES: Final[dict[AudioEventId, AudioPriority]] = {
    # CRITICAL: Guardian security & critical exceptions (never blocked by budgets)
    AudioEventId.GUARDIAN_INTERCEPT: AudioPriority.CRITICAL,
    AudioEventId.GUARDIAN_APPROVED: AudioPriority.CRITICAL,
    AudioEventId.GUARDIAN_BLOCKED: AudioPriority.CRITICAL,
    AudioEventId.APP_ERROR: AudioPriority.CRITICAL,
    # IMPORTANT: System lifecycle & high-value feedback
    AudioEventId.STARTUP: AudioPriority.IMPORTANT,
    AudioEventId.SHUTDOWN: AudioPriority.IMPORTANT,
    AudioEventId.NOTIFICATION_ALERT: AudioPriority.IMPORTANT,
    AudioEventId.NOTIFICATION_PING: AudioPriority.IMPORTANT,
    AudioEventId.CODING_SUCCESS: AudioPriority.IMPORTANT,
    # ATMOSPHERIC: Horror textures & contextual sound effects
    AudioEventId.KEYSTROKE_HAUNT: AudioPriority.ATMOSPHERIC,
    AudioEventId.WHISPER_SPECTRAL: AudioPriority.ATMOSPHERIC,
    AudioEventId.WHISPER_BREATH: AudioPriority.ATMOSPHERIC,
    AudioEventId.WHISPER_MURMUR: AudioPriority.ATMOSPHERIC,
    AudioEventId.GLITCH_DIGITAL: AudioPriority.ATMOSPHERIC,
    AudioEventId.GLITCH_STATIC: AudioPriority.ATMOSPHERIC,
    AudioEventId.GLITCH_CORRUPTION: AudioPriority.ATMOSPHERIC,
    AudioEventId.MOOD_SHIFT: AudioPriority.ATMOSPHERIC,
    # AMBIENT: Background continuous loops
    AudioEventId.AMBIENT_DARK_HUM: AudioPriority.AMBIENT,
    AudioEventId.AMBIENT_COLD_WIND: AudioPriority.AMBIENT,
    AudioEventId.AMBIENT_DISTANT_THUNDER: AudioPriority.AMBIENT,
}

# Declarative budget limits and intervals per experience mode
DEFAULT_ATMOSPHERIC_BUDGETS: Final[dict[str, dict[str, Any]]] = {
    "normal": {
        "max_per_minute": 3,
        "min_interval_seconds": 8.0,
        "glitch_cooldown_seconds": 3.0,
        "whisper_cooldown_seconds": 10.0,
        "collision_window_seconds": 2.5,
    },
    "ambient": {
        "max_per_minute": 5,
        "min_interval_seconds": 5.0,
        "glitch_cooldown_seconds": 2.5,
        "whisper_cooldown_seconds": 8.0,
        "collision_window_seconds": 2.0,
    },
    "haunted": {
        "max_per_minute": 8,
        "min_interval_seconds": 2.0,
        "glitch_cooldown_seconds": 1.5,
        "whisper_cooldown_seconds": 4.0,
        "collision_window_seconds": 1.5,
    },
    "focus": {
        "max_per_minute": 0,
        "min_interval_seconds": 9999.0,
        "glitch_cooldown_seconds": 9999.0,
        "whisper_cooldown_seconds": 9999.0,
        "collision_window_seconds": 9999.0,
    },
}


class HorrorAudioDirector:
    """Centralized coordinator for atmospheric horror audio events in GhostTrace.

    Evaluates application state context, enforces experience-mode policies,
    calculates deterministic intensity, manages event budgets, and eliminates
    sound collisions without creating new audio backends or background worker threads.
    """

    def __init__(
        self,
        audio_manager: AudioManager | None = None,
        settings: Settings | None = None,
        experience_mode: str = "normal",
        random_func: Callable[[], float] | None = None,
        time_func: Callable[[], float] | None = None,
        context_check_func: Callable[[], dict[str, bool]] | None = None,
        budgets: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.audio_manager = audio_manager
        self.settings = settings
        self._experience_mode = str(experience_mode).strip().lower()
        self.random_func = random_func or random.random
        self.time_func = time_func or time.monotonic
        self.context_check_func = context_check_func
        self._budgets = dict(budgets) if budgets is not None else dict(DEFAULT_ATMOSPHERIC_BUDGETS)

        self._lock = threading.RLock()
        self._is_shutdown = False
        self._enabled_override: bool | None = None

        # Rolling state tracking
        self._recent_atmospheric_timestamps: collections.deque[float] = collections.deque()
        self._recent_typing_activity_timestamps: collections.deque[float] = collections.deque()
        self._last_atmospheric_time: float = 0.0
        self._last_whisper_time: float = 0.0
        self._last_typing_effect_time: float = 0.0
        self._last_glitch_time: float = 0.0
        self._last_developer_success_time: float = 0.0
        self._last_suppression_reason: str | None = None
        self._last_event_id: AudioEventId | None = None
        self._last_event_time: float = 0.0

    @property
    def is_enabled(self) -> bool:
        """Return whether dynamic horror orchestration is active."""
        with self._lock:
            if self._enabled_override is not None:
                return self._enabled_override
            if self.settings is not None:
                return getattr(self.settings, "audio_dynamic_horror_enabled", False)
            if self.audio_manager is not None and getattr(self.audio_manager, "settings", None):
                return getattr(self.audio_manager.settings, "audio_dynamic_horror_enabled", False)
            return False

    def set_enabled(self, enabled: bool) -> None:
        """Programmatically override director enabled state."""
        with self._lock:
            self._enabled_override = bool(enabled)
            if self.audio_manager is not None and getattr(self.audio_manager, "settings", None):
                self.audio_manager.settings.audio_dynamic_horror_enabled = bool(enabled)

    @property
    def experience_mode(self) -> str:
        """Return the active experience mode."""
        with self._lock:
            return self._experience_mode

    def set_experience_mode(self, mode: str) -> None:
        """Update active experience mode dynamically without restart."""
        norm_mode = str(mode).strip().lower()
        with self._lock:
            self._experience_mode = norm_mode
        logger.debug("HorrorAudioDirector experience mode updated to '%s'.", norm_mode)

    @property
    def last_suppression_reason(self) -> str | None:
        """Return diagnostic reason for the most recent suppressed atmospheric event."""
        with self._lock:
            return self._last_suppression_reason

    def get_priority(self, event_id: AudioEventId | str) -> AudioPriority:
        """Return the hierarchical priority tier for a given audio event."""
        if isinstance(event_id, str):
            try:
                event_id = AudioEventId(event_id)
            except ValueError:
                return AudioPriority.ATMOSPHERIC
        return EVENT_PRIORITIES.get(event_id, AudioPriority.ATMOSPHERIC)

    def record_typing_activity(self, now: float | None = None) -> None:
        """Record aggregate user typing occurrence (zero character or key metadata)."""
        current_time = now if now is not None else self.time_func()
        with self._lock:
            self._recent_typing_activity_timestamps.append(current_time)
            # Retain only last 30.0 seconds of typing activity
            cutoff = current_time - 30.0
            while (
                self._recent_typing_activity_timestamps
                and self._recent_typing_activity_timestamps[0] < cutoff
            ):
                self._recent_typing_activity_timestamps.popleft()

    def record_developer_success(self, now: float | None = None) -> None:
        """Record developer coding task completion."""
        current_time = now if now is not None else self.time_func()
        with self._lock:
            self._last_developer_success_time = current_time

    def compute_intensity(self, now: float | None = None) -> HorrorIntensity:
        """Calculate deterministic atmospheric horror intensity from application state.

        Determinism Guarantees:
        - Focus mode: strictly DORMANT.
        - Director disabled: strictly DORMANT.
        - Normal mode: DORMANT base; escalates to SUBTLE under sustained typing/activity.
        - Ambient mode: SUBTLE base; escalates to UNSETTLING under sustained activity.
        - Haunted mode: UNSETTLING base; escalates to HAUNTED under sustained activity.
        """
        current_time = now if now is not None else self.time_func()
        with self._lock:
            if not self.is_enabled:
                return HorrorIntensity.DORMANT

            mode = self._experience_mode
            if mode == "focus":
                return HorrorIntensity.DORMANT

            # Clean aged typing activity
            cutoff = current_time - 30.0
            while (
                self._recent_typing_activity_timestamps
                and self._recent_typing_activity_timestamps[0] < cutoff
            ):
                self._recent_typing_activity_timestamps.popleft()

            # Clean aged atmospheric events
            atmo_cutoff = current_time - 60.0
            while (
                self._recent_atmospheric_timestamps
                and self._recent_atmospheric_timestamps[0] < atmo_cutoff
            ):
                self._recent_atmospheric_timestamps.popleft()

            typing_count = len(self._recent_typing_activity_timestamps)
            atmo_count = len(self._recent_atmospheric_timestamps)
            dev_boost = (current_time - self._last_developer_success_time) < 15.0

            if mode == "normal":
                if typing_count >= 5 or atmo_count >= 2 or dev_boost:
                    return HorrorIntensity.SUBTLE
                return HorrorIntensity.DORMANT

            if mode == "ambient":
                if typing_count >= 6 or atmo_count >= 3 or dev_boost:
                    return HorrorIntensity.UNSETTLING
                return HorrorIntensity.SUBTLE

            if mode == "haunted":
                if typing_count >= 4 or atmo_count >= 2 or dev_boost:
                    return HorrorIntensity.HAUNTED
                return HorrorIntensity.UNSETTLING

            return HorrorIntensity.SUBTLE

    def can_dispatch(
        self,
        event_id: AudioEventId | str,
        now: float | None = None,
    ) -> tuple[bool, str | None]:
        """Evaluate whether an audio event is permitted to play under current policy.

        Returns (allowed, suppression_reason).
        """
        current_time = now if now is not None else self.time_func()
        priority = self.get_priority(event_id)

        # Baseline hardware/subsystem availability check
        if self.audio_manager is not None:
            settings = getattr(self.audio_manager, "settings", None)
            if settings is not None and getattr(settings, "audio_enabled", True) is False:
                return False, SuppressionReason.AUDIO_DISABLED.value
            muted_val = getattr(self.audio_manager, "_is_muted", None)
            if muted_val is None or not isinstance(muted_val, bool):
                muted_val = getattr(self.audio_manager, "is_muted", False)
            if muted_val is True:
                return False, SuppressionReason.AUDIO_MUTED.value
            vol_val = getattr(self.audio_manager, "_volume", None)
            if vol_val is None or not isinstance(vol_val, (int, float)):
                vol_val = getattr(self.audio_manager, "master_volume", 1.0)
            if isinstance(vol_val, (int, float)) and vol_val <= 0.0:
                return False, SuppressionReason.AUDIO_MUTED.value

        with self._lock:
            if self._is_shutdown and event_id != AudioEventId.SHUTDOWN:
                return False, SuppressionReason.AUDIO_DISABLED.value

            mode = self._experience_mode

            # CRITICAL events (Guardian approvals/interceptions, App Errors) are NEVER blocked
            if priority == AudioPriority.CRITICAL:
                return True, None

            # IMPORTANT events (Startup, Shutdown, Notifications, Coding Success)
            if priority == AudioPriority.IMPORTANT:
                if mode == "focus" and event_id == AudioEventId.NOTIFICATION_PING:
                    return False, SuppressionReason.FOCUS_MODE.value
                return True, None

            # AMBIENT loops
            if priority == AudioPriority.AMBIENT:
                if mode in ("focus", "normal"):
                    return False, SuppressionReason.FOCUS_MODE.value
                return True, None

            # ATMOSPHERIC events (Keystrokes, Whispers, Glitches, Mood Shifts)
            if not self.is_enabled:
                # When director orchestration is OFF, atmospheric events follow basic rules
                if mode == "focus":
                    return False, SuppressionReason.FOCUS_MODE.value
                return True, None

            # Focus mode 100% suppresses all atmospheric manifestations
            if mode == "focus":
                return False, SuppressionReason.FOCUS_MODE.value

            # Application-context evaluation
            if self.context_check_func is not None:
                try:
                    ctx = self.context_check_func()
                    if ctx.get("is_generating", False):
                        return False, SuppressionReason.AI_GENERATING.value
                    if ctx.get("is_guardian_active", False):
                        return False, SuppressionReason.GUARDIAN_ACTIVE.value
                    if ctx.get("is_executing_command", False):
                        return False, SuppressionReason.COMMAND_EXECUTING.value
                except Exception as exc:
                    logger.debug("Context check function error: %s", exc)

            budget = self._budgets.get(mode, self._budgets["normal"])

            # Clean aged atmospheric timestamps (60s rolling window)
            minute_cutoff = current_time - 60.0
            while (
                self._recent_atmospheric_timestamps
                and self._recent_atmospheric_timestamps[0] < minute_cutoff
            ):
                self._recent_atmospheric_timestamps.popleft()

            # 1. Cross-system conflict prevention
            collision_window = budget.get("collision_window_seconds", 2.0)
            is_whisper = event_id in (
                AudioEventId.WHISPER_BREATH,
                AudioEventId.WHISPER_SPECTRAL,
                AudioEventId.WHISPER_MURMUR,
            )
            is_typing = event_id == AudioEventId.KEYSTROKE_HAUNT
            is_glitch = event_id in (
                AudioEventId.GLITCH_DIGITAL,
                AudioEventId.GLITCH_STATIC,
                AudioEventId.GLITCH_CORRUPTION,
            )

            # Prevent sound collisions between whispers and typing effects
            if is_whisper:
                whisper_cd = budget.get("whisper_cooldown_seconds", 8.0)
                if (current_time - self._last_whisper_time) < whisper_cd:
                    return False, SuppressionReason.WHISPER_COLLISION.value
                if (current_time - self._last_typing_effect_time) < collision_window:
                    return False, SuppressionReason.TYPING_COLLISION.value

            if is_typing and (current_time - self._last_whisper_time) < collision_window:
                return False, SuppressionReason.WHISPER_COLLISION.value

            if is_glitch:
                glitch_cd = budget.get("glitch_cooldown_seconds", 2.5)
                if (current_time - self._last_glitch_time) < glitch_cd:
                    return False, SuppressionReason.GLITCH_BURST.value

            # 2. Minimum interval between atmospheric effects
            min_interval = budget.get("min_interval_seconds", 8.0)
            if (current_time - self._last_atmospheric_time) < min_interval:
                return False, SuppressionReason.COOLDOWN_ACTIVE.value

            # 3. Rate window ceiling check
            max_per_min = budget.get("max_per_minute", 3)
            if len(self._recent_atmospheric_timestamps) >= max_per_min:
                return False, SuppressionReason.RATE_LIMIT_EXCEEDED.value

        return True, None

    def dispatch_event(
        self,
        event_id: AudioEventId | str,
        volume_scale: float = 1.0,
        loop: bool = False,
        now: float | None = None,
    ) -> bool:
        """Evaluate policy, coordinate atmospheric state, and dispatch playback to AudioManager.

        Returns True if playback was dispatched; False if suppressed or failed.
        """
        current_time = now if now is not None else self.time_func()
        allowed, reason = self.can_dispatch(event_id, now=current_time)

        if not allowed:
            with self._lock:
                self._last_suppression_reason = reason
            logger.debug("HorrorAudioDirector suppressed event %s (reason: %s).", event_id, reason)
            return False

        priority = self.get_priority(event_id)
        effective_volume = volume_scale

        with self._lock:
            # For atmospheric events when dynamic horror is active, apply intensity tuning
            if priority == AudioPriority.ATMOSPHERIC and self.is_enabled:
                intensity = self.compute_intensity(now=current_time)
                if intensity == HorrorIntensity.SUBTLE:
                    effective_volume *= 0.85
                elif intensity == HorrorIntensity.HAUNTED:
                    effective_volume = min(1.0, effective_volume * 1.15)

                # Record event metadata
                self._last_atmospheric_time = current_time
                self._recent_atmospheric_timestamps.append(current_time)

                if event_id in (
                    AudioEventId.WHISPER_BREATH,
                    AudioEventId.WHISPER_SPECTRAL,
                    AudioEventId.WHISPER_MURMUR,
                ):
                    self._last_whisper_time = current_time
                elif event_id == AudioEventId.KEYSTROKE_HAUNT:
                    self._last_typing_effect_time = current_time
                elif event_id in (
                    AudioEventId.GLITCH_DIGITAL,
                    AudioEventId.GLITCH_STATIC,
                    AudioEventId.GLITCH_CORRUPTION,
                ):
                    self._last_glitch_time = current_time

            self._last_event_id = event_id if isinstance(event_id, AudioEventId) else None
            self._last_event_time = current_time
            self._last_suppression_reason = None

        if self.audio_manager is None:
            return False

        try:
            if loop:
                return bool(
                    self.audio_manager.play(event_id, volume_scale=effective_volume, loop=True)
                )
            return bool(self.audio_manager.play(event_id, volume_scale=effective_volume))
        except Exception as exc:
            logger.debug(
                "Audio playback failed through director for event %s (%s). Non-blocking.",
                event_id,
                exc,
            )
            return False

    def can_dispatch_whisper(self, now: float | None = None) -> bool:
        """Check whether a scheduled whisper effect is permitted by director policy."""
        allowed, reason = self.can_dispatch(AudioEventId.WHISPER_BREATH, now=now)
        if not allowed:
            with self._lock:
                self._last_suppression_reason = reason
        return allowed

    def can_dispatch_typing(self, now: float | None = None) -> bool:
        """Check whether a typing keystroke effect is permitted by director policy."""
        allowed, reason = self.can_dispatch(AudioEventId.KEYSTROKE_HAUNT, now=now)
        if not allowed:
            with self._lock:
                self._last_suppression_reason = reason
        return allowed

    def get_telemetry(self) -> dict[str, Any]:
        """Return diagnostic metrics and operational status for telemetry inspection."""
        now = self.time_func()
        with self._lock:
            # Clean window for accurate telemetry
            minute_cutoff = now - 60.0
            while (
                self._recent_atmospheric_timestamps
                and self._recent_atmospheric_timestamps[0] < minute_cutoff
            ):
                self._recent_atmospheric_timestamps.popleft()

            atmo_count = len(self._recent_atmospheric_timestamps)
            reason = self._last_suppression_reason
            mode = self._experience_mode
            enabled = self.is_enabled

        intensity = self.compute_intensity(now=now).value

        return {
            "dynamic_horror_enabled": enabled,
            "horror_intensity": intensity,
            "experience_mode": mode,
            "atmospheric_events_in_window": atmo_count,
            "last_suppression_reason": reason,
        }

    def shutdown(self) -> None:
        """Cleanly reset director queues and mark inactive."""
        with self._lock:
            self._is_shutdown = True
            self._recent_atmospheric_timestamps.clear()
            self._recent_typing_activity_timestamps.clear()
        logger.debug("HorrorAudioDirector shut down cleanly.")
