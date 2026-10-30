"""Comprehensive tests for GhostTrace asynchronous audio playback engine."""

from __future__ import annotations

import array
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from ghosttrace.audio.backend import MiniAudioBackend
from ghosttrace.audio.exceptions import InvalidVolumeError
from ghosttrace.audio.manager import AudioManager
from ghosttrace.audio.schemas import AudioEventId
from ghosttrace.config.settings import Settings


@pytest.fixture
def audio_dir() -> Path:
    return Path("assets/audio").resolve()


@pytest.fixture
def test_settings(audio_dir: Path) -> Settings:
    return Settings(audio_enabled=True, audio_asset_dir=audio_dir, audio_volume=0.8)


class TestMiniAudioBackend:
    """Test suite for concrete MiniAudioBackend."""

    def test_backend_initialization_no_devices(self) -> None:
        """When no devices are present, backend initialize returns False gracefully."""
        backend = MiniAudioBackend()
        with patch("miniaudio.Devices") as mock_dev_cls:
            mock_devs = MagicMock()
            mock_devs.get_playbacks.return_value = []
            mock_dev_cls.return_value = mock_devs

            assert backend.initialize() is False
            assert backend.is_available() is False
            status = backend.get_status()
            assert status["initialized"] is False
            backend.shutdown()

    def test_backend_initialization_exception_handled(self) -> None:
        """When device creation raises MiniaudioError, handled gracefully."""
        backend = MiniAudioBackend()
        with patch("miniaudio.PlaybackDevice", side_effect=RuntimeError("WASAPI Error")):
            assert backend.initialize() is False
            assert backend.is_available() is False
            backend.shutdown()

    def test_backend_mono_and_stereo_asset_loading(self, audio_dir: Path) -> None:
        """Backend accurately loads and converts mono and stereo WAV assets to stereo arrays."""
        backend = MiniAudioBackend()

        # Mono asset
        mono_path = audio_dir / "glitch" / "digital_glitch.wav"
        mono_samples = backend._load_asset_samples(mono_path)
        assert mono_samples is not None
        assert isinstance(mono_samples, array.array)
        # Even number of samples because converted to stereo
        assert len(mono_samples) % 2 == 0

        # Stereo asset
        stereo_path = audio_dir / "sfx" / "startup.wav"
        stereo_samples = backend._load_asset_samples(stereo_path)
        assert stereo_samples is not None
        assert len(stereo_samples) % 2 == 0

        # Cache check
        assert mono_path in backend._cache
        assert stereo_path in backend._cache

    def test_backend_missing_asset_returns_none(self, tmp_path: Path) -> None:
        """Loading nonexistent asset returns None without crashing."""
        backend = MiniAudioBackend()
        nonexistent = tmp_path / "ghost_missing.wav"
        assert backend._load_asset_samples(nonexistent) is None
        assert backend.play(nonexistent) is False
        assert backend.play_ambient(nonexistent) is False

    def test_voice_concurrency_and_eviction_limit(self, audio_dir: Path) -> None:
        """Backend enforces MAX_CONCURRENT_VOICES limit (8) by evicting oldest."""
        backend = MiniAudioBackend()
        backend._is_initialized = True
        sound_path = audio_dir / "sfx" / "notification_ping.wav"

        # Dispatch 10 sound requests
        for _i in range(10):
            res = backend.play(sound_path, volume=0.5)
            assert res is True

        # Must not exceed MAX_CONCURRENT_VOICES (8)
        assert len(backend._voices) == MiniAudioBackend.MAX_CONCURRENT_VOICES
        assert backend.get_status()["active_voices"] == 8

    def test_duplicate_ambient_suppression(self, audio_dir: Path) -> None:
        """Dispatching ambient loops suppresses duplicates and maintains singleton voice."""
        backend = MiniAudioBackend()
        backend._is_initialized = True

        hum_path = audio_dir / "ambient" / "dark_hum.wav"
        wind_path = audio_dir / "ambient" / "cold_wind.wav"

        assert backend.play_ambient(hum_path, volume=0.4) is True
        assert backend._ambient_voice is not None
        assert backend._ambient_voice.sound_path == hum_path

        # Dispatch second ambient sound - must replace, not duplicate
        assert backend.play_ambient(wind_path, volume=0.3) is True
        assert backend._ambient_voice is not None
        assert backend._ambient_voice.sound_path == wind_path
        assert backend.get_status()["ambient_playing"] is True

        backend.stop_ambient()
        assert backend._ambient_voice is None
        assert backend.get_status()["ambient_playing"] is False

    def test_stop_event_and_stop_all(self, audio_dir: Path) -> None:
        """Stopping specific event or all events cancels active voices cleanly."""
        backend = MiniAudioBackend()
        backend._is_initialized = True

        ping_path = audio_dir / "sfx" / "notification_ping.wav"
        alert_path = audio_dir / "sfx" / "notification_alert.wav"
        hum_path = audio_dir / "ambient" / "dark_hum.wav"

        backend.play(ping_path)
        backend.play(ping_path)
        backend.play(alert_path)
        backend.play_ambient(hum_path)

        assert len(backend._voices) == 3
        assert backend._ambient_voice is not None

        # Stop only ping
        backend.stop_event(ping_path)
        assert len(backend._voices) == 1
        assert backend._voices[0].sound_path == alert_path
        assert backend._ambient_voice is not None

        # Stop all
        backend.stop_all()
        assert len(backend._voices) == 0
        assert backend._ambient_voice is None

    def test_volume_and_mute_controls(self) -> None:
        """Volume and mute controls update backend state and mixer scaling."""
        backend = MiniAudioBackend(volume=0.5, ambient_volume=0.2)
        backend.set_volume(0.85)
        backend.set_ambient_volume(0.4)
        backend.set_muted(True)

        status = backend.get_status()
        assert status["volume"] == 0.85
        assert status["ambient_volume"] == 0.4
        assert status["muted"] is True

        backend.set_muted(False)
        assert backend.get_status()["muted"] is False

    def test_mixer_generator_silence_when_idle(self) -> None:
        """When no sounds are playing, mixer generator returns pure silence with zero overhead."""
        backend = MiniAudioBackend()
        gen = backend._mixer_callback_generator()
        next(gen)

        silence_chunk = gen.send(512)
        assert len(silence_chunk) == 512 * 4  # 512 frames * 2 channels * 2 bytes
        assert silence_chunk == b"\x00" * (512 * 4)

    def test_shutdown_idempotent(self) -> None:
        """Shutting down multiple times is safe and closes device handles."""
        backend = MiniAudioBackend()
        backend._is_initialized = True
        backend.shutdown()
        assert backend._is_shutdown is True
        assert backend.is_available() is False

        # Repeated calls must not raise
        backend.shutdown()
        backend.shutdown()


