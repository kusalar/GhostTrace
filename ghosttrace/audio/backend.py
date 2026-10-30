"""Backend abstraction and concrete playback implementations for GhostTrace audio."""

from __future__ import annotations

import array
import contextlib
import logging
import struct
import threading
import wave
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("ghosttrace.audio.backend")

try:
    import miniaudio

    MINIAUDIO_AVAILABLE = True
except ImportError:
    miniaudio = None  # type: ignore[assignment]
    MINIAUDIO_AVAILABLE = False


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
    def play_ambient(self, sound_path: Path, volume: float = 1.0) -> bool:
        """Start streaming a continuous ambient background loop.

        Args:
            sound_path: Path to the target loopable audio asset.
            volume: Relative volume multiplier (0.0 to 1.0).

        Returns:
            True if ambient playback was started, False otherwise.
        """

    @abstractmethod
    def stop_ambient(self) -> None:
        """Stop the currently active ambient background loop."""

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
    def set_ambient_volume(self, volume: float) -> None:
        """Update the ambient background output volume level.

        Args:
            volume: Ambient volume level between 0.0 and 1.0.
        """

    @abstractmethod
    def set_muted(self, muted: bool) -> None:
        """Mute or unmute audio output without altering configured volume."""

    @abstractmethod
    def get_status(self) -> dict[str, Any]:
        """Return operational telemetry and diagnostic metrics for the backend."""


class NullAudioBackend(AudioBackend):
    """Safe, silent no-op backend used when audio is disabled or hardware is unavailable.

    Guarantees that no audio hardware, native drivers, or background threads are initialized.
    Every operation completes cleanly with zero side-effects.
    """

    def __init__(self, volume: float = 0.5, ambient_volume: float = 0.2) -> None:
        self._volume = max(0.0, min(1.0, volume))
        self._ambient_volume = max(0.0, min(1.0, ambient_volume))
        self._is_muted = False
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

    def play_ambient(self, sound_path: Path, volume: float = 1.0) -> bool:
        """Absorb ambient loop request silently without error."""
        logger.debug("NullAudioBackend ignoring play_ambient request for: %s", sound_path)
        return False

    def stop_ambient(self) -> None:
        """No-op stop for ambient loop."""

    def stop_event(self, sound_path: Path) -> None:
        """No-op stop for a specific sound effect."""

    def stop_all(self) -> None:
        """No-op stop for all sound effects."""

    def set_volume(self, volume: float) -> None:
        """Record volume adjustment safely."""
        self._volume = max(0.0, min(1.0, volume))

    def set_ambient_volume(self, volume: float) -> None:
        """Record ambient volume adjustment safely."""
        self._ambient_volume = max(0.0, min(1.0, volume))

    def set_muted(self, muted: bool) -> None:
        """Record mute toggle safely."""
        self._is_muted = muted

    def get_status(self) -> dict[str, Any]:
        """Return diagnostic state of the no-op backend."""
        return {
            "backend": "null",
            "initialized": self._is_initialized,
            "shutdown": self._is_shutdown,
            "volume": self._volume,
            "ambient_volume": self._ambient_volume,
            "active_voices": 0,
            "ambient_playing": False,
            "muted": self._is_muted,
            "device_name": "None (No-Op)",
        }


@dataclass
class _Voice:
    """Internal representation of an actively playing sound effect or ambient stream."""

    sound_path: Path
    samples: array.array
    volume: float
    cursor: int = 0
    loop: bool = False
    is_ambient: bool = False


