"""Manual physical smoke test for application event audio integration (Step 04)."""

from __future__ import annotations

import time

from ghosttrace.audio.adapter import AudioEventAdapter, NotificationSeverity
from ghosttrace.audio.manager import AudioManager
from ghosttrace.config.settings import Settings
from ghosttrace.ghost.schemas import GhostMood


def run_event_audio_smoke_test() -> None:
    """Execute end-to-end event audio integration smoke test on host audio hardware."""
    print("==================================================")
    print(" GhostTrace v1.1.0 — Step 04 Event Audio Smoke Test")
    print("==================================================")

    # 1. Disabled audio verification
    print("\n--- Phase 1: Disabled Audio Verification ---")
    silent_settings = Settings(audio_enabled=False)
    silent_mgr = AudioManager(settings=silent_settings)
    silent_adapter = AudioEventAdapter(silent_mgr)
    assert not silent_adapter.is_enabled, "Adapter should report disabled"
    assert not silent_adapter.on_startup(), "Disabled startup must return False"
    assert not silent_adapter.on_notification("Test", severity="warning"), "Disabled notification"
    assert not silent_adapter.on_guardian_intercept("rm -rf /"), "Disabled intercept"
    assert not silent_adapter.on_shutdown(), "Disabled shutdown"
    status = silent_mgr.get_status()
    print(f"[OK] Audio Disabled Mode: backend={status.backend_type}, device_init=False")

    # 2. Enabled audio physical verification
    print("\n--- Phase 2: Physical Hardware Audio Event Playback ---")
    enabled_settings = Settings(audio_enabled=True, audio_volume=0.8)
    mgr = AudioManager(settings=enabled_settings)
    adapter = AudioEventAdapter(mgr)

    if not mgr.backend.is_available():
        print("[SKIP] Physical audio hardware not accessible in this environment.")
        return

    backend_status = mgr.backend.get_status()
    device_name = backend_status.get("device_name", "Unknown Device")
    print(f"[OK] Audio Hardware Ready: {device_name}")

    # Sequence of semantic application events
    print("\n[EVENT 1] Application Startup -> startup.wav")
    t0 = time.perf_counter()
    assert adapter.on_startup(), "Startup event must dispatch"
    us = (time.perf_counter() - t0) * 1_000_000
    print(f"         Dispatched in {us:.1f} us. Listening to startup chime (1.5s)...")
    time.sleep(1.5)

    print("\n[EVENT 2] Important Notification -> notification_alert.wav")
    t0 = time.perf_counter()
    assert adapter.on_notification("High Risk Alert", severity=NotificationSeverity.WARNING)
    us = (time.perf_counter() - t0) * 1_000_000
    print(f"         Dispatched in {us:.1f} us. Listening to alert bell (1.0s)...")
    time.sleep(1.0)

    print("\n[EVENT 3] Ordinary Notification -> notification_ping.wav")
    t0 = time.perf_counter()
    assert adapter.on_notification("Session restored", severity="info")
    us = (time.perf_counter() - t0) * 1_000_000
    print(f"         Dispatched in {us:.1f} us. Listening to ping (0.8s)...")
    time.sleep(0.8)

    print("\n[EVENT 4] Guardian Intercept -> guardian_intercept.wav")
    t0 = time.perf_counter()
    assert adapter.on_guardian_intercept("format c:")
    us = (time.perf_counter() - t0) * 1_000_000
    print(f"         Dispatched in {us:.1f} us. Listening to clamp (1.0s)...")
    time.sleep(1.0)

    print("\n[EVENT 5] Guardian Approved -> guardian_approved.wav")
    t0 = time.perf_counter()
    assert adapter.on_guardian_approved("token-safe-123")
    us = (time.perf_counter() - t0) * 1_000_000
    print(f"         Dispatched in {us:.1f} us. Listening to release latch (0.8s)...")
    time.sleep(0.8)

    print("\n[EVENT 6] Guardian Blocked -> guardian_blocked.wav")
    t0 = time.perf_counter()
    assert adapter.on_guardian_blocked("token-danger-456", "User rejected")
    us = (time.perf_counter() - t0) * 1_000_000
    print(f"         Dispatched in {us:.1f} us. Listening to barricade clang (0.8s)...")
    time.sleep(0.8)

    print("\n[EVENT 7] Developer Coding Success -> coding_success.wav")
    t0 = time.perf_counter()
    assert adapter.on_coding_success("dev generate")
    us = (time.perf_counter() - t0) * 1_000_000
    print(f"         Dispatched in {us:.1f} us. Listening to ethereal chord (1.2s)...")
    time.sleep(1.2)

    print("\n[EVENT 8] Ghost Persona Mood Shift -> mood_shift.wav")
    t0 = time.perf_counter()
    assert adapter.on_mood_shift(GhostMood.DORMANT, GhostMood.CURIOUS)
    us = (time.perf_counter() - t0) * 1_000_000
    print(f"         Dispatched in {us:.1f} us. Listening to atmospheric shift (1.0s)...")
    time.sleep(1.0)

    print("\n[EVENT 9] Application Shutdown -> shutdown.wav")
    t0 = time.perf_counter()
    assert adapter.on_shutdown()
    us = (time.perf_counter() - t0) * 1_000_000
    print(f"         Dispatched in {us:.1f} us. Listening to power-down stinger (1.5s)...")
    time.sleep(1.5)

    print("\n==================================================")
    print(" [SUCCESS] Physical event audio smoke test completed!")
    print("==================================================")


if __name__ == "__main__":
    run_event_audio_smoke_test()
