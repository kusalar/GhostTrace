"""Tests for GhostTrace dynamic horror event director (v1.2.0 Step 09)."""

from __future__ import annotations

import os
import threading
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from ghosttrace.audio.adapter import AudioEventAdapter
from ghosttrace.audio.horror_director import (
    AudioPriority,
    HorrorAudioDirector,
    HorrorIntensity,
    SuppressionReason,
)
from ghosttrace.audio.manager import AudioManager
from ghosttrace.audio.preferences import (
    AudioPreferences,
    apply_preferences_with_precedence,
    load_audio_preferences,
)
from ghosttrace.audio.schemas import AudioEventId
from ghosttrace.config.settings import Settings
from ghosttrace.main import app as cli_app
from typer.testing import CliRunner

runner = CliRunner()


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


class TestHorrorDirectorCore:
    """Core functionality, priorities, intensity, and safety guards."""

    def test_01_director_disabled_by_default(self, tmp_path: Path) -> None:
        """Dynamic horror director must be strictly disabled by default."""
        settings = Settings(app_data_dir=tmp_path)
        assert settings.audio_dynamic_horror_enabled is False
        assert settings.dynamic_horror_enabled is False

        prefs = AudioPreferences()
        assert prefs.dynamic_horror_enabled is False

        mgr = AudioManager(settings=settings)
        assert mgr.dynamic_horror_enabled is False

        director = HorrorAudioDirector(audio_manager=mgr, settings=settings)
        assert director.is_enabled is False
        assert director.compute_intensity() == HorrorIntensity.DORMANT

    def test_02_master_audio_disabled_behavior(self, tmp_path: Path) -> None:
        """When master audio is disabled, director suppresses playback safely."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=False,
            audio_dynamic_horror_enabled=True,
        )
        mgr = AudioManager(settings=settings)
        director = HorrorAudioDirector(audio_manager=mgr, settings=settings)

        allowed, reason = director.can_dispatch(AudioEventId.WHISPER_BREATH)
        assert allowed is False
        assert reason == SuppressionReason.AUDIO_DISABLED.value

    def test_03_mute_behavior(self, tmp_path: Path) -> None:
        """When audio is muted, all atmospheric manifestations are suppressed."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_dynamic_horror_enabled=True,
        )
        mgr = AudioManager(settings=settings)
        mgr.mute(persist=False)

        director = HorrorAudioDirector(audio_manager=mgr, settings=settings)
        allowed, reason = director.can_dispatch(AudioEventId.KEYSTROKE_HAUNT)
        assert allowed is False
        assert reason == SuppressionReason.AUDIO_MUTED.value

    def test_04_normal_mode_intensity(self, tmp_path: Path) -> None:
        """Normal mode: DORMANT base; escalates to SUBTLE on sustained typing."""
        clock = 100.0
        director = HorrorAudioDirector(
            experience_mode="normal",
            time_func=lambda: clock,
        )
        director.set_enabled(True)
        assert director.compute_intensity() == HorrorIntensity.DORMANT

        # Simulate typing activity
        for _ in range(5):
            clock += 0.5
            director.record_typing_activity(now=clock)

        assert director.compute_intensity() == HorrorIntensity.SUBTLE
        # Normal mode never reaches unsettling or haunted
        for _ in range(20):
            clock += 0.1
            director.record_typing_activity(now=clock)
        assert director.compute_intensity() == HorrorIntensity.SUBTLE

    def test_05_ambient_mode_intensity(self, tmp_path: Path) -> None:
        """Ambient mode: SUBTLE base; escalates to UNSETTLING on sustained activity."""
        clock = 200.0
        director = HorrorAudioDirector(
            experience_mode="ambient",
            time_func=lambda: clock,
        )
        director.set_enabled(True)
        assert director.compute_intensity() == HorrorIntensity.SUBTLE

        # Simulate sustained typing activity
        for _ in range(6):
            clock += 0.5
            director.record_typing_activity(now=clock)

        assert director.compute_intensity() == HorrorIntensity.UNSETTLING

    def test_06_haunted_mode_intensity(self, tmp_path: Path) -> None:
        """Haunted mode: UNSETTLING base; escalates to HAUNTED on sustained activity."""
        clock = 300.0
        director = HorrorAudioDirector(
            experience_mode="haunted",
            time_func=lambda: clock,
        )
        director.set_enabled(True)
        assert director.compute_intensity() == HorrorIntensity.UNSETTLING

        # Simulate sustained typing activity
        for _ in range(4):
            clock += 0.5
            director.record_typing_activity(now=clock)

        assert director.compute_intensity() == HorrorIntensity.HAUNTED

    def test_07_focus_mode_suppression(self, tmp_path: Path) -> None:
        """Focus mode strictly forces intensity to DORMANT and suppresses atmospheric events."""
        clock = 400.0
        director = HorrorAudioDirector(
            experience_mode="focus",
            time_func=lambda: clock,
        )
        director.set_enabled(True)
        assert director.compute_intensity() == HorrorIntensity.DORMANT

        allowed, reason = director.can_dispatch(AudioEventId.WHISPER_SPECTRAL)
        assert allowed is False
        assert reason == SuppressionReason.FOCUS_MODE.value

    def test_08_critical_event_priority(self, tmp_path: Path) -> None:
        """Critical events (Guardian security, App Error) have highest priority."""
        settings = Settings(app_data_dir=tmp_path, audio_enabled=True)
        mgr = AudioManager(settings=settings)
        director = HorrorAudioDirector(
            audio_manager=mgr,
            settings=settings,
            experience_mode="focus",
        )
        director.set_enabled(True)

        assert director.get_priority(AudioEventId.GUARDIAN_INTERCEPT) == AudioPriority.CRITICAL
        assert director.get_priority(AudioEventId.GUARDIAN_APPROVED) == AudioPriority.CRITICAL
        assert director.get_priority(AudioEventId.GUARDIAN_BLOCKED) == AudioPriority.CRITICAL
        assert director.get_priority(AudioEventId.APP_ERROR) == AudioPriority.CRITICAL

        # Allowed even in Focus mode
        allowed, reason = director.can_dispatch(AudioEventId.GUARDIAN_INTERCEPT)
        assert allowed is True
        assert reason is None

    def test_09_guardian_events_unaffected_by_atmospheric_budgets(self, tmp_path: Path) -> None:
        """Exhausting atmospheric event budgets must never block Guardian sounds."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_dynamic_horror_enabled=True,
        )
        mgr = AudioManager(settings=settings)
        mgr.play = MagicMock(return_value=True)
        director = HorrorAudioDirector(
            audio_manager=mgr,
            settings=settings,
            experience_mode="normal",
        )

        clock = 100.0
        # Exhaust normal atmospheric budget (max 3/min)
        for _ in range(3):
            clock += 10.0
            assert director.dispatch_event(AudioEventId.GLITCH_DIGITAL, now=clock) is True

        # 4th atmospheric event is rejected
        clock += 5.0
        assert director.dispatch_event(AudioEventId.GLITCH_DIGITAL, now=clock) is False

        # But Guardian events are dispatched unconditionally
        assert director.dispatch_event(AudioEventId.GUARDIAN_INTERCEPT, now=clock) is True
        assert director.dispatch_event(AudioEventId.GUARDIAN_APPROVED, now=clock) is True
        assert director.dispatch_event(AudioEventId.GUARDIAN_BLOCKED, now=clock) is True

    def test_10_important_events_taking_precedence(self, tmp_path: Path) -> None:
        """Important lifecycle and feedback events take precedence over atmospheric effects."""
        director = HorrorAudioDirector()
        assert director.get_priority(AudioEventId.STARTUP) == AudioPriority.IMPORTANT
        assert director.get_priority(AudioEventId.SHUTDOWN) == AudioPriority.IMPORTANT
        assert director.get_priority(AudioEventId.NOTIFICATION_ALERT) == AudioPriority.IMPORTANT
        assert director.get_priority(AudioEventId.CODING_SUCCESS) == AudioPriority.IMPORTANT

        # Important events are permitted during active atmospheric cooldown
        clock = 100.0
        director._last_atmospheric_time = clock
        allowed, reason = director.can_dispatch(AudioEventId.CODING_SUCCESS, now=clock + 0.5)
        assert allowed is True
        assert reason is None

    def test_11_atmospheric_rate_limits(self, tmp_path: Path) -> None:
        """Atmospheric effects strictly respect per-minute rolling rate ceilings."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_dynamic_horror_enabled=True,
        )
        mgr = AudioManager(settings=settings)
        mgr.play = MagicMock(return_value=True)

        director = HorrorAudioDirector(
            audio_manager=mgr,
            settings=settings,
            experience_mode="normal",  # max 3 per min, min_interval 8.0s
        )

        t = 100.0
        assert director.dispatch_event(AudioEventId.GLITCH_DIGITAL, now=t) is True
        t += 8.5
        assert director.dispatch_event(AudioEventId.GLITCH_DIGITAL, now=t) is True
        t += 8.5
        assert director.dispatch_event(AudioEventId.GLITCH_DIGITAL, now=t) is True

        # 4th within 60s exceeds budget
        t += 8.5
        allowed, reason = director.can_dispatch(AudioEventId.GLITCH_DIGITAL, now=t)
        assert allowed is False
        assert reason == SuppressionReason.RATE_LIMIT_EXCEEDED.value

    def test_12_duplicate_event_suppression(self, tmp_path: Path) -> None:
        """Repeated glitch bursts are suppressed by glitch cooldown."""
        director = HorrorAudioDirector(experience_mode="normal")
        director.set_enabled(True)

        t = 100.0
        allowed1, _ = director.can_dispatch(AudioEventId.GLITCH_DIGITAL, now=t)
        assert allowed1 is True
        director.dispatch_event(AudioEventId.GLITCH_DIGITAL, now=t)

        # Immediate repeated glitch within 3.0s is suppressed
        allowed2, reason2 = director.can_dispatch(AudioEventId.GLITCH_STATIC, now=t + 0.5)
        assert allowed2 is False
        assert reason2 in (
            SuppressionReason.GLITCH_BURST.value,
            SuppressionReason.COOLDOWN_ACTIVE.value,
        )

    def test_13_whisper_and_typing_conflict_prevention(self, tmp_path: Path) -> None:
        """Whispers and typing effects prevent sound collisions within collision window."""
        settings = Settings(app_data_dir=tmp_path, audio_enabled=True)
        mgr = AudioManager(settings=settings)
        mgr.play = MagicMock(return_value=True)

        director = HorrorAudioDirector(
            audio_manager=mgr,
            settings=settings,
            experience_mode="normal",
        )
        director.set_enabled(True)

        t = 500.0
        # Trigger whisper at t=500.0
        assert director.dispatch_event(AudioEventId.WHISPER_BREATH, now=t) is True

        # Typing effect at t=501.0 within collision window (2.5s) is rejected
        allowed_typing, reason_typing = director.can_dispatch(
            AudioEventId.KEYSTROKE_HAUNT, now=t + 1.0
        )
        assert allowed_typing is False
        assert reason_typing == SuppressionReason.WHISPER_COLLISION.value

        # At t=515.0, trigger typing effect
        t = 515.0
        assert director.dispatch_event(AudioEventId.KEYSTROKE_HAUNT, now=t) is True

        # Whisper at t=516.0 within collision window is rejected
        allowed_whisper, reason_whisper = director.can_dispatch(
            AudioEventId.WHISPER_BREATH, now=t + 1.0
        )
        assert allowed_whisper is False
        assert reason_whisper in (
            SuppressionReason.TYPING_COLLISION.value,
            SuppressionReason.COOLDOWN_ACTIVE.value,
        )

    def test_14_ai_generation_suppression(self, tmp_path: Path) -> None:
        """Active AI generation suppresses atmospheric effects while permitting critical events."""
        is_gen = True
        director = HorrorAudioDirector(
            context_check_func=lambda: {"is_generating": is_gen},
            experience_mode="haunted",
        )
        director.set_enabled(True)

        # Atmospheric effect is suppressed
        allowed, reason = director.can_dispatch(AudioEventId.WHISPER_SPECTRAL)
        assert allowed is False
        assert reason == SuppressionReason.AI_GENERATING.value

        # Guardian and app error are still permitted
        assert director.can_dispatch(AudioEventId.GUARDIAN_INTERCEPT)[0] is True
        assert director.can_dispatch(AudioEventId.APP_ERROR)[0] is True

    def test_15_guardian_confirmation_suppression(self, tmp_path: Path) -> None:
        """Pending Guardian confirmation dialog suppresses atmospheric effects."""
        guardian_pending = True
        director = HorrorAudioDirector(
            context_check_func=lambda: {"is_guardian_active": guardian_pending},
            experience_mode="haunted",
        )
        director.set_enabled(True)

        allowed, reason = director.can_dispatch(AudioEventId.KEYSTROKE_HAUNT)
        assert allowed is False
        assert reason == SuppressionReason.GUARDIAN_ACTIVE.value

    def test_16_mode_changes_update_intensity_immediately(self, tmp_path: Path) -> None:
        """Dynamic mode change immediately updates intensity and policies without restart."""
        director = HorrorAudioDirector(experience_mode="normal")
        director.set_enabled(True)
        assert director.experience_mode == "normal"

        director.set_experience_mode("haunted")
        assert director.experience_mode == "haunted"
        assert director.compute_intensity() == HorrorIntensity.UNSETTLING

        director.set_experience_mode("focus")
        assert director.experience_mode == "focus"
        assert director.compute_intensity() == HorrorIntensity.DORMANT

    def test_17_preference_persistence(self, tmp_path: Path) -> None:
        """Dynamic horror preference persists to JSON and honors environment variable."""
        settings = Settings(app_data_dir=tmp_path)
        mgr = AudioManager(settings=settings)

        assert mgr.dynamic_horror_enabled is False
        mgr.set_dynamic_horror(True, persist=True)
        assert mgr.dynamic_horror_enabled is True

        loaded = load_audio_preferences()
        assert loaded.dynamic_horror_enabled is True

        # Environment variable precedence
        os.environ["GHOSTTRACE_AUDIO_DYNAMIC_HORROR_ENABLED"] = "false"
        try:
            resolved = apply_preferences_with_precedence(settings)
            assert resolved["dynamic_horror_enabled"] is False
        finally:
            os.environ.pop("GHOSTTRACE_AUDIO_DYNAMIC_HORROR_ENABLED", None)

    def test_18_cli_and_tui_controls(self, tmp_path: Path) -> None:
        """CLI audio horror on/off commands work properly and update status telemetry."""
        res_on = runner.invoke(cli_app, ["audio", "horror", "on"])
        assert res_on.exit_code == 0
        assert "Dynamic horror event orchestration ENABLED" in res_on.stdout

        status_res = runner.invoke(cli_app, ["audio", "status"])
        assert status_res.exit_code == 0
        assert "Horror Director    : ENABLED" in status_res.stdout

        res_off = runner.invoke(cli_app, ["audio", "horror", "off"])
        assert res_off.exit_code == 0
        assert "Dynamic horror event orchestration DISABLED" in res_off.stdout

        status_res2 = runner.invoke(cli_app, ["audio", "status"])
        assert status_res2.exit_code == 0
        assert "Horror Director    : DISABLED" in status_res2.stdout

    def test_19_safe_shutdown(self, tmp_path: Path) -> None:
        """Director shuts down cleanly and idempotently."""
        director = HorrorAudioDirector()
        director.set_enabled(True)
        director.dispatch_event(AudioEventId.GLITCH_DIGITAL)

        director.shutdown()
        assert director._is_shutdown is True
        assert len(director._recent_atmospheric_timestamps) == 0

        # Subsequent non-shutdown dispatches are rejected
        allowed, _ = director.can_dispatch(AudioEventId.WHISPER_BREATH)
        assert allowed is False

        # Idempotent second call
        director.shutdown()
        assert director._is_shutdown is True

    def test_20_no_extra_persistent_worker_threads(self, tmp_path: Path) -> None:
        """HorrorAudioDirector creates exactly zero extra persistent worker threads."""
        initial_threads = threading.active_count()
        director = HorrorAudioDirector(experience_mode="haunted")
        director.set_enabled(True)

        for _ in range(50):
            director.can_dispatch(AudioEventId.KEYSTROKE_HAUNT)
            director.compute_intensity()

        assert threading.active_count() == initial_threads

    def test_21_no_raw_keyboard_data_or_command_contents(self, tmp_path: Path) -> None:
        """Director strictly rejects keyboard characters and command strings (privacy guarantee)."""
        director = HorrorAudioDirector()
        # record_typing_activity accepts only an optional float timestamp 'now'
        director.record_typing_activity(now=123.45)

        # Verify no text inspection attributes or buffers exist
        assert not hasattr(director, "keystroke_buffer")
        assert not hasattr(director, "command_text")
        assert not hasattr(director, "last_key_name")

    def test_22_deterministic_intensity_calculations(self, tmp_path: Path) -> None:
        """Intensity calculation is 100% deterministic from application state."""
        director1 = HorrorAudioDirector(experience_mode="haunted", time_func=lambda: 100.0)
        director2 = HorrorAudioDirector(experience_mode="haunted", time_func=lambda: 100.0)
        director1.set_enabled(True)
        director2.set_enabled(True)

        assert director1.compute_intensity() == director2.compute_intensity()

        for _ in range(4):
            director1.record_typing_activity(now=100.0)
            director2.record_typing_activity(now=100.0)

        assert (
            director1.compute_intensity()
            == director2.compute_intensity()
            == HorrorIntensity.HAUNTED
        )

    def test_23_injected_clock_and_random_source_behavior(self, tmp_path: Path) -> None:
        """Injected clocks and random sources are strictly utilized."""
        mock_clock = MagicMock(return_value=999.0)
        mock_rand = MagicMock(return_value=0.42)

        director = HorrorAudioDirector(
            time_func=mock_clock,
            random_func=mock_rand,
        )
        director.can_dispatch(AudioEventId.GLITCH_DIGITAL)
        assert mock_clock.called

    def test_24_dynamic_horror_disabled_without_affecting_standard_audio_events(
        self, tmp_path: Path
    ) -> None:
        """When dynamic horror is disabled, all standard application events function normally."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_dynamic_horror_enabled=False,
        )
        mgr = AudioManager(settings=settings)
        mgr.play = MagicMock(return_value=True)

        adapter = AudioEventAdapter(mgr)
        assert adapter.horror_director.is_enabled is False

        # Verify all standard events dispatch cleanly
        assert adapter.on_startup() is True
        assert adapter.on_notification("Test Alert", important=True) is True
        assert adapter.on_coding_success("testing") is True
        assert adapter.on_guardian_intercept("rm -rf /") is True
        assert adapter.on_guardian_approved("token") is True
        assert adapter.on_guardian_blocked("token", "danger") is True
        assert adapter.on_app_error("Exception") is True
        assert adapter.on_glitch("digital") is True
        assert adapter.on_shutdown() is True
