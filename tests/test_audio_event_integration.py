"""Tests for application event audio integration in GhostTrace v1.1.0 (Step 04)."""

from __future__ import annotations

import concurrent.futures
from unittest.mock import MagicMock

from ghosttrace.audio.adapter import AudioEventAdapter, NotificationSeverity
from ghosttrace.audio.manager import AudioManager
from ghosttrace.audio.schemas import AudioEventId
from ghosttrace.config.settings import Settings
from ghosttrace.developer.engine import DeveloperEngine
from ghosttrace.ghost.schemas import GhostMood
from ghosttrace.guardian.schemas import ExecutionStatus
from ghosttrace.terminal.app import GhostTraceApp
from ghosttrace.terminal.command_registry import CommandContext
from ghosttrace.terminal.commands import handle_dev, handle_guard


def _create_mock_manager(enabled: bool = True) -> MagicMock:
    """Helper to create a mocked AudioManager with configurable settings."""
    settings = Settings(audio_enabled=enabled)
    mock_mgr = MagicMock(spec=AudioManager)
    mock_mgr.settings = settings
    mock_mgr.play.return_value = True
    return mock_mgr


class TestLifecycleAudioIntegration:
    """Tests for application lifecycle audio events."""

    def test_startup_event_dispatches_once(self) -> None:
        """Startup event dispatches exactly once after successful initialization."""
        mock_mgr = _create_mock_manager(enabled=True)
        adapter = AudioEventAdapter(mock_mgr)

        assert adapter.on_startup() is True
        mock_mgr.play.assert_called_once_with(AudioEventId.STARTUP, volume_scale=1.0)

        # Repeated call must be ignored
        assert adapter.on_startup() is False
        assert mock_mgr.play.call_count == 1

    def test_shutdown_dispatches_before_teardown(self) -> None:
        """Shutdown event dispatches shutdown sound and tears down backend."""
        mock_mgr = _create_mock_manager(enabled=True)
        adapter = AudioEventAdapter(mock_mgr)

        assert adapter.on_shutdown() is True
        mock_mgr.play.assert_called_once_with(AudioEventId.SHUTDOWN, volume_scale=1.0)
        mock_mgr.shutdown.assert_called_once()

    def test_repeated_shutdown_idempotent(self) -> None:
        """Repeated shutdown calls do not produce duplicate sounds or errors."""
        mock_mgr = _create_mock_manager(enabled=True)
        adapter = AudioEventAdapter(mock_mgr)

        assert adapter.on_shutdown() is True
        assert adapter.on_shutdown() is False
        assert mock_mgr.play.call_count == 1
        assert mock_mgr.shutdown.call_count == 1

    def test_disabled_audio_dispatches_no_playback(self) -> None:
        """When audio is disabled, lifecycle events trigger no playback."""
        mock_mgr = _create_mock_manager(enabled=False)
        adapter = AudioEventAdapter(mock_mgr)

        assert adapter.on_startup() is False
        assert adapter.on_shutdown() is False
        mock_mgr.play.assert_not_called()


