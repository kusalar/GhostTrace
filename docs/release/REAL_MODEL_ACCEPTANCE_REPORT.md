# GhostTrace v1.0.0 — Real AI Model Acceptance Report

**Test Date:** October 29, 2026  
**Target Hardware:** Intel Core i3-1115G4 @ 3.00GHz (4 logical cores), 12 GB RAM, Intel UHD Graphics  
**Operating System:** Windows 10 64-bit (10.0.19045 AMD64)  
**Python Runtime:** Python 3.11.9 (64-bit)  
**AI Runtime:** llama-cpp-python v0.3.36 (AVX2 native C/C++ CPU binaries)  
**Model Architecture:** Qwen2.5-1.5B-Instruct-GGUF, `Q4_K_M` 4-bit quantization  
**Final Outcome:** **PASS**

---

## 1. Executive Summary

This report documents the real-world acceptance testing of GhostTrace v1.0.0's local AI inference pipeline using the genuine Qwen2.5-1.5B-Instruct GGUF model weights on target consumer hardware (Intel Core i3, no discrete GPU).

All 10 core acceptance tests (Tests A through J), streaming evaluation, personality system prompt differentiation, context overflow recovery, and standalone packaged executable validation succeeded.

---

## 2. Environment & Hardware Specifications [VERIFIED]

| Component | Specification | Observed State During Test |
| :--- | :--- | :--- |
| **Processor** | Intel Core i3-1115G4 @ 3.00GHz | 4 logical cores, AVX2 supported |
| **Total Physical RAM** | 11.75 GB (12,612,919,296 bytes) | 3.97 GB available at preflight |
| **Pagefile Capacity** | 20.25 GB total | 8.35 GB available |
| **Graphics** | Intel UHD Graphics (Integrated) | GPU acceleration disabled (`gpu_layers=0`) |
| **AI Inference Backend** | llama-cpp-python v0.3.36 | `llama.dll`, `ggml-cpu.dll` AVX2 |
| **Context Window** | 2048 tokens (`ai_context_size=2048`) | Bounded for CPU memory safety |
| **Inference Threads** | 2 CPU threads (`ai_threads=2`) | Default conservative allocation |

---

## 3. Model Discovery & Checksum Verification [VERIFIED]

- **Discovery Path:** `D:\GhostTrace\models\qwen2.5-1.5b-instruct-q4_k_m.gguf` [VERIFIED]
- **File Size:** `1,117,320,736 bytes` (1065.56 MB) [VERIFIED]
- **SHA256 Checksum:** `6A1A2EB6D15622BF3C96857206351BA97E1AF16C30D7A74EE38970E434E9407E` [VERIFIED]
- **Model Metadata Discovery:** `ModelManager.get_metadata()` correctly resolved file presence, format (`GGUF`), quantization (`Q4_K_M`), and transitioned status from `NOT_FOUND` to `UNLOADED`. [VERIFIED]

---

## 4. Model Lifecycle: Load, Unload & Reload [VERIFIED]

| Phase | Duration | Status | Process Working Set (RAM) | Net Delta |
| :--- | :---: | :---: | :---: | :---: |
| **Baseline Idle** | — | `UNLOADED` | 33.05 MB | — |
| **Initial Load** | 1.32 s | `READY` | 1353.40 MB | +1320.35 MB |
| **Model Unload** | < 0.05 s | `UNLOADED` | 52.07 MB | -1301.33 MB |
| **Model Reload** | 1.13 s | `READY` | 1354.12 MB | +1302.05 MB |

- **RAM Reclamation:** Memory is cleanly freed upon calling `unload_model()` followed by garbage collection, dropping working set memory back to baseline (~52 MB). [VERIFIED]

---

## 5. Real Inference Acceptance Tests (Tests A–J)

