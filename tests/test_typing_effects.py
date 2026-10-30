"""Tests for GhostTrace haunted keystrokes and typing audio effects (v1.2.0 Step 07)."""

from __future__ import annotations

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
from ghosttrace.audio.schemas import AudioEventId
from ghosttrace.audio.typing_effects import TYPING_MODE_PROFILES, TypingEffectsManager
from ghosttrace.config.settings import Settings
from ghosttrace.main import app as cli_app
from ghosttrace.terminal.app import GhostTraceApp
from ghosttrace.terminal.history import SessionHistory
from ghosttrace.terminal.widgets.audio_modal import AudioSettingsModal
from ghosttrace.terminal.widgets.input import CommandInput
from textual import events
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


class TestHauntedKeystrokesConfiguration:
    """Tests for default state, preferences persistence, and CLI commands."""

    def test_disabled_by_default(self, tmp_path: Path) -> None:
        """Haunted keystrokes must be strictly disabled by default."""
        settings = Settings(app_data_dir=tmp_path)
        assert settings.audio_haunted_keystrokes_enabled is False
        assert settings.haunted_keystrokes_enabled is False

        prefs = AudioPreferences()
        assert prefs.haunted_keystrokes_enabled is False

        mgr = AudioManager(settings=settings)
        assert mgr.haunted_keystrokes_enabled is False
        status = mgr.get_status()
        assert status.haunted_keystrokes_enabled is False

    def test_preferences_persistence(self, tmp_path: Path) -> None:
        """Haunted keystrokes preference persists and reloads correctly."""
        pref_file = tmp_path / "audio_preferences.json"
        prefs = AudioPreferences(enabled=True, haunted_keystrokes_enabled=True)
        assert save_audio_preferences(prefs, pref_file) is True

        loaded = load_audio_preferences(pref_file)
        assert loaded.enabled is True
        assert loaded.haunted_keystrokes_enabled is True

        settings = Settings(app_data_dir=tmp_path)
        resolved = apply_preferences_with_precedence(settings, loaded)
        assert resolved["haunted_keystrokes_enabled"] is True

    def test_cli_keystrokes_command(self, tmp_path: Path) -> None:
        """CLI audio keystrokes on/off updates preferences cleanly."""
        res_on = runner.invoke(cli_app, ["audio", "keystrokes", "on"])
        assert res_on.exit_code == 0
        assert "Haunted keystrokes ENABLED" in res_on.stdout

        status_res = runner.invoke(cli_app, ["audio", "status"])
        assert status_res.exit_code == 0
        assert "Haunted Keystrokes : ENABLED" in status_res.stdout

        res_off = runner.invoke(cli_app, ["audio", "keystrokes", "off"])
        assert res_off.exit_code == 0
        assert "Haunted keystrokes DISABLED" in res_off.stdout

        status_res2 = runner.invoke(cli_app, ["audio", "status"])
        assert status_res2.exit_code == 0
        assert "Haunted Keystrokes : DISABLED" in status_res2.stdout

    def test_cli_invalid_argument(self) -> None:
        """CLI audio keystrokes rejects invalid arguments."""
        res = runner.invoke(cli_app, ["audio", "keystrokes", "maybe"])
        assert res.exit_code == 1
        assert "Invalid state" in res.stdout


