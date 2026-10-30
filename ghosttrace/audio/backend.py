"""Backend abstraction and no-op implementation for GhostTrace audio playback."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

logger = logging.getLogger("ghosttrace.audio.backend")


class AudioBackend(ABC):
    """Abstract interface for audio playback engines."""

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the audio playback subsystem and underlying drivers.

        Returns:
            True if initialization succeeded, False otherwise.
        """

    @abstractmethod
    def shutdown(self) -> None:
        """Release all audio resources and close hardware handles cleanly and idempotently."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the backend is initialized and capable of audio playback."""

    @abstractmethod
    def play(self, sound_path: Path, volume: float = 1.0, loop: bool = False) -> bool:
        """Dispatch a sound effect for playback.

        Args:
            sound_path: Path to the target audio asset on disk.
            volume: Relative volume multiplier (0.0 to 1.0).
            loop: Whether the sound effect should repeat indefinitely.

        Returns:
            True if the playback was initiated, False otherwise.
        """

    @abstractmethod
    def stop_event(self, sound_path: Path) -> None:
        """Stop playback of a specific audio asset if currently playing."""

    @abstractmethod
    def stop_all(self) -> None:
        """Immediately stop all currently playing sound effects and ambient tracks."""

    @abstractmethod
    def set_volume(self, volume: float) -> None:
        """Update the master output volume level.

        Args:
            volume: Master volume level between 0.0 and 1.0.
        """

    @abstractmethod
    def get_status(self) -> dict[str, Any]:
        """Return operational telemetry and diagnostic metrics for the backend."""


class NullAudioBackend(AudioBackend):
    """Safe, silent no-op backend used when audio is disabled or hardware is unavailable.

    Guarantees that no audio hardware, native drivers, or background threads are initialized.
    Every operation completes cleanly with zero side-effects.
    """

    def __init__(self, volume: float = 0.5) -> None:
        self._volume = max(0.0, min(1.0, volume))
        self._is_initialized = False
        self._is_shutdown = False

    def initialize(self) -> bool:
        """Simulate successful no-op backend initialization."""
        self._is_initialized = True
        self._is_shutdown = False
        logger.debug("NullAudioBackend initialized in safe no-op mode.")
        return True

    def shutdown(self) -> None:
        """Idempotently close the no-op backend."""
        self._is_initialized = False
        self._is_shutdown = True
        logger.debug("NullAudioBackend shutdown cleanly.")

    def is_available(self) -> bool:
        """Null backend is available in the sense that it safely absorbs calls."""
        return self._is_initialized and not self._is_shutdown

    def play(self, sound_path: Path, volume: float = 1.0, loop: bool = False) -> bool:
        """Absorb playback request silently without error."""
        logger.debug("NullAudioBackend ignoring play request for: %s", sound_path)
        return False

    def stop_event(self, sound_path: Path) -> None:
        """No-op stop for a specific sound effect."""

    def stop_all(self) -> None:
        """No-op stop for all sound effects."""

    def set_volume(self, volume: float) -> None:
        """Record volume adjustment safely."""
        self._volume = max(0.0, min(1.0, volume))

    def get_status(self) -> dict[str, Any]:
        """Return diagnostic state of the no-op backend."""
        return {
            "backend": "null",
            "initialized": self._is_initialized,
            "shutdown": self._is_shutdown,
            "volume": self._volume,
            "active_voices": 0,
        }