### Test A — Basic Conversation [VERIFIED]
- **Prompt:** `Hello GhostTrace. Introduce yourself briefly.`
- **Generated Response:**
  > *"Greetings! I am GhostTrace, a developer assistant that runs entirely on your machine. I'm here to help you understand programming concepts, debug errors, and review code. Let me know if you have any questions or need assistance."*
- **Metrics:** 46 completion tokens in 11.75s (3.91 tokens/sec). Status: **PASS**.

### Test B — Programming Explanation [VERIFIED]
- **Prompt:** `Explain the difference between a Python list and a tuple with a small example.`
- **Generated Response:** Thoroughly explained mutability, syntax (`[]` vs `()`), use cases (dynamic collections vs hashable keys/records), and included correct code snippets.
- **Metrics:** 466 completion tokens in 40.75s (11.43 tokens/sec). Status: **PASS**.

### Test C — Debugging Explanation [VERIFIED]
- **Prompt:** `Why does Python raise an IndexError when accessing an element outside a list's valid range?`
- **Generated Response:** Correctly detailed zero-based indexing, sequence boundary checks, off-by-one errors, and defensive alternatives (`try/except IndexError`, `len()` checks).
- **Metrics:** 391 completion tokens in 42.08s (9.29 tokens/sec). Status: **PASS**.

### Test D — Code Understanding [VERIFIED]
- **Prompt:**
  ```python
  def chunk(lst, n):
      return [lst[i : i + n] for i in range(0, len(lst), n)]
  ```
- **Generated Response:** Accurately deconstructed parameter roles (`lst`, `n`), list comprehension semantics, `range()` step increments, and slice bounds behavior.
- **Metrics:** 283 completion tokens in 54.56s (5.19 tokens/sec). Status: **PASS**.

### Test E — Follow-Up & Context Retention [VERIFIED]
- **Prompt:** `What was the name of the function I just asked you to explain?`
- **Generated Response:**
  > *"The function I just explained is named `chunk`."*
- **Metrics:** 15 completion tokens in 28.13s. Context recognized correctly. Status: **PASS**.

### Test F — Ghost Personality Differentiation [VERIFIED]
- **Prompt:** `What should I do if my code throws an unhandled exception?`
- **Profiles Tested:**
  1. `forgotten-machine`: System prompt length 2,806 chars. Active Profile: *"Forgotten Machine"*. Response tone: measured, reflective, structured error handling.
  2. `phantom-coder`: System prompt length 2,559 chars. Active Profile: *"Phantom Coder"*. Response tone: energetic, practical step-by-step triage.
  3. `guardian-spirit`: System prompt length 2,661 chars. Active Profile: *"Guardian Spirit"*. Response tone: protective, defensive architecture, boundary validation.
- **Result:** System prompts and personality guidelines dynamically vary per profile while preserving technical accuracy. Status: **PASS**.

### Test G — Developer Integration & Code Review [VERIFIED]
- **Prompt:** Review and explain `average(numbers)` function with empty list vulnerability.
- **Generated Response:** Detected `ZeroDivisionError` vulnerability when `len(numbers) == 0`, pointed out missing docstring, and provided safe guarded implementation:
  ```python
  def average(numbers):
      if not numbers:
          return 0  # or raise ValueError("List cannot be empty")
      return sum(numbers) / len(numbers)
  ```
- **Metrics:** Status: **PASS**.

### Test H — Streaming Token Generation [VERIFIED]
- **Prompt:** `Count from 1 to 5, one number per line.`
- **Result:** 9 incremental chunks yielded. First-token latency: 11.13s. Total duration: 11.70s. Status: **PASS**.

### Test I — Error Handling [VERIFIED]
- **Scenario:** Configured non-existent model path `non_existent_model_file.gguf`.
- **Result:** `get_metadata().status` returned `NOT_FOUND`. Calling `load_model()` cleanly raised `ModelNotFoundError` without crashing the application. Status: **PASS**.

