# Changelog

All notable changes to GhostTrace are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] - 2026-10-30

### Added
- **Dark Horror Audio Subsystem Foundation (Step 01):**
  - Architecture foundation with `AudioManager`, abstract `AudioBackend`, and silent fallback `NullAudioBackend`.
  - Canonical taxonomy of 20 audio events across 5 horror categories: SFX, Ambient, Glitch, Whisper, and Haunt.
  - Configuration settings (`GHOSTTRACE_AUDIO_*`) with audio strictly disabled by default (`audio_enabled = false`).
- **Original Horror Sound Asset Library (Step 02):**
  - 20 original procedural DSP sound effects generated at 16-bit 44.1 kHz PCM WAV (9 stereo, 11 mono).
  - Accurate technical metadata registered in `assets/audio/ASSET_MANIFEST.json` totaling exactly 37.500 seconds across 5.73 MB.
- **Asynchronous Local Playback Engine (Step 03):**
  - `MiniAudioBackend` implementing multi-voice polyphonic software mixer (up to 8 concurrent voices).
  - Singleton seamless looping ambient track with modular wraparound.
  - In-memory 16-bit PCM sample cache bypassing disk I/O during execution ($< 5\text{ ms}$ cached latency).
  - Lightweight `miniaudio` WASAPI / DirectSound binding with zero external PortAudio DLL dependencies.
- **Application Event Audio Integration (Step 04):**
  - `AudioEventAdapter` wiring audio to GhostTrace application lifecycle: startup, shutdown, notifications, developer coding tasks, and mood shifts.
  - Deep Command Guardian integration: audible intercept clamps, approval latches, and rejection clangs.
  - Bounded deduplication and debounce mechanisms preventing double-stingers and notification audio flooding.
- **Audio Controls & Experience Mode Integration (Step 05):**
  - Interactive Textual TUI modal screen (`AudioSettingsModal`) with live telemetry, level meters, and keyboard controls.
  - Headless CLI commands under `ghosttrace audio [status|enable|disable|volume|ambient-volume|mute|unmute|test]`.
  - Independent master and ambient volume scaling $[0.0, 1.0]$.
  - Mute/unmute state preservation without resetting user volume preferences.
  - Persistent user preferences saved to `<app_data_dir>/audio_preferences.json`.
  - Strict configuration precedence: CLI options > Environment variables > Persisted preferences > Built-in defaults.
  - Experience mode synchronization (`normal`, `ambient`, `haunted`, `focus`).
  - Focus Mode policy: suppresses non-essential auditory cues while preserving Command Guardian security alerts and fatal application error stingers.
- **Production Packaging & Hardening (Step 06):**
  - PyInstaller onedir production build including `miniaudio` extension and asset collection.
  - Cross-environment asset directory discovery supporting frozen execution (`sys._MEIPASS` and executable directory).
  - Full automated regression test suite expanded to 565 automated tests + 1 real-AI interactive smoke test (100% pass rate).
  - Rollback preservation for v1.0.0 release artifacts.

### Changed
- Bumped application version metadata to `1.1.0`.
- Optimized mixer callback generator lock scoping, reducing backend lock acquisition delay from hundreds of milliseconds to $< 0.01\text{ ms}$.

### Security
- Audio subsystem is strictly sound-effects only: zero microphone capture, zero TTS, zero cloud audio services.
- Guardian security policy invariant maintained: audio events cannot bypass, alter, or synthesize security tokens.

---

## [1.0.0] - 2026-10-28

### Added
- **Core TUI Assistant:** Textual-powered split terminal interface with real-time green-phosphor visual styling.
- **Local AI Inference Engine:** CPU-optimized `llama-cpp-python` running local Qwen2.5-1.5B-Instruct GGUF Q4_K_M.
- **Digital Ghost Persona Engine:** Three atmospheric personas (`forgotten-machine`, `phantom-coder`, `guardian-spirit`) with dynamic mood transitions.
- **Developer Assistance Subsystem:** Safe code generation, explanation, syntax highlighting, diff analysis, and regex assistance.
- **Command Guardian:** Strict safety analysis classifying commands into LOW, MEDIUM, HIGH, and BLOCKED risks with token-based approval.
- **Persistent Memory & Project Index:** SQLite database (WAL mode) storing conversations and read-only project codebase context.
- **System Telemetry & Health Diagnostics:** Real-time host CPU, RAM, disk, and process telemetry.
- **Atmospheric Experience Scheduler:** Supernatural haunt modes (`normal`, `ambient`, `haunted`, `focus`).
- **Production Packaging:** Standalone Windows x64 distribution bundle.
