"""Central audio subsystem lifecycle and event management for GhostTrace."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from ghosttrace.audio.backend import AudioBackend, NullAudioBackend
from ghosttrace.audio.catalog import AudioCatalog
from ghosttrace.audio.exceptions import (
    AudioInitializationError,
    InvalidVolumeError,
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
        self._is_shutdown = False
        self._is_muted = False
        self._volume: float = self.settings.audio_volume
        self._ambient_volume: float = self.settings.audio_ambient_volume

        # Select and initialize backend
        self.backend: AudioBackend = self._initialize_backend(backend)

    def _initialize_backend(self, custom_backend: AudioBackend | None) -> AudioBackend:
        """Initialize the audio backend safely.

        If audio is disabled, or if backend initialization fails, cleanly falls back
        to NullAudioBackend so GhostTrace startup is never blocked or crashed.
        """
        if not self.settings.audio_enabled:
            logger.debug("Audio subsystem is disabled in configuration. Using NullAudioBackend.")
            null_backend = NullAudioBackend(volume=self._volume)
            null_backend.initialize()
            return null_backend

        # Audio is explicitly enabled in settings
        target_backend = (
            custom_backend if custom_backend is not None else NullAudioBackend(volume=self._volume)
        )

        try:
            success = target_backend.initialize()
            if not success:
                logger.warning(
                    "Configured audio backend failed initialization. "
                    "Falling back to safe NullAudioBackend."
                )
                fallback = NullAudioBackend(volume=self._volume)
                fallback.initialize()
                return fallback
            return target_backend
        except Exception as exc:
            logger.warning(
                "Exception initializing audio backend (%s). Falling back to NullAudioBackend: %s",
                type(exc).__name__,
                exc,
            )
            fallback = NullAudioBackend(volume=self._volume)
            fallback.initialize()
            return fallback

    def initialize(self) -> bool:
        """Explicitly re-initialize backend resources if previously shutdown."""
        with self._lock:
            if not self._is_shutdown and self.backend.is_available():
                return True
            self._is_shutdown = False
            try:
                return self.backend.initialize()
            except Exception as exc:
                msg = f"Failed to initialize audio backend: {exc}"
                raise AudioInitializationError(msg) from exc

    def shutdown(self) -> None:
        """Safely and idempotently release all audio handles and background tasks."""
        with self._lock:
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
                active_voices_count=int(backend_state.get("active_voices", 0)),
            )

    def resolve_asset_path(self, event_id: AudioEventId | str) -> Path | None:
        """Locate the concrete on-disk asset file for a registered sound effect.

        Args:
            event_id: Canonical event identifier.

        Returns:
            Resolved absolute Path if file exists on disk, None otherwise.
        """
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
        """Dispatch a sound effect request.

        In Step 01 Foundation, playback is not implemented and no sound hardware
        is engaged. This method returns False safely.

        Args:
            event_id: Canonical event identifier.
            volume_scale: Relative volume scaling (0.0 to 1.0).
            loop: Whether the sound effect loops.

        Returns:
            True if playback was initiated, False otherwise.
        """
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

            effective_volume = max(0.0, min(1.0, self._volume * volume_scale))
            return self.backend.play(asset_path, volume=effective_volume, loop=loop)

    def stop_all(self) -> None:
        """Stop all currently playing sound effects and ambient tracks."""
        with self._lock:
            self.backend.stop_all()

    def set_volume(self, volume: float) -> None:
        """Adjust master audio volume.

        Args:
            volume: Master volume between 0.0 and 1.0.

        Raises:
            InvalidVolumeError: If volume is outside [0.0, 1.0].
        """
        if not (0.0 <= volume <= 1.0):
            raise InvalidVolumeError(f"Invalid volume {volume}. Must be between 0.0 and 1.0.")
        with self._lock:
            self._volume = volume
            self.backend.set_volume(volume)

    def set_ambient_volume(self, volume: float) -> None:
        """Adjust background ambient audio volume.

        Args:
            volume: Ambient volume between 0.0 and 1.0.

        Raises:
            InvalidVolumeError: If volume is outside [0.0, 1.0].
        """
        if not (0.0 <= volume <= 1.0):
            raise InvalidVolumeError(
                f"Invalid ambient volume {volume}. Must be between 0.0 and 1.0."
            )
        with self._lock:
            self._ambient_volume = volume

    def mute(self) -> None:
        """Silence all audio output without changing volume configurations."""
        with self._lock:
            self._is_muted = True
            self.backend.stop_all()

    def unmute(self) -> None:
        """Unmute audio output."""
        with self._lock:
            self._is_muted = False
