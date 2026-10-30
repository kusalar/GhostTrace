"""Tests for GhostTrace scheduled whispers and time-aware manifestations (v1.2.0 Step 08)."""

from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from ghosttrace.audio.adapter import AudioEventAdapter
from ghosttrace.audio.manager import AudioManager
from ghosttrace.audio.preferences import (
    AudioPreferences,
    apply_preferences_with_precedence,
    load_audio_preferences,
    save_audio_preferences,
)
from ghosttrace.audio.typing_effects import TypingEffectsManager
from ghosttrace.audio.whisper_scheduler import WHISPER_MODE_PROFILES, WhisperScheduler
from ghosttrace.config.settings import Settings
from ghosttrace.main import app as cli_app
from ghosttrace.terminal.app import GhostTraceApp
from ghosttrace.terminal.widgets.audio_modal import AudioSettingsModal
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


class TestWhispersConfigurationAndPreferences:
    """Tests for default state, preferences persistence, and CLI commands."""

    def test_disabled_by_default(self, tmp_path: Path) -> None:
        """Scheduled whispers must be strictly disabled by default."""
        settings = Settings(app_data_dir=tmp_path)
        assert settings.audio_scheduled_whispers_enabled is False
        assert settings.scheduled_whispers_enabled is False

        prefs = AudioPreferences()
        assert prefs.scheduled_whispers_enabled is False

        mgr = AudioManager(settings=settings)
        assert mgr.scheduled_whispers_enabled is False
        st = mgr.get_status()
        assert st.scheduled_whispers_enabled is False

    def test_preferences_persistence(self, tmp_path: Path) -> None:
        """Scheduled whispers preference persists and reloads correctly."""
        pref_file = tmp_path / "audio_preferences.json"
        prefs = AudioPreferences(enabled=True, scheduled_whispers_enabled=True)
        assert save_audio_preferences(prefs, pref_file) is True

        loaded = load_audio_preferences(pref_file)
        assert loaded.enabled is True
        assert loaded.scheduled_whispers_enabled is True

        settings = Settings(app_data_dir=tmp_path)
        resolved = apply_preferences_with_precedence(settings, loaded)
        assert resolved["scheduled_whispers_enabled"] is True

    def test_cli_whispers_commands(self) -> None:
        """CLI audio whispers on/off updates preferences cleanly."""
        res_on = runner.invoke(cli_app, ["audio", "whispers", "on"])
        assert res_on.exit_code == 0
        assert "Scheduled whispers ENABLED" in res_on.stdout

        status_res = runner.invoke(cli_app, ["audio", "status"])
        assert status_res.exit_code == 0
        assert "Scheduled Whispers : ENABLED" in status_res.stdout

        res_off = runner.invoke(cli_app, ["audio", "whispers", "off"])
        assert res_off.exit_code == 0
        assert "Scheduled whispers DISABLED" in res_off.stdout

        status_res2 = runner.invoke(cli_app, ["audio", "status"])
        assert status_res2.exit_code == 0
        assert "Scheduled Whispers : DISABLED" in status_res2.stdout

    def test_cli_whispers_invalid_argument(self) -> None:
        """CLI audio whispers rejects invalid arguments."""
        res = runner.invoke(cli_app, ["audio", "whispers", "perhaps"])
        assert res.exit_code == 1
        assert "Invalid state" in res.stdout


