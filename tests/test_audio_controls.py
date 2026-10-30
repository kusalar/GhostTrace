"""Tests for GhostTrace audio controls, persistence, CLI, and experience modes (Step 05)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from ghosttrace.audio.adapter import AudioEventAdapter
from ghosttrace.audio.backend import MiniAudioBackend, NullAudioBackend
from ghosttrace.audio.manager import AudioManager
from ghosttrace.audio.preferences import (
    AudioPreferences,
    apply_preferences_with_precedence,
    load_audio_preferences,
    save_audio_preferences,
)
from ghosttrace.audio.schemas import AudioEventId
from ghosttrace.config.settings import Settings
from ghosttrace.ghost.schemas import GhostMood
from ghosttrace.haunt.engine import HauntEngine
from ghosttrace.main import app as cli_app
from ghosttrace.terminal.command_registry import CommandContext
from ghosttrace.terminal.commands import handle_audio, handle_haunt
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


class TestAudioSettingsAndPersistence:
    """Tests for persistent user audio preferences and precedence."""

    def test_default_settings_keep_audio_disabled(self, tmp_path: Path) -> None:
        """New installations default to disabled audio."""
        settings = Settings(app_data_dir=tmp_path)
        prefs = load_audio_preferences(tmp_path / "audio_preferences.json")
        assert prefs.enabled is False
        assert prefs.volume == 0.50
        assert prefs.ambient_volume == 0.20
        assert prefs.muted is False
        assert settings.audio_enabled is False

    def test_preferences_persist_across_reloads(self, tmp_path: Path) -> None:
        """Preferences saved to disk survive application restarts."""
        pref_file = tmp_path / "audio_preferences.json"
        prefs = AudioPreferences(enabled=True, volume=0.75, ambient_volume=0.35, muted=True)
        assert save_audio_preferences(prefs, pref_file) is True

        loaded = load_audio_preferences(pref_file)
        assert loaded.enabled is True
        assert loaded.volume == 0.75
        assert loaded.ambient_volume == 0.35
        assert loaded.muted is True

    def test_corrupted_preferences_fallback_safely(self, tmp_path: Path) -> None:
        """Corrupted JSON or invalid schema falls back safely to default preferences."""
        pref_file = tmp_path / "audio_preferences.json"
        pref_file.write_text("{ corrupt json ...", encoding="utf-8")

        loaded = load_audio_preferences(pref_file)
        assert loaded.enabled is False
        assert loaded.volume == 0.50
        assert loaded.ambient_volume == 0.20
        assert loaded.muted is False

    def test_non_dict_json_fallback(self, tmp_path: Path) -> None:
        """JSON with non-dict root falls back safely."""
        pref_file = tmp_path / "audio_preferences.json"
        pref_file.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")

        loaded = load_audio_preferences(pref_file)
        assert loaded.enabled is False

    def test_environment_variable_precedence_over_persisted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Environment variables take precedence over persisted preferences."""
        pref_file = tmp_path / "audio_preferences.json"
        save_audio_preferences(
            AudioPreferences(enabled=True, volume=0.40, ambient_volume=0.15, muted=False),
            pref_file,
        )

        monkeypatch.setenv("GHOSTTRACE_AUDIO_VOLUME", "0.85")
        monkeypatch.setenv("GHOSTTRACE_AUDIO_MUTED", "true")

        settings = Settings(app_data_dir=tmp_path)
        resolved = apply_preferences_with_precedence(settings, load_audio_preferences(pref_file))

        assert resolved["enabled"] is True  # from persisted
        assert resolved["volume"] == 0.85  # from env
        assert resolved["ambient_volume"] == 0.15  # from persisted
        assert resolved["muted"] is True  # from env

    def test_explicit_env_disable_cannot_be_overridden_by_persisted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Explicit GHOSTTRACE_AUDIO_ENABLED=false cannot be overridden by persisted enabled."""
        pref_file = tmp_path / "audio_preferences.json"
        save_audio_preferences(AudioPreferences(enabled=True), pref_file)

        monkeypatch.setenv("GHOSTTRACE_AUDIO_ENABLED", "false")
        settings = Settings(app_data_dir=tmp_path)
        resolved = apply_preferences_with_precedence(settings, load_audio_preferences(pref_file))

        assert resolved["enabled"] is False

    def test_volume_boundary_validation(self) -> None:
        """Volume values outside [0.0, 1.0] raise validation error."""
        with pytest.raises(ValueError):
            AudioPreferences(volume=-0.1)
        with pytest.raises(ValueError):
            AudioPreferences(volume=1.05)
        with pytest.raises(ValueError):
            AudioPreferences(ambient_volume=1.5)


class TestCLIAudioCommands:
    """Tests for Typer CLI audio command suite."""

    def test_cli_status_does_not_initialize_hardware(self) -> None:
        """`ghosttrace audio status` displays configuration without starting hardware."""
        with patch.object(MiniAudioBackend, "initialize") as mock_init:
            result = runner.invoke(cli_app, ["audio", "status"])
            assert result.exit_code == 0
            assert "GHOSTTRACE AUDIO SUBSYSTEM" in result.output
            assert "DISABLED" in result.output or "ENABLED" in result.output
            # Must NOT initialize miniaudio device
            mock_init.assert_not_called()

    def test_cli_enable_and_disable(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """CLI enable and disable update preferences."""
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        with patch.object(MiniAudioBackend, "initialize", return_value=True):
            res_enable = runner.invoke(cli_app, ["audio", "enable"])
            assert res_enable.exit_code == 0
            assert "enabled" in res_enable.output.lower()

            res_disable = runner.invoke(cli_app, ["audio", "disable"])
            assert res_disable.exit_code == 0
            assert "disabled" in res_disable.output.lower()

    def test_cli_volume_validation(self) -> None:
        """CLI volume rejects out-of-range inputs."""
        res_invalid = runner.invoke(cli_app, ["audio", "volume", "1.5"])
        assert res_invalid.exit_code != 0

        res_valid = runner.invoke(cli_app, ["audio", "volume", "0.75"])
        assert res_valid.exit_code == 0
        assert "75%" in res_valid.output

    def test_cli_ambient_volume(self) -> None:
        """CLI ambient-volume sets independent ambient level."""
        res = runner.invoke(cli_app, ["audio", "ambient-volume", "0.35"])
        assert res.exit_code == 0
        assert "35%" in res.output

    def test_cli_mute_and_unmute(self) -> None:
        """CLI mute and unmute operate correctly."""
        res_mute = runner.invoke(cli_app, ["audio", "mute"])
        assert res_mute.exit_code == 0
        assert "muted" in res_mute.output.lower()

        res_unmute = runner.invoke(cli_app, ["audio", "unmute"])
        assert res_unmute.exit_code == 0
        assert "unmuted" in res_unmute.output.lower()

    def test_cli_test_sound_respects_disabled_state(self) -> None:
        """CLI test sound reports message when audio is disabled."""
        with patch("ghosttrace.main.get_settings", return_value=Settings(audio_enabled=False)):
            res = runner.invoke(cli_app, ["audio", "test"])
            assert res.exit_code == 0
            assert "DISABLED" in res.output


class TestTerminalAudioCommands:
    """Tests for interactive TUI commands (`audio ...`)."""

    def test_tui_audio_status(self) -> None:
        """TUI `audio status` returns formatted telemetry table."""
        ctx = CommandContext(
            settings=Settings(audio_enabled=False),
            history=MagicMock(),
        )
        res = handle_audio(["status"], ctx)
        assert res.success is True
        assert "GHOSTTRACE AUDIO STATUS" in res.output
        assert "DISABLED" in res.output

    def test_tui_audio_volume_adjustment(self) -> None:
        """TUI `audio volume` updates manager volume."""
        mock_mgr = MagicMock(spec=AudioManager)
        mock_mgr.settings = Settings(audio_enabled=True)
        ctx = CommandContext(
            settings=Settings(audio_enabled=True),
            history=MagicMock(),
            audio_manager=mock_mgr,
        )
        res = handle_audio(["volume", "0.85"], ctx)
        assert res.success is True
        mock_mgr.set_volume.assert_called_with(0.85, persist=True)

    def test_tui_audio_mute_toggle(self) -> None:
        """TUI `audio mute` and `audio unmute` call manager methods."""
        mock_mgr = MagicMock(spec=AudioManager)
        mock_mgr.settings = Settings(audio_enabled=True)
        mock_mgr._volume = 0.5
        ctx = CommandContext(
            settings=Settings(audio_enabled=True),
            history=MagicMock(),
            audio_manager=mock_mgr,
        )
        res_mute = handle_audio(["mute"], ctx)
        assert res_mute.success is True
        mock_mgr.mute.assert_called_with(persist=True)

        res_unmute = handle_audio(["unmute"], ctx)
        assert res_unmute.success is True
        mock_mgr.unmute.assert_called_with(persist=True)

    def test_tui_audio_settings_command(self) -> None:
        """TUI `audio settings` returns audio_settings command_name to trigger modal."""
        ctx = CommandContext(
            settings=Settings(),
            history=MagicMock(),
        )
        res = handle_audio(["settings"], ctx)
        assert res.success is True
        assert res.command_name == "audio_settings"


class TestExperienceModeAudioIntegration:
    """Tests for audio synchronization with Haunt experience modes."""

    def test_normal_mode_does_not_start_ambient(self) -> None:
        """Normal mode keeps ambient stream stopped."""
        mock_mgr = MagicMock(spec=AudioManager)
        mock_mgr.settings = Settings(audio_enabled=True)
        adapter = AudioEventAdapter(mock_mgr)

        adapter.set_experience_mode("normal", force=True)
        assert adapter.experience_mode == "normal"
        mock_mgr.stop_ambient.assert_called()
        mock_mgr.play_ambient.assert_not_called()

    def test_ambient_mode_starts_ambient_loop(self) -> None:
        """Ambient mode starts dark hum loop when audio is enabled."""
        mock_mgr = MagicMock(spec=AudioManager)
        mock_mgr.settings = Settings(audio_enabled=True)
        mock_mgr._is_muted = False
        adapter = AudioEventAdapter(mock_mgr)

        adapter.set_experience_mode("ambient")
        assert adapter.experience_mode == "ambient"
        mock_mgr.play_ambient.assert_called_with(AudioEventId.AMBIENT_DARK_HUM)

    def test_haunted_mode_starts_cold_wind_loop(self) -> None:
        """Haunted mode starts cold wind loop when audio is enabled."""
        mock_mgr = MagicMock(spec=AudioManager)
        mock_mgr.settings = Settings(audio_enabled=True)
        mock_mgr._is_muted = False
        adapter = AudioEventAdapter(mock_mgr)

        adapter.set_experience_mode("haunted")
        assert adapter.experience_mode == "haunted"
        mock_mgr.play_ambient.assert_called_with(AudioEventId.AMBIENT_COLD_WIND)

    def test_focus_mode_stops_ambient_and_suppresses_non_essential(self) -> None:
        """Focus mode stops ambient and suppresses notifications, glitches, and coding sounds."""
        mock_mgr = MagicMock(spec=AudioManager)
        mock_mgr.settings = Settings(audio_enabled=True)
        adapter = AudioEventAdapter(mock_mgr)

        adapter.set_experience_mode("focus")
        assert adapter.experience_mode == "focus"
        mock_mgr.stop_ambient.assert_called()

        # Non-essential events MUST be suppressed
        assert adapter.on_notification("Ordinary update", severity="info") is False
        assert adapter.on_coding_success("dev generate") is False
        assert adapter.on_mood_shift(GhostMood.DORMANT, GhostMood.CURIOUS) is False
        assert adapter.on_glitch("digital") is False
        mock_mgr.play.assert_not_called()

        # Essential Guardian events MUST STILL WORK in Focus mode
        assert adapter.on_guardian_intercept("rm -rf /") is True
        mock_mgr.play.assert_called_with(AudioEventId.GUARDIAN_INTERCEPT, volume_scale=1.0)

        assert adapter.on_guardian_approved("tok123") is True
        mock_mgr.play.assert_called_with(AudioEventId.GUARDIAN_APPROVED, volume_scale=1.0)

        assert adapter.on_guardian_blocked("tok123") is True
        mock_mgr.play.assert_called_with(AudioEventId.GUARDIAN_BLOCKED, volume_scale=1.0)

        # Critical errors must also remain audible in Focus mode
        assert adapter.on_app_error(Exception("Critical fault")) is True
        mock_mgr.play.assert_called_with(AudioEventId.APP_ERROR, volume_scale=1.0)

    def test_mode_transitions_are_idempotent(self) -> None:
        """Setting the same mode repeatedly does not restart loops."""
        mock_mgr = MagicMock(spec=AudioManager)
        mock_mgr.settings = Settings(audio_enabled=True)
        mock_mgr._is_muted = False
        adapter = AudioEventAdapter(mock_mgr)

        adapter.set_experience_mode("ambient")
        adapter.set_experience_mode("ambient")
        assert mock_mgr.play_ambient.call_count == 1

    def test_disabled_audio_remains_silent_in_every_mode(self) -> None:
        """When audio is disabled, entering any mode never starts ambient audio."""
        mock_mgr = MagicMock(spec=AudioManager)
        mock_mgr.settings = Settings(audio_enabled=False)
        adapter = AudioEventAdapter(mock_mgr)

        for mode in ("normal", "ambient", "haunted", "focus"):
            adapter.set_experience_mode(mode)
            mock_mgr.play_ambient.assert_not_called()

    def test_haunt_cli_mode_command_synchronizes_audio(self) -> None:
        """CLI `haunt mode <name>` informs audio_adapter of new mode."""
        mock_mgr = MagicMock(spec=AudioManager)
        mock_mgr.settings = Settings(audio_enabled=True)
        adapter = AudioEventAdapter(mock_mgr)
        haunt_engine = HauntEngine(settings=Settings())

        ctx = CommandContext(
            settings=Settings(audio_enabled=True),
            history=MagicMock(),
            haunt_engine=haunt_engine,
            audio_adapter=adapter,
        )

        res = handle_haunt(["mode", "focus"], ctx)
        assert res.success is True
        assert adapter.experience_mode == "focus"


class TestAudioModalScreen:
    """Tests for the AudioSettingsModal Textual widget."""

    def test_modal_instantiation_and_details_rendering(self) -> None:
        """AudioSettingsModal renders status details cleanly without exceptions."""
        mgr = AudioManager(settings=Settings(audio_enabled=False))
        adapter = AudioEventAdapter(mgr)
        modal = AudioSettingsModal(audio_manager=mgr, audio_adapter=adapter)

        details = modal._render_details()
        assert "Subsystem State" in details
        assert "DISABLED" in details
        assert "Master Volume" in details
        assert "50%" in details

    def test_modal_volume_buttons(self) -> None:
        """Modal volume action handlers adjust manager volume."""
        mgr = AudioManager(settings=Settings(audio_enabled=True))
        adapter = AudioEventAdapter(mgr)
        modal = AudioSettingsModal(audio_manager=mgr, audio_adapter=adapter)

        modal.action_vol_up()
        assert mgr._volume == 0.60
        modal.action_vol_down()
        assert mgr._volume == 0.50

    def test_modal_mute_toggle(self) -> None:
        """Modal mute toggle updates manager mute state."""
        mgr = AudioManager(settings=Settings(audio_enabled=True))
        modal = AudioSettingsModal(audio_manager=mgr)

        modal.action_toggle_mute()
        assert mgr._is_muted is True
        modal.action_toggle_mute()
        assert mgr._is_muted is False


class TestConcurrencyAndRobustness:
    """Tests for thread safety and device isolation."""

    def test_concurrent_enable_calls_safe(self) -> None:
        """Multiple concurrent calls to enable do not crash or corrupt manager."""
        mgr = AudioManager(settings=Settings(audio_enabled=False))
        with patch.object(MiniAudioBackend, "initialize", return_value=True):
            res1 = mgr.enable(persist=False)
            res2 = mgr.enable(persist=False)
            assert res1 is True
            assert res2 is True
            assert mgr.settings.audio_enabled is True

    def test_repeated_enable_disable_cycles_clean(self) -> None:
        """Cycling enable and disable leaves backend in expected state."""
        mgr = AudioManager(settings=Settings(audio_enabled=False))
        with patch.object(MiniAudioBackend, "initialize", return_value=True):
            for _ in range(5):
                mgr.enable(persist=False)
                assert mgr.settings.audio_enabled is True
                mgr.disable(persist=False)
                assert mgr.settings.audio_enabled is False
                assert isinstance(mgr.backend, NullAudioBackend)
