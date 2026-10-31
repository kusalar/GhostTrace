"""Central audio subsystem lifecycle, controls, and event management for GhostTrace."""

from __future__ import annotations

import contextlib
import logging
import threading
from pathlib import Path
from typing import Any

from ghosttrace.audio.backend import AudioBackend, MiniAudioBackend, NullAudioBackend
from ghosttrace.audio.catalog import AudioCatalog
from ghosttrace.audio.exceptions import (
    AudioInitializationError,
    InvalidVolumeError,
)
from ghosttrace.audio.preferences import (
    AudioPreferences,
    apply_preferences_with_precedence,
    get_audio_preferences_path,
    save_audio_preferences,
)
from ghosttrace.audio.schemas import AudioEventId, AudioStatus, SoundEffect
from ghosttrace.config.settings import Settings, get_settings

logger = logging.getLogger("ghosttrace.audio.manager")


class AudioManager:
    """High-level orchestrator for horror sound effects and atmospheric audio."""

    def __init__(
        self,
        settings: Settings | None = None,
        backend: AudioBackend | None = None,
        catalog: AudioCatalog | None = None,
    ) -> None:
        self.settings: Settings = settings if settings is not None else get_settings()
        self.catalog: AudioCatalog = catalog if catalog is not None else AudioCatalog()
        self._lock = threading.Lock()
        self._init_lock = threading.Lock()
        self._is_shutdown = False

        # Apply persisted user preferences with strict environment variable precedence
        resolved = apply_preferences_with_precedence(self.settings)
        self.settings.audio_enabled = resolved["enabled"]
        self.settings.audio_volume = resolved["volume"]
        self.settings.audio_ambient_volume = resolved["ambient_volume"]
        self.settings.audio_muted = resolved["muted"]
        self.settings.audio_haunted_keystrokes_enabled = resolved.get(
            "haunted_keystrokes_enabled", False
        )
        self.settings.audio_scheduled_whispers_enabled = resolved.get(
            "scheduled_whispers_enabled", False
        )
        self.settings.audio_dynamic_horror_enabled = resolved.get("dynamic_horror_enabled", False)

        self._volume: float = self.settings.audio_volume
        self._director: Any | None = None
        self._whisper_scheduler: Any | None = None
        self._ambient_volume: float = self.settings.audio_ambient_volume
        self._is_muted: bool = self.settings.audio_muted

        # Select and initialize backend
        self.backend: AudioBackend = self._initialize_backend(backend)

    def _initialize_backend(self, custom_backend: AudioBackend | None) -> AudioBackend:
        """Initialize the audio backend safely.

        If audio is disabled, or if backend initialization fails, cleanly falls back
        to NullAudioBackend so GhostTrace startup is never blocked or crashed.
        """
        if not self.settings.audio_enabled:
            logger.debug("Audio subsystem is disabled in configuration. Using NullAudioBackend.")
            null_backend = NullAudioBackend(
                volume=self._volume, ambient_volume=self._ambient_volume
            )
            null_backend.set_muted(self._is_muted)
            null_backend.initialize()
            return null_backend

        # Audio is explicitly enabled
        target_backend = (
            custom_backend
            if custom_backend is not None
            else MiniAudioBackend(volume=self._volume, ambient_volume=self._ambient_volume)
        )
        target_backend.set_muted(self._is_muted)

        try:
            success = target_backend.initialize()
            if not success:
                logger.warning(
                    "Configured audio backend failed initialization. "
                    "Falling back to safe NullAudioBackend."
                )
                fallback = NullAudioBackend(
                    volume=self._volume, ambient_volume=self._ambient_volume
                )
                fallback.set_muted(self._is_muted)
                fallback.initialize()
                return fallback
            return target_backend
        except Exception as exc:
            logger.warning(
                "Exception initializing audio backend (%s). Falling back to NullAudioBackend: %s",
                type(exc).__name__,
                exc,
            )
            fallback = NullAudioBackend(volume=self._volume, ambient_volume=self._ambient_volume)
            fallback.set_muted(self._is_muted)
            fallback.initialize()
            return fallback

    def initialize(self) -> bool:
        """Explicitly re-initialize backend resources if previously shutdown."""
        with self._init_lock:
            with self._lock:
                if (
                    not self._is_shutdown
                    and not isinstance(self.backend, NullAudioBackend)
                    and self.backend.is_available()
                ):
                    return True
                self._is_shutdown = False

            try:
                return self.backend.initialize()
            except Exception as exc:
                msg = f"Failed to initialize audio backend: {exc}"
                raise AudioInitializationError(msg) from exc

    def shutdown(self) -> None:
        """Safely and idempotently release all audio handles and background tasks."""
        with self._init_lock, self._lock:
            if self._is_shutdown:
                return
            logger.debug("Shutting down AudioManager and releasing audio resources.")
            try:
                self.backend.stop_all()
                self.backend.shutdown()
            except Exception as exc:
                logger.warning("Error during audio backend shutdown: %s", exc)
            finally:
                self._is_shutdown = True

    def is_available(self) -> bool:
        """Return True if backend is initialized and playback hardware is available."""
        with self._lock:
            return not isinstance(self.backend, NullAudioBackend) and self.backend.is_available()

    def enable(self, persist: bool = True) -> bool:
        """Enable audio subsystem, initialize hardware if available, and persist preference."""
        with self._init_lock:
            with self._lock:
                self.settings.audio_enabled = True
                self._is_shutdown = False
                if not isinstance(self.backend, NullAudioBackend) and self.backend.is_available():
                    if persist:
                        self._persist_current_preferences()
                    return True

            target_backend = MiniAudioBackend(
                volume=self._volume, ambient_volume=self._ambient_volume
            )
            target_backend.set_muted(self._is_muted)
            try:
                success = target_backend.initialize()
                with self._lock:
                    if success:
                        self.backend = target_backend
                        logger.info("Audio enabled successfully on MiniAudioBackend.")
                    else:
                        logger.warning(
                            "Audio enabled in configuration, but hardware device is unavailable."
                        )
                        self.backend = NullAudioBackend(
                            volume=self._volume, ambient_volume=self._ambient_volume
                        )
                        self.backend.set_muted(self._is_muted)
                        self.backend.initialize()
            except Exception as exc:
                logger.warning("Error initializing backend during enable: %s", exc)
                with self._lock:
                    self.backend = NullAudioBackend(
                        volume=self._volume, ambient_volume=self._ambient_volume
                    )
                    self.backend.set_muted(self._is_muted)
                    self.backend.initialize()
                success = False

            with self._lock:
                scheduler = self._whisper_scheduler
                whispers_active = (
                    success
                    and self.settings.audio_scheduled_whispers_enabled
                    and not self._is_muted
                )

            if scheduler is not None:
                if whispers_active:
                    scheduler.start()
                else:
                    scheduler.cancel()

            if persist:
                self._persist_current_preferences()
            return success

    def disable(self, persist: bool = True) -> None:
        """Disable audio subsystem, stop all playback and ambient loops, and persist preference."""
        with self._init_lock:
            old_backend = None
            with self._lock:
                self.settings.audio_enabled = False
                old_backend = self.backend
                self.backend = NullAudioBackend(
                    volume=self._volume, ambient_volume=self._ambient_volume
                )
                self.backend.set_muted(self._is_muted)
                self.backend.initialize()
                scheduler = self._whisper_scheduler

            if scheduler is not None:
                scheduler.cancel()

            if old_backend is not None:
                with contextlib.suppress(Exception):
                    old_backend.stop_all()
                    old_backend.shutdown()

            if persist:
                self._persist_current_preferences()
            logger.info("Audio subsystem disabled.")

    def _persist_current_preferences(self) -> None:
        """Save current audio settings to persistent storage."""
        prefs = AudioPreferences(
            enabled=self.settings.audio_enabled,
            volume=self._volume,
            ambient_volume=self._ambient_volume,
            muted=self._is_muted,
            haunted_keystrokes_enabled=self.settings.audio_haunted_keystrokes_enabled,
            scheduled_whispers_enabled=self.settings.audio_scheduled_whispers_enabled,
            dynamic_horror_enabled=self.settings.audio_dynamic_horror_enabled,
        )
        save_audio_preferences(prefs, get_audio_preferences_path(self.settings))

    def get_status(self) -> AudioStatus:
        """Return operational telemetry and diagnostic metrics for the audio subsystem."""
        with self._lock:
            backend_state = self.backend.get_status()
            asset_dir_path = self.settings.audio_asset_dir
            asset_dir_exists = asset_dir_path.is_dir() if asset_dir_path is not None else False

            return AudioStatus(
                enabled=self.settings.audio_enabled,
                ambient_enabled=self.settings.audio_ambient_enabled,
                volume=self._volume,
                ambient_volume=self._ambient_volume,
                backend_type=str(backend_state.get("backend", "null")),
                backend_available=self.backend.is_available(),
                asset_dir=str(asset_dir_path) if asset_dir_path else "",
                asset_dir_exists=asset_dir_exists,
                known_events_count=self.catalog.count(),
                is_muted=self._is_muted,
                ambient_playing=bool(backend_state.get("ambient_playing", False)),
                active_voices_count=int(backend_state.get("active_voices", 0)),
                haunted_keystrokes_enabled=self.settings.audio_haunted_keystrokes_enabled,
                scheduled_whispers_enabled=self.settings.audio_scheduled_whispers_enabled,
                dynamic_horror_enabled=self.settings.audio_dynamic_horror_enabled,
                horror_intensity=(
                    self._director.compute_intensity().value
                    if self._director is not None
                    else "dormant"
                ),
                atmospheric_events_in_window=(
                    self._director.get_telemetry().get("atmospheric_events_in_window", 0)
                    if self._director is not None
                    else 0
                ),
                last_suppression_reason=(
                    self._director.last_suppression_reason if self._director is not None else None
                ),
            )

    def resolve_asset_path(self, event_id: AudioEventId | str) -> Path | None:
        """Locate the concrete on-disk asset file for a registered sound effect."""
        sound: SoundEffect | None = self.catalog.get_sound(event_id)
        if sound is None:
            return None

        if self.settings.audio_asset_dir is None:
            return None

        asset_path = (self.settings.audio_asset_dir / sound.relative_path).resolve()
        if asset_path.is_file():
            return asset_path
        return None

    def play(
        self,
        event_id: AudioEventId | str,
        volume_scale: float = 1.0,
        loop: bool = False,
    ) -> bool:
        """Dispatch a sound effect request."""
        with self._lock:
            if not self.settings.audio_enabled or self._is_muted or self._is_shutdown:
                return False

            if not (0.0 <= volume_scale <= 1.0):
                raise InvalidVolumeError(
                    f"Invalid volume_scale {volume_scale}. Must be between 0.0 and 1.0."
                )

            asset_path = self.resolve_asset_path(event_id)
            if asset_path is None:
                logger.debug("Asset file missing or unresolvable for audio event: %s", event_id)
                return False

            effective_volume = max(0.0, min(1.0, volume_scale))
            return self.backend.play(asset_path, volume=effective_volume, loop=loop)

    def play_ambient(
        self,
        event_id: AudioEventId | str,
        volume_scale: float = 1.0,
    ) -> bool:
        """Start streaming a continuous ambient horror loop."""
        with self._lock:
            if not self.settings.audio_enabled or self._is_muted or self._is_shutdown:
                return False

            if not (0.0 <= volume_scale <= 1.0):
                raise InvalidVolumeError(
                    f"Invalid volume_scale {volume_scale}. Must be between 0.0 and 1.0."
                )

            asset_path = self.resolve_asset_path(event_id)
            if asset_path is None:
                logger.debug("Asset file missing or unresolvable for ambient event: %s", event_id)
                return False

            return self.backend.play_ambient(asset_path, volume=volume_scale)

    def stop_ambient(self) -> None:
        """Stop the currently active ambient background loop."""
        with self._lock:
            self.backend.stop_ambient()

    def stop_event(self, event_id: AudioEventId | str) -> None:
        """Stop all voices playing a specific event."""
        with self._lock:
            sound = self.catalog.get_sound(event_id)
            if sound is not None and self.settings.audio_asset_dir is not None:
                target_path = (self.settings.audio_asset_dir / sound.relative_path).resolve()
                self.backend.stop_event(target_path)

    def stop_all(self) -> None:
        """Stop all currently playing sound effects and ambient tracks."""
        with self._lock:
            self.backend.stop_all()

    def set_volume(self, volume: float, persist: bool = True) -> None:
        """Adjust master audio volume and optionally persist preferences."""
        if not (0.0 <= volume <= 1.0):
            raise InvalidVolumeError(f"Invalid volume {volume}. Must be between 0.0 and 1.0.")
        with self._lock:
            self._volume = volume
            self.settings.audio_volume = volume
            self.backend.set_volume(volume)
            if persist:
                self._persist_current_preferences()

    def set_ambient_volume(self, volume: float, persist: bool = True) -> None:
        """Adjust background ambient audio volume and optionally persist preferences."""
        if not (0.0 <= volume <= 1.0):
            raise InvalidVolumeError(
                f"Invalid ambient volume {volume}. Must be between 0.0 and 1.0."
            )
        with self._lock:
            self._ambient_volume = volume
            self.settings.audio_ambient_volume = volume
            self.backend.set_ambient_volume(volume)
            if persist:
                self._persist_current_preferences()

    def mute(self, persist: bool = True) -> None:
        """Silence all audio output without resetting configured volume values."""
        with self._lock:
            self._is_muted = True
            self.settings.audio_muted = True
            self.backend.set_muted(True)
            self.backend.stop_all()
            scheduler = self._whisper_scheduler
            if persist:
                self._persist_current_preferences()
        if scheduler is not None:
            scheduler.cancel()

    def unmute(self, persist: bool = True) -> None:
        """Unmute audio output and restore previous configured volume."""
        with self._lock:
            self._is_muted = False
            self.settings.audio_muted = False
            self.backend.set_muted(False)
            scheduler = self._whisper_scheduler
            whispers_active = (
                self.settings.audio_enabled and self.settings.audio_scheduled_whispers_enabled
            )
            if persist:
                self._persist_current_preferences()
        if scheduler is not None and whispers_active:
            scheduler.start()

    @property
    def is_muted(self) -> bool:
        """Return whether audio playback is currently muted."""
        with self._lock:
            return self._is_muted

    @property
    def master_volume(self) -> float:
        """Return current master output volume level."""
        with self._lock:
            return self._volume

    @property
    def haunted_keystrokes_enabled(self) -> bool:
        """Return whether haunted keystrokes are enabled."""
        with self._lock:
            return self.settings.audio_haunted_keystrokes_enabled

    def set_haunted_keystrokes(self, enabled: bool, persist: bool = True) -> None:
        """Configure haunted keystroke effects and optionally persist preferences."""
        with self._lock:
            self.settings.audio_haunted_keystrokes_enabled = bool(enabled)
            if persist:
                self._persist_current_preferences()

    @property
    def scheduled_whispers_enabled(self) -> bool:
        """Return whether scheduled whispers are enabled."""
        with self._lock:
            return self.settings.audio_scheduled_whispers_enabled

    def set_scheduled_whispers(self, enabled: bool, persist: bool = True) -> None:
        """Configure scheduled whisper effects and optionally persist preferences."""
        with self._lock:
            self.settings.audio_scheduled_whispers_enabled = bool(enabled)
            scheduler = self._whisper_scheduler
            whispers_active = bool(enabled) and self.settings.audio_enabled and not self._is_muted
            if persist:
                self._persist_current_preferences()

        if scheduler is not None:
            if whispers_active:
                scheduler.start()
            else:
                scheduler.cancel()

    @property
    def whisper_scheduler(self) -> Any | None:
        """Return attached WhisperScheduler instance."""
        with self._lock:
            return self._whisper_scheduler

    def set_whisper_scheduler(self, scheduler: Any) -> None:
        """Attach a WhisperScheduler instance."""
        with self._lock:
            self._whisper_scheduler = scheduler

    @property
    def dynamic_horror_enabled(self) -> bool:
        """Return whether dynamic horror orchestration is enabled."""
        with self._lock:
            return self.settings.audio_dynamic_horror_enabled

    def set_dynamic_horror(self, enabled: bool, persist: bool = True) -> None:
        """Configure dynamic horror orchestration and optionally persist preferences."""
        with self._lock:
            self.settings.audio_dynamic_horror_enabled = bool(enabled)
            if self._director is not None:
                self._director.set_enabled(bool(enabled))
            if persist:
                self._persist_current_preferences()

    @property
    def director(self) -> Any | None:
        """Return attached HorrorAudioDirector instance."""
        with self._lock:
            return self._director

    def set_director(self, director: Any) -> None:
        """Attach a HorrorAudioDirector instance."""
        with self._lock:
            self._director = director

    def play_test_sound(self) -> bool:
        """Play a safe, short sound effect to verify output."""
        with self._lock:
            if not self.settings.audio_enabled or self._is_muted or self._is_shutdown:
                return False

            asset_path = self.resolve_asset_path(AudioEventId.NOTIFICATION_PING)
            if asset_path is None:
                asset_path = self.resolve_asset_path(AudioEventId.STARTUP)
            if asset_path is None:
                return False

            return self.backend.play(asset_path, volume=1.0)