class TestNotificationAudioIntegration:
    """Tests for notification severity mapping and deduplication."""

    def test_important_notification_maps_to_alert(self) -> None:
        """Important notifications and warnings map to notification_alert."""
        mock_mgr = _create_mock_manager(enabled=True)
        adapter = AudioEventAdapter(mock_mgr, cooldowns={})

        assert adapter.on_notification("Critical disk warning", severity="warning") is True
        mock_mgr.play.assert_called_with(AudioEventId.NOTIFICATION_ALERT, volume_scale=1.0)

        assert adapter.on_notification("Custom alert", important=True) is True
        mock_mgr.play.assert_called_with(AudioEventId.NOTIFICATION_ALERT, volume_scale=1.0)

    def test_critical_notification_maps_to_alert(self) -> None:
        """Critical severity notifications trigger alert cue."""
        mock_mgr = _create_mock_manager(enabled=True)
        adapter = AudioEventAdapter(mock_mgr)

        assert (
            adapter.on_notification("System fault", severity=NotificationSeverity.CRITICAL) is True
        )
        mock_mgr.play.assert_called_with(AudioEventId.NOTIFICATION_ALERT, volume_scale=1.0)

    def test_ordinary_notification_maps_to_ping(self) -> None:
        """Ordinary info notifications map to notification_ping."""
        mock_mgr = _create_mock_manager(enabled=True)
        adapter = AudioEventAdapter(mock_mgr)

        assert adapter.on_notification("Task completed", severity="info") is True
        mock_mgr.play.assert_called_with(AudioEventId.NOTIFICATION_PING, volume_scale=1.0)

    def test_unimportant_status_updates_suppressed(self) -> None:
        """Status and debug updates do not trigger sound playback."""
        mock_mgr = _create_mock_manager(enabled=True)
        adapter = AudioEventAdapter(mock_mgr)

        assert adapter.on_notification("Syncing memory index...", severity="status") is False
        assert adapter.on_notification("Background poll", severity="debug") is False
        mock_mgr.play.assert_not_called()

    def test_duplicate_notification_suppression(self) -> None:
        """Identical notification messages in rapid succession are suppressed."""
        mock_mgr = _create_mock_manager(enabled=True)
        adapter = AudioEventAdapter(mock_mgr)

        assert adapter.on_notification("File saved successfully", severity="info") is True
        assert adapter.on_notification("File saved successfully", severity="info") is False
        assert mock_mgr.play.call_count == 1


class TestGuardianAudioIntegration:
    """Tests for Command Guardian security event audio integration."""

    def test_guardian_intercept_maps_correctly(self) -> None:
        """Intercepting a dangerous command triggers guardian_intercept."""
        mock_mgr = _create_mock_manager(enabled=True)
        adapter = AudioEventAdapter(mock_mgr)

        assert adapter.on_guardian_intercept("rm -rf /") is True
        mock_mgr.play.assert_called_once_with(AudioEventId.GUARDIAN_INTERCEPT, volume_scale=1.0)

    def test_guardian_approved_only_after_approval(self) -> None:
        """Approved command triggers guardian_approved only after explicit user approval."""
        mock_mgr = _create_mock_manager(enabled=True)
        adapter = AudioEventAdapter(mock_mgr)

        assert adapter.on_guardian_approved("tok-999") is True
        mock_mgr.play.assert_called_once_with(AudioEventId.GUARDIAN_APPROVED, volume_scale=1.0)

    def test_guardian_blocked_maps_correctly(self) -> None:
        """Rejected or cancelled command triggers guardian_blocked."""
        mock_mgr = _create_mock_manager(enabled=True)
        adapter = AudioEventAdapter(mock_mgr)

        assert adapter.on_guardian_blocked("tok-999", "User cancelled") is True
        mock_mgr.play.assert_called_once_with(AudioEventId.GUARDIAN_BLOCKED, volume_scale=1.0)

    def test_audio_errors_never_change_guardian_outcomes(self) -> None:
        """Audio backend errors do not propagate or disrupt Guardian decisions."""
        mock_mgr = _create_mock_manager(enabled=True)
        mock_mgr.play.side_effect = RuntimeError("Audio device lost")
        adapter = AudioEventAdapter(mock_mgr)

        # Must not raise exceptions
        assert adapter.on_guardian_intercept("test") is False
        assert adapter.on_guardian_approved("test") is False
        assert adapter.on_guardian_blocked("test") is False

    def test_guardian_cli_approve_and_cancel_triggers_adapter(self) -> None:
        """CLI guard approve and guard cancel execute adapter audio callbacks."""
        from ghosttrace.guardian.schemas import ExecutionResult

        mock_mgr = _create_mock_manager(enabled=True)
        adapter = AudioEventAdapter(mock_mgr)

        mock_guard = MagicMock()
        mock_req = MagicMock()
        mock_req.analysis.original_command = "echo safe"
        mock_guard.approval_mgr.get_request.return_value = mock_req
        mock_guard.execute_approved.return_value = ExecutionResult(
            token="tok123",
            command="echo safe",
            status=ExecutionStatus.SUCCESS,
            exit_code=0,
            stdout="safe\n",
            stderr="",
            duration_seconds=0.012,
            working_dir="D:/GhostTrace",
        )
        mock_guard.cancel_approval.return_value = (True, "Cancelled")

        ctx = CommandContext(
            settings=Settings(audio_enabled=True),
            history=MagicMock(),
            guardian_engine=mock_guard,
            audio_adapter=adapter,
        )

        res_approve = handle_guard(["approve", "tok123"], ctx)
        assert res_approve.success is True
        mock_mgr.play.assert_called_with(AudioEventId.GUARDIAN_APPROVED, volume_scale=1.0)

        res_cancel = handle_guard(["cancel", "tok123"], ctx)
        assert res_cancel.success is True
        mock_mgr.play.assert_called_with(AudioEventId.GUARDIAN_BLOCKED, volume_scale=1.0)


