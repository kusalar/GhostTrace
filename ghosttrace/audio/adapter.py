"""Event-to-audio adapter connecting GhostTrace application events to horror sound effects."""

from __future__ import annotations

import logging
import threading
import time
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Final

from ghosttrace.audio.schemas import AudioEventId

if TYPE_CHECKING:
    from ghosttrace.audio.manager import AudioManager

logger = logging.getLogger("ghosttrace.audio.adapter")


class NotificationSeverity(StrEnum):
    """Severity classification for application notifications."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    STATUS = "status"


# Default cooldown intervals in seconds to prevent sound flooding
DEFAULT_COOLDOWNS: Final[dict[AudioEventId, float]] = {
    AudioEventId.NOTIFICATION_PING: 0.3,
    AudioEventId.NOTIFICATION_ALERT: 0.5,
    AudioEventId.APP_ERROR: 1.0,
    AudioEventId.CODING_SUCCESS: 1.0,
    AudioEventId.MOOD_SHIFT: 2.0,
    AudioEventId.GLITCH_DIGITAL: 0.8,
}


class AudioEventAdapter:
    """Centralized integration adapter routing application events to audio playback.

    Provides semantic, decoupled event hooks (startup, shutdown, notifications,
    Guardian security decisions, developer coding success, errors, and mood shifts).
    Handles thread safety, duplicate suppression, non-blocking failure isolation,
    and experience-mode policy enforcement (Focus, Normal, Ambient, Haunted).
    """

    def __init__(
        self,
        audio_manager: AudioManager | None = None,
        cooldowns: dict[AudioEventId, float] | None = None,
        typing_effects: Any | None = None,
        whisper_scheduler: Any | None = None,
    ) -> None:
        self.audio_manager = audio_manager
        self._lock = threading.Lock()
        self._is_shutdown = False
        self._startup_dispatched = False
        self._experience_mode: str = "normal"
        self._typing_effects = typing_effects
        self._whisper_scheduler = whisper_scheduler

        # Bounded cooldown and deduplication state
        self._cooldowns: dict[AudioEventId, float] = (
            dict(cooldowns) if cooldowns is not None else dict(DEFAULT_COOLDOWNS)
        )
        self._last_event_times: dict[AudioEventId, float] = {}
        self._last_notification_text: str | None = None
        self._last_notification_time: float = 0.0
        self._last_error_time: float = 0.0

    @property
    def is_enabled(self) -> bool:
        """Return whether underlying audio subsystem is enabled."""
        if self.audio_manager is None:
            return False
        return self.audio_manager.settings.audio_enabled

    @property
    def experience_mode(self) -> str:
        """Return the active experience mode."""
        with self._lock:
            return self._experience_mode

    def set_experience_mode(self, mode: str, force: bool = False) -> None:
        """Synchronize audio behavior with the active experience mode.

        Policies:
        - Normal: Normal event sounds; ambient off.
        - Ambient: Ambient dark hum loop started if audio enabled; normal event sounds.
        - Haunted: Ambient cold wind loop started if audio enabled; horror sounds active.
        - Focus: Ambient stopped immediately; non-essential sounds suppressed.
                 Critical Guardian and error sounds remain audible.
        """
        norm_mode = str(mode).strip().lower()
        with self._lock:
            if not force and self._experience_mode == norm_mode:
                return
            self._experience_mode = norm_mode

        logger.debug("AudioEventAdapter experience mode switched to '%s'.", norm_mode)

        if self._typing_effects is not None:
            self._typing_effects.set_experience_mode(norm_mode)

        if self._whisper_scheduler is not None:
            self._whisper_scheduler.set_experience_mode(norm_mode)

        if self.audio_manager is None:
            return

        # Ambient stream management per mode
        if norm_mode in ("focus", "normal"):
            self.audio_manager.stop_ambient()
        elif norm_mode == "ambient":
            if self.audio_manager.settings.audio_enabled and not self.audio_manager._is_muted:
                self.audio_manager.play_ambient(AudioEventId.AMBIENT_DARK_HUM)
            else:
                self.audio_manager.stop_ambient()
        elif norm_mode == "haunted":
            if self.audio_manager.settings.audio_enabled and not self.audio_manager._is_muted:
                self.audio_manager.play_ambient(AudioEventId.AMBIENT_COLD_WIND)
            else:
                self.audio_manager.stop_ambient()

    def on_experience_mode_changed(self, mode: str, force: bool = False) -> None:
        """Alias for set_experience_mode."""
        self.set_experience_mode(mode, force=force)

    def _should_suppress_cooldown(self, event_id: AudioEventId, now: float) -> bool:
        """Check if an event should be suppressed by its configured cooldown period."""
        cooldown = self._cooldowns.get(event_id, 0.0)
        if cooldown <= 0.0:
            return False
        last_time = self._last_event_times.get(event_id, 0.0)
        return (now - last_time) < cooldown

    def _safe_play(
        self,
        event_id: AudioEventId,
        volume_scale: float = 1.0,
        enforce_cooldown: bool = True,
    ) -> bool:
        """Internal thread-safe dispatch with error suppression."""
        if self.audio_manager is None or not self.audio_manager.settings.audio_enabled:
            return False

        now = time.monotonic()
        with self._lock:
            if self._is_shutdown and event_id != AudioEventId.SHUTDOWN:
                return False

            if enforce_cooldown and self._should_suppress_cooldown(event_id, now):
                logger.debug("Suppressing audio event %s due to active cooldown.", event_id)
                return False

            self._last_event_times[event_id] = now

        try:
            return bool(self.audio_manager.play(event_id, volume_scale=volume_scale))
        except Exception as exc:
            logger.debug(
                "Audio playback failed for event %s (%s). Non-blocking fallback.",
                event_id,
                type(exc).__name__,
            )
            return False

    def on_startup(self) -> bool:
        """Triggered upon successful application and UI initialization.

        Dispatches the startup sound exactly once. Subsequent invocations are ignored.
        """
        with self._lock:
            if self._startup_dispatched or self._is_shutdown:
                return False
            self._startup_dispatched = True

        logger.debug("Dispatching application startup audio event.")
        return self._safe_play(AudioEventId.STARTUP, enforce_cooldown=False)

    def on_shutdown(self) -> bool:
        """Triggered prior to application exit.

        Dispatches the shutdown sound and ensures safe audio backend teardown.
        Idempotent; repeated calls produce no additional sounds.
        """
        with self._lock:
            if self._is_shutdown:
                return False
            self._is_shutdown = True

        logger.debug("Dispatching application shutdown audio event.")
        # Play shutdown cue before teardown
        played = self._safe_play(AudioEventId.SHUTDOWN, enforce_cooldown=False)

        # Teardown whisper scheduler cleanly
        if self._whisper_scheduler is not None:
            try:
                self._whisper_scheduler.shutdown()
            except Exception as exc:
                logger.debug("Error shutting down whisper scheduler: %s", exc)

        # Teardown audio manager cleanly
        if self.audio_manager is not None:
            try:
                self.audio_manager.shutdown()
            except Exception as exc:
                logger.debug("Error shutting down audio manager: %s", exc)

        return played

    def on_notification(
        self,
        message: str = "",
        severity: NotificationSeverity | str = NotificationSeverity.INFO,
        important: bool = False,
    ) -> bool:
        """Triggered when an application notification is published.

        Maps severity to appropriate sound cue:
        - Critical / Error / Warning / important=True -> notification_alert
        - Info / Normal -> notification_ping (suppressed in Focus mode)
        - Status / Debug / Unimportant -> no sound (suppressed)
        """
        norm_severity = (
            severity.value if isinstance(severity, NotificationSeverity) else str(severity).lower()
        )

        # Unimportant status updates never trigger audio
        if norm_severity in ("status", "debug", "unimportant", "none"):
            return False

        is_important = important or norm_severity in ("warning", "error", "critical", "alert")

        # Focus mode suppresses non-essential notification pings
        with self._lock:
            if self._experience_mode == "focus" and not is_important:
                logger.debug("Focus mode suppressing standard notification ping.")
                return False

        now = time.monotonic()
        clean_msg = message.strip()

        with self._lock:
            # Duplicate notification message suppression within 1.0 second
            if (
                clean_msg
                and clean_msg == self._last_notification_text
                and (now - self._last_notification_time) < 1.0
            ):
                logger.debug("Suppressing duplicate notification audio.")
                return False

            self._last_notification_text = clean_msg
            self._last_notification_time = now

        target_event = (
            AudioEventId.NOTIFICATION_ALERT if is_important else AudioEventId.NOTIFICATION_PING
        )

        # If it was an error notification, record timestamp to deduplicate on_app_error
        if norm_severity in ("error", "critical"):
            with self._lock:
                self._last_error_time = now

        return self._safe_play(target_event, enforce_cooldown=True)

    def on_keystroke_activity(self, now: float | None = None) -> AudioEventId | None:
        """Triggered upon aggregate user typing activity in the terminal input widget.

        Strict Privacy Notice:
        No keystroke character, keycode, or text content is ever accepted or inspected.
        Only temporal typing metadata is processed.
        """
        if self._typing_effects is None:
            from ghosttrace.audio.typing_effects import TypingEffectsManager

            self._typing_effects = TypingEffectsManager(
                audio_manager=self.audio_manager,
                audio_adapter=self,
            )
        return self._typing_effects.record_keystroke(now=now)

    def on_guardian_intercept(self, command: str = "") -> bool:
        """Triggered when Command Guardian intercepts a dangerous command for approval.

        Never suppressed by cooldown or Focus mode to preserve safety awareness.
        """
        logger.debug("Guardian intercepted command for user approval.")
        return self._safe_play(AudioEventId.GUARDIAN_INTERCEPT, enforce_cooldown=False)

    def on_guardian_approved(self, token: str = "") -> bool:
        """Triggered ONLY after the user explicitly confirms and approves command execution."""
        logger.debug("Guardian command execution approved by user.")
        return self._safe_play(AudioEventId.GUARDIAN_APPROVED, enforce_cooldown=False)

    def on_guardian_blocked(self, token: str = "", reason: str = "") -> bool:
        """Triggered when a command is rejected, cancelled, or blocked by Guardian policy."""
        logger.debug("Guardian command blocked or cancelled.")
        return self._safe_play(AudioEventId.GUARDIAN_BLOCKED, enforce_cooldown=False)

    def on_coding_success(self, intent: str = "") -> bool:
        """Triggered when a developer coding operation (generation, review, analysis) succeeds.

        Suppressed in Focus mode.
        """
        with self._lock:
            if self._experience_mode == "focus":
                logger.debug("Focus mode suppressing developer coding success sound.")
                return False

        logger.debug("Developer coding task succeeded (%s).", intent)
        return self._safe_play(AudioEventId.CODING_SUCCESS, enforce_cooldown=True)

    def on_app_error(self, error: Exception | str | None = None) -> bool:
        """Triggered upon an application-level exception or inference failure.

        Deduplicated against notification errors. Never suppressed in Focus mode.
        """
        now = time.monotonic()
        with self._lock:
            # Suppress if error sound was already played via notification within 1.0 second
            if (now - self._last_error_time) < 1.0:
                logger.debug("Suppressing duplicate error audio.")
                return False
            self._last_error_time = now

        err_type = type(error).__name__ if isinstance(error, Exception) else "AppError"
        logger.debug("Application error dispatched to audio: %s", err_type)
        return self._safe_play(AudioEventId.APP_ERROR, enforce_cooldown=True)

    def on_mood_shift(self, old_mood: Any, new_mood: Any) -> bool:
        """Triggered when the ghost persona transitions between distinct emotional moods.

        Plays ONLY when old_mood != new_mood. Suppressed in Focus mode.
        """
        if old_mood is None or new_mood is None or old_mood == new_mood:
            return False

        with self._lock:
            if self._experience_mode == "focus":
                logger.debug("Focus mode suppressing mood shift sound.")
                return False

        logger.debug("Ghost persona mood shift detected: %s -> %s", old_mood, new_mood)
        return self._safe_play(AudioEventId.MOOD_SHIFT, enforce_cooldown=True)

    def on_glitch(self, glitch_type: str = "digital") -> bool:
        """Triggered upon atmospheric digital glitch or terminal fracture events.

        Suppressed in Focus mode.
        """
        with self._lock:
            if self._experience_mode == "focus":
                logger.debug("Focus mode suppressing glitch sound.")
                return False

        target_event = AudioEventId.GLITCH_DIGITAL
        if glitch_type == "static":
            target_event = AudioEventId.GLITCH_STATIC
        elif glitch_type == "corruption":
            target_event = AudioEventId.GLITCH_CORRUPTION

        return self._safe_play(target_event, enforce_cooldown=True)
