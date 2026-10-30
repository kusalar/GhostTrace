"""Benchmark script measuring HorrorAudioDirector latency and resource efficiency."""

from __future__ import annotations

import sys
import threading
import time
import tracemalloc

from ghosttrace.audio.horror_director import HorrorAudioDirector
from ghosttrace.audio.schemas import AudioEventId
from ghosttrace.config.settings import Settings


def main() -> int:
    print("=================================================================")
    print(" GhostTrace v1.2.0 Step 09 — Horror Audio Director Benchmark")
    print("=================================================================")

    tracemalloc.start()

    initial_threads = threading.active_count()
    settings = Settings(audio_enabled=True, audio_dynamic_horror_enabled=True)
    director = HorrorAudioDirector(settings=settings, experience_mode="haunted")
    director.set_enabled(True)

    # 1. Benchmark policy evaluation throughput
    iterations = 10000
    clock = 1000.0
    start_t = time.perf_counter()
    for _ in range(iterations):
        director.can_dispatch(AudioEventId.GLITCH_DIGITAL, now=clock)
    eval_elapsed = time.perf_counter() - start_t
    us_per_eval = (eval_elapsed / iterations) * 1_000_000.0

    print(f"Policy evaluation: {iterations} checks in {eval_elapsed * 1000.0:.2f} ms")
    print(f"Latency per check: {us_per_eval:.3f} microseconds / evaluation")

    # 2. Benchmark intensity computation
    start_t = time.perf_counter()
    for i in range(iterations):
        director.compute_intensity(now=clock + (i * 0.1))
    calc_elapsed = time.perf_counter() - start_t
    us_per_calc = (calc_elapsed / iterations) * 1_000_000.0

    print(f"Intensity calculation: {iterations} in {calc_elapsed * 1000.0:.2f} ms")
    print(f"Latency per calc : {us_per_calc:.3f} microseconds / calculation")

    # 3. Thread verification
    current_threads = threading.active_count()
    extra_threads = current_threads - initial_threads
    print(f"Persistent background worker threads created: {extra_threads}")

    # 4. Memory overhead
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(
        f"Memory overhead: current={current_mem / 1024.0:.2f} KB, peak={peak_mem / 1024.0:.2f} KB"
    )

    print("=================================================================")
    if us_per_eval < 100.0 and extra_threads == 0:
        print(" [PASS] Performance and resource budgets fully satisfied!")
        return 0
    else:
        print(" [WARN] Performance limits exceeded.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
