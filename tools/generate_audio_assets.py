"""Deterministic generator for GhostTrace original dark horror sound effects.

Generates 16-bit 44.1 kHz PCM WAV assets using pure Python standard library DSP synthesis.
Zero external libraries, zero network dependencies, 100% reproducible with a fixed seed.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import struct
import wave
from pathlib import Path

SAMPLE_RATE = 44100
MAX_AMP = 32767.0
TARGET_PEAK = 0.72  # Approx -2.85 dBFS, leaving comfortable headroom without clipping


def clamp(val: float, low: float = -1.0, high: float = 1.0) -> float:
    """Clamp float between low and high boundaries."""
    return max(low, min(high, val))


def normalize_samples(
    samples: list[tuple[float, float]],
    target_peak: float = TARGET_PEAK,
) -> list[tuple[float, float]]:
    """Normalize stereo sample frames so peak amplitude equals target_peak."""
    max_val = 0.0
    for left, right in samples:
        max_val = max(max_val, abs(left), abs(right))

    if max_val <= 1e-6:
        return samples

    scale = target_peak / max_val
    return [(left * scale, right * scale) for left, right in samples]


def write_wav_file(
    out_path: Path,
    samples: list[tuple[float, float]],
    channels: int = 2,
    sample_rate: int = SAMPLE_RATE,
) -> None:
    """Write normalized floating-point samples to a standard 16-bit PCM WAV file."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    norm_samples = normalize_samples(samples)

    with wave.open(str(out_path), "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)

        raw_frames = bytearray()
        for left, right in norm_samples:
            left_val = int(clamp(left) * MAX_AMP)
            if channels == 1:
                # Average to mono
                mono_val = int(clamp((left + right) * 0.5) * MAX_AMP)
                raw_frames.extend(struct.pack("<h", mono_val))
            else:
                right_val = int(clamp(right) * MAX_AMP)
                raw_frames.extend(struct.pack("<hh", left_val, right_val))

        wav_file.writeframes(raw_frames)


class ProceduralHorrorSynth:
    """Procedural synthesis engine for GhostTrace original horror soundscapes."""

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed
        self.rng = random.Random(seed)

    def _white_noise(self) -> float:
        return self.rng.uniform(-1.0, 1.0)

    def _fade_envelope(self, length: int, attack_frames: int, release_frames: int) -> list[float]:
        """Generate smooth sinusoidal attack/release envelope."""
        env = [1.0] * length
        for i in range(min(attack_frames, length)):
            env[i] = 0.5 * (1.0 - math.cos(math.pi * i / attack_frames))
        for i in range(min(release_frames, length)):
            idx = length - 1 - i
            val = 0.5 * (1.0 - math.cos(math.pi * i / release_frames))
            env[idx] = min(env[idx], val)
        return env

    def _apply_loop_crossfade(
        self, samples: list[tuple[float, float]], crossfade_frames: int
    ) -> list[tuple[float, float]]:
        """Cross-fade tail into head to make ambient audio perfectly seamless."""
        n = len(samples)
        fade_len = min(crossfade_frames, n // 2)
        result = list(samples)

        for i in range(fade_len):
            t = i / fade_len
            w_out = 0.5 * (1.0 + math.cos(math.pi * t))
            w_in = 0.5 * (1.0 - math.cos(math.pi * t))

            tail_idx = n - fade_len + i
            tail_l, tail_r = samples[tail_idx]
            head_l, head_r = samples[i]

            blended_l = head_l * w_in + tail_l * w_out
            blended_r = head_r * w_in + tail_r * w_out

            result[i] = (blended_l, blended_r)
            result[tail_idx] = (blended_l, blended_r)

        return result

    # --- 1. System Lifecycle ---

    def gen_startup(self) -> list[tuple[float, float]]:
        """System: Mysterious machine boot swell and resonant CRT chime."""
        duration = 2.5
        n = int(SAMPLE_RATE * duration)
        samples: list[tuple[float, float]] = []

        attack = int(SAMPLE_RATE * 0.8)
        release = int(SAMPLE_RATE * 0.6)
        env = self._fade_envelope(n, attack, release)

        for i in range(n):
            t = i / SAMPLE_RATE
            # Sub-bass swell rising 45Hz -> 65Hz
            f_sub = 45.0 + 20.0 * (i / n)
            sub = math.sin(2.0 * math.pi * f_sub * t) * (0.6 + 0.1 * math.sin(6.0 * math.pi * t))

            # Resonant harmonic chime (277Hz + 415Hz) entering at 0.4s
            chime_t = max(0.0, t - 0.4)
            chime_env = math.exp(-chime_t * 2.2) if t >= 0.4 else 0.0
            chime = (
                math.sin(2.0 * math.pi * 277.18 * chime_t)
                + 0.5 * math.sin(2.0 * math.pi * 415.30 * chime_t)
                + 0.25 * math.sin(2.0 * math.pi * 830.61 * chime_t)
            ) * chime_env

            # High CRT electromagnetic hum (fading in and dropping 6000 -> 3500)
            crt_env = math.exp(-max(0.0, t - 0.8) * 3.5) if t >= 0.8 else min(1.0, t / 0.8)
            f_crt = 6000.0 - 2500.0 * min(1.0, t / 1.5)
            crt = math.sin(2.0 * math.pi * f_crt * t) * 0.08 * crt_env

            left = (sub * 0.6 + chime * 0.5 + crt) * env[i]
            right = (sub * 0.58 + chime * 0.52 - crt * 0.8) * env[i]
            samples.append((left, right))

        return samples

    def gen_shutdown(self) -> list[tuple[float, float]]:
        """System: Slowly fading machine power-down and tape dissolution."""
        duration = 2.2
        n = int(SAMPLE_RATE * duration)
        samples: list[tuple[float, float]] = []

        for i in range(n):
            t = i / SAMPLE_RATE
            progress = i / n

            # Pitch winding down: 240Hz exponentially decaying to 30Hz
            freq = 30.0 + 210.0 * math.exp(-progress * 2.8)
            tone = math.sin(2.0 * math.pi * freq * t)

            # Motor rotation flutter
            flutter = 1.0 + 0.3 * math.sin(2.0 * math.pi * (8.0 * (1.0 - progress * 0.7)) * t)

            # Smooth fade-out envelope
            amp = math.exp(-t * 1.5) * (1.0 - progress)

            left = tone * flutter * amp
            right = tone * (flutter * 0.95) * amp
            samples.append((left, right))

        return samples

    # --- 2. Ambient Background (Seamless Loops) ---

    def gen_ambient_dark_hum(self) -> list[tuple[float, float]]:
        """Ambient: Deep subterranean drone with slow binaural undulation."""
        duration = 6.0
        n = int(SAMPLE_RATE * duration)
        samples: list[tuple[float, float]] = []

        # Binaural detuned sub-bass: 48Hz (left) and 51Hz (right)
        for i in range(n):
            t = i / SAMPLE_RATE
            # 0.25 Hz slow breathing LFO
            lfo = 0.75 + 0.25 * math.sin(2.0 * math.pi * 0.25 * t)

            left_drone = (
                math.sin(2.0 * math.pi * 48.0 * t)
                + 0.35 * math.sin(2.0 * math.pi * 96.0 * t)
                + 0.15 * math.sin(2.0 * math.pi * 144.0 * t)
            ) * lfo

            right_drone = (
                math.sin(2.0 * math.pi * 51.0 * t)
                + 0.35 * math.sin(2.0 * math.pi * 102.0 * t)
                + 0.15 * math.sin(2.0 * math.pi * 153.0 * t)
            ) * lfo

            samples.append((left_drone, right_drone))

        return self._apply_loop_crossfade(samples, int(SAMPLE_RATE * 0.6))

    def gen_ambient_cold_wind(self) -> list[tuple[float, float]]:
        """Ambient: Soft, distant howling wind sweeping across empty architecture."""
        duration = 6.0
        n = int(SAMPLE_RATE * duration)
        samples: list[tuple[float, float]] = []

        # Filtered noise via 1-pole stateful sweep
        filter_state_l = 0.0
        filter_state_r = 0.0

        for i in range(n):
            t = i / SAMPLE_RATE
            # Gust modulation
            gust_lfo = 0.5 + 0.5 * math.sin(2.0 * math.pi * 0.35 * t + 0.4)
            pan_lfo = 0.5 + 0.5 * math.sin(2.0 * math.pi * 0.15 * t)

            noise_l = self._white_noise()
            noise_r = self._white_noise()

            # Dynamic cutoff 200Hz -> 650Hz
            fc = 200.0 + 450.0 * gust_lfo
            alpha = (2.0 * math.pi * fc) / SAMPLE_RATE

            filter_state_l += alpha * (noise_l - filter_state_l)
            filter_state_r += alpha * (noise_r - filter_state_r)

            left = filter_state_l * (1.2 - pan_lfo * 0.6) * gust_lfo
            right = filter_state_r * (0.6 + pan_lfo * 0.6) * gust_lfo
            samples.append((left, right))

        return self._apply_loop_crossfade(samples, int(SAMPLE_RATE * 0.6))

    def gen_ambient_distant_thunder(self) -> list[tuple[float, float]]:
        """Ambient: Low resonant thunder rolling far beyond the terminal."""
        duration = 5.0
        n = int(SAMPLE_RATE * duration)
        samples: list[tuple[float, float]] = []

        brown_noise = 0.0
        for i in range(n):
            t = i / SAMPLE_RATE
            # Brown noise integration
            white = self._white_noise()
            brown_noise = (brown_noise + 0.03 * white) / 1.02

            # Three rolling blast waves
            impact1 = math.exp(-max(0.0, t - 0.2) * 1.4) if t >= 0.2 else t / 0.2
            impact2 = math.exp(-max(0.0, t - 1.5) * 1.8) * 0.6 if t >= 1.5 else 0.0
            impact3 = math.exp(-max(0.0, t - 2.8) * 2.2) * 0.35 if t >= 2.8 else 0.0
            impact_total = impact1 + impact2 + impact3

            # Sub-bass punch (38Hz -> 30Hz)
            sub = math.sin(2.0 * math.pi * 38.0 * t) * impact_total

            left = (brown_noise * 1.5 + sub) * impact_total
            right = (brown_noise * 1.4 + sub * 0.95) * impact_total
            samples.append((left, right))

        return samples

    # --- 3. Glitches & Digital Decay ---

    def gen_glitch_digital(self) -> list[tuple[float, float]]:
        """Glitch: Rapid bit-crushed micro-burst of stepped frequencies."""
        duration = 0.35
        n = int(SAMPLE_RATE * duration)
        samples: list[tuple[float, float]] = []

        freqs = [880.0, 1760.0, 440.0, 3520.0, 110.0, 2200.0]
        step_len = n // len(freqs)

        held_sample = 0.0
        downsample_factor = 10

        for i in range(n):
            t = i / SAMPLE_RATE
            f_idx = min(len(freqs) - 1, i // step_len)
            freq = freqs[f_idx]

            if i % downsample_factor == 0:
                raw = math.sin(2.0 * math.pi * freq * t) + 0.3 * self._white_noise()
                # 4-bit quantization
                held_sample = round(raw * 8.0) / 8.0

            env = math.exp(-t * 7.0)
            val = held_sample * env
            samples.append((val, val))

        return samples

    def gen_glitch_static(self) -> list[tuple[float, float]]:
        """Glitch: CRT electromagnetic interference burst with sync-loss dropouts."""
        duration = 0.40
        n = int(SAMPLE_RATE * duration)
        samples: list[tuple[float, float]] = []

        hp_state = 0.0
        alpha_hp = 0.85  # High-pass filter coefficient

        for i in range(n):
            t = i / SAMPLE_RATE
            white = self._white_noise()
            # Simple high-pass
            hp = white - hp_state
            hp_state += (1.0 - alpha_hp) * hp

            # Intermittent dropouts (simulating CRT frame sync loss)
            gate = 0.0 if (0.08 <= t <= 0.10 or 0.22 <= t <= 0.24) else 1.0
            env = math.exp(-t * 5.5) * gate

            val = hp * env
            samples.append((val, val))

        return samples

    def gen_glitch_corruption(self) -> list[tuple[float, float]]:
        """Glitch: Warped tape flutter and corrupted frequency modulation."""
        duration = 0.60
        n = int(SAMPLE_RATE * duration)
        samples: list[tuple[float, float]] = []

        for i in range(n):
            t = i / SAMPLE_RATE
            # Chaotic FM
            mod = math.sin(2.0 * math.pi * 37.0 * t) * 180.0
            carrier = math.sin(2.0 * math.pi * (130.0 + mod) * t)

            # Sample & hold bit crushing
            quant = round(carrier * 6.0) / 6.0
            env = math.exp(-t * 3.5)

            val = quant * env
            samples.append((val, val))

        return samples

    # --- 4. Ghost Whispers (Nonverbal Sound Effects) ---

    def gen_whisper_spectral(self) -> list[tuple[float, float]]:
        """Whisper: Nonverbal breathy vocal formant sweep panning in stereo."""
        duration = 1.8
        n = int(SAMPLE_RATE * duration)
        samples: list[tuple[float, float]] = []

        # Stateful 2-pole resonant bandpass filters for vowel formants
        y1_l = y2_l = 0.0
        y1_r = y2_r = 0.0

        attack = int(SAMPLE_RATE * 0.4)
        release = int(SAMPLE_RATE * 0.6)
        env = self._fade_envelope(n, attack, release)

        for i in range(n):
            t = i / SAMPLE_RATE
            white_l = self._white_noise()
            white_r = self._white_noise()

            # Dynamic formant resonance around 800Hz & 1800Hz
            f_center = 750.0 + 300.0 * math.sin(2.0 * math.pi * 0.8 * t)
            bw = 80.0
            r_coeff = 1.0 - (math.pi * bw / SAMPLE_RATE)
            theta = 2.0 * math.pi * f_center / SAMPLE_RATE

            # Resonator update
            new_y_l = (
                2.0 * r_coeff * math.cos(theta) * y1_l
                - (r_coeff**2) * y2_l
                + (1.0 - r_coeff) * white_l
            )
            y2_l = y1_l
            y1_l = new_y_l

            new_y_r = (
                2.0 * r_coeff * math.cos(theta) * y1_r
                - (r_coeff**2) * y2_r
                + (1.0 - r_coeff) * white_r
            )
            y2_r = y1_r
            y1_r = new_y_r

            # Slow stereo pan from left to right
            pan = t / duration  # 0.0 (left) to 1.0 (right)
            left = y1_l * (1.0 - pan) * env[i]
            right = y1_r * pan * env[i]

            samples.append((left, right))

        return samples

    def gen_whisper_breath(self) -> list[tuple[float, float]]:
        """Whisper: Sudden cold nonverbal exhalation envelope."""
        duration = 1.4
        n = int(SAMPLE_RATE * duration)
        samples: list[tuple[float, float]] = []

        lp_l = 0.0
        lp_r = 0.0

        attack = int(SAMPLE_RATE * 0.25)
        release = int(SAMPLE_RATE * 0.8)
        env = self._fade_envelope(n, attack, release)

        for i in range(n):
            # Low pass filtered noise at 900Hz
            alpha = (2.0 * math.pi * 900.0) / SAMPLE_RATE
            lp_l += alpha * (self._white_noise() - lp_l)
            lp_r += alpha * (self._white_noise() - lp_r)

            left = lp_l * env[i]
            right = lp_r * env[i]
            samples.append((left, right))

        return samples

    def gen_whisper_murmur(self) -> list[tuple[float, float]]:
        """Whisper: Low, unintelligible vocal harmonic murmur."""
        duration = 2.0
        n = int(SAMPLE_RATE * duration)
        samples: list[tuple[float, float]] = []

        attack = int(SAMPLE_RATE * 0.5)
        release = int(SAMPLE_RATE * 0.7)
        env = self._fade_envelope(n, attack, release)

        for i in range(n):
            t = i / SAMPLE_RATE
            # 130Hz vocal chord fundamental with subtle pitch undulation
            f0 = 130.0 + 6.0 * math.sin(2.0 * math.pi * 3.5 * t)
            harmonics = (
                math.sin(2.0 * math.pi * f0 * t)
                + 0.6 * math.sin(2.0 * math.pi * 2.0 * f0 * t)
                + 0.4 * math.sin(2.0 * math.pi * 3.0 * f0 * t)
                + 0.2 * math.sin(2.0 * math.pi * 4.0 * f0 * t)
            )

            # Tremolo modulation
            trem = 0.6 + 0.4 * math.sin(2.0 * math.pi * 4.0 * t)
            left = (harmonics * 0.6 + 0.15 * self._white_noise()) * trem * env[i]
            right = (harmonics * 0.58 + 0.15 * self._white_noise()) * trem * env[i]
            samples.append((left, right))

        return samples

    # --- 5. Notifications & Safety Interceptions ---

    def gen_notification_alert(self) -> list[tuple[float, float]]:
        """Notification: Dissonant two-tone bell strike (minor second interval)."""
        duration = 0.8
        n = int(SAMPLE_RATE * duration)
        samples: list[tuple[float, float]] = []

        for i in range(n):
            t = i / SAMPLE_RATE
            # Dissonant pair: 440Hz + 466.16Hz (A4 + Bb4)
            decay = math.exp(-t * 4.5)
            chime = (
                math.sin(2.0 * math.pi * 440.0 * t)
                + math.sin(2.0 * math.pi * 466.16 * t)
                + 0.3 * math.sin(2.0 * math.pi * 880.0 * t)
            ) * decay

            samples.append((chime, chime))

        return samples

    def gen_notification_ping(self) -> list[tuple[float, float]]:
        """Notification: Crystalline hollow glass ping."""
        duration = 0.6
        n = int(SAMPLE_RATE * duration)
        samples: list[tuple[float, float]] = []

        for i in range(n):
            t = i / SAMPLE_RATE
            decay = math.exp(-t * 6.5)
            ping = (
                math.sin(2.0 * math.pi * 1174.66 * t)  # D6
                + 0.4 * math.sin(2.0 * math.pi * 2349.32 * t)
                + 0.15 * math.sin(2.0 * math.pi * 3523.98 * t)
            ) * decay
            samples.append((ping, ping))

        return samples

    def gen_guardian_intercept(self) -> list[tuple[float, float]]:
        """Haunt: Heavy metallic clamp halting command execution."""
        duration = 1.0
        n = int(SAMPLE_RATE * duration)
        samples: list[tuple[float, float]] = []

        for i in range(n):
            t = i / SAMPLE_RATE
            # Heavy low thud (65Hz pitch dropped)
            f_thud = 65.0 * math.exp(-t * 12.0) + 40.0
            thud = math.sin(2.0 * math.pi * f_thud * t) * math.exp(-t * 6.0)

            # Metallic clamp ring (320Hz + 580Hz)
            clamp_ring = (
                math.sin(2.0 * math.pi * 320.0 * t) + 0.7 * math.sin(2.0 * math.pi * 580.0 * t)
            ) * math.exp(-t * 8.0)

            # Gate shut at 0.7s
            gate = 1.0 if t < 0.7 else max(0.0, 1.0 - (t - 0.7) * 8.0)
            val = (thud * 0.7 + clamp_ring * 0.45) * gate
            samples.append((val, val))

        return samples

    def gen_guardian_approved(self) -> list[tuple[float, float]]:
        """Haunt: Mechanical click and harmonic seal release."""
        duration = 0.7
        n = int(SAMPLE_RATE * duration)
        samples: list[tuple[float, float]] = []

        for i in range(n):
            t = i / SAMPLE_RATE
            # Double click: primary at 0.04s, secondary at 0.12s
            click1 = math.exp(-abs(t - 0.04) * 120.0)
            click2 = math.exp(-abs(t - 0.12) * 100.0) * 0.7
            clicks = click1 + click2

            # Warm harmonic resolution chime (440Hz -> 554.37Hz)
            t_chime = max(0.0, t - 0.12)
            chime = (
                (
                    math.sin(2.0 * math.pi * 554.37 * t_chime)
                    + 0.4 * math.sin(2.0 * math.pi * 880.0 * t_chime)
                )
                * math.exp(-t_chime * 5.0)
                if t >= 0.12
                else 0.0
            )

            val = clicks * 0.6 + chime * 0.5
            samples.append((val, val))

        return samples

    def gen_guardian_blocked(self) -> list[tuple[float, float]]:
        """Haunt: Harsh industrial barricade strike."""
        duration = 1.2
        n = int(SAMPLE_RATE * duration)
        samples: list[tuple[float, float]] = []

        for i in range(n):
            t = i / SAMPLE_RATE
            # Heavy metal plate impact
            impact = (
                math.sin(2.0 * math.pi * 55.0 * t)
                + 0.8 * math.sin(2.0 * math.pi * 175.0 * t)
                + 0.5 * math.sin(2.0 * math.pi * 310.0 * t)
                + 0.3 * math.sin(2.0 * math.pi * 780.0 * t)
            ) * math.exp(-t * 3.8)

            noise = self._white_noise() * math.exp(-t * 18.0) * 0.5
            val = impact * 0.7 + noise
            samples.append((val, val))

        return samples

    # --- 6. Atmospheric & Haunt Events ---

    def gen_coding_success(self) -> list[tuple[float, float]]:
        """Haunt: Ethereal ascending spectral chord resolution."""
        duration = 1.5
        n = int(SAMPLE_RATE * duration)
        samples: list[tuple[float, float]] = []

        attack = int(SAMPLE_RATE * 0.1)
        release = int(SAMPLE_RATE * 0.6)
        env = self._fade_envelope(n, attack, release)

        chord_freqs = [220.0, 329.63, 440.0, 554.37, 659.25]  # A-major 9th

        for i in range(n):
            t = i / SAMPLE_RATE
            chime = 0.0
            for idx, f in enumerate(chord_freqs):
                delay = idx * 0.06
                t_note = max(0.0, t - delay)
                note_env = math.exp(-t_note * 2.8) if t >= delay else 0.0
                chime += math.sin(2.0 * math.pi * f * t_note) * note_env

            left = chime * 0.22 * env[i]
            right = chime * 0.24 * env[i]
            samples.append((left, right))

        return samples

    def gen_app_error(self) -> list[tuple[float, float]]:
        """Haunt: Discordant screech and digital tritone crash."""
        duration = 0.8
        n = int(SAMPLE_RATE * duration)
        samples: list[tuple[float, float]] = []

        for i in range(n):
            t = i / SAMPLE_RATE
            # Tritone screech (220Hz + 311.13Hz)
            decay = math.exp(-t * 4.5)
            f_slide = 220.0 * math.exp(-t * 3.0)
            screech = (
                math.sin(2.0 * math.pi * f_slide * t)
                + math.sin(2.0 * math.pi * (f_slide * 1.414) * t)
                + 0.25 * self._white_noise()
            ) * decay

            samples.append((screech, screech))

        return samples

    def gen_keystroke_haunt(self) -> list[tuple[float, float]]:
        """Haunt: Subterranean mechanical typewriter keystroke impact."""
        duration = 0.45
        n = int(SAMPLE_RATE * duration)
        samples: list[tuple[float, float]] = []

        for i in range(n):
            t = i / SAMPLE_RATE
            # Sharp transient
            strike = math.exp(-t * 80.0) * 0.8
            # Hollow acoustic cavity body (210Hz)
            resonance = math.sin(2.0 * math.pi * 210.0 * t) * math.exp(-t * 9.0)

            val = strike + resonance * 0.5
            samples.append((val, val))

        return samples

    def gen_mood_shift(self) -> list[tuple[float, float]]:
        """Haunt: Ominous sub-bass pitch bend and atmospheric pressure shift."""
        duration = 2.2
        n = int(SAMPLE_RATE * duration)
        samples: list[tuple[float, float]] = []

        attack = int(SAMPLE_RATE * 0.4)
        release = int(SAMPLE_RATE * 0.7)
        env = self._fade_envelope(n, attack, release)

        for i in range(n):
            t = i / SAMPLE_RATE
            # Pitch bending down from 82Hz to 41Hz
            freq = 41.0 + 41.0 * (1.0 - (i / n))
            phase = 2.0 * math.pi * freq * t

            left = math.sin(phase) * env[i]
            right = math.sin(phase + 0.4) * env[i]  # Spatial phase shift
            samples.append((left, right))

        return samples


ASSET_SPECS = [
    # (event_id, relative_path, generator_func_name, channels, loop, description)
    (
        "startup",
        "sfx/startup.wav",
        "gen_startup",
        2,
        False,
        "Spectral terminal boot swell and chime",
    ),
    ("shutdown", "sfx/shutdown.wav", "gen_shutdown", 2, False, "Terminal dissolution power-down"),
    (
        "ambient_dark_hum",
        "ambient/dark_hum.wav",
        "gen_ambient_dark_hum",
        2,
        True,
        "Subterranean dark drone loop",
    ),
    (
        "ambient_cold_wind",
        "ambient/cold_wind.wav",
        "gen_ambient_cold_wind",
        2,
        True,
        "Chilling draft howling wind loop",
    ),
    (
        "ambient_distant_thunder",
        "ambient/distant_thunder.wav",
        "gen_ambient_distant_thunder",
        2,
        True,
        "Distant storm sub-bass rumble",
    ),
    (
        "glitch_digital",
        "glitch/digital_glitch.wav",
        "gen_glitch_digital",
        1,
        False,
        "Bit-crushed digital fracture",
    ),
    (
        "glitch_static",
        "glitch/static_burst.wav",
        "gen_glitch_static",
        1,
        False,
        "CRT electromagnetic static burst",
    ),
    (
        "glitch_corruption",
        "glitch/corruption_artifact.wav",
        "gen_glitch_corruption",
        1,
        False,
        "Memory corruption artifact",
    ),
    (
        "whisper_spectral",
        "whisper/spectral_whisper.wav",
        "gen_whisper_spectral",
        2,
        False,
        "Spectral nonverbal whisper sweep",
    ),
    (
        "whisper_breath",
        "whisper/chilling_breath.wav",
        "gen_whisper_breath",
        2,
        False,
        "Cold nonverbal exhalation envelope",
    ),
    (
        "whisper_murmur",
        "whisper/eerie_murmur.wav",
        "gen_whisper_murmur",
        2,
        False,
        "Incomprehensible vocal harmonic murmur",
    ),
    (
        "notification_alert",
        "sfx/notification_alert.wav",
        "gen_notification_alert",
        1,
        False,
        "Ghost warning dissonant bell strike",
    ),
    (
        "notification_ping",
        "sfx/notification_ping.wav",
        "gen_notification_ping",
        1,
        False,
        "Resonant crystalline terminal ping",
    ),
    (
        "guardian_intercept",
        "haunt/guardian_intercept.wav",
        "gen_guardian_intercept",
        1,
        False,
        "Heavy metallic clamp halting command",
    ),
    (
        "guardian_approved",
        "haunt/guardian_approved.wav",
        "gen_guardian_approved",
        1,
        False,
        "Mechanical seal release chime",
    ),
    (
        "guardian_blocked",
        "haunt/guardian_blocked.wav",
        "gen_guardian_blocked",
        1,
        False,
        "Harsh barricade strike",
    ),
    (
        "coding_success",
        "haunt/coding_success.wav",
        "gen_coding_success",
        2,
        False,
        "Supernatural resolution ascending chord",
    ),
    (
        "app_error",
        "haunt/app_error.wav",
        "gen_app_error",
        1,
        False,
        "Discordant glitch screech stinger",
    ),
    (
        "keystroke_haunt",
        "haunt/keystroke_haunt.wav",
        "gen_keystroke_haunt",
        1,
        False,
        "Subterranean keystroke impact",
    ),
    (
        "mood_shift",
        "haunt/mood_shift.wav",
        "gen_mood_shift",
        2,
        False,
        "Atmospheric pressure shift sub-bass bend",
    ),
]


def generate_all_assets(output_dir: Path, force: bool = False, seed: int = 42) -> dict[str, object]:
    """Generate all 20 canonical horror sound effects deterministically."""
    synth = ProceduralHorrorSynth(seed=seed)
    manifest_entries: list[dict[str, object]] = []

    for event_id, rel_path, gen_name, channels, loop, desc in ASSET_SPECS:
        target_path = output_dir / rel_path
        if target_path.exists() and not force:
            print(f"[SKIP] {rel_path} already exists (use --force to overwrite).")
            continue

        gen_func = getattr(synth, gen_name)
        samples = gen_func()
        write_wav_file(target_path, samples, channels=channels, sample_rate=SAMPLE_RATE)

        duration = len(samples) / SAMPLE_RATE
        size_bytes = target_path.stat().st_size

        entry = {
            "asset_id": event_id,
            "relative_path": rel_path,
            "event_id": event_id,
            "category": rel_path.split("/")[0],
            "duration_seconds": round(duration, 3),
            "sample_rate": SAMPLE_RATE,
            "channels": channels,
            "bit_depth": 16,
            "loopable": loop,
            "description": desc,
            "size_bytes": size_bytes,
            "source": "GhostTrace Original Procedural DSP Synthesis",
            "license": "MIT (Repository License)",
        }
        manifest_entries.append(entry)
        print(f"[GEN] {rel_path: <32} ({channels}ch, {duration:.2f}s, {size_bytes / 1024:.1f} KB)")

    # Save manifest
    manifest_path = output_dir / "ASSET_MANIFEST.json"
    manifest_data = {
        "version": "1.1.0",
        "description": "GhostTrace Original Dark Horror Sound Effects Manifest",
        "provenance": "100% Original Procedural Python DSP Synthesis",
        "license": "MIT License (Project Owned)",
        "sample_rate": SAMPLE_RATE,
        "format": "16-bit Linear PCM WAV",
        "total_assets": len(ASSET_SPECS),
        "assets": manifest_entries,
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    print(f"\nManifest successfully written to: {manifest_path}")
    return manifest_data


def main() -> None:
    parser = argparse.ArgumentParser(description="GhostTrace Procedural Horror Sound Generator")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("assets/audio"),
        help="Target output directory for sound assets (default: assets/audio)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing asset files",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic generation (default: 42)",
    )

    args = parser.parse_args()
    generate_all_assets(output_dir=args.output_dir, force=args.force, seed=args.seed)


if __name__ == "__main__":
    main()
