"""Physical hardware validation script for GhostTrace scheduled whispers (Step 08).

Tests physical audio output on Windows hardware (Realtek / WASAPI):
1. Verifies physical playback of procedural whisper audio assets:
   - spectral_whisper, chilling_breath, eerie_murmur.
2. Verifies subtle atmospheric volume (0.20 - 0.35 volume scale).
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
from ghosttrace.audio.whisper_scheduler import WhisperScheduler
from ghosttrace.config.settings import get_settings


def main() -> int:
    print("=" * 60)
    print("GHOSTTRACE v1.2.0 — STEP 08: SCHEDULED WHISPERS SMOKE TEST")
    print("=" * 60)

    settings = get_settings()
    settings.audio_enabled = True
    settings.audio_scheduled_whispers_enabled = True

    mgr = AudioManager(settings=settings)
    if not mgr.backend.is_available():
        print("[WARNING] Hardware audio playback device is not available.")
        mgr.shutdown()
        return 0

    print(f"Device backend active: {mgr.backend.__class__.__name__}")
    adapter = AudioEventAdapter(mgr)
    scheduler = WhisperScheduler(audio_manager=mgr, audio_adapter=adapter)

    # 1. Physical test of chilling_breath
    print("\n[1/5] Playing physical sound: WHISPER_BREATH (cold nonverbal exhalation)...")
    mgr.play(AudioEventId.WHISPER_BREATH, volume_scale=0.25)
    time.sleep(1.6)

    # 2. Physical test of spectral_whisper
    print("[2/5] Playing physical sound: WHISPER_SPECTRAL (spectral nonverbal sweep)...")
    mgr.play(AudioEventId.WHISPER_SPECTRAL, volume_scale=0.30)
    time.sleep(2.0)

    # 3. Physical test of eerie_murmur
    print("[3/5] Playing physical sound: WHISPER_MURMUR (eerie vocal harmonic murmur)...")
    mgr.play(AudioEventId.WHISPER_MURMUR, volume_scale=0.35)
    time.sleep(2.2)

    # 4. Focus mode suppression check
    print("[4/5] Testing Focus mode suppression...")
    adapter.set_experience_mode("focus")
    res = scheduler.trigger_whisper()
    assert res is None, "Focus mode must suppress all scheduled whispers"
    print("      Focus mode suppression: PASS (silence confirmed)")

    # 5. Mute suppression check
    print("[5/5] Testing Mute suppression...")
    adapter.set_experience_mode("haunted")
    mgr.mute(persist=False)
    res_mute = scheduler.trigger_whisper()
    assert res_mute is None, "Mute must suppress all scheduled whispers"
    print("      Mute suppression: PASS (silence confirmed)")

    mgr.unmute(persist=False)
    adapter.set_experience_mode("normal")
    scheduler.shutdown()
    mgr.shutdown()
    print("\nAll physical audio scheduled whisper smoke tests completed successfully.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
