# Changelog

All notable changes to GhostTrace are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased] - v1.2.0

### Added
- **Haunted Keystrokes & Context-Aware Typing Audio Effects (Step 07):**
  - Subtle, atmospheric typing audio manifestations triggered strictly by keyboard activity within GhostTrace's own interactive Textual terminal input widget.
  - Dedicated `TypingEffectsManager` component enforcing aggregate event counting, activity rates, dynamic cooldowns, and debouncing.
  - Context-aware audio manifestations using existing verified procedural assets (`KEYSTROKE_HAUNT`, `GLITCH_DIGITAL`, `GLITCH_STATIC`, `GLITCH_CORRUPTION`).
  - High-cadence typing burst detection triggering rare corruption artifacts in Haunted mode.
  - Dedicated configuration setting `audio_haunted_keystrokes_enabled` / `haunted_keystrokes_enabled`, strictly disabled by default (`OFF`).
  - Persistent user preference storage in `audio_preferences.json`.
  - Full experience mode integration:
    - `Normal`: Infrequent, very subtle keystroke echoes and digital fractures.
    - `Ambient`: Faint static bursts and keystroke thuds coexisting with background ambient loops.
    - `Haunted`: Full atmospheric manifestations with elevated probabilities during sustained typing bursts.
    - `Focus`: 100% immediate suppression of all typing audio effects (Guardian safety cues remain active).
  - TUI controls in `AudioSettingsModal`: interactive toggle button and single-key shortcut (`k`).
  - CLI commands: `ghosttrace audio keystrokes <on|off>` and status telemetry integration.
  - **Strict Privacy Guarantees:**
    - Zero global keyboard hooks; observes only input events inside GhostTrace's own Textual terminal widget.
    - Zero inspection, capturing, storage, or logging of typed characters, passwords, or command text.
    - Operates purely on aggregate temporal metadata (timestamps, key counts, intervals).
    - Zero network egress, zero disk writes per keystroke, and zero AI inference overhead.
- **Scheduled Whispers & Time-Aware Audio Manifestations (Step 08):**
  - Rare, unpredictable atmospheric whisper manifestations powered by procedural audio assets (`whisper_spectral`, `whisper_breath`, `whisper_murmur`).
  - Purely synthetic/instrumental sound effects; zero spoken words, speech, TTS, or voice interaction.
  - Dedicated `WhisperScheduler` component integrated with Textual's event loop timer; zero additional persistent worker threads.
  - Configurable randomized intervals, cooldowns, and rolling hourly frequency limits.
  - Context-aware suppression policy: whispers are silenced during LLM generation, command execution, or active Command Guardian approval prompts.
  - Full experience mode integration:
    - `Normal`: Very rare exhalations (3–6 min interval, 3/hour max).
    - `Ambient`: Rare spectral murmurs at low volume (1.5–3.5 min interval, 6/hour max).
    - `Haunted`: Moderately rare whisper sweeps (45s–2 min interval, 12/hour max).
    - `Focus`: 100% immediate suppression of all scheduled whispers.
  - Dedicated configuration setting `audio_scheduled_whispers_enabled` / `scheduled_whispers_enabled`, strictly disabled by default (`OFF`).
  - Persistent user preference storage in `audio_preferences.json`.
  - TUI controls in `AudioSettingsModal`: interactive toggle button and single-key shortcut (`w`).
  - CLI commands: `ghosttrace audio whispers <on|off>` and status telemetry integration.
  - Safe lifecycle management with clean cancellation upon unmount and shutdown.
- **Dynamic Horror Event Orchestration & Adaptive Audio Director (Step 09):**
  - Centralized HorrorAudioDirector component coordinating haunted typing, scheduled whispers, glitches, application events, and ambient horror loops.
  - Hierarchical priority tiering: CRITICAL (Guardian events and errors), IMPORTANT (lifecycle, notifications, coding success), ATMOSPHERIC (whispers, typing effects, glitches), and AMBIENT (background streams).
  - Guardian security decisions, approvals, and interceptions retain unconditional priority and are never throttled or deferred by atmospheric limits.
  - Deterministic adaptive horror intensity states: dormant, subtle, unsettling, and haunted, calculated from experience mode, aggregate typing rates, and developer task successes without LLM inference or background system surveillance.
  - Cross-system collision prevention ensuring typing effects and scheduled whispers never trigger simultaneously within collision windows.
  - Glitch burst suppression enforcing dedicated cooldowns against repeated audio clutter.
  - Strict context evaluation suppressing atmospheric cues during AI generation, active command execution, or pending Command Guardian approval dialogs.
  - Dedicated configuration setting audio_dynamic_horror_enabled / dynamic_horror_enabled, disabled by default (OFF), persisted in audio_preferences.json.
  - TUI controls in AudioSettingsModal: interactive toggle button and keyboard shortcut (h).
  - CLI command: ghosttrace audio horror <on|off> and status telemetry integration.
  - Comprehensive privacy guarantees: zero raw keyboard capture, zero command text inspection, zero microphone access, zero clipboard inspection, and zero OS surveillance.

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
