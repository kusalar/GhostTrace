"""Manual physical audio smoke-test script for GhostTrace playback verification."""

from __future__ import annotations

import time
from pathlib import Path

from ghosttrace.audio.backend import MiniAudioBackend
from ghosttrace.audio.catalog import AudioCatalog
from ghosttrace.audio.schemas import AudioEventId


def run_audio_smoke_test() -> None:
    """Execute sequence testing real audible sound effects and ambient streaming."""
    audio_dir = Path("assets/audio").resolve()
    catalog = AudioCatalog()

    print("==================================================")
    print(" GhostTrace v1.1.0 — Physical Audio Smoke Test")
    print("==================================================")

    backend = MiniAudioBackend(volume=0.75, ambient_volume=0.35)
    t0 = time.perf_counter()
    init_success = backend.initialize()
    init_duration_ms = (time.perf_counter() - t0) * 1000

    if not init_success:
        print("[FAIL] Could not initialize MiniAudioBackend. No audio device available.")
        return

    status = backend.get_status()
    print(f"[OK] Device Initialized : {status.get('device_name')} in {init_duration_ms:.2f} ms")
    print(f"[OK] Device Running     : {status.get('running')}")

    test_events = [
        (AudioEventId.STARTUP, "Startup sound (Sub-bass swell & resonant chime)", 2.6),
        (AudioEventId.GLITCH_DIGITAL, "Digital glitch (Bit-crushed micro-burst)", 0.5),
        (AudioEventId.WHISPER_SPECTRAL, "Spectral whisper (Formant panning breath)", 2.0),
    ]

    for event_id, description, wait_time in test_events:
        sound = catalog.get_sound(event_id)
        if sound is None:
            print(f"[ERROR] Sound not found in catalog: {event_id}")
            continue

        wav_path = audio_dir / sound.relative_path
        print(f"\n[PLAY] {event_id.value}: {description}")
        t_play = time.perf_counter()
        dispatched = backend.play(wav_path, volume=0.9)
        dispatch_us = (time.perf_counter() - t_play) * 1_000_000
        print(f"       Dispatched in {dispatch_us:.1f} us, waiting {wait_time}s for completion...")
        assert dispatched is True
        time.sleep(wait_time)

    # Test ambient loop & stop behavior
    ambient_sound = catalog.get_sound(AudioEventId.AMBIENT_DARK_HUM)
    if ambient_sound:
        amb_path = audio_dir / ambient_sound.relative_path
        print(f"\n[AMBIENT] Starting ambient loop: {AudioEventId.AMBIENT_DARK_HUM.value} (3.0s)...")
        t_amb = time.perf_counter()
        amb_dispatched = backend.play_ambient(amb_path, volume=0.5)
        amb_dispatch_us = (time.perf_counter() - t_amb) * 1_000_000
        is_active = backend.get_status().get("ambient_playing")
        print(f"          Dispatched in {amb_dispatch_us:.1f} us. Active: {is_active}")
        assert amb_dispatched is True
        time.sleep(3.0)

        print("[AMBIENT] Stopping ambient loop now...")
        backend.stop_ambient()
        time.sleep(0.2)
        assert backend.get_status().get("ambient_playing") is False
        print("[OK] Ambient loop stopped cleanly.")

    print("\n[SHUTDOWN] Releasing audio device...")
    t_shut = time.perf_counter()
    backend.shutdown()
    shut_ms = (time.perf_counter() - t_shut) * 1000
    print(f"[OK] Shutdown completed in {shut_ms:.2f} ms.")
    print("==================================================")
    print(" Physical Audio Smoke Test Completed Successfully!")
    print("==================================================")


if __name__ == "__main__":
    run_audio_smoke_test()
