# GhostTrace Audio Subsystem Architecture

> **Release:** GhostTrace v1.1.0  
> **Milestone:** Step 02 / 10 — Original Horror Sound Asset Library  
> **Status:** Sound Asset Library Complete (Playback NOT Implemented in Step 02)

---

## 1. Architectural Vision & Scope

GhostTrace introduces an optional, local-only **Dark Horror sound-effects subsystem** designed to provide eerie atmosphere and responsive auditory feedback for terminal actions without impeding developer productivity or local inference performance.

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
│            │ Future Playback Engine (Step 02+)            │            │
│            │  - Asynchronous thread pool / worker         │            │
│            │  - Local-only WAV/OGG playback               │            │
│            └──────────────────────────────────────────────┘            │
└────────────────────────────────────────────────────────────────────────┘
```

### Strict Non-Functional Guarantees
1. **Sound Effects Only:** No AI speech, no text-to-speech (TTS), no voice acting. Ghost whispers are strictly nonverbal acoustic sound effects (breaths, sibilance, eerie vocal harmonics).
2. **Zero Interference with TUI:** Audio operations are decoupled and asynchronous; they never block Textual layout, frame rendering, keyboard input, or terminal scrolling.
3. **Zero Impact on Inference:** Audio processing consumes negligible CPU overhead, leaving CPU threads and memory entirely dedicated to the local Qwen GGUF model and Command Guardian.
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
| `AudioBackend` | [`ghosttrace.audio.backend`](file:///d:/GhostTrace/ghosttrace/audio/backend.py) | Abstract interface defining hardware initialization, asset playback, volume scaling, and teardown. |
| `NullAudioBackend` | [`ghosttrace.audio.backend`](file:///d:/GhostTrace/ghosttrace/audio/backend.py) | Safe, silent no-op implementation. Active whenever audio is disabled or hardware initialization fails. |
| `AudioCatalog` | [`ghosttrace.audio.catalog`](file:///d:/GhostTrace/ghosttrace/audio/catalog.py) | Declarative registry mapping canonical `AudioEventId` values to `SoundEffect` models with relative file paths and descriptive metadata. |
| `AudioStatus` | [`ghosttrace.audio.schemas`](file:///d:/GhostTrace/ghosttrace/audio/schemas.py) | Pydantic telemetry model reporting operational state, backend type, asset directory status, and active voice counts. |
| `AudioError` | [`ghosttrace.audio.exceptions`](file:///d:/GhostTrace/ghosttrace/audio/exceptions.py) | Domain exception hierarchy (`AudioInitializationError`, `AudioDisabledError`, `AssetNotFoundError`, `InvalidVolumeError`). |

---

## 4. Asset Organization & Original Procedural Library

All 20 canonical sound effects reside under `assets/audio/` with complete technical metadata registered in [`assets/audio/ASSET_MANIFEST.json`](file:///d:/GhostTrace/assets/audio/ASSET_MANIFEST.json):
- `assets/audio/sfx/`: System startup, shutdown, and notification chimes (2.50s startup, 2.20s shutdown, alert & ping).
- `assets/audio/ambient/`: Continuous, low-frequency horror drones and wind loops (6.0s dark hum, 6.0s cold wind, 5.0s distant thunder).
- `assets/audio/glitch/`: Sharp bit-crushed bursts and static interference (0.35s - 0.60s).
- `assets/audio/whisper/`: Nonverbal spectral sibilance, cold breaths, and faint murmurs (1.40s - 2.00s).
- `assets/audio/haunt/`: Reactions to Guardian intercepts, execution approvals, coding milestones, and mood transitions (0.45s - 2.20s).

### Technical Specifications & Licensing
- **Format:** 16-bit linear PCM WAV, 44.1 kHz sample rate.
- **Mastering:** Normalized to -2.85 dBFS peak, leaving safe dynamic headroom without digital clipping.
- **Provenance:** 100% original procedural synthesis generated via Python standard library DSP (`tools/generate_audio_assets.py`, seed=42). Zero copyrighted samples.
- **License:** Project-owned original assets released under the **MIT License**.

---

## 5. Playback Implementation Status

> [!IMPORTANT]
> **Audio playback is NOT implemented in Step 02.**  
> While the sound asset library is fully generated and verified on disk, all runtime sound operations continue to route strictly through `NullAudioBackend`. No audio drivers, background playback threads, WASAPI endpoints, or external audio libraries are loaded or initialized. All v1.0.0 functionality, CLI commands, and TUI layouts remain 100% preserved.