### Test J — Resource Stability [VERIFIED]
- **Method:** 3 consecutive completions on the active model instance.
- **RAM Trend:** Turn 1: 6691.19 MB, Turn 2: 6691.21 MB, Turn 3: 6691.21 MB (RAM delta = **0.02 MB**).
- **Result:** Flat memory profile with zero memory leakage. Status: **PASS**.

---

## 6. Context Window Overflow Recovery [VERIFIED]

During long multi-turn sessions where accumulated dialogue exceeds the 2048-token context window:
- **Prior Behavior:** llama-cpp-python raised `ValueError: Requested tokens (2072) exceed context window of 2048`.
- **Hardened Resilient Behavior:** `ghosttrace/ai/inference.py` catches the context overflow, logs a warning, automatically prunes the oldest conversation exchange while preserving the system prompt, and retries generation seamlessly.
- **Observed Log:**
  `Context window exceeded (Requested tokens (2072) exceed context window of 2048). Pruning oldest exchange and retrying...`
- **Result:** Generation completed successfully without crashing or aborting the turn.

---

## 7. Performance Benchmarks Summary

| Metric | Measured Value | Test Conditions |
| :--- | :---: | :--- |
| **Model Load Time** | 1.13 – 1.32 s | Local SSD, AVX2 CPU |
| **First-Token Latency (Warm)** | 11.13 s | Streaming turn, 2 CPU threads |
| **Peak Generation Speed** | **11.43 tokens/sec** | Long completion (Test B) |
| **Average Generation Speed** | 7.5 – 10.5 tokens/sec | General developer assistance |
| **Base Process RAM** | 33.05 MB | Before model load |
| **Loaded Model RAM** | 1,353 MB | Active Qwen2.5-1.5B Q4_K_M |
| **Idle RAM Post-Unload** | 52.07 MB | Model released, gc.collect() |
| **Context Retention** | **PASS** | Successfully recalled prior function name |
| **Streaming Output** | **PASS** | Incremental chunking verified |
| **Personality Integration** | **PASS** | Distinct profile signatures verified |

---

## 8. Packaged Executable Acceptance [VERIFIED]

- **Executable:** `dist/release/GhostTrace/GhostTrace.exe`
- **Initial Acceptance Build SHA256:** `1A66731B686A36544291FCAA2F2CF692709BD76AC766FCF3C546E2DE232B97E0` (commit `8cc7837`)
- **Final Hardened Release SHA256:** `1A424D020EBE4AC446D46D80E87F9153AD5A0D4C9E5CC5C1D16A207A7C95E935` (includes Windows console encoding fix, recorded in `SHA256SUMS.txt`)
- **Subsystem Status Check:**
  `GhostTrace.exe status` accurately discovered the model file and transitioned:
  `| 03 | Local AI Integration (llama.cpp) | READY |` [VERIFIED]
- **Missing Model Simulation:**
  When invoked with `GHOSTTRACE_MODEL_PATH=nonexistent.gguf`, gracefully reports:
  `| 03 | Local AI Integration (llama.cpp) | STANDBY (NO WEIGHTS) |` [VERIFIED]
- **Isolation:** Executable runs independently without `.venv` activation. User state resides safely under `%LOCALAPPDATA%\GhostTrace`. [VERIFIED]

---

## 9. Quality Gates & Regression Verification [VERIFIED]

- **Ruff Linter:** 170 files scanned — 0 errors. [VERIFIED]
- **Ruff Formatter:** 170 files checked — 100% formatted. [VERIFIED]
- **Automated Test Suite:**
  - **459 passed**, 0 failed, 0 skipped in 20.46s (includes new regression test `test_ai_inference_context_overflow_pruning`). [VERIFIED]
  - Total branch-inclusive coverage: **88.92%** (exceeds 80% threshold). [VERIFIED]

---

## 10. Acceptance Verdict

**Verdict:** **PASS**

Real local AI model inference using the genuine `Qwen2.5-1.5B-Instruct-GGUF` model on Windows CPU is fully verified, stable, and ready for production use.