class TestAudioManagerIntegration:
    """Test suite for AudioManager integrating real and fallback backends."""

    def test_disabled_audio_uses_null_backend(self, audio_dir: Path) -> None:
        """Disabled audio uses NullAudioBackend with zero hardware initialization."""
        settings = Settings(audio_enabled=False, audio_asset_dir=audio_dir)
        manager = AudioManager(settings)

        status = manager.get_status()
        assert status.enabled is False
        assert status.backend_type == "null"
        assert status.backend_available is True
        assert status.ambient_playing is False

        # Playback requests return False safely
        assert manager.play(AudioEventId.STARTUP) is False
        assert manager.play_ambient(AudioEventId.AMBIENT_DARK_HUM) is False

        manager.shutdown()

    def test_enabled_audio_attempts_real_backend_with_fallback(self, audio_dir: Path) -> None:
        """Enabled audio attempts MiniAudioBackend, falling back safely if init fails."""
        settings = Settings(audio_enabled=True, audio_asset_dir=audio_dir)

        # Mock failing backend
        failing_backend = MagicMock(spec=MiniAudioBackend)
        failing_backend.initialize.return_value = False

        manager = AudioManager(settings, backend=failing_backend)
        status = manager.get_status()
        # Cleanly falls back to null backend
        assert status.backend_type == "null"
        assert status.backend_available is True
        manager.shutdown()

    def test_manager_play_and_ambient_lifecycle(self, audio_dir: Path) -> None:
        """Manager coordinates play, play_ambient, stop_ambient, and stop_all."""
        settings = Settings(audio_enabled=True, audio_asset_dir=audio_dir)
        mock_backend = MagicMock(spec=MiniAudioBackend)
        mock_backend.initialize.return_value = True
        mock_backend.is_available.return_value = True
        mock_backend.play.return_value = True
        mock_backend.play_ambient.return_value = True
        mock_backend.get_status.return_value = {
            "backend": "miniaudio",
            "active_voices": 1,
            "ambient_playing": True,
        }

        manager = AudioManager(settings, backend=mock_backend)

        # Play sound effect
        assert manager.play(AudioEventId.NOTIFICATION_PING) is True
        mock_backend.play.assert_called_once()

        # Play ambient loop
        assert manager.play_ambient(AudioEventId.AMBIENT_DARK_HUM) is True
        mock_backend.play_ambient.assert_called_once()

        # Stop ambient
        manager.stop_ambient()
        mock_backend.stop_ambient.assert_called_once()

        # Stop all
        manager.stop_all()
        mock_backend.stop_all.assert_called_once()

        manager.shutdown()

    def test_manager_volume_boundaries(self, audio_dir: Path) -> None:
        """Manager validates volume inputs and rejects invalid volumes."""
        manager = AudioManager(Settings(audio_enabled=True, audio_asset_dir=audio_dir))

        manager.set_volume(0.3)
        assert manager.get_status().volume == 0.3

        manager.set_ambient_volume(0.15)
        assert manager.get_status().ambient_volume == 0.15

        with pytest.raises(InvalidVolumeError):
            manager.set_volume(-0.01)

        with pytest.raises(InvalidVolumeError):
            manager.set_ambient_volume(1.05)

        with pytest.raises(InvalidVolumeError):
            manager.play(AudioEventId.STARTUP, volume_scale=1.5)

        with pytest.raises(InvalidVolumeError):
            manager.play_ambient(AudioEventId.AMBIENT_DARK_HUM, volume_scale=-0.1)

        manager.shutdown()


class TestMultithreadedConcurrency:
    """Stress test multithreaded non-blocking audio dispatching."""

    def test_concurrent_dispatches_do_not_crash(self, audio_dir: Path) -> None:
        """Spamming play calls from multiple threads is thread-safe and non-blocking."""
        import concurrent.futures

        backend = MiniAudioBackend()
        backend._is_initialized = True
        sound_path = audio_dir / "sfx" / "notification_ping.wav"

        def trigger_worker(worker_id: int) -> bool:
            return backend.play(sound_path, volume=0.5)

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(trigger_worker, i) for i in range(50)]
            results = [f.result() for f in futures]

        assert all(results)
        # Bounded voice limit must hold
        assert len(backend._voices) <= MiniAudioBackend.MAX_CONCURRENT_VOICES
        backend.shutdown()