class TestTypingEffectsEngine:
    """Tests for core rate limiting, cooldowns, mode policies, and deterministic rolls."""

    def test_no_effect_when_audio_disabled(self, tmp_path: Path) -> None:
        """No audio effects trigger when overall audio is disabled."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=False,
            audio_haunted_keystrokes_enabled=True,
        )
        mgr = AudioManager(settings=settings)
        engine = TypingEffectsManager(
            audio_manager=mgr,
            random_func=lambda: 0.01,  # Guaranteed roll
            time_func=lambda: 100.0,
        )
        assert engine.is_enabled is False
        for _ in range(10):
            assert engine.record_keystroke() is None

    def test_no_effect_when_feature_disabled(self, tmp_path: Path) -> None:
        """No audio effects trigger when haunted keystrokes feature is disabled."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_haunted_keystrokes_enabled=False,
        )
        mgr = AudioManager(settings=settings)
        engine = TypingEffectsManager(
            audio_manager=mgr,
            random_func=lambda: 0.01,
            time_func=lambda: 100.0,
        )
        assert engine.is_enabled is False
        for _ in range(10):
            assert engine.record_keystroke() is None

    def test_no_effect_when_muted(self, tmp_path: Path) -> None:
        """No audio effects trigger when audio subsystem is muted."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_haunted_keystrokes_enabled=True,
        )
        mgr = AudioManager(settings=settings)
        mgr.mute(persist=False)

        engine = TypingEffectsManager(
            audio_manager=mgr,
            random_func=lambda: 0.01,
            time_func=lambda: 100.0,
        )
        assert engine.is_enabled is False
        for _ in range(10):
            assert engine.record_keystroke() is None

    def test_no_effect_in_focus_mode(self, tmp_path: Path) -> None:
        """Focus mode strictly suppresses all haunted keystroke effects."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_haunted_keystrokes_enabled=True,
        )
        mgr = AudioManager(settings=settings)
        adapter = AudioEventAdapter(mgr)
        adapter.set_experience_mode("focus")

        engine = TypingEffectsManager(
            audio_manager=mgr,
            audio_adapter=adapter,
            random_func=lambda: 0.01,
        )
        assert engine.experience_mode == "focus"
        simulated_time = 100.0
        for _ in range(20):
            simulated_time += 0.2
            assert engine.record_keystroke(now=simulated_time) is None

    def test_normal_mode_consecutive_keys_and_cooldown(self, tmp_path: Path) -> None:
        """Normal mode requires minimum consecutive keys and enforces cooldown."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_haunted_keystrokes_enabled=True,
        )
        mgr = AudioManager(settings=settings)
        mgr.play = MagicMock(return_value=True)  # Mock actual playback

        engine = TypingEffectsManager(
            audio_manager=mgr,
            random_func=lambda: 0.01,  # Guaranteed roll (< 0.06 base_prob)
        )
        engine.set_experience_mode("normal")

        # In normal mode, min_keystrokes_before_effect = 5
        t = 100.0
        for _ in range(4):
            t += 0.1
            res = engine.record_keystroke(now=t)
            assert res is None  # Not enough consecutive keys

        # 5th keystroke triggers effect
        t += 0.1
        effect = engine.record_keystroke(now=t)
        assert effect in (AudioEventId.KEYSTROKE_HAUNT, AudioEventId.GLITCH_DIGITAL)
        assert mgr.play.called

        # Immediate next keystrokes within cooldown (4.0s) must be suppressed
        mgr.play.reset_mock()
        t += 0.5
        assert engine.record_keystroke(now=t) is None
        assert not mgr.play.called

        t += 1.0  # 1.5s since effect < 4.0s
        assert engine.record_keystroke(now=t) is None

        # Keep typing at 0.5s intervals (so inactivity threshold 1.2s does not expire)
        # Advance until past 4.0s cooldown
        t += 0.5  # 2.0s
        engine.record_keystroke(now=t)
        t += 0.5  # 2.5s
        engine.record_keystroke(now=t)
        t += 0.5  # 3.0s
        engine.record_keystroke(now=t)
        t += 0.5  # 3.5s
        engine.record_keystroke(now=t)
        t += 0.6  # 4.1s past effect -> Cooldown expired!
        effect2 = engine.record_keystroke(now=t)
        assert effect2 in (AudioEventId.KEYSTROKE_HAUNT, AudioEventId.GLITCH_DIGITAL)

    def test_ambient_mode_behavior(self, tmp_path: Path) -> None:
        """Ambient mode permits subtle typing effects with ambient volume."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_haunted_keystrokes_enabled=True,
        )
        mgr = AudioManager(settings=settings)
        mgr.play = MagicMock(return_value=True)

        engine = TypingEffectsManager(
            audio_manager=mgr,
            random_func=lambda: 0.01,
        )
        engine.set_experience_mode("ambient")

        t = 50.0
        # Ambient requires 4 keys
        for _ in range(3):
            t += 0.1
            assert engine.record_keystroke(now=t) is None

        t += 0.1
        res = engine.record_keystroke(now=t)
        assert res in (AudioEventId.KEYSTROKE_HAUNT, AudioEventId.GLITCH_STATIC)
        assert mgr.play.called

    def test_haunted_mode_and_burst_detection(self, tmp_path: Path) -> None:
        """Haunted mode detects typing bursts and selects burst events."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_haunted_keystrokes_enabled=True,
        )
        mgr = AudioManager(settings=settings)
        mgr.play = MagicMock(return_value=True)

        # Roll returns 0.18:
        # Base prob in haunted is 0.12 (0.18 >= 0.12 -> fails regular check)
        # Burst prob in haunted is 0.22 (0.18 < 0.22 -> succeeds burst check!)
        engine = TypingEffectsManager(
            audio_manager=mgr,
            random_func=lambda: 0.18,
        )
        engine.set_experience_mode("haunted")

        t = 200.0
        # 3 slow keys (< 8 in 2s): does not trigger because 0.18 >= 0.12
        for _ in range(3):
            t += 0.5
            assert engine.record_keystroke(now=t) is None

        # Simulate fast typing burst (8 keys in < 1 second)
        t = 210.0
        for _ in range(7):
            t += 0.08
            engine.record_keystroke(now=t)

        t += 0.08
        # Now 8 keys in 2s window -> burst mode active -> prob 0.22 > 0.18 -> triggers!
        res = engine.record_keystroke(now=t)
        assert res in TYPING_MODE_PROFILES["haunted"]["burst_events"]

    def test_typing_inactivity_detection(self, tmp_path: Path) -> None:
        """Stopping typing resets consecutive keystroke count."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_haunted_keystrokes_enabled=True,
        )
        mgr = AudioManager(settings=settings)
        mgr.play = MagicMock(return_value=True)

        engine = TypingEffectsManager(
            audio_manager=mgr,
            random_func=lambda: 0.01,
            inactivity_threshold=1.0,
        )
        engine.set_experience_mode("normal")  # requires 5 keys

        t = 10.0
        # Type 4 keys (not yet 5)
        for _ in range(4):
            t += 0.1
            engine.record_keystroke(now=t)

        assert engine.is_typing_active(now=t) is True

        # User pauses typing for 1.5s (> 1.0s threshold)
        t += 1.5
        assert engine.is_typing_active(now=t) is False

        # Next single keystroke should NOT trigger because consecutive count reset to 1
        res = engine.record_keystroke(now=t)
        assert res is None
        assert engine._consecutive_keystrokes == 1

    def test_max_effects_per_minute(self, tmp_path: Path) -> None:
        """Enforces hard ceiling on effects within any 60-second window."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_haunted_keystrokes_enabled=True,
        )
        mgr = AudioManager(settings=settings)
        mgr.play = MagicMock(return_value=True)

        engine = TypingEffectsManager(
            audio_manager=mgr,
            random_func=lambda: 0.01,
        )
        engine.set_experience_mode("normal")  # max 4 per minute, cooldown 4.0s

        t = 0.0
        effects_fired = 0
        for _ in range(10):
            t += 5.0  # greater than cooldown
            # Type 5 keys to qualify
            for _ in range(5):
                t += 0.05
                res = engine.record_keystroke(now=t)
                if res is not None:
                    effects_fired += 1

        # Must not exceed max_effects_per_minute (4)
        assert effects_fired == 4

    def test_probability_threshold_rejection(self, tmp_path: Path) -> None:
        """When random roll exceeds probability, no sound effect is triggered."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_haunted_keystrokes_enabled=True,
        )
        mgr = AudioManager(settings=settings)
        mgr.play = MagicMock(return_value=True)

        engine = TypingEffectsManager(
            audio_manager=mgr,
            random_func=lambda: 0.99,  # Never triggers
        )
        engine.set_experience_mode("haunted")

        t = 100.0
        for _ in range(30):
            t += 0.1
            assert engine.record_keystroke(now=t) is None
        assert not mgr.play.called

    def test_debounce_rapid_key_chatter(self, tmp_path: Path) -> None:
        """Key repetitions faster than min_key_interval (30ms) are debounced."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_haunted_keystrokes_enabled=True,
        )
        mgr = AudioManager(settings=settings)

        engine = TypingEffectsManager(
            audio_manager=mgr,
            min_key_interval=0.03,
        )
        t = 10.0
        engine.record_keystroke(now=t)
        assert engine._consecutive_keystrokes == 1

        # Key chatter arriving 10ms later
        engine.record_keystroke(now=t + 0.01)
        assert engine._consecutive_keystrokes == 1  # Debounced, not incremented


class TestPrivacyAndInterfaceIntegrity:
    """Tests ensuring zero keylogging, zero data leakage, and normal UI behavior."""

    def test_privacy_record_keystroke_accepts_no_characters(self, tmp_path: Path) -> None:
        """Verification that record_keystroke API does not accept key characters or text."""
        import inspect

        sig = inspect.signature(TypingEffectsManager.record_keystroke)
        # Parameters should strictly be self and optional now: float
        params = list(sig.parameters.keys())
        assert params == ["self", "now"]
        assert "key" not in params
        assert "char" not in params
        assert "text" not in params

    def test_command_input_history_navigation_unaffected(self) -> None:
        """CommandInput navigation (Up/Down) remains completely functional without active app."""
        history = SessionHistory()
        history.add("status")
        history.add("ai prompt test")

        cmd_input = CommandInput(history=history)

        # Send Up arrow key
        event_up = events.Key("up", "up")
        cmd_input.on_key(event_up)

        # Verify command history was loaded into input value
        assert cmd_input.value == "ai prompt test"

        # Send Down arrow key
        event_down = events.Key("down", "down")
        cmd_input.on_key(event_down)
        assert cmd_input.value == ""

    def test_audio_modal_details_includes_keystrokes(self, tmp_path: Path) -> None:
        """AudioSettingsModal details string renders Haunted Keystrokes status."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_haunted_keystrokes_enabled=True,
        )
        mgr = AudioManager(settings=settings)
        modal = AudioSettingsModal(audio_manager=mgr)
        details = modal._render_details()
        assert "Haunted Keystrokes" in details
        assert "ON" in details

        mgr.set_haunted_keystrokes(False, persist=False)
        details_off = modal._render_details()
        assert "Haunted Keystrokes" in details_off
        assert "OFF" in details_off

    def test_audio_modal_toggle_keystrokes_action(self, tmp_path: Path) -> None:
        """AudioSettingsModal action_toggle_keystrokes toggles manager state."""
        settings = Settings(app_data_dir=tmp_path, audio_enabled=True)
        mgr = AudioManager(settings=settings)
        assert mgr.haunted_keystrokes_enabled is False

        modal = AudioSettingsModal(audio_manager=mgr)
        modal.action_toggle_keystrokes()
        assert mgr.haunted_keystrokes_enabled is True

        modal.action_toggle_keystrokes()
        assert mgr.haunted_keystrokes_enabled is False

    @pytest.mark.asyncio
    async def test_interactive_tui_keystrokes_integration(self, tmp_path: Path) -> None:
        """Typing in GhostTraceApp CommandInput triggers typing effects in TUI."""
        settings = Settings(
            app_data_dir=tmp_path,
            audio_enabled=True,
            audio_haunted_keystrokes_enabled=True,
        )
        app = GhostTraceApp(settings=settings)
        app.typing_effects.record_keystroke = MagicMock(return_value=AudioEventId.KEYSTROKE_HAUNT)

        async with app.run_test(size=(80, 24)) as pilot:
            for ch in "hello":
                await pilot.press(ch)
            await pilot.pause()

            assert app.typing_effects.record_keystroke.call_count == 5
