"""Declarative sound effects catalog for GhostTrace dark horror audio."""

from __future__ import annotations

from typing import Final

from ghosttrace.audio.schemas import AudioCategory, AudioEventId, SoundEffect

# Default dark horror sound catalog entries
DEFAULT_CATALOG: Final[dict[AudioEventId, SoundEffect]] = {
    # System Lifecycle
    AudioEventId.STARTUP: SoundEffect(
        id=AudioEventId.STARTUP,
        name="Spectral Terminal Boot",
        category=AudioCategory.SYSTEM,
        relative_path="sfx/startup.wav",
        description="Eerie sub-bass swell and decaying high-frequency terminal chime.",
        loop=False,
        default_volume=0.8,
    ),
    AudioEventId.SHUTDOWN: SoundEffect(
        id=AudioEventId.SHUTDOWN,
        name="Terminal Dissolution",
        category=AudioCategory.SYSTEM,
        relative_path="sfx/shutdown.wav",
        description="Low resonant power-down with ghostly fading harmonic trail.",
        loop=False,
        default_volume=0.7,
    ),
    # Ambient Background
    AudioEventId.AMBIENT_DARK_HUM: SoundEffect(
        id=AudioEventId.AMBIENT_DARK_HUM,
        name="Subterranean Drone",
        category=AudioCategory.AMBIENT,
        relative_path="ambient/dark_hum.ogg",
        description="Subtle, low-frequency atmospheric rumble and room-tone decay.",
        loop=True,
        default_volume=0.4,
    ),
    AudioEventId.AMBIENT_COLD_WIND: SoundEffect(
        id=AudioEventId.AMBIENT_COLD_WIND,
        name="Chilling Draft",
        category=AudioCategory.AMBIENT,
        relative_path="ambient/cold_wind.ogg",
        description="Distantly howling wind whistling through deserted architecture.",
        loop=True,
        default_volume=0.3,
    ),
    AudioEventId.AMBIENT_DISTANT_THUNDER: SoundEffect(
        id=AudioEventId.AMBIENT_DISTANT_THUNDER,
        name="Distant Storm Rumble",
        category=AudioCategory.AMBIENT,
        relative_path="ambient/distant_thunder.ogg",
        description="Muffled sub-bass thunder rolling beyond the terminal walls.",
        loop=True,
        default_volume=0.3,
    ),
    # Glitches & Digital Decay
    AudioEventId.GLITCH_DIGITAL: SoundEffect(
        id=AudioEventId.GLITCH_DIGITAL,
        name="Digital Fracture",
        category=AudioCategory.GLITCH,
        relative_path="glitch/digital_glitch.wav",
        description="Sharp bit-crushed micro-burst of corrupted digital audio.",
        loop=False,
        default_volume=0.6,
    ),
    AudioEventId.GLITCH_STATIC: SoundEffect(
        id=AudioEventId.GLITCH_STATIC,
        name="Spectral Static",
        category=AudioCategory.GLITCH,
        relative_path="glitch/static_burst.wav",
        description="Bursts of CRT radio static and electromagnetic interference.",
        loop=False,
        default_volume=0.5,
    ),
    AudioEventId.GLITCH_CORRUPTION: SoundEffect(
        id=AudioEventId.GLITCH_CORRUPTION,
        name="Memory Corruption Artifact",
        category=AudioCategory.GLITCH,
        relative_path="glitch/corruption_artifact.wav",
        description="Warped tape flutter and pitch-shifted digital fragmentation.",
        loop=False,
        default_volume=0.6,
    ),
    # Ghost Whispers (Nonverbal Sound Effects)
    AudioEventId.WHISPER_SPECTRAL: SoundEffect(
        id=AudioEventId.WHISPER_SPECTRAL,
        name="Spectral Whisper",
        category=AudioCategory.WHISPER,
        relative_path="whisper/spectral_whisper.wav",
        description="Chilling, nonverbal breathy sibilance panning across stereo space.",
        loop=False,
        default_volume=0.5,
    ),
    AudioEventId.WHISPER_BREATH: SoundEffect(
        id=AudioEventId.WHISPER_BREATH,
        name="Chilling Exhale",
        category=AudioCategory.WHISPER,
        relative_path="whisper/chilling_breath.wav",
        description="A cold, sudden intake of air behind the developer's neck.",
        loop=False,
        default_volume=0.4,
    ),
    AudioEventId.WHISPER_MURMUR: SoundEffect(
        id=AudioEventId.WHISPER_MURMUR,
        name="Incomprehensible Murmur",
        category=AudioCategory.WHISPER,
        relative_path="whisper/eerie_murmur.wav",
        description="Faint, unintelligible vocal harmonics buried in machine noise.",
        loop=False,
        default_volume=0.4,
    ),
    # Notifications & Safety Interceptions
    AudioEventId.NOTIFICATION_ALERT: SoundEffect(
        id=AudioEventId.NOTIFICATION_ALERT,
        name="Ghost Warning Cue",
        category=AudioCategory.NOTIFICATION,
        relative_path="sfx/notification_alert.wav",
        description="Dissonant bell strike signaling an impending supernatural or system event.",
        loop=False,
        default_volume=0.7,
    ),
    AudioEventId.NOTIFICATION_PING: SoundEffect(
        id=AudioEventId.NOTIFICATION_PING,
        name="Resonant Terminal Ping",
        category=AudioCategory.NOTIFICATION,
        relative_path="sfx/notification_ping.wav",
        description="Glass-like hollow ping indicating an incoming terminal update.",
        loop=False,
        default_volume=0.5,
    ),
    AudioEventId.GUARDIAN_INTERCEPT: SoundEffect(
        id=AudioEventId.GUARDIAN_INTERCEPT,
        name="Guardian Stasis Clamp",
        category=AudioCategory.HAUNT,
        relative_path="haunt/guardian_intercept.wav",
        description="Heavy metallic clamp and resonant thud halting command execution.",
        loop=False,
        default_volume=0.8,
    ),
    AudioEventId.GUARDIAN_APPROVED: SoundEffect(
        id=AudioEventId.GUARDIAN_APPROVED,
        name="Guardian Seal Release",
        category=AudioCategory.HAUNT,
        relative_path="haunt/guardian_approved.wav",
        description="Satisfying mechanical latch unlocking execution permissions.",
        loop=False,
        default_volume=0.6,
    ),
    AudioEventId.GUARDIAN_BLOCKED: SoundEffect(
        id=AudioEventId.GUARDIAN_BLOCKED,
        name="Guardian Barricade Strike",
        category=AudioCategory.HAUNT,
        relative_path="haunt/guardian_blocked.wav",
        description="Harsh industrial clang rejecting high-risk command execution.",
        loop=False,
        default_volume=0.8,
    ),
    # Atmospheric & Haunt Events
    AudioEventId.CODING_SUCCESS: SoundEffect(
        id=AudioEventId.CODING_SUCCESS,
        name="Supernatural Resolution",
        category=AudioCategory.HAUNT,
        relative_path="haunt/coding_success.wav",
        description="Ethereal ascending chord acknowledging completed code work.",
        loop=False,
        default_volume=0.6,
    ),
    AudioEventId.APP_ERROR: SoundEffect(
        id=AudioEventId.APP_ERROR,
        name="Glitch Stinger",
        category=AudioCategory.HAUNT,
        relative_path="haunt/app_error.wav",
        description="Sudden dissonant screech indicating an unhandled terminal exception.",
        loop=False,
        default_volume=0.7,
    ),
    AudioEventId.KEYSTROKE_HAUNT: SoundEffect(
        id=AudioEventId.KEYSTROKE_HAUNT,
        name="Haunted Keystroke Echo",
        category=AudioCategory.HAUNT,
        relative_path="haunt/keystroke_haunt.wav",
        description="Reverberant acoustic typewriter impact with subterranean decay.",
        loop=False,
        default_volume=0.4,
    ),
    AudioEventId.MOOD_SHIFT: SoundEffect(
        id=AudioEventId.MOOD_SHIFT,
        name="Atmospheric Pressure Shift",
        category=AudioCategory.HAUNT,
        relative_path="haunt/mood_shift.wav",
        description="Slow sub-bass pitch bend indicating a change in ghost personality mood.",
        loop=False,
        default_volume=0.5,
    ),
}


class AudioCatalog:
    """Registry managing sound effect definitions and categorization."""

    def __init__(self, catalog: dict[AudioEventId, SoundEffect] | None = None) -> None:
        self._entries: dict[AudioEventId, SoundEffect] = (
            dict(catalog) if catalog is not None else dict(DEFAULT_CATALOG)
        )

    def get_sound(self, event_id: AudioEventId | str) -> SoundEffect | None:
        """Retrieve the SoundEffect definition for the given event ID.

        Args:
            event_id: Canonical event enum or string key.

        Returns:
            SoundEffect if registered, None otherwise.
        """
        if isinstance(event_id, str):
            try:
                event_id = AudioEventId(event_id)
            except ValueError:
                return None
        return self._entries.get(event_id)

    def list_events(self) -> list[AudioEventId]:
        """Return all registered audio event identifiers."""
        return list(self._entries.keys())

    def list_by_category(self, category: AudioCategory) -> list[SoundEffect]:
        """Return all sound effects belonging to a specific category."""
        return [sound for sound in self._entries.values() if sound.category == category]

    def count(self) -> int:
        """Return total number of registered sound effects."""
        return len(self._entries)
