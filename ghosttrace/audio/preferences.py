"""User audio preferences persistence and precedence management for GhostTrace."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, field_validator

from ghosttrace.config.settings import get_default_app_data_dir

if TYPE_CHECKING:
    from ghosttrace.config.settings import Settings

logger = logging.getLogger("ghosttrace.audio.preferences")

DEFAULT_PREFERENCES_FILENAME = "audio_preferences.json"


class AudioPreferences(BaseModel):
    """Persistent user preferences for the audio subsystem."""

    enabled: bool = Field(
        default=False,
        description="Whether audio subsystem is enabled by the user.",
    )
    volume: float = Field(
        default=0.50,
        ge=0.0,
        le=1.0,
        description="Master output volume between 0.0 and 1.0.",
    )
    ambient_volume: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description="Ambient background volume between 0.0 and 1.0.",
    )
    muted: bool = Field(
        default=False,
        description="Whether audio output is temporarily muted.",
    )
    haunted_keystrokes_enabled: bool = Field(
        default=False,
        description="Whether haunted typing sound effects are enabled.",
    )
    scheduled_whispers_enabled: bool = Field(
        default=False,
        description="Whether scheduled whisper sound effects are enabled.",
    )

    @field_validator("volume", "ambient_volume")
    @classmethod
    def validate_volume_range(cls, v: float) -> float:
        """Clamp or validate volume within [0.0, 1.0]."""
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"Volume {v} outside valid range [0.0, 1.0].")
        return round(float(v), 3)


def get_audio_preferences_path(settings: Settings | None = None) -> Path:
    """Return the absolute path to the audio preferences file."""
    if settings is not None and getattr(settings, "app_data_dir", None):
        base_dir = Path(settings.app_data_dir)
    else:
        base_dir = get_default_app_data_dir()
    return (base_dir / DEFAULT_PREFERENCES_FILENAME).resolve()


def load_audio_preferences(path: Path | None = None) -> AudioPreferences:
    """Load persisted audio preferences from disk.

    Safely falls back to default values if the file does not exist,
    is corrupted, or contains invalid schemas.
    """
    pref_path = path if path is not None else get_audio_preferences_path()

    if not pref_path.is_file():
        return AudioPreferences()

    try:
        raw_text = pref_path.read_text(encoding="utf-8")
        data = json.loads(raw_text)
        if not isinstance(data, dict):
            logger.warning("Audio preferences file contains non-dict JSON; using defaults.")
            return AudioPreferences()
        return AudioPreferences.model_validate(data)
    except Exception as exc:
        logger.warning(
            "Failed to load audio preferences from %s (%s). Falling back to safe defaults.",
            pref_path,
            exc,
        )
        return AudioPreferences()


def save_audio_preferences(prefs: AudioPreferences, path: Path | None = None) -> bool:
    """Persist audio preferences to disk atomically and safely.

    Args:
        prefs: AudioPreferences instance to save.
        path: Optional explicit target path.

    Returns:
        True if successfully saved, False otherwise.
    """
    pref_path = path if path is not None else get_audio_preferences_path()

    try:
        pref_path.parent.mkdir(parents=True, exist_ok=True)
        json_content = json.dumps(prefs.model_dump(), indent=2)
        pref_path.write_text(json_content, encoding="utf-8")
        logger.debug("Persisted audio preferences to %s: %s", pref_path, prefs.model_dump())
        return True
    except Exception as exc:
        logger.warning("Could not persist audio preferences to %s: %s", pref_path, exc)
        return False


def apply_preferences_with_precedence(
    settings: Settings,
    prefs: AudioPreferences | None = None,
) -> dict[str, Any]:
    """Calculate effective audio configuration respecting strict precedence rules.

    Precedence order:
    1. Explicit environment variables (e.g. GHOSTTRACE_AUDIO_ENABLED).
       - Critical: If GHOSTTRACE_AUDIO_ENABLED=false is explicitly set in env,
         persisted preferences cannot override it to true.
    2. Persisted preferences from audio_preferences.json.
    3. Default application settings.

    Returns:
        Dictionary with resolved keys: 'enabled', 'volume', 'ambient_volume', 'muted'.
    """
    if prefs is None:
        prefs = load_audio_preferences(get_audio_preferences_path(settings))

    # Check environment variable overrides
    env_enabled_raw = os.environ.get("GHOSTTRACE_AUDIO_ENABLED")
    env_volume_raw = os.environ.get("GHOSTTRACE_AUDIO_VOLUME")
    env_ambient_vol_raw = os.environ.get("GHOSTTRACE_AUDIO_AMBIENT_VOLUME")
    env_muted_raw = os.environ.get("GHOSTTRACE_AUDIO_MUTED")

    # 1. Enabled resolution
    if env_enabled_raw is not None:
        # Explicit env var always wins
        effective_enabled = env_enabled_raw.strip().lower() in ("true", "1", "yes", "on")
    elif "audio_enabled" in getattr(settings, "model_fields_set", set()):
        # Explicitly passed parameter to Settings()
        effective_enabled = settings.audio_enabled
    else:
        # Persisted preference
        effective_enabled = prefs.enabled

    # 2. Volume resolution
    if env_volume_raw is not None:
        try:
            effective_volume = max(0.0, min(1.0, float(env_volume_raw)))
        except ValueError:
            effective_volume = settings.audio_volume
    elif "audio_volume" in getattr(settings, "model_fields_set", set()):
        effective_volume = settings.audio_volume
    else:
        effective_volume = prefs.volume

    # 3. Ambient volume resolution
    if env_ambient_vol_raw is not None:
        try:
            effective_ambient_volume = max(0.0, min(1.0, float(env_ambient_vol_raw)))
        except ValueError:
            effective_ambient_volume = settings.audio_ambient_volume
    elif "audio_ambient_volume" in getattr(settings, "model_fields_set", set()):
        effective_ambient_volume = settings.audio_ambient_volume
    else:
        effective_ambient_volume = prefs.ambient_volume

    # 4. Muted resolution
    if env_muted_raw is not None:
        effective_muted = env_muted_raw.strip().lower() in ("true", "1", "yes", "on")
    else:
        effective_muted = prefs.muted

    # 5. Haunted keystrokes resolution
    env_haunted_raw = os.environ.get("GHOSTTRACE_AUDIO_HAUNTED_KEYSTROKES_ENABLED")
    if env_haunted_raw is not None:
        effective_haunted = env_haunted_raw.strip().lower() in ("true", "1", "yes", "on")
    elif "audio_haunted_keystrokes_enabled" in getattr(settings, "model_fields_set", set()):
        effective_haunted = settings.audio_haunted_keystrokes_enabled
    else:
        effective_haunted = prefs.haunted_keystrokes_enabled

    # 6. Scheduled whispers resolution
    env_whispers_raw = os.environ.get("GHOSTTRACE_AUDIO_SCHEDULED_WHISPERS_ENABLED")
    if env_whispers_raw is not None:
        effective_whispers = env_whispers_raw.strip().lower() in ("true", "1", "yes", "on")
    elif "audio_scheduled_whispers_enabled" in getattr(settings, "model_fields_set", set()):
        effective_whispers = settings.audio_scheduled_whispers_enabled
    else:
        effective_whispers = prefs.scheduled_whispers_enabled

    return {
        "enabled": effective_enabled,
        "volume": effective_volume,
        "ambient_volume": effective_ambient_volume,
        "muted": effective_muted,
        "haunted_keystrokes_enabled": effective_haunted,
        "scheduled_whispers_enabled": effective_whispers,
    }
