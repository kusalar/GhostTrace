"""Performance and overhead benchmark for GhostTrace scheduled whispers (Step 08)."""

from __future__ import annotations

import gc
import threading
import time
import tracemalloc

from ghosttrace.audio.adapter import AudioEventAdapter
from ghosttrace.audio.manager import AudioManager
from ghosttrace.audio.whisper_scheduler import WhisperScheduler
from ghosttrace.config.settings import Settings


def main() -> int:
    print("=" * 60)
    print("GHOSTTRACE v1.2.0 — STEP 08: WHISPER SCHEDULER BENCHMARK")
    print("=" * 60)

    tracemalloc.start()
    gc.collect()

    initial_threads = threading.active_count()

    settings = Settings(
        audio_enabled=True,
        audio_scheduled_whispers_enabled=True,
    )
    mgr = AudioManager(settings=settings)
    adapter = AudioEventAdapter(mgr)
    scheduler = WhisperScheduler(audio_manager=mgr, audio_adapter=adapter)

    # 1. Measure can_play_whisper() check throughput
    iterations = 5000
    t0 = time.perf_counter()
    for _ in range(iterations):
        scheduler.can_play_whisper(now=1000.0)
    dur = time.perf_counter() - t0
    avg_us = (dur / iterations) * 1_000_000
    ms_str = f"{avg_us / 1000:.4f} ms"
    print(f"1. Policy check throughput  : {iterations:,} checks in {dur * 1000:.2f} ms")
    print(f"   Average check latency    : {avg_us:.3f} us ({ms_str})")

    # 2. Measure interval calculation throughput
    t0 = time.perf_counter()
    for _ in range(iterations):
        scheduler.calculate_next_interval("haunted")
    dur_calc = time.perf_counter() - t0
    avg_calc_us = (dur_calc / iterations) * 1_000_000
    ms_calc_str = f"{avg_calc_us / 1000:.4f} ms"
    print(f"2. Interval calc throughput : {iterations:,} calls in {dur_calc * 1000:.2f} ms")
    print(f"   Average calc latency     : {avg_calc_us:.3f} us ({ms_calc_str})")

    # 3. Thread count audit
    current_threads = threading.active_count()
    extra_threads = current_threads - initial_threads
    print(f"3. Extra worker threads     : {extra_threads} (Target: 0)")

    # 4. Memory overhead
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    cur_kb = current_mem / 1024
    peak_kb = peak_mem / 1024
    print(f"4. Memory overhead          : current={cur_kb:.2f} KB, peak={peak_kb:.2f} KB")

    # 5. Measure whisper dispatch latency (playback initialization)
    t0 = time.perf_counter()
    event = scheduler.trigger_whisper(now=5000.0)
    dispatch_time_ms = (time.perf_counter() - t0) * 1000
    print(f"5. Firing whisper dispatch  : {dispatch_time_ms:.4f} ms (Event: {event})")

    mgr.shutdown()
    print("\nBenchmark completed cleanly.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    main()