class TestWhisperSchedulerCorePolicy:
    """Tests for scheduler intervals, cooldowns, mode policies, and limits."""

    def test_no_whisper_when_master_audio_disabled(self, tmp_path: Path) -> None:
        """No whisper triggers when master audio is disabled."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=False,
            audio_scheduled_whispers_enabled=True,
        )
        mgr = AudioManager(settings=settings)
        scheduler = WhisperScheduler(audio_manager=mgr)
        assert scheduler.is_enabled is False
        assert scheduler.can_play_whisper() is False
        assert scheduler.tick() is None

    def test_no_whisper_when_whisper_setting_disabled(self, tmp_path: Path) -> None:
        """No whisper triggers when scheduled whispers feature is disabled."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_scheduled_whispers_enabled=False,
        )
        mgr = AudioManager(settings=settings)
        scheduler = WhisperScheduler(audio_manager=mgr)
        assert scheduler.is_enabled is False
        assert scheduler.can_play_whisper() is False
        assert scheduler.tick() is None

    def test_no_whisper_when_muted(self, tmp_path: Path) -> None:
        """Muted state suppresses scheduled whispers immediately."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_scheduled_whispers_enabled=True,
        )
        mgr = AudioManager(settings=settings)
        mgr.mute(persist=False)

        scheduler = WhisperScheduler(audio_manager=mgr)
        assert scheduler.is_enabled is False
        assert scheduler.can_play_whisper() is False

    def test_focus_mode_suppresses_whispers(self, tmp_path: Path) -> None:
        """Focus mode strictly suppresses all whisper manifestations."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_scheduled_whispers_enabled=True,
        )
        mgr = AudioManager(settings=settings)
        adapter = AudioEventAdapter(mgr)
        adapter.set_experience_mode("focus")

        scheduler = WhisperScheduler(audio_manager=mgr, audio_adapter=adapter)
        assert scheduler.experience_mode == "focus"
        assert scheduler.can_play_whisper() is False
        assert scheduler.tick() is None

    def test_interval_calculation_within_bounds(self, tmp_path: Path) -> None:
        """Calculates randomized intervals strictly within mode boundaries."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_scheduled_whispers_enabled=True,
        )
        mgr = AudioManager(settings=settings)

        # Min boundary (random_func returns 0.0)
        sched_min = WhisperScheduler(audio_manager=mgr, random_func=lambda: 0.0)
        norm_prof = WHISPER_MODE_PROFILES["normal"]
        assert sched_min.calculate_next_interval("normal") == norm_prof["min_interval_seconds"]

        # Max boundary (random_func returns 1.0)
        sched_max = WhisperScheduler(audio_manager=mgr, random_func=lambda: 1.0)
        assert sched_max.calculate_next_interval("normal") == norm_prof["max_interval_seconds"]

        # Midpoint (random_func returns 0.5)
        sched_mid = WhisperScheduler(audio_manager=mgr, random_func=lambda: 0.5)
        expected_mid = (norm_prof["min_interval_seconds"] + norm_prof["max_interval_seconds"]) / 2.0
        assert sched_mid.calculate_next_interval("normal") == expected_mid

    def test_cooldown_enforcement(self, tmp_path: Path) -> None:
        """Enforces cooldown between whispers."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_scheduled_whispers_enabled=True,
        )
        mgr = AudioManager(settings=settings)
        mgr.play = MagicMock(return_value=True)

        scheduler = WhisperScheduler(audio_manager=mgr)
        scheduler.set_experience_mode("haunted")  # cooldown = 30s

        t = 1000.0
        # First whisper plays
        res = scheduler.trigger_whisper(now=t)
        assert res in WHISPER_MODE_PROFILES["haunted"]["allowed_events"]
        assert mgr.play.called

        # Second whisper within 30s cooldown is suppressed
        mgr.play.reset_mock()
        assert scheduler.can_play_whisper(now=t + 10.0) is False
        assert scheduler.trigger_whisper(now=t + 10.0) is None
        assert not mgr.play.called

        # After 31.0s (> 30s cooldown), next whisper is permitted
        assert scheduler.can_play_whisper(now=t + 31.0) is True
        res2 = scheduler.trigger_whisper(now=t + 31.0)
        assert res2 is not None
        assert mgr.play.called

    def test_hourly_frequency_ceiling(self, tmp_path: Path) -> None:
        """Ceiling on total whispers within rolling 1-hour window."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_scheduled_whispers_enabled=True,
        )
        mgr = AudioManager(settings=settings)
        mgr.play = MagicMock(return_value=True)

        scheduler = WhisperScheduler(audio_manager=mgr)
        scheduler.set_experience_mode("normal")  # max 3 per hour, cooldown 120s

        t = 100.0
        # Trigger 3 whispers spaced past cooldown
        for _ in range(3):
            t += 130.0
            res = scheduler.trigger_whisper(now=t)
            assert res is not None

        # 4th attempt within same hour must be rejected by hourly ceiling
        t += 130.0
        assert scheduler.can_play_whisper(now=t) is False
        assert scheduler.trigger_whisper(now=t) is None

        # After rolling window moves past the 1st whisper (> 3600s from t=230), permitted
        t = 100.0 + 130.0 + 3601.0
        assert scheduler.can_play_whisper(now=t) is True

    def test_context_check_suppression(self, tmp_path: Path) -> None:
        """Context check suppresses whispers during busy terminal states."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_scheduled_whispers_enabled=True,
        )
        mgr = AudioManager(settings=settings)
        is_safe = True
        scheduler = WhisperScheduler(
            audio_manager=mgr,
            context_check_func=lambda: is_safe,
        )
        scheduler.set_experience_mode("haunted")
        assert scheduler.can_play_whisper(now=100.0) is True

        is_safe = False
        assert scheduler.can_play_whisper(now=100.0) is False

    def test_no_overlapping_whispers(self, tmp_path: Path) -> None:
        """Prevents overlapping whisper playback if one is currently active."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_scheduled_whispers_enabled=True,
        )
        mgr = AudioManager(settings=settings)
        scheduler = WhisperScheduler(audio_manager=mgr)
        scheduler.set_experience_mode("haunted")

        scheduler._is_whisper_playing = True
        assert scheduler.can_play_whisper(now=1000.0) is False


class TestSchedulerTimerIntegrationAndConcurrency:
    """Tests for Textual timer loop integration, cancellation, and concurrency."""

    def test_schedule_next_registers_timer_without_threads(self, tmp_path: Path) -> None:
        """Scheduling uses timer function and spawns zero new threads."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_scheduled_whispers_enabled=True,
        )
        mgr = AudioManager(settings=settings)
        initial_threads = threading.active_count()

        mock_timer_setter = MagicMock(return_value="mock_timer_token")
        scheduler = WhisperScheduler(
            audio_manager=mgr,
            schedule_timer_func=mock_timer_setter,
        )
        scheduler.set_experience_mode("haunted")
        scheduler.schedule_next(delay=45.0)

        mock_timer_setter.assert_called_once()
        args = mock_timer_setter.call_args[0]
        assert args[0] == 45.0
        assert scheduler._active_timer == "mock_timer_token"
        assert threading.active_count() == initial_threads

    def test_cancel_timer_on_mode_change_to_focus(self, tmp_path: Path) -> None:
        """Switching to Focus mode cancels active timer immediately."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_scheduled_whispers_enabled=True,
        )
        mgr = AudioManager(settings=settings)
        mock_cancel = MagicMock()
        mock_setter = MagicMock(return_value="active_token")

        scheduler = WhisperScheduler(
            audio_manager=mgr,
            schedule_timer_func=mock_setter,
            cancel_timer_func=mock_cancel,
        )
        scheduler.set_experience_mode("haunted")
        scheduler.schedule_next(delay=30.0)
        assert scheduler._active_timer == "active_token"

        scheduler.set_experience_mode("focus")
        mock_cancel.assert_called_once_with("active_token")
        assert scheduler._active_timer is None

    def test_no_duplicate_timers_on_reschedule(self, tmp_path: Path) -> None:
        """Rescheduling cancels any prior pending timer."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_scheduled_whispers_enabled=True,
        )
        mgr = AudioManager(settings=settings)
        mock_cancel = MagicMock()
        mock_setter = MagicMock(side_effect=["token_1", "token_2"])

        scheduler = WhisperScheduler(
            audio_manager=mgr,
            schedule_timer_func=mock_setter,
            cancel_timer_func=mock_cancel,
        )
        scheduler.set_experience_mode("haunted")
        scheduler.schedule_next(delay=30.0)
        assert scheduler._active_timer == "token_1"

        scheduler.schedule_next(delay=60.0)
        mock_cancel.assert_called_once_with("token_1")
        assert scheduler._active_timer == "token_2"

    def test_shutdown_lifecycle_safety(self, tmp_path: Path) -> None:
        """Shutdown marks scheduler inactive and releases timer."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_scheduled_whispers_enabled=True,
        )
        mgr = AudioManager(settings=settings)
        mock_cancel = MagicMock()
        scheduler = WhisperScheduler(
            audio_manager=mgr,
            schedule_timer_func=lambda d, cb: "timer_handle",
            cancel_timer_func=mock_cancel,
        )
        scheduler.set_experience_mode("haunted")
        scheduler.schedule_next(delay=30.0)

        scheduler.shutdown()
        assert scheduler._is_shutdown is True
        assert scheduler.is_enabled is False
        mock_cancel.assert_called_once_with("timer_handle")
        assert scheduler.tick() is None

    def test_audio_modal_whispers_toggle(self, tmp_path: Path) -> None:
        """AudioSettingsModal toggles scheduled whispers cleanly."""
        settings = Settings(app_data_dir=tmp_path, audio_enabled=True)
        mgr = AudioManager(settings=settings)
        assert mgr.scheduled_whispers_enabled is False

        modal = AudioSettingsModal(audio_manager=mgr)
        modal.action_toggle_whispers()
        assert mgr.scheduled_whispers_enabled is True

        modal.action_toggle_whispers()
        assert mgr.scheduled_whispers_enabled is False

    def test_coexistence_with_haunted_keystrokes(self, tmp_path: Path) -> None:
        """Whisper scheduler and typing effects engine coexist without conflict."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_haunted_keystrokes_enabled=True,
            audio_scheduled_whispers_enabled=True,
        )
        mgr = AudioManager(settings=settings)
        mgr.play = MagicMock(return_value=True)

        typing_eng = TypingEffectsManager(audio_manager=mgr, random_func=lambda: 0.01)
        whisper_sched = WhisperScheduler(audio_manager=mgr, random_func=lambda: 0.01)

        typing_eng.set_experience_mode("haunted")
        whisper_sched.set_experience_mode("haunted")

        # Typing effect
        for i in range(4):
            typing_eng.record_keystroke(now=100.0 + i * 0.1)

        # Whisper event
        whisper_res = whisper_sched.trigger_whisper(now=1000.0)
        assert whisper_res in WHISPER_MODE_PROFILES["haunted"]["allowed_events"]
        assert mgr.play.called

    @pytest.mark.asyncio
    async def test_terminal_app_whisper_scheduler_lifecycle(self, tmp_path: Path) -> None:
        """WhisperScheduler mounts and shuts down cleanly within GhostTraceApp."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_scheduled_whispers_enabled=True,
        )
        app = GhostTraceApp(settings=settings)
        assert app.whisper_scheduler is not None

        async with app.run_test(size=(80, 24)) as pilot:
            assert app.whisper_scheduler._is_shutdown is False
            assert app.whisper_scheduler._active_timer is not None
            await pilot.pause()

        # After exiting run_test, unmount ran shutdown
        assert app.whisper_scheduler._is_shutdown is True
        assert app.whisper_scheduler._active_timer is None