class TestDeveloperEventAudioIntegration:
    """Tests for developer coding workflow audio integration."""

    def test_coding_success_maps_correctly(self) -> None:
        """Developer coding operations trigger coding_success."""
        mock_mgr = _create_mock_manager(enabled=True)
        adapter = AudioEventAdapter(mock_mgr)

        assert adapter.on_coding_success("dev generate") is True
        mock_mgr.play.assert_called_once_with(AudioEventId.CODING_SUCCESS, volume_scale=1.0)

    def test_dev_analyze_triggers_coding_success(self) -> None:
        """Safe local static analysis command dispatches coding_success."""
        mock_mgr = _create_mock_manager(enabled=True)
        adapter = AudioEventAdapter(mock_mgr)

        mock_dev = MagicMock(spec=DeveloperEngine)
        mock_dev.format_static_analysis_report.return_value = "Report: 0 issues"

        ctx = CommandContext(
            settings=Settings(audio_enabled=True),
            history=MagicMock(),
            dev_engine=mock_dev,
            audio_adapter=adapter,
        )

        res = handle_dev(["analyze", "def foo(): pass"], ctx)
        assert res.success is True
        mock_mgr.play.assert_called_once_with(AudioEventId.CODING_SUCCESS, volume_scale=1.0)

    def test_app_error_deduplicated_against_notification_error(self) -> None:
        """App error is suppressed if error notification was already played."""
        mock_mgr = _create_mock_manager(enabled=True)
        adapter = AudioEventAdapter(mock_mgr)

        # 1. Error notification plays alert
        assert adapter.on_notification("Inference failed", severity="error") is True
        mock_mgr.play.assert_called_with(AudioEventId.NOTIFICATION_ALERT, volume_scale=1.0)

        # 2. Immediate app_error hook is suppressed to prevent double-stinger
        assert adapter.on_app_error(Exception("Inference failed")) is False
        assert mock_mgr.play.call_count == 1

    def test_app_error_dispatches_when_not_duplicate(self) -> None:
        """App error dispatches app_error stinger when independent."""
        mock_mgr = _create_mock_manager(enabled=True)
        adapter = AudioEventAdapter(mock_mgr)

        assert adapter.on_app_error(RuntimeError("Out of memory")) is True
        mock_mgr.play.assert_called_once_with(AudioEventId.APP_ERROR, volume_scale=1.0)


