# GhostTrace Audio Assets Specification (Dark Horror)

> **Status:** v1.1.0 — Step 01 Foundation  
> **Notice:** No audio files are bundled or downloaded in Step 01. Audio playback is disabled by default.

---

## 1. Aesthetic Direction: Dark Horror

GhostTrace sound effects follow a distinct **Dark Horror / Cyber-Gothic Terminal** aesthetic:
- **Atmosphere:** Deep sub-bass rumbles, low electromagnetic interference, cold room tone, distant resonance.
- **Digital Decay:** Subtle bit-crushing, tape flutter, analog CRT static, and memory corruption cues.
- **Ghost Whispers:** Strictly **nonverbal** sound effects (breaths, sibilance, eerie murmurs, vocal harmonics).
  - *Zero AI speech, zero TTS, zero voice acting.*
- **Restraint & Subtlety:** Sounds must never be jarring, cheesy, or loud jump scares. They must exist as subtle, organic texture behind the developer's work.

---

## 2. Directory Taxonomy

```text
assets/audio/
├── sfx/            # System lifecycle sounds (startup, shutdown, notifications)
├── ambient/        # Subtle, seamlessly looping background horror soundscapes
├── glitch/         # Short, sharp digital static bursts and corruption cues
├── whisper/        # Nonverbal chilling breaths, sibilance, and spectral murmurs
└── haunt/          # Reactions for Guardian halts, code milestones, and mood transitions
```

---

## 3. Technical Asset Specifications

When sound assets are integrated in future steps, they must strictly adhere to:

| Parameter | Specification | Rationale |
|---|---|---|
| **Format** | Standard uncompressed 16-bit PCM WAV (or OGG Vorbis for ambient loops) | Minimal CPU decoding overhead on Intel Core i3 hardware. |
| **Sample Rate** | 44.1 kHz or 48.0 kHz | High compatibility with Windows DirectSound and WASAPI. |
| **Channels** | Stereo (preferred) or Mono | Atmospheric spatial width for whispers and ambience. |
| **Target Peak Volume** | -6.0 dBFS to -3.0 dBFS | Headroom prevention against digital clipping. |
| **Duration (SFX)** | 0.2s to 2.5s | Immediate responsiveness; does not linger or impede workflow. |
| **Duration (Ambient)** | 10.0s to 60.0s seamless loop | Seamless repetition without audible transition seam. |

---

## 4. Legal & Licensing Mandate

To maintain GhostTrace as a strictly open-source, redistributable project:
- **Strictly Prohibited:** Commercial movie, television, anime, commercial video game sound effects, or copyrighted audio clips.
- **Permitted Sources:**
  - Original synthesizer designs created specifically for GhostTrace.
  - Public Domain / Creative Commons 0 (CC0) sound effects.
  - CC-BY licensed audio where full attribution is documented in an `ASSET_MANIFEST.md`.
