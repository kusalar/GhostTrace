"""Focused tests for GhostTrace audio subsystem foundation and architecture."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from ghosttrace.audio.backend import AudioBackend, NullAudioBackend
from ghosttrace.audio.catalog import AudioCatalog
from ghosttrace.audio.exceptions import InvalidVolumeError
from ghosttrace.audio.manager import AudioManager
from ghosttrace.audio.schemas import AudioCategory, AudioEventId, AudioStatus
from ghosttrace.config.settings import Settings
from ghosttrace.terminal.app import GhostTraceApp
from pydantic import ValidationError


class TestAudioConfiguration:
    """Test suite for audio configuration and validation."""

    def test_default_audio_configuration(self) -> None:
        """Audio must be disabled by default with sensible default volumes."""
        settings = Settings()
        assert settings.audio_enabled is False
        assert settings.audio_volume == 0.5
        assert settings.audio_ambient_enabled is False
        assert settings.audio_ambient_volume == 0.2
        assert settings.audio_asset_dir is not None
        assert settings.audio_asset_dir.name == "audio"

    def test_explicitly_enabled_configuration(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Audio configuration can be enabled and customized via parameters or env."""
        settings = Settings(
            audio_enabled=True,
            audio_volume=0.8,
            audio_ambient_enabled=True,
            audio_ambient_volume=0.35,
        )
        assert settings.audio_enabled is True
        assert settings.audio_volume == 0.8
        assert settings.audio_ambient_enabled is True
        assert settings.audio_ambient_volume == 0.35

        monkeypatch.setenv("GHOSTTRACE_AUDIO_ENABLED", "true")
        monkeypatch.setenv("GHOSTTRACE_AUDIO_VOLUME", "0.9")
        env_settings = Settings()
        assert env_settings.audio_enabled is True
        assert env_settings.audio_volume == 0.9

    @pytest.mark.parametrize("volume", [0.0, 0.5, 1.0])
    def test_volume_boundary_valid(self, volume: float) -> None:
        """Volume boundaries 0.0 and 1.0 are valid."""
        settings = Settings(audio_volume=volume, audio_ambient_volume=volume)
        assert settings.audio_volume == volume
        assert settings.audio_ambient_volume == volume

    @pytest.mark.parametrize("invalid_volume", [-0.1, -1.0, 1.01, 2.5])
    def test_invalid_volume_rejected(self, invalid_volume: float) -> None:
        """Volume values outside [0.0, 1.0] must be rejected with ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(audio_volume=invalid_volume)
        assert "audio_volume" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            Settings(audio_ambient_volume=invalid_volume)
        assert "audio_ambient_volume" in str(exc_info.value)

    def test_custom_asset_dir_resolution(self, tmp_path: Path) -> None:
        """Asset directory is resolved to absolute Path."""
        custom_dir = tmp_path / "custom_sounds"
        settings = Settings(audio_asset_dir=custom_dir)
        assert settings.audio_asset_dir == custom_dir.resolve()

    def test_missing_asset_dir_does_not_crash_startup(self, tmp_path: Path) -> None:
        """A nonexistent asset directory must not crash settings instantiation."""
        nonexistent = tmp_path / "does_not_exist"
        assert not nonexistent.exists()
        settings = Settings(audio_asset_dir=nonexistent)
        assert settings.audio_asset_dir == nonexistent.resolve()


class TestNullAudioBackend:
    """Test suite for NullAudioBackend safe no-op behavior."""

    def test_null_backend_lifecycle(self) -> None:
        """Null backend initializes and shuts down cleanly."""
        backend = NullAudioBackend(volume=0.6)
        assert not backend.is_available()

        assert backend.initialize() is True
        assert backend.is_available()

        # Idempotent shutdown
        backend.shutdown()
        assert not backend.is_available()
        backend.shutdown()  # Second call must be safe
        assert not backend.is_available()

    def test_null_backend_play_is_noop(self, tmp_path: Path) -> None:
        """Null backend play returns False and performs no hardware access."""
        backend = NullAudioBackend()
        backend.initialize()
        dummy_file = tmp_path / "sound.wav"
        result = backend.play(dummy_file, volume=0.5, loop=False)
        assert result is False

    def test_null_backend_volume_and_status(self) -> None:
        """Null backend tracks volume and returns expected status."""
        backend = NullAudioBackend(volume=0.4)
        backend.initialize()
        backend.set_volume(0.85)

        status = backend.get_status()
        assert status["backend"] == "null"
        assert status["volume"] == 0.85
        assert status["initialized"] is True
        assert status["shutdown"] is False


class TestAudioCatalog:
    """Test suite for the sound effects catalog."""

    def test_catalog_entries_populated(self) -> None:
        """Default catalog contains all required core sound event definitions."""
        catalog = AudioCatalog()
        assert catalog.count() >= 15

        startup_sound = catalog.get_sound(AudioEventId.STARTUP)
        assert startup_sound is not None
        assert startup_sound.category == AudioCategory.SYSTEM
        assert "startup.wav" in startup_sound.relative_path

    def test_catalog_category_filtering(self) -> None:
        """Catalog filters sounds by category accurately."""
        catalog = AudioCatalog()
        ambient_sounds = catalog.list_by_category(AudioCategory.AMBIENT)
        assert len(ambient_sounds) >= 2
        for sound in ambient_sounds:
            assert sound.category == AudioCategory.AMBIENT
            assert sound.loop is True

        whisper_sounds = catalog.list_by_category(AudioCategory.WHISPER)
        assert len(whisper_sounds) >= 2
        for sound in whisper_sounds:
            assert sound.category == AudioCategory.WHISPER

    def test_unknown_event_lookup(self) -> None:
        """Looking up unknown event returns None."""
        catalog = AudioCatalog()
        assert catalog.get_sound("unknown_event_xyz") is None


class TestAudioManager:
    """Test suite for high-level AudioManager."""

    def test_manager_default_disabled(self) -> None:
        """When audio is disabled, AudioManager uses NullAudioBackend and safe state."""
        settings = Settings(audio_enabled=False)
        manager = AudioManager(settings)
        status: AudioStatus = manager.get_status()

        assert status.enabled is False
        assert status.backend_type == "null"
        assert status.backend_available is True
        assert status.is_muted is False
        assert status.known_events_count >= 15

        # Play returns False when disabled
        assert manager.play(AudioEventId.STARTUP) is False
        manager.shutdown()

    def test_manager_explicitly_enabled_with_mock_backend(self) -> None:
        """When enabled with a mock backend, initialization and shutdown work cleanly."""
        settings = Settings(audio_enabled=True)
        mock_backend = MagicMock(spec=AudioBackend)
        mock_backend.initialize.return_value = True
        mock_backend.is_available.return_value = True
        mock_backend.get_status.return_value = {"backend": "mock_test", "active_voices": 0}

        manager = AudioManager(settings, backend=mock_backend)
        status = manager.get_status()
        assert status.enabled is True
        assert status.backend_type == "mock_test"
        mock_backend.initialize.assert_called_once()

        manager.shutdown()
        mock_backend.shutdown.assert_called_once()
        mock_backend.stop_all.assert_called_once()

    def test_manager_backend_init_failure_fallback(self) -> None:
        """If custom backend fails initialization, AudioManager falls back to NullAudioBackend."""
        settings = Settings(audio_enabled=True)
        failing_backend = MagicMock(spec=AudioBackend)
        failing_backend.initialize.side_effect = RuntimeError("Audio device busy")

        manager = AudioManager(settings, backend=failing_backend)
        status = manager.get_status()
        assert status.backend_type == "null"
        assert status.backend_available is True

        # Must not raise error
        manager.shutdown()

    def test_manager_backend_init_returns_false_fallback(self) -> None:
        """If backend initialize returns False, fallback to NullAudioBackend occurs."""
        settings = Settings(audio_enabled=True)
        failing_backend = MagicMock(spec=AudioBackend)
        failing_backend.initialize.return_value = False

        manager = AudioManager(settings, backend=failing_backend)
        status = manager.get_status()
        assert status.backend_type == "null"
        manager.shutdown()

    def test_repeated_shutdown_is_idempotent(self) -> None:
        """Calling shutdown multiple times is safe and causes no errors."""
        manager = AudioManager(Settings(audio_enabled=False))
        manager.shutdown()
        manager.shutdown()
        manager.shutdown()
        status = manager.get_status()
        assert status.backend_available is False

    def test_volume_controls_and_validation(self) -> None:
        """Manager allows volume adjustments and rejects invalid volumes."""
        manager = AudioManager(Settings(audio_enabled=False, audio_volume=0.5))
        manager.set_volume(0.75)
        assert manager.get_status().volume == 0.75

        manager.set_ambient_volume(0.3)
        assert manager.get_status().ambient_volume == 0.3

        with pytest.raises(InvalidVolumeError):
            manager.set_volume(-0.1)

        with pytest.raises(InvalidVolumeError):
            manager.set_volume(1.1)

        with pytest.raises(InvalidVolumeError):
            manager.set_ambient_volume(-0.5)

        with pytest.raises(InvalidVolumeError):
            manager.set_ambient_volume(1.5)

        manager.shutdown()

    def test_mute_unmute(self) -> None:
        """Muting silences playback and reflects in status."""
        manager = AudioManager(Settings(audio_enabled=True))
        assert not manager.get_status().is_muted

        manager.mute()
        assert manager.get_status().is_muted
        assert manager.play(AudioEventId.STARTUP) is False

        manager.unmute()
        assert not manager.get_status().is_muted
        manager.shutdown()

    def test_resolve_asset_path(self, tmp_path: Path) -> None:
        """Asset path resolves only when concrete file exists on disk."""
        assets_dir = tmp_path / "audio"
        sfx_dir = assets_dir / "sfx"
        sfx_dir.mkdir(parents=True)
        startup_file = sfx_dir / "startup.wav"
        startup_file.write_bytes(b"RIFF dummy wav header")

        settings = Settings(audio_asset_dir=assets_dir)
        manager = AudioManager(settings)

        # Existing asset
        resolved = manager.resolve_asset_path(AudioEventId.STARTUP)
        assert resolved is not None
        assert resolved.exists()
        assert resolved.name == "startup.wav"

        # Missing asset
        missing = manager.resolve_asset_path(AudioEventId.SHUTDOWN)
        assert missing is None

        # Unknown asset
        unknown = manager.resolve_asset_path("unknown_random_id")
        assert unknown is None

        manager.shutdown()


class TestApplicationAudioIntegration:
    """Verify GhostTraceApp integration with disabled audio subsystem."""

    @pytest.mark.asyncio
    async def test_app_starts_and_quits_with_audio_disabled(self) -> None:
        """GhostTraceApp starts cleanly with audio disabled, preserving v1.0.0 behavior."""
        settings = Settings(audio_enabled=False)
        app = GhostTraceApp(settings=settings)

        assert hasattr(app, "audio_manager")
        assert app.audio_manager.get_status().enabled is False

        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            assert app.audio_manager.get_status().enabled is False
            app.action_quit_app()
            await pilot.pause()

        # Manager should be shut down upon quit
        assert app.audio_manager.get_status().backend_available is False
