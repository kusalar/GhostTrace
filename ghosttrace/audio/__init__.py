"""GhostTrace audio and horror sound effects subsystem."""

from __future__ import annotations

from ghosttrace.audio.adapter import AudioEventAdapter, NotificationSeverity
from ghosttrace.audio.backend import AudioBackend, MiniAudioBackend, NullAudioBackend
from ghosttrace.audio.catalog import AudioCatalog
from ghosttrace.audio.exceptions import (
    AssetNotFoundError,
    AudioDisabledError,
    AudioError,
    AudioInitializationError,
    InvalidVolumeError,
)
from ghosttrace.audio.horror_director import (
    EVENT_PRIORITIES,
    AudioPriority,
    HorrorAudioDirector,
    HorrorIntensity,
    SuppressionReason,
)
from ghosttrace.audio.manager import AudioManager
from ghosttrace.audio.preferences import (
    AudioPreferences,
    apply_preferences_with_precedence,
    get_audio_preferences_path,
    load_audio_preferences,
    save_audio_preferences,
)
from ghosttrace.audio.schemas import (
    AudioCategory,
    AudioEventId,
    AudioPlaybackRequest,
    AudioStatus,
    SoundEffect,
)
from ghosttrace.audio.typing_effects import TYPING_MODE_PROFILES, TypingEffectsManager
from ghosttrace.audio.whisper_scheduler import WHISPER_MODE_PROFILES, WhisperScheduler

__all__ = [
    "EVENT_PRIORITIES",
    "TYPING_MODE_PROFILES",
    "WHISPER_MODE_PROFILES",
    "AssetNotFoundError",
    "AudioBackend",
    "AudioCatalog",
    "AudioCategory",
    "AudioDisabledError",
    "AudioError",
    "AudioEventAdapter",
    "AudioEventId",
    "AudioInitializationError",
    "AudioManager",
    "AudioPlaybackRequest",
    "AudioPreferences",
    "AudioPriority",
    "AudioStatus",
    "HorrorAudioDirector",
    "HorrorIntensity",
    "InvalidVolumeError",
    "MiniAudioBackend",
    "NotificationSeverity",
    "NullAudioBackend",
    "SoundEffect",
    "SuppressionReason",
    "TypingEffectsManager",
    "WhisperScheduler",
    "apply_preferences_with_precedence",
    "get_audio_preferences_path",
    "load_audio_preferences",
    "save_audio_preferences",
]