class MiniAudioBackend(AudioBackend):
    """Real, lightweight, asynchronous audio playback engine powered by miniaudio.

    Features:
        - Native Windows WASAPI / DirectSound device output.
        - In-memory sample caching for zero-latency repeated triggering.
        - Software polyphonic mixing with up to 8 concurrent voices.
        - Singleton ambient background loop with seamless wraparound.
        - Real-time master, ambient, and per-voice volume scaling.
        - Complete non-blocking asynchronous operation.
    """

    MAX_CONCURRENT_VOICES: int = 8
    BUFFER_SIZE_MSEC: int = 80
    SAMPLE_RATE: int = 44100
    CHANNELS: int = 2

    def __init__(self, volume: float = 0.5, ambient_volume: float = 0.2) -> None:
        self._master_volume = max(0.0, min(1.0, volume))
        self._ambient_volume = max(0.0, min(1.0, ambient_volume))
        self._is_muted = False
        self._is_initialized = False
        self._is_shutdown = False

        self._lock = threading.Lock()
        self._device: Any = None
        self._device_name: str = "Unknown"

        # Asset memory cache: Path -> array.array('h') stereo interleaved
        self._cache: dict[Path, array.array] = {}

        # Concurrency state
        self._voices: list[_Voice] = []
        self._ambient_voice: _Voice | None = None

    def initialize(self) -> bool:
        """Initialize miniaudio playback device with stereo 16-bit 44.1 kHz stream."""
        with self._lock:
            if self._is_initialized and not self._is_shutdown:
                return True

            if not MINIAUDIO_AVAILABLE or miniaudio is None:
                logger.warning("miniaudio library is not available in environment.")
                return False

            try:
                devices = miniaudio.Devices().get_playbacks()
                if not devices:
                    logger.warning("No Windows audio playback devices detected.")
                    return False
                self._device_name = devices[0].get("name", "Default Playback Device")

                self._device = miniaudio.PlaybackDevice(
                    output_format=miniaudio.SampleFormat.SIGNED16,
                    nchannels=self.CHANNELS,
                    sample_rate=self.SAMPLE_RATE,
                    buffersize_msec=self.BUFFER_SIZE_MSEC,
                )

                gen = self._mixer_callback_generator()
                next(gen)
                self._device.start(gen)

                self._is_initialized = True
                self._is_shutdown = False
                logger.info(
                    "MiniAudioBackend initialized on '%s' (WASAPI/DirectSound).",
                    self._device_name,
                )
                return True
            except Exception as exc:
                logger.warning("Failed to initialize miniaudio device: %s", exc)
                self._is_initialized = False
                if self._device is not None:
                    with contextlib.suppress(Exception):
                        self._device.close()
                    self._device = None
                return False

    def shutdown(self) -> None:
        """Safely release audio device and background streaming handles."""
        device_to_close = None
        with self._lock:
            if self._is_shutdown:
                return
            logger.debug("Shutting down MiniAudioBackend.")
            self._is_initialized = False
            self._is_shutdown = True
            self._voices.clear()
            self._ambient_voice = None

            device_to_close = self._device
            self._device = None

        if device_to_close is not None:
            try:
                device_to_close.stop()
                device_to_close.close()
            except Exception as exc:
                logger.debug("Ignored exception during device close: %s", exc)

    def is_available(self) -> bool:
        """Return True if device is initialized and currently running."""
        with self._lock:
            if not self._is_initialized or self._is_shutdown or self._device is None:
                return False
            try:
                return bool(self._device.running)
            except Exception:
                return False

    def _load_asset_samples(self, sound_path: Path) -> array.array | None:
        """Read 16-bit PCM WAV and convert to stereo interleaved array.array('h')."""
        if sound_path in self._cache:
            return self._cache[sound_path]

        if not sound_path.is_file():
            logger.warning("Sound asset does not exist on disk: %s", sound_path)
            return None

        try:
            with wave.open(str(sound_path), "rb") as wf:
                nch = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                raw_bytes = wf.readframes(wf.getnframes())

            if sampwidth != 2:
                logger.warning("Unsupported bit depth for %s: %d bytes", sound_path, sampwidth)
                return None

            fmt = f"<{len(raw_bytes) // 2}h"
            unpacked = struct.unpack(fmt, raw_bytes)

            if nch == 1:
                # Duplicate mono samples into stereo pairs (L, R)
                stereo_list: list[int] = []
                for sample in unpacked:
                    stereo_list.append(sample)
                    stereo_list.append(sample)
                stereo_array = array.array("h", stereo_list)
            else:
                stereo_array = array.array("h", unpacked)

            self._cache[sound_path] = stereo_array
            return stereo_array
        except Exception as exc:
            logger.warning("Error decoding audio asset %s: %s", sound_path, exc)
            return None

    def play(self, sound_path: Path, volume: float = 1.0, loop: bool = False) -> bool:
        """Dispatch a sound effect for polyphonic asynchronous mixing."""
        with self._lock:
            if not self._is_initialized or self._is_shutdown or self._is_muted:
                return False

            samples = self._load_asset_samples(sound_path)
            if samples is None:
                return False

            # Voice management: enforce maximum voice limit
            if len(self._voices) >= self.MAX_CONCURRENT_VOICES:
                # Evict the voice that is closest to completion
                self._voices.pop(0)

            voice = _Voice(
                sound_path=sound_path,
                samples=samples,
                volume=max(0.0, min(1.0, volume)),
                cursor=0,
                loop=loop,
                is_ambient=False,
            )
            self._voices.append(voice)
            return True

    def play_ambient(self, sound_path: Path, volume: float = 1.0) -> bool:
        """Start or replace the looping ambient background voice."""
        with self._lock:
            if not self._is_initialized or self._is_shutdown:
                return False

            samples = self._load_asset_samples(sound_path)
            if samples is None:
                return False

            self._ambient_voice = _Voice(
                sound_path=sound_path,
                samples=samples,
                volume=max(0.0, min(1.0, volume)),
                cursor=0,
                loop=True,
                is_ambient=True,
            )
            return True

    def stop_ambient(self) -> None:
        """Silence and stop the ambient background loop."""
        with self._lock:
            self._ambient_voice = None

    def stop_event(self, sound_path: Path) -> None:
        """Stop all voices matching the target asset path."""
        with self._lock:
            resolved_target = sound_path.resolve()
            self._voices = [v for v in self._voices if v.sound_path.resolve() != resolved_target]
            if self._ambient_voice and self._ambient_voice.sound_path.resolve() == resolved_target:
                self._ambient_voice = None

    def stop_all(self) -> None:
        """Stop all short effects and ambient tracks immediately."""
        with self._lock:
            self._voices.clear()
            self._ambient_voice = None

    def set_volume(self, volume: float) -> None:
        """Update master volume scaling in real-time."""
        with self._lock:
            self._master_volume = max(0.0, min(1.0, volume))

    def set_ambient_volume(self, volume: float) -> None:
        """Update ambient loop volume scaling in real-time."""
        with self._lock:
            self._ambient_volume = max(0.0, min(1.0, volume))

    def set_muted(self, muted: bool) -> None:
        """Update mute state."""
        with self._lock:
            self._is_muted = muted

    def get_status(self) -> dict[str, Any]:
        """Return diagnostic metrics."""
        with self._lock:
            running = False
            if self._device is not None and not self._is_shutdown:
                try:
                    running = bool(self._device.running)
                except Exception:
                    running = False

            return {
                "backend": "miniaudio",
                "initialized": self._is_initialized,
                "shutdown": self._is_shutdown,
                "volume": self._master_volume,
                "ambient_volume": self._ambient_volume,
                "active_voices": len(self._voices),
                "ambient_playing": self._ambient_voice is not None,
                "muted": self._is_muted,
                "device_name": self._device_name,
                "running": running,
            }

    def _mixer_callback_generator(self) -> Any:
        """Generator delivering mixed audio frames to miniaudio PlaybackDevice callback."""
        req_frames = yield b""

        while not self._is_shutdown:
            if not req_frames or req_frames <= 0:
                req_frames = yield b""
                continue

            num_samples = req_frames * self.CHANNELS

            buffer_to_yield = None
            with self._lock:
                if self._is_muted or (not self._voices and self._ambient_voice is None):
                    buffer_to_yield = b"\x00" * (num_samples * 2)
                else:
                    acc = [0.0] * num_samples
                    finished_indices: list[int] = []

                    # 1. Mix short sound effects
                    for idx, v in enumerate(self._voices):
                        smps = v.samples
                        cur = v.cursor
                        vol = v.volume * self._master_volume
                        avail = min(len(smps) - cur, num_samples)

                        for i in range(avail):
                            acc[i] += smps[cur + i] * vol

                        v.cursor += avail
                        if v.cursor >= len(smps):
                            if v.loop:
                                v.cursor = 0
                            else:
                                finished_indices.append(idx)

                    # Remove completed one-shot voices
                    for idx in reversed(finished_indices):
                        self._voices.pop(idx)

                    # 2. Mix ambient loop (if active)
                    if self._ambient_voice is not None:
                        amb = self._ambient_voice
                        smps = amb.samples
                        total_len = len(smps)
                        vol = amb.volume * self._ambient_volume * self._master_volume

                        for i in range(num_samples):
                            acc[i] += smps[amb.cursor] * vol
                            amb.cursor = (amb.cursor + 1) % total_len

                    # Clamp accumulated samples to signed 16-bit range
                    clamped = array.array("h", (max(-32768, min(32767, int(s))) for s in acc))
                    buffer_to_yield = clamped.tobytes()

            req_frames = yield buffer_to_yield
