"""Physical host hardware verification script for Dynamic Horror Director (v1.2.0 Step 09).

Tests real device playback, volume scaling, intensity changes, conflict prevention,
Focus mode silence, and clean shutdown on Windows audio hardware.
"""

from __future__ import annotations

import sys
import time

from ghosttrace.audio.adapter import AudioEventAdapter
from ghosttrace.audio.horror_director import (
    AudioPriority,
    HorrorAudioDirector,
    HorrorIntensity,
)
from ghosttrace.audio.manager import AudioManager
from ghosttrace.audio.schemas import AudioEventId
from ghosttrace.config.settings import Settings


def main() -> int:
    print("=================================================================")
    print(" GhostTrace v1.2.0 Step 09 — Dynamic Horror Director Smoke Test")
    print("=================================================================")

    settings = Settings(
        audio_enabled=True,
        audio_volume=0.35,
        audio_dynamic_horror_enabled=False,
    )
    mgr = AudioManager(settings=settings)

    if not mgr.backend.is_available():
        print("[SKIP] No audio output device available on this host.")
        mgr.shutdown()
        return 0

    status = mgr.get_status()
    print(f"Backend: {status.backend_type} (device ready: {status.backend_available})")
    print(f"Initial State: dynamic_horror={status.dynamic_horror_enabled}")

    # 1. Test standard application audio when dynamic horror is disabled (default)
    print("\n--- Test 1: Standard Application Sounds (Director Disabled) ---")
    director = HorrorAudioDirector(audio_manager=mgr, settings=settings)
    adapter = AudioEventAdapter(mgr, horror_director=director)

    print("Playing startup sound...")
    res = adapter.on_startup()
    print(f"Startup dispatched: {res}")
    time.sleep(1.2)

    # 2. Enable dynamic horror orchestration
    print("\n--- Test 2: Enable Dynamic Horror Orchestration ---")
    director.set_enabled(True)
    mgr.set_dynamic_horror(True, persist=False)
    print(f"Director is_enabled: {director.is_enabled}")
    assert director.is_enabled is True

    # 3. Test experience modes and intensity calibration
    print("\n--- Test 3: Experience Modes & Intensity Calibration ---")
    for mode in ("normal", "ambient", "haunted", "focus"):
        director.set_experience_mode(mode)
        intensity = director.compute_intensity()
        print(f"Mode: {mode.upper():<8} -> Base Intensity: {intensity.value.upper()}")
        if mode == "focus":
            assert intensity == HorrorIntensity.DORMANT

    # 4. Test atmospheric dispatch in Haunted mode
    print("\n--- Test 4: Audible Atmospheric Manifestation (Haunted Mode) ---")
    director.set_experience_mode("haunted")
    # Record sustained typing activity to escalate intensity to HAUNTED
    for _ in range(5):
        director.record_typing_activity()

    intensity = director.compute_intensity()
    print(f"Escalated Intensity: {intensity.value.upper()}")
    assert intensity == HorrorIntensity.HAUNTED

    print("Playing glitch sound through director...")
    dispatched_glitch = director.dispatch_event(AudioEventId.GLITCH_DIGITAL, volume_scale=0.5)
    print(f"Glitch dispatched: {dispatched_glitch}")
    time.sleep(2.5)

    # 5. Test cross-system conflict prevention (whisper vs typing)
    print("\n--- Test 5: Conflict Prevention (Whisper vs Typing Collisions) ---")
    print("Playing whisper sound through director...")
    t_now = time.monotonic()
    whisper_res = director.dispatch_event(AudioEventId.WHISPER_BREATH, volume_scale=0.4, now=t_now)
    print(f"Whisper dispatched: {whisper_res}")

    # Immediate typing keystroke attempt within collision window must be rejected
    can_type, reason = director.can_dispatch(AudioEventId.KEYSTROKE_HAUNT, now=t_now + 0.5)
    print(f"Immediate typing attempt: allowed={can_type}, reason={reason}")
    assert can_type is False
    assert reason == "whisper_collision"
    time.sleep(1.5)

    # 6. Test Focus Mode Silence
    print("\n--- Test 6: Focus Mode Absolute Atmospheric Suppression ---")
    director.set_experience_mode("focus")
    can_whisper, w_reason = director.can_dispatch(AudioEventId.WHISPER_SPECTRAL)
    print(f"Focus whisper attempt: allowed={can_whisper}, reason={w_reason}")
    assert can_whisper is False
    assert w_reason == "focus_mode"

    # Guardian sounds must still work in Focus mode
    can_guard, _ = director.can_dispatch(AudioEventId.GUARDIAN_INTERCEPT)
    print(f"Focus Guardian attempt: allowed={can_guard}, priority={AudioPriority.CRITICAL.name}")
    assert can_guard is True

    # 7. Test Mute Silence
    print("\n--- Test 7: Master Mute Silence ---")
    mgr.mute(persist=False)
    can_guard_muted, m_reason = director.can_dispatch(AudioEventId.GUARDIAN_INTERCEPT)
    print(f"Muted Guardian attempt: allowed={can_guard_muted}, reason={m_reason}")
    assert can_guard_muted is False
    assert m_reason == "audio_muted"
    mgr.unmute(persist=False)

    # 8. Clean Shutdown
    print("\n--- Test 8: Clean Director & Adapter Teardown ---")
    adapter.on_shutdown()
    mgr.shutdown()
    print("Shutdown complete. All resources released cleanly.")
    print("=================================================================")
    print(" [PASS] Physical host hardware validation successful!")
    print("=================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
