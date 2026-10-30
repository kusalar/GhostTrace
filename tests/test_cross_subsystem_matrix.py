"""Automated Cross-Subsystem Interaction Matrix for GhostTrace v1.2.0 (Step 10).

Covers all 20 required cross-subsystem operational scenarios:
1. Audio disabled + all optional effects disabled.
2. Audio enabled + all optional effects disabled.
3. Haunted Keystrokes enabled alone.
4. Scheduled Whispers enabled alone.
5. Dynamic Horror enabled alone.
6. All three optional features enabled together.
7. Normal mode.
8. Ambient mode.
9. Haunted mode.
10. Focus mode.
11. Master mute.
12. Master volume set to zero.
13. AI inference in progress.
14. Guardian confirmation active.
15. Command execution in progress.
16. Rapid sustained typing.
17. Scheduled whisper coinciding with typing activity.
18. Important notification coinciding with an atmospheric event.
19. Guardian event coinciding with atmospheric cooldown.
20. Application shutdown with timers pending.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from ghosttrace.audio.adapter import AudioEventAdapter
from ghosttrace.audio.horror_director import (
    HorrorAudioDirector,
    HorrorIntensity,
    SuppressionReason,
)
from ghosttrace.audio.manager import AudioManager
from ghosttrace.audio.schemas import AudioEventId
from ghosttrace.audio.typing_effects import TypingEffectsManager
from ghosttrace.audio.whisper_scheduler import WhisperScheduler
from ghosttrace.config.settings import Settings


@pytest.fixture(autouse=True)
def isolate_audio_preferences(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate audio preferences to a temporary path for each test."""
    from ghosttrace.config.settings import get_settings

    get_settings.cache_clear()
    pref_path = tmp_path / "audio_preferences.json"
    monkeypatch.setattr(
        "ghosttrace.audio.preferences.get_audio_preferences_path",
        lambda *args, **kwargs: pref_path,
    )
    monkeypatch.setattr(
        "ghosttrace.audio.manager.get_audio_preferences_path",
        lambda *args, **kwargs: pref_path,
    )
    yield
    get_settings.cache_clear()