class TestHauntAudioIntegration:
    """Tests for haunt events, mood shifts, and glitch cues."""

    def test_mood_shift_maps_correctly(self) -> None:
        """Real mood transition triggers mood_shift sound cue."""
        mock_mgr = _create_mock_manager(enabled=True)
        adapter = AudioEventAdapter(mock_mgr)

        assert adapter.on_mood_shift(GhostMood.DORMANT, GhostMood.CURIOUS) is True
        mock_mgr.play.assert_called_once_with(AudioEventId.MOOD_SHIFT, volume_scale=1.0)

    def test_no_sound_when_mood_unchanged(self) -> None:
        """No sound cue is played when mood is unchanged or None."""
        mock_mgr = _create_mock_manager(enabled=True)
        adapter = AudioEventAdapter(mock_mgr)

        assert adapter.on_mood_shift(GhostMood.DORMANT, GhostMood.DORMANT) is False
        assert adapter.on_mood_shift(None, GhostMood.CURIOUS) is False
        mock_mgr.play.assert_not_called()

    def test_glitch_events_map_correctly(self) -> None:
        """Glitch variants map to their appropriate canonical audio events."""
        mock_mgr = _create_mock_manager(enabled=True)
        adapter = AudioEventAdapter(mock_mgr)

        assert adapter.on_glitch("digital") is True
        mock_mgr.play.assert_called_with(AudioEventId.GLITCH_DIGITAL, volume_scale=1.0)

        assert adapter.on_glitch("static") is True
        mock_mgr.play.assert_called_with(AudioEventId.GLITCH_STATIC, volume_scale=1.0)

        assert adapter.on_glitch("corruption") is True
        mock_mgr.play.assert_called_with(AudioEventId.GLITCH_CORRUPTION, volume_scale=1.0)

    def test_ambient_not_automatically_started(self) -> None:
        """Neither app initialization nor adapter startup starts ambient audio."""
        settings = Settings(audio_enabled=True, audio_ambient_enabled=True)
        mock_mgr = MagicMock(spec=AudioManager)
        mock_mgr.settings = settings
        mock_mgr.play.return_value = True

        adapter = AudioEventAdapter(mock_mgr)
        adapter.on_startup()

        # play_ambient must NEVER be called automatically
        mock_mgr.play_ambient.assert_not_called()


class TestRobustnessAndConcurrency:
    """Tests for exception isolation, cooldowns, and concurrent safety."""

    def test_backend_exceptions_handled_gracefully(self) -> None:
        """Exceptions in AudioManager are caught safely and return False."""
        mock_mgr = _create_mock_manager(enabled=True)
        mock_mgr.play.side_effect = Exception("Sound hardware disconnected")
        adapter = AudioEventAdapter(mock_mgr)

        assert adapter.on_startup() is False
        assert adapter.on_notification("Test", severity="info") is False
        assert adapter.on_coding_success("test") is False
        assert adapter.on_mood_shift(GhostMood.DORMANT, GhostMood.AMUSED) is False

    def test_cooldown_debounce_behavior(self) -> None:
        """Events adhering to cooldown intervals are debounced."""
        mock_mgr = _create_mock_manager(enabled=True)
        adapter = AudioEventAdapter(mock_mgr)

        assert adapter.on_coding_success("run 1") is True
        # Immediate subsequent call is debounced
        assert adapter.on_coding_success("run 2") is False
        assert mock_mgr.play.call_count == 1

    def test_concurrent_event_dispatch_thread_safety(self) -> None:
        """Concurrent calls from multiple threads do not corrupt internal state."""
        mock_mgr = _create_mock_manager(enabled=True)
        adapter = AudioEventAdapter(mock_mgr)

        def worker(idx: int) -> bool:
            return adapter.on_notification(f"Message {idx}", severity="info")

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(worker, i) for i in range(40)]
            results = [f.result() for f in futures]

        assert any(results)
        # Lock ensured no crashes or unhandled exceptions occurred
        assert mock_mgr.play.call_count > 0

    def test_audio_disabled_app_initialization_no_hardware(self) -> None:
        """With default disabled audio, app initializes with NullAudioBackend and zero sound."""
        settings = Settings(audio_enabled=False)
        app = GhostTraceApp(settings=settings)
        assert app.audio_manager.settings.audio_enabled is False
        assert app.audio_adapter.is_enabled is False

        # Verify on_startup and on_shutdown execute safely
        assert app.audio_adapter.on_startup() is False
        assert app.audio_adapter.on_shutdown() is False
