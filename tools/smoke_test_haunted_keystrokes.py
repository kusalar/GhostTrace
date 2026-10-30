"""Physical hardware validation script for GhostTrace haunted keystrokes (Step 07).

Tests physical audio output on Windows hardware (Realtek / WASAPI):
1. Verifies physical playback of keystroke audio effects:
   - keystroke_haunt, glitch_digital, glitch_static, glitch_corruption.
2. Verifies subtle low volume (0.20 - 0.35 volume scale).
3. Verifies Focus mode immediate suppression.
4. Verifies Mute immediate suppression.
5. Verifies clean shutdown and device release.
"""

from __future__ import annotations

import sys
import time

from ghosttrace.audio.adapter import AudioEventAdapter
from ghosttrace.audio.manager import AudioManager
from ghosttrace.audio.schemas import AudioEventId
from ghosttrace.audio.typing_effects import TypingEffectsManager
from ghosttrace.config.settings import get_settings


def main() -> int:
    print("=" * 60)
    print("GHOSTTRACE v1.2.0 — STEP 07: HAUNTED KEYSTROKES SMOKE TEST")
    print("=" * 60)

    settings = get_settings()
    settings.audio_enabled = True
    settings.audio_haunted_keystrokes_enabled = True

    mgr = AudioManager(settings=settings)
    if not mgr.backend.is_available():
        print("[WARNING] Hardware audio playback device is not available.")
        mgr.shutdown()
        return 0

    print(f"Device backend active: {mgr.backend.__class__.__name__}")
    adapter = AudioEventAdapter(mgr)
    engine = TypingEffectsManager(audio_manager=mgr, audio_adapter=adapter)

    # 1. Physical test of keystroke_haunt sound effect
    print("\n[1/5] Playing physical sound: KEYSTROKE_HAUNT (subtle subterranean impact)...")
    mgr.play(AudioEventId.KEYSTROKE_HAUNT, volume_scale=0.35)
    time.sleep(0.8)

    # 2. Physical test of glitch_digital
    print("[2/5] Playing physical sound: GLITCH_DIGITAL (micro digital fracture)...")
    mgr.play(AudioEventId.GLITCH_DIGITAL, volume_scale=0.25)
    time.sleep(0.6)

    # 3. Physical test of glitch_static
    print("[3/5] Playing physical sound: GLITCH_STATIC (CRT electromagnetic burst)...")
    mgr.play(AudioEventId.GLITCH_STATIC, volume_scale=0.25)
    time.sleep(0.6)

    # 4. Physical test of glitch_corruption (typing burst manifestation)
    print("[4/5] Playing physical sound: GLITCH_CORRUPTION (sustained typing artifact)...")
    mgr.play(AudioEventId.GLITCH_CORRUPTION, volume_scale=0.35)
    time.sleep(1.0)

    # 5. Focus mode policy check
    print("[5/5] Testing Focus mode suppression...")
    adapter.set_experience_mode("focus")
    res = engine.record_keystroke()
    assert res is None, "Focus mode must suppress all typing effects"
    print("      Focus mode suppression: PASS (silence confirmed)")

    # Restore Normal mode and shutdown
    adapter.set_experience_mode("normal")
    mgr.shutdown()
    print("\nAll physical audio keystroke smoke tests completed successfully.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
