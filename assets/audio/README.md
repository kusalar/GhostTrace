# GhostTrace Audio Assets Specification (Dark Horror)

> **Status:** v1.1.0 — Step 02: Original Horror Sound Asset Library  
> **Audio Scope:** Sound Effects Only (Strictly No Voice/TTS).  
> **Notice:** The sound asset library is complete and on disk, but playback is NOT implemented in Step 02. Audio remains disabled by default (`GHOSTTRACE_AUDIO_ENABLED=false`).

---

## 1. Aesthetic Direction: Dark Horror

GhostTrace sound effects follow a distinct **Dark Horror / Cyber-Gothic Terminal** aesthetic:
- **Atmosphere:** Deep sub-bass rumbles, low electromagnetic interference, cold room tone, distant resonance.
- **Digital Decay:** Subtle bit-crushing, tape flutter, analog CRT static, and memory corruption cues.
- **Ghost Whispers:** Strictly **nonverbal** sound effects (breaths, sibilance, eerie murmurs, vocal harmonics).
  - *Zero AI speech, zero TTS, zero voice acting.*
- **Restraint & Subtlety:** Sounds are designed as subtle, organic ambient textures that stay in the background without interrupting developer workflows or spiking CPU load.

---

## 2. Directory Taxonomy & Generated Asset Roster

All 20 canonical sound effects are 16-bit linear PCM WAV files at 44.1 kHz, normalized with headroom (`-2.85 dBFS` peak):

| Canonical Event ID | Category | Relative Path | Duration | Ch | Size | Description |
|---|---|---|---|---|---|---|
| `startup` | `sfx` | `sfx/startup.wav` | 2.50s | 2 | 441.0 KB | Spectral terminal boot swell and chime |
| `shutdown` | `sfx` | `sfx/shutdown.wav` | 2.20s | 2 | 388.1 KB | Terminal dissolution power-down |
| `ambient_dark_hum` | `ambient` | `ambient/dark_hum.wav` | 6.00s | 2 | 1033.6 KB | Subterranean dark drone (seamless loop) |
| `ambient_cold_wind` | `ambient` | `ambient/cold_wind.wav` | 6.00s | 2 | 1033.6 KB | Chilling draft howling wind (seamless loop) |
| `ambient_distant_thunder` | `ambient` | `ambient/distant_thunder.wav` | 5.00s | 2 | 861.4 KB | Distant storm sub-bass rumble |
| `glitch_digital` | `glitch` | `glitch/digital_glitch.wav` | 0.35s | 1 | 30.2 KB | Bit-crushed digital fracture |
| `glitch_static` | `glitch` | `glitch/static_burst.wav` | 0.40s | 1 | 34.5 KB | CRT electromagnetic static burst |
| `glitch_corruption` | `glitch` | `glitch/corruption_artifact.wav` | 0.60s | 1 | 51.7 KB | Memory corruption artifact |
| `whisper_spectral` | `whisper` | `whisper/spectral_whisper.wav` | 1.80s | 2 | 310.1 KB | Spectral nonverbal whisper sweep |
| `whisper_breath` | `whisper` | `whisper/chilling_breath.wav` | 1.40s | 2 | 241.2 KB | Cold nonverbal exhalation envelope |
| `whisper_murmur` | `whisper` | `whisper/eerie_murmur.wav` | 2.00s | 2 | 344.6 KB | Incomprehensible vocal harmonic murmur |
| `notification_alert` | `sfx` | `sfx/notification_alert.wav` | 0.80s | 1 | 68.9 KB | Ghost warning dissonant bell strike |
| `notification_ping` | `sfx` | `sfx/notification_ping.wav` | 0.60s | 1 | 51.7 KB | Resonant crystalline terminal ping |
| `guardian_intercept` | `haunt` | `haunt/guardian_intercept.wav` | 1.00s | 1 | 86.2 KB | Heavy metallic clamp halting command |
| `guardian_approved` | `haunt` | `haunt/guardian_approved.wav` | 0.70s | 1 | 60.3 KB | Mechanical seal release chime |
| `guardian_blocked` | `haunt` | `haunt/guardian_blocked.wav` | 1.20s | 1 | 103.4 KB | Harsh barricade strike |
| `coding_success` | `haunt` | `haunt/coding_success.wav` | 1.50s | 2 | 258.4 KB | Supernatural resolution ascending chord |
| `app_error` | `haunt` | `haunt/app_error.wav` | 0.80s | 1 | 68.9 KB | Discordant glitch screech stinger |
| `keystroke_haunt` | `haunt` | `haunt/keystroke_haunt.wav` | 0.45s | 1 | 38.8 KB | Subterranean keystroke impact |
| `mood_shift` | `haunt` | `haunt/mood_shift.wav` | 2.20s | 2 | 379.0 KB | Atmospheric pressure shift sub-bass bend |

---

## 3. Provenance & Regeneration

All sound assets are 100% original, generated via pure Python standard library DSP synthesis:
- **Zero external recordings or samples:** No commercial samples, no movie/game sound effects.
- **Generator script:** `tools/generate_audio_assets.py`.
- **Deterministic:** Using `seed=42` produces identical binary WAV files.

To regenerate the entire library and manifest:
```powershell
.venv\Scripts\python.exe tools/generate_audio_assets.py --output-dir assets/audio --force
```

---

## 4. Legal & Licensing Notice

All sound effects in this directory were created specifically for GhostTrace and are released under the project's **MIT License**. They are fully open source, royalty-free, and redistributable.
