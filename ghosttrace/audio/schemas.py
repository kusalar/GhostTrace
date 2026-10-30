"""Pydantic schemas and typed data models for GhostTrace audio subsystem."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class AudioCategory(StrEnum):
    """Categorization of horror sound effects and atmospheric cues."""

    SYSTEM = "system"
    AMBIENT = "ambient"
    GLITCH = "glitch"
    WHISPER = "whisper"
    NOTIFICATION = "notification"
    HAUNT = "haunt"


class AudioEventId(StrEnum):
    """Canonical event identifiers for horror sound cues throughout GhostTrace."""

    # System Lifecycle
    STARTUP = "startup"
    SHUTDOWN = "shutdown"

    # Ambient Background
    AMBIENT_DARK_HUM = "ambient_dark_hum"
    AMBIENT_COLD_WIND = "ambient_cold_wind"
    AMBIENT_DISTANT_THUNDER = "ambient_distant_thunder"

    # Glitches & Digital Decay
    GLITCH_DIGITAL = "glitch_digital"
    GLITCH_STATIC = "glitch_static"
    GLITCH_CORRUPTION = "glitch_corruption"

    # Ghost Whispers (Strictly Nonverbal Sound Effects)
    WHISPER_SPECTRAL = "whisper_spectral"
    WHISPER_BREATH = "whisper_breath"
    WHISPER_MURMUR = "whisper_murmur"

    # Notifications & Safety Interceptions
    NOTIFICATION_ALERT = "notification_alert"
    NOTIFICATION_PING = "notification_ping"
    GUARDIAN_INTERCEPT = "guardian_intercept"
    GUARDIAN_APPROVED = "guardian_approved"
    GUARDIAN_BLOCKED = "guardian_blocked"

    # Atmospheric & Haunt Events
    CODING_SUCCESS = "coding_success"
    APP_ERROR = "app_error"
    KEYSTROKE_HAUNT = "keystroke_haunt"
    MOOD_SHIFT = "mood_shift"


class SoundEffect(BaseModel):
    """Metadata definition for a localized sound effect asset."""

    id: AudioEventId = Field(description="Unique audio event identifier.")
    name: str = Field(description="Human-readable title for the sound effect.")
    category: AudioCategory = Field(description="Audio taxonomy category.")
    relative_path: str = Field(description="Relative path within the audio asset directory.")
    description: str = Field(description="Aesthetic description and intended atmospheric role.")
    loop: bool = Field(default=False, description="Whether this sound effect loops continuously.")
    default_volume: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Default relative volume multiplier."
    )
    license_note: str = Field(
        default="CC0 Public Domain / Open Source Sound Effect",
        description="Licensing or attribution requirements for this asset.",
    )


class AudioPlaybackRequest(BaseModel):
    """Declarative request for asynchronous sound playback."""

    event_id: AudioEventId | str = Field(description="Target audio event identifier.")
    volume_scale: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Volume scaling factor for this playback."
    )
    loop: bool = Field(default=False, description="Whether to loop this playback.")
    interrupt_current: bool = Field(
        default=False, description="Whether to cut off conflicting sounds in the same category."
    )


class AudioStatus(BaseModel):
    """Operational telemetry and health of the audio subsystem."""

    enabled: bool = Field(description="Whether the audio subsystem is enabled in settings.")
    ambient_enabled: bool = Field(description="Whether ambient background audio loop is active.")
    volume: float = Field(description="Master volume level (0.0 to 1.0).")
    ambient_volume: float = Field(description="Ambient loop volume level (0.0 to 1.0).")
    backend_type: str = Field(description="Identifier of the active backend implementation.")
    backend_available: bool = Field(description="Whether backend hardware/drivers are usable.")
    asset_dir: str = Field(description="Absolute path to the configured audio assets directory.")
    asset_dir_exists: bool = Field(description="Whether the audio asset directory exists on disk.")
    known_events_count: int = Field(description="Total registered sound effects in the catalog.")
    is_muted: bool = Field(default=False, description="Whether audio playback is currently muted.")
    ambient_playing: bool = Field(
        default=False, description="Whether an ambient horror loop is currently streaming."
    )
    active_voices_count: int = Field(
        default=0, description="Number of sound effects currently playing."
    )
    haunted_keystrokes_enabled: bool = Field(
        default=False, description="Whether haunted typing sound effects are active."
    )
    scheduled_whispers_enabled: bool = Field(
        default=False, description="Whether scheduled whisper sound effects are active."
    )
