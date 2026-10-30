# GhostTrace Audio Subsystem Architecture

> **Release:** GhostTrace v1.1.0  
> **Milestone:** Step 04 / 10 — Application Event Audio Integration  
> **Status:** Event Integration Implemented & Verified (Audio Controls Deferred to Step 05)

---

## 1. Architectural Vision & Scope

GhostTrace features an optional, local-only **Dark Horror sound-effects subsystem** designed to provide eerie atmosphere and responsive auditory feedback for terminal actions without impeding developer productivity or local inference performance.

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        GhostTrace Interactive TUI                      │
│            (GhostTraceApp, ConversationLog, CommandInput)              │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ triggers
┌───────────────────────────────────▼────────────────────────────────────┐
│                             AudioManager                               │
│       - Settings integration (GHOSTTRACE_AUDIO_*)                      │
│       - Audio Catalog (Taxonomy, Asset Metadata)                       │
│       - Safe fallback to NullAudioBackend on error                     │
│       - Idempotent lifecycle (init / shutdown)                         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ delegates
┌───────────────────────────────────▼────────────────────────────────────┐
│                         AudioBackend (Protocol)                        │
│            ┌──────────────────────────────────────────────┐            │
│            │ NullAudioBackend (Safe, Silent No-Op)        │            │
│            │  - Default when GHOSTTRACE_AUDIO_ENABLED=false│           │
│            │  - Zero hardware initialization              │            │
│            │  - Zero native library dependencies          │            │
│            └──────────────────────────────────────────────┘            │
│            ┌──────────────────────────────────────────────┐            │
│            │ MiniAudioBackend (Windows Native Audio)      │            │
│            │  - Lightweight miniaudio (WASAPI/DirectSound)│            │
│            │  - 8-Voice Polyphonic Software Mixer         │            │
│            │  - Singleton Ambient Looping Track           │            │
│            │  - In-memory 16-bit PCM sample cache         │            │
│            │  - Zero-blocking asynchronous execution      │            │
│            └──────────────────────────────────────────────┘            │
└────────────────────────────────────────────────────────────────────────┘
```

### Strict Non-Functional Guarantees
1. **Sound Effects Only:** No AI speech, no text-to-speech (TTS), no voice acting. Ghost whispers are strictly nonverbal acoustic sound effects (breaths, sibilance, eerie vocal harmonics).
2. **Zero Interference with TUI:** Audio operations are decoupled and asynchronous; they never block Textual layout, frame rendering, keyboard input, or terminal scrolling.
3. **Zero Impact on Inference:** Audio mixing occurs in lightweight callback slices (~80ms buffer), consuming negligible CPU overhead and leaving threads and RAM entirely dedicated to the local Qwen GGUF model and Command Guardian.
4. **Disabled by Default:** `GHOSTTRACE_AUDIO_ENABLED=false` by default. Existing v1.0.0 installations retain 100% identical behavior.

---

## 2. Configuration & Environment Variables

All audio configuration parameters follow existing `GHOSTTRACE_*` environment variable conventions:

| Environment Variable | Setting Field | Default | Allowed Values | Description |
|---|---|---|---|---|
| `GHOSTTRACE_AUDIO_ENABLED` | `audio_enabled` | `false` | `true`, `false` | Master toggle for the entire audio subsystem. |
| `GHOSTTRACE_AUDIO_VOLUME` | `audio_volume` | `0.5` | `0.0` to `1.0` | Master output volume for all sound effects. |
| `GHOSTTRACE_AUDIO_AMBIENT_ENABLED` | `audio_ambient_enabled` | `false` | `true`, `false` | Enable/disable subtle background ambient horror loop. |
| `GHOSTTRACE_AUDIO_AMBIENT_VOLUME` | `audio_ambient_volume` | `0.2` | `0.0` to `1.0` | Volume scaling for looping ambient soundscapes. |
| `GHOSTTRACE_AUDIO_ASSET_DIR` | `audio_asset_dir` | `assets/audio` | Absolute / relative path | Directory containing local audio files. |

Volume values are strictly validated at instantiation; values outside `[0.0, 1.0]` raise a descriptive `ValidationError` or `InvalidVolumeError`.

---

## 3. Core Component Responsibilities

| Component | Module | Responsibility |
|---|---|---|
| `AudioManager` | [`ghosttrace.audio.manager`](file:///d:/GhostTrace/ghosttrace/audio/manager.py) | High-level orchestrator; manages active backend, tracks volume and mute states, resolves on-disk asset files, and coordinates shutdown. |
| `AudioBackend` | [`ghosttrace.audio.backend`](file:///d:/GhostTrace/ghosttrace/audio/backend.py) | Abstract interface defining hardware initialization, asset playback, ambient streaming, volume scaling, and teardown. |
| `MiniAudioBackend` | [`ghosttrace.audio.backend`](file:///d:/GhostTrace/ghosttrace/audio/backend.py) | Concrete Windows playback engine utilizing `miniaudio`. Manages 8-voice polyphony, singleton ambient loop, in-memory sample caching, and device lifecycle. |
| `NullAudioBackend` | [`ghosttrace.audio.backend`](file:///d:/GhostTrace/ghosttrace/audio/backend.py) | Safe, silent no-op implementation. Active whenever audio is disabled or hardware initialization fails. |
| `AudioCatalog` | [`ghosttrace.audio.catalog`](file:///d:/GhostTrace/ghosttrace/audio/catalog.py) | Declarative registry mapping canonical `AudioEventId` values to `SoundEffect` models with relative file paths and descriptive metadata. |
| `AudioStatus` | [`ghosttrace.audio.schemas`](file:///d:/GhostTrace/ghosttrace/audio/schemas.py) | Pydantic telemetry model reporting operational state, backend type, asset directory status, ambient playing state, and active voice counts. |
| `AudioError` | [`ghosttrace.audio.exceptions`](file:///d:/GhostTrace/ghosttrace/audio/exceptions.py) | Domain exception hierarchy (`AudioInitializationError`, `AudioDisabledError`, `AssetNotFoundError`, `InvalidVolumeError`). |

---

## 4. Playback Backend Selection & Rationale

### Evaluated Alternatives
- **`winsound` (Standard Library):** Only supports mono synchronous playback, blocks caller threads, allows only ONE sound at a time, has no volume control, and cannot mix ambient loops with sound effects.
- **`sounddevice` / `PyAudio`:** Requires heavy external PortAudio C libraries, complicated Windows wheel building, and significant runtime memory footprint.
- **`pygame` / `pygame-ce`:** Pulls in massive multimedia dependencies (SDL2, SDL_mixer, display systems, font engines) inappropriate for a lightweight terminal companion.
- **`miniaudio` (Selected):**
  - Ultra-lightweight (~274 KB single wheel).
  - Native Windows WASAPI / DirectSound support without external DLLs.
  - Zero-latency multi-channel PCM streaming.
  - Clean PyInstaller compilation.
  - Pinned in `pyproject.toml` as `miniaudio>=1.59.0,<2.0.0`.

---

## 5. Playback Concurrency & Lifecycle Architecture

1. **Polyphonic Voice Mixing:**
   - Supports up to 8 concurrent short sound effects.
   - If voice limit is reached, the oldest or closest-to-completion voice is cleanly evicted.
2. **Singleton Ambient Stream:**
   - Loopable ambient tracks (`ambient_dark_hum`, `ambient_cold_wind`, `ambient_distant_thunder`) stream continuously with modular wraparound.
   - Only ONE ambient track can play at a time; starting a new ambient track seamlessly replaces the active loop with zero duplication.
3. **In-Memory PCM Cache:**
   - Sound assets are loaded into RAM once as 16-bit 44.1 kHz stereo arrays (`array.array('h')`).
   - Playback dispatch latency is sub-millisecond ($< 0.1\text{ ms}$), completely bypassing disk I/O during execution.
4. **Idempotent Teardown:**
   - Device closure executes outside the mixer lock to eliminate thread deadlocks.
   - Multiple calls to `shutdown()` are safe and produce no unhandled exceptions.

---

## 6. Asset Organization & Verified Duration Reconciliation

All 20 canonical sound effects reside under `assets/audio/` with complete technical metadata registered in [`assets/audio/ASSET_MANIFEST.json`](file:///d:/GhostTrace/assets/audio/ASSET_MANIFEST.json).

### Duration Reconciliation (Step 02 Discrepancy Resolved)
The Step 02 narrative estimated total duration at 38.55s, but physical summation across all 20 WAV files on disk is **37.500 seconds**:
- `sfx/startup.wav`: 2.500s
- `sfx/shutdown.wav`: 2.200s
- `sfx/notification_alert.wav`: 0.800s
- `sfx/notification_ping.wav`: 0.600s
- `ambient/dark_hum.wav`: 6.000s
- `ambient/cold_wind.wav`: 6.000s
- `ambient/distant_thunder.wav`: 5.000s
- `glitch/digital_glitch.wav`: 0.350s
- `glitch/static_burst.wav`: 0.400s
- `glitch/corruption_artifact.wav`: 0.600s
- `whisper/spectral_whisper.wav`: 1.800s
- `whisper/chilling_breath.wav`: 1.400s
- `whisper/eerie_murmur.wav`: 2.000s
- `haunt/guardian_intercept.wav`: 1.000s
- `haunt/guardian_approved.wav`: 0.700s
- `haunt/guardian_blocked.wav`: 1.200s
- `haunt/coding_success.wav`: 1.500s
- `haunt/app_error.wav`: 0.800s
- `haunt/keystroke_haunt.wav`: 0.450s
- `haunt/mood_shift.wav`: 2.200s
- **Total Physical Duration:** $37.500\text{ seconds}$ across $5.52\text{ MB}$.

---

## 7. Physical Audio Smoke Test Procedure

Physical playback was verified on host hardware (`Speaker (Realtek(R) Audio)`):
```powershell
.venv\Scripts\python.exe tools/smoke_test_audio.py
```
**Test Results:**
- Device Initialized: `Speaker (Realtek(R) Audio)` in `578.49 ms`.
- Played `startup` (2.50s swell & chime).
- Played `glitch_digital` (0.35s bit-crushed burst).
- Played `whisper_spectral` (1.80s formant panning breath).
- Started ambient loop `ambient_dark_hum` for 3.0s, then stopped cleanly.
- Device shutdown completed in `514.51 ms`.

---

## 8. Application Event Audio Integration (`AudioEventAdapter`)

Step 04 connects GhostTrace application events to original dark horror sound effects via a decoupled, centralized adapter architecture ([`ghosttrace.audio.adapter.AudioEventAdapter`](file:///d:/GhostTrace/ghosttrace/audio/adapter.py)).

### Event-to-Sound Mapping Reference

| Application Event Category | Trigger Hook | Canonical Sound Effect | File Asset | Behavior & Policies |
|---|---|---|---|---|
| **Lifecycle** | `on_startup()` | `startup` | `sfx/startup.wav` | Dispatches once after successful TUI mount. |
| **Lifecycle** | `on_shutdown()` | `shutdown` | `sfx/shutdown.wav` | Dispatches power-down stinger before backend release. Idempotent. |
| **Notification** | `on_notification(important=True)` | `notification_alert` | `sfx/notification_alert.wav` | Critical alerts, warnings, and error notifications. |
| **Notification** | `on_notification(important=False)`| `notification_ping` | `sfx/notification_ping.wav` | Standard information notifications. 0.3s cooldown. |
| **Notification** | `on_notification(severity="status")` | *None (Suppressed)* | *None* | Minor status/debug updates produce zero sound. |
| **Guardian Security** | `on_guardian_intercept()` | `guardian_intercept` | `haunt/guardian_intercept.wav` | Dispatched when command is intercepted for approval. |
| **Guardian Security** | `on_guardian_approved()` | `guardian_approved` | `haunt/guardian_approved.wav` | Dispatched ONLY after user confirms execution approval. |
| **Guardian Security** | `on_guardian_blocked()` | `guardian_blocked` | `haunt/guardian_blocked.wav` | Dispatched when command is rejected or cancelled. |
| **Developer Workflow**| `on_coding_success()` | `coding_success` | `haunt/coding_success.wav` | Code generation, code review, refactoring, or AST analysis. |
| **Developer Workflow**| `on_app_error()` | `app_error` | `haunt/app_error.wav` | Inference/app exception stinger; deduplicated vs alert notifications. |
| **Ghost Haunt** | `on_mood_shift()` | `mood_shift` | `haunt/mood_shift.wav` | Real persona transitions (`old_mood != new_mood`). 2.0s cooldown. |
| **Ghost Haunt** | `on_glitch()` | `glitch_digital` | `glitch/digital_glitch.wav` | Terminal glitch, static, or memory corruption manifestations. |

### Deduplication & Debounce Strategy
- **Notification Deduplication:** Repeated identical messages within 1.0s are suppressed.
- **Error Stinger Deduplication:** If `notification_alert` fired for an error, `on_app_error` within 1.0s is suppressed to prevent jarring double-stingers.
- **Guardian Priority:** Guardian security decisions are never suppressed by normal cooldowns, ensuring 100% audible safety transparency.
- **Thread Safety:** State transitions are protected by an internal `threading.Lock()` across worker threads and the main Textual event loop.

---

## 9. Physical Hardware Verification (Step 04)

Hardware playback was verified across all event pathways on host hardware (`Speaker (Realtek(R) Audio)`):
```powershell
.venv\Scripts\python.exe tools/smoke_test_event_audio.py
```
**Physical Test Output:**
- Audio Disabled Mode: `backend=null`, `device_init=False` (100% silent, 0ms overhead).
- Audio Hardware Initialized: `Speaker (Realtek(R) Audio)`.
- Dispatched `startup` stinger (sub-bass swell & chime).
- Dispatched `notification_alert` (resonant bell) and `notification_ping` (hollow glass chime).
- Dispatched Guardian sequence: `guardian_intercept` (clamp) $\to$ `guardian_approved` (latch) $\to$ `guardian_blocked` (barricade clang).
- Dispatched `coding_success` (ethereal ascending chord).
- Dispatched `mood_shift` (sub-bass pitch bend).
- Dispatched `shutdown` (resonant power-down fade) followed by clean device teardown.