class TestCrossSubsystemInteractionMatrix:
    """Automated cross-subsystem interaction test matrix."""

    def test_scenario_01_audio_disabled_all_optional_disabled(self, tmp_path: Path) -> None:
        """Scenario 1: Audio disabled + all optional effects disabled."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=False,
            audio_haunted_keystrokes_enabled=False,
            audio_scheduled_whispers_enabled=False,
            audio_dynamic_horror_enabled=False,
        )
        mgr = AudioManager(settings=settings)
        director = HorrorAudioDirector(audio_manager=mgr, settings=settings)
        adapter = AudioEventAdapter(mgr, horror_director=director)

        # Nothing should play
        assert adapter.is_enabled is False
        assert director.is_enabled is False
        assert adapter.on_startup() is False
        assert adapter.on_glitch("digital") is False
        allowed, reason = director.can_dispatch(AudioEventId.STARTUP)
        assert allowed is False
        assert reason == SuppressionReason.AUDIO_DISABLED.value

    def test_scenario_02_audio_enabled_all_optional_disabled(self, tmp_path: Path) -> None:
        """Scenario 2: Audio enabled + all optional effects disabled."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_haunted_keystrokes_enabled=False,
            audio_scheduled_whispers_enabled=False,
            audio_dynamic_horror_enabled=False,
        )
        mgr = AudioManager(settings=settings)
        mgr.play = MagicMock(return_value=True)
        director = HorrorAudioDirector(audio_manager=mgr, settings=settings)
        adapter = AudioEventAdapter(mgr, horror_director=director)
        typing_mgr = TypingEffectsManager(audio_manager=mgr, audio_adapter=adapter)
        whisper_sched = WhisperScheduler(audio_manager=mgr, audio_adapter=adapter)

        # Standard events play
        assert adapter.on_startup() is True
        assert adapter.on_notification("Alert", important=True) is True

        # Optional features do NOT play
        assert typing_mgr.is_enabled is False
        assert typing_mgr.record_keystroke() is None
        assert whisper_sched.is_enabled is False
        assert whisper_sched.can_play_whisper() is False
        assert director.is_enabled is False

    def test_scenario_03_haunted_keystrokes_enabled_alone(self, tmp_path: Path) -> None:
        """Scenario 3: Haunted Keystrokes enabled alone."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_haunted_keystrokes_enabled=True,
            audio_scheduled_whispers_enabled=False,
            audio_dynamic_horror_enabled=False,
        )
        mgr = AudioManager(settings=settings)
        mgr.play = MagicMock(return_value=True)
        adapter = AudioEventAdapter(mgr)
        typing_mgr = TypingEffectsManager(
            audio_manager=mgr,
            audio_adapter=adapter,
            random_func=lambda: 0.01,
        )
        whisper_sched = WhisperScheduler(audio_manager=mgr, audio_adapter=adapter)

        assert typing_mgr.is_enabled is True
        assert whisper_sched.is_enabled is False
        assert mgr.dynamic_horror_enabled is False

        # Typing triggers after consecutive threshold
        t = 100.0
        for _ in range(4):
            t += 0.1
            typing_mgr.record_keystroke(now=t)
        t += 0.1
        effect = typing_mgr.record_keystroke(now=t)
        assert effect is not None

        # Whispers remain strictly disabled
        assert whisper_sched.can_play_whisper(now=t) is False

    def test_scenario_04_scheduled_whispers_enabled_alone(self, tmp_path: Path) -> None:
        """Scenario 4: Scheduled Whispers enabled alone."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_haunted_keystrokes_enabled=False,
            audio_scheduled_whispers_enabled=True,
            audio_dynamic_horror_enabled=False,
        )
        mgr = AudioManager(settings=settings)
        mgr.play = MagicMock(return_value=True)
        adapter = AudioEventAdapter(mgr)
        whisper_sched = WhisperScheduler(audio_manager=mgr, audio_adapter=adapter)
        typing_mgr = TypingEffectsManager(audio_manager=mgr, audio_adapter=adapter)

        assert whisper_sched.is_enabled is True
        assert typing_mgr.is_enabled is False
        assert mgr.dynamic_horror_enabled is False

        assert whisper_sched.can_play_whisper(now=100.0) is True
        for _ in range(10):
            assert typing_mgr.record_keystroke(now=100.0) is None

    def test_scenario_05_dynamic_horror_enabled_alone(self, tmp_path: Path) -> None:
        """Scenario 5: Dynamic Horror enabled alone."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_haunted_keystrokes_enabled=False,
            audio_scheduled_whispers_enabled=False,
            audio_dynamic_horror_enabled=True,
        )
        mgr = AudioManager(settings=settings)
        mgr.play = MagicMock(return_value=True)
        director = HorrorAudioDirector(
            audio_manager=mgr, settings=settings, experience_mode="normal"
        )
        adapter = AudioEventAdapter(mgr, horror_director=director)
        typing_mgr = TypingEffectsManager(audio_manager=mgr, audio_adapter=adapter)
        whisper_sched = WhisperScheduler(audio_manager=mgr, audio_adapter=adapter)

        assert director.is_enabled is True
        assert typing_mgr.is_enabled is False
        assert whisper_sched.is_enabled is False

        # Glitches go through director rate limiting
        assert adapter.on_glitch("digital") is True

    def test_scenario_06_all_three_optional_features_together(self, tmp_path: Path) -> None:
        """Scenario 6: All three optional features enabled together."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_haunted_keystrokes_enabled=True,
            audio_scheduled_whispers_enabled=True,
            audio_dynamic_horror_enabled=True,
        )
        mgr = AudioManager(settings=settings)
        mgr.play = MagicMock(return_value=True)
        director = HorrorAudioDirector(
            audio_manager=mgr, settings=settings, experience_mode="haunted"
        )
        adapter = AudioEventAdapter(mgr, horror_director=director)
        typing_mgr = TypingEffectsManager(
            audio_manager=mgr,
            audio_adapter=adapter,
            horror_director=director,
            random_func=lambda: 0.01,
        )
        whisper_sched = WhisperScheduler(
            audio_manager=mgr,
            audio_adapter=adapter,
            horror_director=director,
        )

        assert typing_mgr.is_enabled is True
        assert whisper_sched.is_enabled is True
        assert director.is_enabled is True

        # All coordinate cleanly through director
        assert whisper_sched.can_play_whisper(now=100.0) is True

    def test_scenario_07_normal_mode(self, tmp_path: Path) -> None:
        """Scenario 7: Normal mode policies."""
        director = HorrorAudioDirector(experience_mode="normal")
        director.set_enabled(True)
        assert director.experience_mode == "normal"
        assert director.compute_intensity() == HorrorIntensity.DORMANT

        # Ambient stream should be stopped in normal mode
        mock_mgr = MagicMock(spec=AudioManager)
        mock_mgr.settings = Settings(audio_enabled=True)
        mock_mgr.is_muted = False
        mock_mgr._is_muted = False
        adapter = AudioEventAdapter(mock_mgr, horror_director=director)
        adapter.set_experience_mode("ambient")
        adapter.set_experience_mode("normal")
        mock_mgr.stop_ambient.assert_called()

    def test_scenario_08_ambient_mode(self, tmp_path: Path) -> None:
        """Scenario 8: Ambient mode policies."""
        director = HorrorAudioDirector(experience_mode="ambient")
        director.set_enabled(True)
        assert director.compute_intensity() == HorrorIntensity.SUBTLE

        mock_mgr = MagicMock(spec=AudioManager)
        mock_mgr.settings = Settings(audio_enabled=True)
        mock_mgr.is_muted = False
        mock_mgr._is_muted = False
        adapter = AudioEventAdapter(mock_mgr, horror_director=director)
        adapter.set_experience_mode("ambient")
        mock_mgr.play_ambient.assert_called_with(AudioEventId.AMBIENT_DARK_HUM)

    def test_scenario_09_haunted_mode(self, tmp_path: Path) -> None:
        """Scenario 9: Haunted mode policies."""
        director = HorrorAudioDirector(experience_mode="haunted")
        director.set_enabled(True)
        assert director.compute_intensity() == HorrorIntensity.UNSETTLING

        mock_mgr = MagicMock(spec=AudioManager)
        mock_mgr.settings = Settings(audio_enabled=True)
        mock_mgr.is_muted = False
        mock_mgr._is_muted = False
        adapter = AudioEventAdapter(mock_mgr, horror_director=director)
        adapter.set_experience_mode("haunted")
        mock_mgr.play_ambient.assert_called_with(AudioEventId.AMBIENT_COLD_WIND)

    def test_scenario_10_focus_mode(self, tmp_path: Path) -> None:
        """Scenario 10: Focus mode absolute atmospheric suppression."""
        mock_mgr = MagicMock(spec=AudioManager)
        mock_mgr.settings = Settings(audio_enabled=True)
        mock_mgr.is_muted = False
        mock_mgr._is_muted = False
        director = HorrorAudioDirector(
            audio_manager=mock_mgr, settings=mock_mgr.settings, experience_mode="focus"
        )
        director.set_enabled(True)
        adapter = AudioEventAdapter(mock_mgr, horror_director=director)
        adapter.set_experience_mode("focus")

        # Atmospheric silenced
        assert director.can_dispatch(AudioEventId.WHISPER_BREATH)[0] is False
        assert director.can_dispatch(AudioEventId.KEYSTROKE_HAUNT)[0] is False
        assert director.can_dispatch(AudioEventId.GLITCH_DIGITAL)[0] is False

        # Critical Guardian preserved
        assert director.can_dispatch(AudioEventId.GUARDIAN_INTERCEPT)[0] is True
        assert director.can_dispatch(AudioEventId.APP_ERROR)[0] is True

    def test_scenario_11_master_mute(self, tmp_path: Path) -> None:
        """Scenario 11: Master mute produces silence across all categories."""
        settings = Settings(app_data_dir=tmp_path, audio_enabled=True)
        mgr = AudioManager(settings=settings)
        mgr.mute(persist=False)
        director = HorrorAudioDirector(audio_manager=mgr, settings=settings)

        assert director.can_dispatch(AudioEventId.STARTUP)[0] is False
        assert director.can_dispatch(AudioEventId.GUARDIAN_INTERCEPT)[0] is False
        assert director.can_dispatch(AudioEventId.WHISPER_BREATH)[0] is False

    def test_scenario_12_master_volume_zero(self, tmp_path: Path) -> None:
        """Scenario 12: Master volume set to zero suppresses playback."""
        settings = Settings(app_data_dir=tmp_path, audio_enabled=True, audio_volume=0.0)
        mgr = AudioManager(settings=settings)
        director = HorrorAudioDirector(audio_manager=mgr, settings=settings)

        assert director.can_dispatch(AudioEventId.STARTUP)[0] is False
        assert director.can_dispatch(AudioEventId.WHISPER_BREATH)[0] is False

    def test_scenario_13_ai_inference_in_progress(self, tmp_path: Path) -> None:
        """Scenario 13: AI inference active suppresses atmospheric effects."""
        director = HorrorAudioDirector(
            context_check_func=lambda: {"is_generating": True},
            experience_mode="haunted",
        )
        director.set_enabled(True)

        allowed, reason = director.can_dispatch(AudioEventId.WHISPER_BREATH)
        assert allowed is False
        assert reason == SuppressionReason.AI_GENERATING.value

        # Guardian cues remain allowed
        assert director.can_dispatch(AudioEventId.GUARDIAN_INTERCEPT)[0] is True

    def test_scenario_14_guardian_confirmation_active(self, tmp_path: Path) -> None:
        """Scenario 14: Guardian prompt active suppresses atmospheric effects."""
        director = HorrorAudioDirector(
            context_check_func=lambda: {"is_guardian_active": True},
            experience_mode="haunted",
        )
        director.set_enabled(True)

        allowed, reason = director.can_dispatch(AudioEventId.KEYSTROKE_HAUNT)
        assert allowed is False
        assert reason == SuppressionReason.GUARDIAN_ACTIVE.value

        # Guardian event itself is dispatched
        assert director.can_dispatch(AudioEventId.GUARDIAN_INTERCEPT)[0] is True

    def test_scenario_15_command_execution_in_progress(self, tmp_path: Path) -> None:
        """Scenario 15: Command executing suppresses atmospheric effects."""
        director = HorrorAudioDirector(
            context_check_func=lambda: {"is_executing_command": True},
            experience_mode="haunted",
        )
        director.set_enabled(True)

        allowed, reason = director.can_dispatch(AudioEventId.GLITCH_DIGITAL)
        assert allowed is False
        assert reason == SuppressionReason.COMMAND_EXECUTING.value

    def test_scenario_16_rapid_sustained_typing(self, tmp_path: Path) -> None:
        """Scenario 16: Rapid sustained typing elevates intensity deterministically."""
        director = HorrorAudioDirector(experience_mode="haunted")
        director.set_enabled(True)

        clock = 100.0
        for _ in range(10):
            clock += 0.05
            director.record_typing_activity(now=clock)

        assert director.compute_intensity(now=clock) == HorrorIntensity.HAUNTED

    def test_scenario_17_scheduled_whisper_coinciding_with_typing(self, tmp_path: Path) -> None:
        """Scenario 17: Scheduled whisper coinciding with typing activity is rejected."""
        settings = Settings(app_data_dir=tmp_path, audio_enabled=True)
        mgr = AudioManager(settings=settings)
        mgr.play = MagicMock(return_value=True)
        director = HorrorAudioDirector(
            audio_manager=mgr, settings=settings, experience_mode="normal"
        )
        director.set_enabled(True)

        t = 500.0
        # Typing effect triggered at t
        assert director.dispatch_event(AudioEventId.KEYSTROKE_HAUNT, now=t) is True

        # Whisper attempt within collision window (2.5s) is rejected
        allowed, reason = director.can_dispatch(AudioEventId.WHISPER_BREATH, now=t + 1.0)
        assert allowed is False
        assert reason in (
            SuppressionReason.TYPING_COLLISION.value,
            SuppressionReason.COOLDOWN_ACTIVE.value,
        )

    def test_scenario_18_important_notification_coinciding_with_atmospheric(
        self, tmp_path: Path
    ) -> None:
        """Scenario 18: Important notification dispatches despite atmospheric cooldown."""
        director = HorrorAudioDirector(experience_mode="normal")
        director.set_enabled(True)

        clock = 100.0
        director._last_atmospheric_time = clock

        # Atmospheric event rejected by cooldown
        allowed_atmo, _ = director.can_dispatch(AudioEventId.GLITCH_DIGITAL, now=clock + 0.5)
        assert allowed_atmo is False

        # Important notification passes
        allowed_notif, _ = director.can_dispatch(AudioEventId.NOTIFICATION_ALERT, now=clock + 0.5)
        assert allowed_notif is True

    def test_scenario_19_guardian_event_coinciding_with_atmospheric_cooldown(
        self, tmp_path: Path
    ) -> None:
        """Scenario 19: Guardian safety event dispatches despite atmospheric cooldown."""
        director = HorrorAudioDirector(experience_mode="normal")
        director.set_enabled(True)

        clock = 100.0
        director._last_atmospheric_time = clock

        # Atmospheric event rejected
        allowed_atmo, _ = director.can_dispatch(AudioEventId.KEYSTROKE_HAUNT, now=clock + 0.2)
        assert allowed_atmo is False

        # Guardian events dispatch unconditionally
        assert director.can_dispatch(AudioEventId.GUARDIAN_INTERCEPT, now=clock + 0.2)[0] is True
        assert director.can_dispatch(AudioEventId.GUARDIAN_APPROVED, now=clock + 0.2)[0] is True
        assert director.can_dispatch(AudioEventId.GUARDIAN_BLOCKED, now=clock + 0.2)[0] is True

    def test_scenario_20_application_shutdown_with_timers_pending(self, tmp_path: Path) -> None:
        """Scenario 20: Clean application teardown safely cancels pending timers and queues."""
        settings = Settings(app_data_dir=tmp_path, audio_enabled=True)
        mgr = AudioManager(settings=settings)
        director = HorrorAudioDirector(audio_manager=mgr, settings=settings)
        director.set_enabled(True)
        adapter = AudioEventAdapter(mgr, horror_director=director)

        mock_timer = MagicMock()
        scheduler = WhisperScheduler(
            audio_manager=mgr,
            audio_adapter=adapter,
            horror_director=director,
            cancel_timer_func=lambda t: t.stop(),
        )
        scheduler._active_timer = mock_timer
        adapter._whisper_scheduler = scheduler

        # Shutdown through adapter
        adapter.on_shutdown()
        assert director._is_shutdown is True
        assert scheduler._is_shutdown is True
        mock_timer.stop.assert_called_once()
