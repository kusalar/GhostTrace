"""Automated regression tests verifying the audio subsystem repair and diagnostics."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from ghosttrace.audio.backend import MiniAudioBackend, NullAudioBackend
from ghosttrace.audio.manager import AudioManager
from ghosttrace.audio.schemas import AudioEventId
from ghosttrace.audio.whisper_scheduler import WhisperScheduler
from ghosttrace.config.settings import Settings


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    """Fixture providing clean settings with test asset directory and isolated app_data_dir."""
    asset_dir = tmp_path / "assets" / "audio"
    asset_dir.mkdir(parents=True, exist_ok=True)
    return Settings(
        app_data_dir=tmp_path / "app_data",
        audio_enabled=False,
        audio_asset_dir=asset_dir,
    )


class TestAudioSubsystemRepair:
    """Tests confirming the repair of the audio subsystem."""

    def test_null_backend_reported_as_unavailable_by_manager(self, test_settings: Settings) -> None:
        """AudioManager reports hardware is unavailable when NullAudioBackend is mounted."""
        mgr = AudioManager(settings=test_settings)
        try:
            assert isinstance(mgr.backend, NullAudioBackend)
            assert mgr.is_available() is False
            status = mgr.get_status()
            assert status.backend_type == "null"
            # In v1.1.0 contract, NullAudioBackend reports backend_available True as safe absorber
            assert status.backend_available is True
        finally:
            mgr.shutdown()

    def test_enable_transitions_from_null_to_miniaudio(self, test_settings: Settings) -> None:
        """Calling enable() transitions NullAudioBackend to MiniAudioBackend."""
        mgr = AudioManager(settings=test_settings)
        try:
            assert isinstance(mgr.backend, NullAudioBackend)
            success = mgr.enable(persist=False)
            assert success is True
            assert isinstance(mgr.backend, MiniAudioBackend)
            assert mgr.is_available() is True
            status = mgr.get_status()
            assert status.backend_available is True
            assert status.backend_type == "miniaudio"
        finally:
            mgr.shutdown()

    def test_volume_scaling_avoids_double_attenuation(self, test_settings: Settings) -> None:
        """AudioManager passes linear volume_scale to backend without squaring master volume."""
        mock_backend = MagicMock(spec=MiniAudioBackend)
        mock_backend.is_available.return_value = True
        mock_backend.play.return_value = True

        test_settings.audio_enabled = True
        test_settings.audio_volume = 0.75
        mgr = AudioManager(settings=test_settings, backend=mock_backend)

        # Create asset at catalog relative path: sfx/notification_ping.wav
        sound = mgr.catalog.get_sound(AudioEventId.NOTIFICATION_PING)
        assert sound is not None
        dummy_file = test_settings.audio_asset_dir / sound.relative_path
        dummy_file.parent.mkdir(parents=True, exist_ok=True)
        dummy_file.touch()

        # Play with volume scale 0.20
        res = mgr.play(AudioEventId.NOTIFICATION_PING, volume_scale=0.20)
        assert res is True

        # Verify backend.play was called with volume=0.20 (NOT 0.75 * 0.20 = 0.15)
        mock_backend.play.assert_called_once_with(dummy_file, volume=0.20, loop=False)

        # Verify test sound plays at full volume scale 1.0 (letting backend apply master volume)
        mock_backend.reset_mock()
        test_res = mgr.play_test_sound()
        assert test_res is True
        mock_backend.play.assert_called_once_with(dummy_file, volume=1.0)

    def test_whisper_scheduler_lifecycle_starts_and_cancels(self, test_settings: Settings) -> None:
        """WhisperScheduler dynamically starts and cancels timer when toggled on/off."""
        test_settings.audio_enabled = True
        test_settings.audio_scheduled_whispers_enabled = False
        mgr = AudioManager(settings=test_settings)
        try:
            timers: list[tuple[float, Any]] = []

            def fake_schedule(delay: float, cb: Any) -> Any:
                timer_obj = MagicMock()
                timers.append((delay, timer_obj))
                return timer_obj

            scheduler = WhisperScheduler(
                audio_manager=mgr,
                schedule_timer_func=fake_schedule,
            )
            mgr.set_whisper_scheduler(scheduler)

            # Initially whispers disabled: no timer
            assert scheduler.is_enabled is False
            assert scheduler._active_timer is None

            # Toggle whispers ON -> timer scheduled
            mgr.set_scheduled_whispers(True, persist=False)
            assert scheduler.is_enabled is True
            assert scheduler._active_timer is not None
            assert len(timers) == 1

            # Toggle whispers OFF -> timer cancelled
            active_timer = scheduler._active_timer
            mgr.set_scheduled_whispers(False, persist=False)
            assert scheduler.is_enabled is False
            assert scheduler._active_timer is None
            active_timer.stop.assert_called()

            # Enable whispers again
            mgr.set_scheduled_whispers(True, persist=False)
            assert scheduler.is_enabled is True
            assert scheduler._active_timer is not None

            # Muting audio cancels active whisper timer
            active_timer2 = scheduler._active_timer
            mgr.mute(persist=False)
            assert scheduler.is_enabled is False
            assert scheduler._active_timer is None
            active_timer2.stop.assert_called()

            # Unmuting restores whisper timer
            mgr.unmute(persist=False)
            assert scheduler.is_enabled is True
            assert scheduler._active_timer is not None

            # Disabling audio cancels whisper timer
            active_timer3 = scheduler._active_timer
            mgr.disable(persist=False)
            assert scheduler.is_enabled is False
            assert scheduler._active_timer is None
            active_timer3.stop.assert_called()
        finally:
            mgr.shutdown()

    def test_miniaudio_backend_tracks_frames_delivered(self) -> None:
        """MiniAudioBackend tracks frames_delivered and reports in get_status()."""
        backend = MiniAudioBackend(volume=0.5)
        try:
            status = backend.get_status()
            assert "frames_delivered" in status
            assert status["frames_delivered"] == 0
            assert status["sample_rate"] == 44100
            assert status["channels"] == 2
            assert status["sample_format"] == "s16le"
        finally:
            backend.shutdown()
