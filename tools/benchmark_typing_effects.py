"""Performance and latency benchmark for GhostTrace haunted keystrokes (Step 07)."""

from __future__ import annotations

import gc
import threading
import time
import tracemalloc

from ghosttrace.audio.adapter import AudioEventAdapter
from ghosttrace.audio.manager import AudioManager
from ghosttrace.audio.typing_effects import TypingEffectsManager
from ghosttrace.config.settings import Settings


def main() -> int:
    print("=" * 60)
    print("GHOSTTRACE v1.2.0 — STEP 07: KEYSTROKE PERFORMANCE BENCHMARK")
    print("=" * 60)

    tracemalloc.start()
    gc.collect()

    initial_threads = threading.active_count()

    settings = Settings(
        audio_enabled=True,
        audio_haunted_keystrokes_enabled=True,
    )
    mgr = AudioManager(settings=settings)
    adapter = AudioEventAdapter(mgr)
    engine = TypingEffectsManager(audio_manager=mgr, audio_adapter=adapter)

    # 1. Measure raw non-firing keystroke latency (95%+ of typical keystrokes)
    engine.set_experience_mode("normal")
    iterations = 2000
    start_t = time.perf_counter()
    sim_t = 100.0
    for _ in range(iterations):
        sim_t += 0.05
        engine.record_keystroke(now=sim_t)
    total_time = time.perf_counter() - start_t
    avg_keystroke_us = (total_time / iterations) * 1_000_000

    print(f"1. Non-firing throughput   : {iterations:,} calls in {total_time * 1000:.2f} ms")
    ms_str = f"{avg_keystroke_us / 1000:.4f} ms"
    print(f"   Average latency/key     : {avg_keystroke_us:.3f} us ({ms_str})")

    # 2. Measure firing keystroke dispatch latency (when sound triggers)
    firing_engine = TypingEffectsManager(
        audio_manager=mgr,
        random_func=lambda: 0.01,  # Force trigger
    )
    firing_engine.set_experience_mode("haunted")
    # Prime 3 keystrokes to satisfy min_keystrokes
    sim_t = 200.0
    for _ in range(3):
        sim_t += 0.1
        firing_engine.record_keystroke(now=sim_t)

    # Measure dispatch of triggered effect
    t0 = time.perf_counter()
    sim_t += 0.1
    effect = firing_engine.record_keystroke(now=sim_t)
    dispatch_time_ms = (time.perf_counter() - t0) * 1000
    print(f"2. Firing effect dispatch  : {dispatch_time_ms:.4f} ms (Event: {effect})")

    # 3. Thread count audit
    current_threads = threading.active_count()
    extra_threads = current_threads - initial_threads
    print(f"3. Extra worker threads    : {extra_threads} (Target: 0)")

    # 4. Memory overhead
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    cur_kb = current_mem / 1024
    peak_kb = peak_mem / 1024
    print(f"4. Memory overhead         : current={cur_kb:.2f} KB, peak={peak_kb:.2f} KB")

    # 5. Sustained typing burst simulation (500 keys over 10 seconds of simulated time)
    burst_engine = TypingEffectsManager(audio_manager=mgr)
    burst_engine.set_experience_mode("haunted")
    t_burst_start = time.perf_counter()
    for i in range(500):
        burst_engine.record_keystroke(now=300.0 + i * 0.04)
    burst_dur = (time.perf_counter() - t_burst_start) * 1000
    print(f"5. Burst typing throughput (500 keys): {burst_dur:.2f} ms total")

    mgr.shutdown()
    print("\nBenchmark completed cleanly.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    main()
