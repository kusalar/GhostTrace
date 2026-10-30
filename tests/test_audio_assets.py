"""Comprehensive verification tests for GhostTrace original horror sound asset library."""

from __future__ import annotations

import json
import struct
import wave
from pathlib import Path

from ghosttrace.audio.catalog import DEFAULT_CATALOG, AudioCatalog
from ghosttrace.audio.manager import AudioManager
from ghosttrace.audio.schemas import AudioEventId
from ghosttrace.config.settings import Settings
from ghosttrace.terminal.app import GhostTraceApp
from tools.generate_audio_assets import (
    ASSET_SPECS,
    SAMPLE_RATE,
    generate_all_assets,
)


class TestAudioAssetLibrary:
    """Test suite validating concrete sound asset files and metadata."""

    @property
    def audio_dir(self) -> Path:
        return Path("assets/audio").resolve()

    @property
    def manifest_path(self) -> Path:
        return self.audio_dir / "ASSET_MANIFEST.json"

    def test_asset_manifest_exists_and_valid(self) -> None:
        """ASSET_MANIFEST.json must exist and be valid JSON with 20 registered assets."""
        assert self.manifest_path.is_file(), "ASSET_MANIFEST.json must exist in assets/audio"

        with open(self.manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)

        assert manifest["version"] == "1.1.0"
        assert manifest["sample_rate"] == 44100
        assert manifest["format"] == "16-bit Linear PCM WAV"
        assert manifest["total_assets"] == 20
        assert len(manifest["assets"]) == 20

    def test_all_catalog_assets_exist_on_disk(self) -> None:
        """Every sound effect in DEFAULT_CATALOG must exist as a real WAV file on disk."""
        catalog = AudioCatalog()
        presence = catalog.validate_assets_present(self.audio_dir)

        missing = [event_id for event_id, is_present in presence.items() if not is_present]
        assert not missing, f"Missing audio asset files for canonical events: {missing}"
        assert len(presence) == 20

    def test_all_wav_headers_and_technical_specifications(self) -> None:
        """All WAV files must be valid 16-bit PCM at 44.1 kHz with correct channels."""
        with open(self.manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)

        for asset in manifest["assets"]:
            rel_path = asset["relative_path"]
            wav_path = self.audio_dir / rel_path
            assert wav_path.is_file(), f"Asset {rel_path} does not exist"

            with wave.open(str(wav_path), "rb") as wf:
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                framerate = wf.getframerate()
                n_frames = wf.getnframes()

                assert n_channels == asset["channels"], f"{rel_path}: channel mismatch"
                assert sampwidth == 2, f"{rel_path}: must be 16-bit PCM (sampwidth=2)"
                assert framerate == SAMPLE_RATE, f"{rel_path}: sample rate must be 44100"
                assert n_frames > 0, f"{rel_path}: file contains zero audio frames"

                duration = n_frames / framerate
                diff = abs(duration - asset["duration_seconds"])
                msg = f"{rel_path}: duration {duration} does not match {asset['duration_seconds']}"
                assert diff < 0.05, msg
                assert 0.2 <= duration <= 8.0, f"{rel_path}: duration {duration}s outside range"

    def test_audio_frames_not_empty_or_clipping(self) -> None:
        """Inspect actual sample amplitudes: non-silent, non-zero RMS, and no integer clipping."""
        for event_id, sound in DEFAULT_CATALOG.items():
            wav_path = self.audio_dir / sound.relative_path
            with wave.open(str(wav_path), "rb") as wf:
                raw_bytes = wf.readframes(wf.getnframes())
                fmt = f"<{len(raw_bytes) // 2}h"
                samples = struct.unpack(fmt, raw_bytes)

                max_amp = max(abs(s) for s in samples)
                assert max_amp > 1000, f"{event_id}: sound is completely silent"
                assert max_amp <= 32767, f"{event_id}: sample clipping detected"
                # Check that max amplitude respects headroom (under ~28000 out of 32767)
                assert max_amp < 30000, (
                    f"{event_id}: peak amplitude {max_amp} exceeds headroom ceiling"
                )

    def test_manifest_entries_map_to_canonical_event_ids(self) -> None:
        """Every entry in ASSET_MANIFEST.json must correspond to a valid AudioEventId."""
        with open(self.manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)

        valid_event_ids = {e.value for e in AudioEventId}
        for entry in manifest["assets"]:
            assert entry["event_id"] in valid_event_ids, (
                f"Unknown event_id {entry['event_id']} in manifest"
            )

    def test_ambient_assets_are_loopable(self) -> None:
        """Ambient category assets must be flagged as loopable and have duration >= 5.0s."""
        catalog = AudioCatalog()
        for sound in catalog.list_by_category(
            catalog.get_sound(AudioEventId.AMBIENT_DARK_HUM).category
        ):
            assert sound.loop is True
            wav_path = self.audio_dir / sound.relative_path
            with wave.open(str(wav_path), "rb") as wf:
                duration = wf.getnframes() / wf.getframerate()
                assert duration >= 5.0, (
                    f"{sound.relative_path}: ambient duration {duration}s too short"
                )

    def test_audio_manager_resolves_all_20_assets(self) -> None:
        """AudioManager must resolve concrete on-disk Path for all 20 canonical event IDs."""
        settings = Settings(audio_asset_dir=self.audio_dir)
        manager = AudioManager(settings)

        for event in AudioEventId:
            resolved = manager.resolve_asset_path(event)
            assert resolved is not None, f"Failed to resolve asset path for {event}"
            assert resolved.is_file(), f"Resolved path for {event} does not exist: {resolved}"

        manager.shutdown()

    def test_generator_determinism(self, tmp_path: Path) -> None:
        """Generator script must produce byte-for-byte deterministic output for fixed seed."""
        out1 = tmp_path / "run1"
        out2 = tmp_path / "run2"

        generate_all_assets(output_dir=out1, force=True, seed=42)
        generate_all_assets(output_dir=out2, force=True, seed=42)

        for spec in ASSET_SPECS:
            rel_path = spec[1]
            bytes1 = (out1 / rel_path).read_bytes()
            bytes2 = (out2 / rel_path).read_bytes()
            assert bytes1 == bytes2, f"Nondeterministic output detected for {rel_path}"

    def test_no_playback_initialized_at_runtime(self) -> None:
        """Importing audio package and running GhostTraceApp initializes no playback."""
        settings = Settings(audio_enabled=False, audio_asset_dir=self.audio_dir)
        app = GhostTraceApp(settings=settings)

        # Manager status must confirm null backend and no active voices
        status = app.audio_manager.get_status()
        assert status.enabled is False
        assert status.backend_type == "null"
        assert status.active_voices_count == 0
        assert status.asset_dir_exists is True

        app.audio_manager.shutdown()
