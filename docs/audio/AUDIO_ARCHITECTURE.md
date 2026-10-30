# GhostTrace Audio Subsystem Architecture

> **Release:** GhostTrace v1.1.0  
> **Milestone:** Step 05 / 10 — Audio Controls & Experience Mode Integration  
> **Status:** Controls, CLI, TUI Modal, Persistence, and Experience Modes Verified

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

---

## 10. Persistent Audio Preferences & Precedence Architecture (Step 05)

Step 05 introduces persistent user audio preferences via [`ghosttrace.audio.preferences`](file:///d:/GhostTrace/ghosttrace/audio/preferences.py). User configuration changes made through the interactive TUI or CLI survive application restarts while strictly respecting deterministic configuration precedence.

### Preferences Storage
- **File Location:** `<app_data_dir>/audio_preferences.json` (defaults to `%LOCALAPPDATA%\GhostTrace\audio_preferences.json` on Windows).
- **Format:** Human-readable JSON validated via Pydantic model `AudioPreferences`.
- **Fault-Tolerance:** Missing, unreadable, or corrupted preference files cleanly fall back to default settings without crashing or interrupting the terminal.

```json
{
  "enabled": false,
  "volume": 0.5,
  "ambient_volume": 0.2,
  "muted": false
}
```

### Deterministic Precedence Hierarchy
Precedence order is strictly enforced by `apply_preferences_with_precedence()`:
1. **Explicit in-code arguments or CLI flags:** Highest priority.
2. **Explicit environment variables (`GHOSTTRACE_AUDIO_*`):**
   - **Critical Rule:** If `GHOSTTRACE_AUDIO_ENABLED=false` is explicitly set in the environment, persisted preferences can never override it to `true`.
3. **Persisted preferences (`audio_preferences.json`):** Applied on initialization when no environment override exists.
4. **Built-in default settings:** `audio_enabled=false`, `volume=0.50`, `ambient_volume=0.20`, `muted=false`.

---

## 11. Command-Line Interface (`ghosttrace audio`)

Comprehensive CLI control is exposed via the Typer CLI sub-app `ghosttrace audio`:

| Command | Usage | Description |
|---|---|---|
| `status` | `ghosttrace audio [status]` | Displays complete audio diagnostics (state, backend type, device availability, volume levels, mute state, active voices, ambient loop status, experience mode). |
| `enable` | `ghosttrace audio enable` | Enables audio subsystem, initializes hardware device, and persists `enabled=true`. |
| `disable` | `ghosttrace audio disable` | Silences all playback immediately, stops ambient loops, switches to `NullAudioBackend`, and persists `enabled=false`. |
| `volume` | `ghosttrace audio volume <0.0-1.0>` | Adjusts master volume level in real-time ($0.0$ to $1.0$) and persists preference. |
| `ambient-volume` | `ghosttrace audio ambient-volume <0.0-1.0>` | Adjusts ambient loop volume independently ($0.0$ to $1.0$) and persists preference. |
| `mute` | `ghosttrace audio mute` | Mutes all audio output without wiping out or resetting configured volume preferences. |
| `unmute` | `ghosttrace audio unmute` | Restores audio output at previously configured master and ambient volume levels. |
| `test` | `ghosttrace audio test` | Dispatches a short verification sound effect (`notification_ping`) to test physical output. |

All CLI commands cleanly release hardware device handles on exit, preventing background process hangs.

---

## 12. Interactive Terminal UI Controls & Modal (`AudioSettingsModal`)

Interactive audio control is integrated directly into the Textual TUI via [`AudioSettingsModal`](file:///d:/GhostTrace/ghosttrace/terminal/widgets/audio_modal.py):

- **Activation:**
  - Command: `audio settings`, `audio ui`, or `audio` with no arguments.
  - TUI Subcommands: `audio status`, `audio enable`, `audio disable`, `audio volume <val>`, `audio ambient-volume <val>`, `audio mute`, `audio unmute`, `audio test`.
  - Aliases: `sound`, `sfx`.
- **Visual Design:** Phosphor green aesthetic matching GhostTrace terminal theme (`#00ff66` accents, `#0d1117` backdrop, `#161b22` panels).
- **Interactive Capabilities:**
  - Real-time diagnostic telemetry display and visual ASCII meter bars (`[########........] 50%`).
  - Single-key and button toggles for Enable/Disable, Mute/Unmute, and Test Sound.
  - Quick-preset master volume adjustments: `+10%`, `-10%`, `50%`, `100%`.
  - Quick-preset ambient volume adjustments: `+5%`, `-5%`, `20%`, `50%`.
  - Dismissible with `Esc` or `Close` button.

---

## 13. Experience Mode Audio Policy Integration

GhostTrace experience modes (`normal`, `ambient`, `haunted`, `focus`) are synchronized with the audio subsystem via `AudioEventAdapter.set_experience_mode()`:

```text
┌─────────────────┬───────────────────────────────┬──────────────────────────────────────────┐
│ Experience Mode │ Ambient Sound Loop            │ Event Sound Effects Policy               │
├─────────────────┼───────────────────────────────┼──────────────────────────────────────────┤
│ normal          │ INACTIVE (silenced)           │ Standard event sounds audible.           │
│ ambient         │ ACTIVE (ambient_dark_hum loop)│ Standard event sounds audible.           │
│ haunted         │ ACTIVE (ambient_cold_wind loop│ All horror event sounds & whispers active│
│ focus           │ INACTIVE (silenced)           │ NON-ESSENTIAL SOUNDS SUPPRESSED:         │
│                 │                               │ - Non-important notifications silenced   │
│                 │                               │ - Coding success stingers silenced       │
│                 │                               │ - Ghost mood shifts silenced             │
│                 │                               │ - Digital glitch stingers silenced       │
│                 │                               │ CRITICAL EVENTS REMAIN AUDIBLE:          │
│                 │                               │ - Command Guardian intercept & approvals │
│                 │                               │ - Critical application error stingers    │
└─────────────────┴───────────────────────────────┴──────────────────────────────────────────┘
```

- When switching to `focus`, any active ambient loop stops immediately.
- When switching between `ambient` and `haunted`, the loop smoothly transitions from dark hum to eerie cold wind.
- Guardian safety operations and fatal errors bypass Focus mode filtering to guarantee operational safety awareness at all times.

---

## 14. Startup Latency Analysis & Lock Optimization

During Step 04 hardware validation, a cold-start delay of $\approx 886.6\text{ ms}$ was observed when initializing the audio subsystem. Component profiling revealed:

### Root Cause Breakdown
1. **OS/Driver Enumeration:** COM `IMMDeviceEnumerator` (`miniaudio.Devices().get_playbacks()`) requires $\approx 112\text{ ms}$.
2. **WASAPI Device Initialization:** `miniaudio.PlaybackDevice()` allocation and stream negotiation on Windows Realtek HD audio drivers requires $\approx 445\text{ ms}$.
3. **Mixer Lock Contention (Fixed in Step 05):** In initial implementation, `MiniAudioBackend._mixer_callback_generator` yielded silence buffers while holding `self._lock`. This caused caller threads trying to acquire `_lock` during initial device pre-roll to block for hundreds of milliseconds.
   - **Optimization:** Moved buffer `yield` outside the critical section in `_mixer_callback_generator()`. Calling threads now acquire the backend lock in $< 0.01\text{ ms}$ with zero lock contention.
4. **Sample Decoding:** Procedural WAV decoding and array conversion requires only $2.6\text{ ms}$; once decoded, in-memory cache lookup operates in $0.007\text{ ms}$.
5. **Disabled Default Protection:** With `audio_enabled=false` (the default), `NullAudioBackend` initializes in $< 0.05\text{ ms}$, ensuring zero impact on GhostTrace cold-boot time.

---

## 15. Haunted Keystrokes & Typing Audio Effects (v1.2.0 Step 07)

Step 07 introduces subtle, context-aware typing audio manifestations implemented in [`ghosttrace.audio.typing_effects.TypingEffectsManager`](file:///d:/GhostTrace/ghosttrace/audio/typing_effects.py).

### Strict Privacy Architecture
GhostTrace strictly upholds user privacy by enforcing an uncompromising architectural boundary between keyboard input and the audio subsystem:
- **Local Application Scope:** Only observes keyboard events delivered directly to GhostTrace's own Textual input widget (`CommandInput`).
- **Zero Global Hooks:** Never installs global Windows hooks, DLL injections, or system-wide event listeners.
- **Zero Character Capture:** Never receives, captures, logs, or inspects typed characters, key codes, passwords, or clipboard buffers.
- **Aggregate Metadata Only:** Operates purely on temporal metrics: timestamp gaps, consecutive keystroke counts, and short-window typing rates (keys/second).
- **Zero I/O & AI Overhead:** Generates zero disk writes per keystroke, zero network traffic, and zero LLM inference calls.

### Behavioral Parameters per Experience Mode

| Experience Mode | Base Prob | Burst Prob | Min Keys | Cooldown | Max/Min | Volume Scale | Allowed Audio Assets |
|---|---|---|---|---|---|---|---|
| `normal` | $6\%$ | $8\%$ | 5 | $4.0\text{ s}$ | 4 | 0.20 | `keystroke_haunt`, `glitch_digital` |
| `ambient` | $8\%$ | $12\%$ | 4 | $3.0\text{ s}$ | 6 | 0.25 | `keystroke_haunt`, `glitch_static` |
| `haunted` | $12\%$ | $22\%$ | 3 | $2.0\text{ s}$ | 8 | 0.35 | `keystroke_haunt`, `glitch_digital`, `glitch_static`, `glitch_corruption` |
| `focus` | **0%** | **0%** | N/A | N/A | 0 | 0.00 | **All typing effects suppressed immediately** |

### Event Lifecycle & Burst Detection
1. **Debouncing:** Rapid key events arriving faster than $30\text{ ms}$ are debounced to eliminate mechanical key chatter.
2. **Inactivity Reset:** A typing pause exceeding $1.2\text{ s}$ resets consecutive stroke counts, preventing lone accidental keypresses from triggering audio.
3. **Burst Cadence:** When typing speed exceeds 8 keystrokes within a 2-second rolling window in `haunted` mode, the engine elevates triggering probability and introduces rare memory corruption artifacts (`glitch_corruption`).
4. **Cooldown & Rate Ceiling:** Enforces minimum quiet intervals ($2.0\text{ s}$ to $4.0\text{ s}$) and hard per-minute ceilings (4 to 8 effects/min) to prevent audio fatigue.
5. **Deterministic Testing:** Fully supports injectable random and monotonic clock sources for 100% deterministic test coverage.

---

## 16. Scheduled Whispers & Time-Aware Audio Manifestations (v1.2.0 Step 08)

Step 08 introduces rare, unpredictable, atmospheric whisper-like sound effects managed by [`ghosttrace.audio.whisper_scheduler.WhisperScheduler`](file:///d:/GhostTrace/ghosttrace/audio/whisper_scheduler.py).

### Synthetic Procedural Nature & Privacy Guarantees
- **100% Procedural Audio Effects:** All whisper manifestations use original mathematical sound synthesis assets (`whisper_spectral`, `whisper_breath`, `whisper_murmur`). There is strictly zero spoken dialogue, zero text-to-speech (TTS), zero voice interaction, zero AI-generated speech, and zero cloud synthesis.
- **Zero Audio Capture:** Zero microphone access, capture buffers, or recording APIs.
- **Zero Network Dependency:** Fully offline execution with zero telemetry or network calls.
- **Strict Opt-In Preference:** Disabled by default (`audio_scheduled_whispers_enabled = false`).

### Scheduling Architecture & Concurrency Model
- **Event-Driven Timers:** Integrates with Textual's async event loop (`self.set_timer`), creating zero permanent Python worker threads.
- **Zero Busy Polling:** Never uses `time.sleep()` in UI threads and runs no polling loops.
- **Context-Aware Suppression:** Immediately suspends whisper opportunities during active command generation (`is_generating`), command execution, or active Command Guardian confirmation modals.
- **Clean Shutdown Lifecycle:** Pending timers are safely cancelled upon application shutdown or modal dismissal.

### Experience Mode Tuning Profiles

| Experience Mode | Randomized Interval Range | Cooldown | Hourly Ceiling | Volume Scale | Permitted Sound Assets |
|---|---|---|---|---|---|
| `normal` | $180.0\text{ s} - 360.0\text{ s}$ (3–6 min) | $120.0\text{ s}$ | 3 / hour | 0.20 | `whisper_breath` |
| `ambient` | $90.0\text{ s} - 210.0\text{ s}$ (1.5–3.5 min) | $60.0\text{ s}$ | 6 / hour | 0.25 | `whisper_breath`, `whisper_spectral` |
| `haunted` | $45.0\text{ s} - 120.0\text{ s}$ (45s–2 min) | $30.0\text{ s}$ | 12 / hour | 0.35 | `whisper_breath`, `whisper_spectral`, `whisper_murmur` |
| `focus` | **Suppressed** | N/A | 0 / hour | 0.00 | **All scheduled whispers suppressed immediately** |


