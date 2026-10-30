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
from ghosttrace.audio.manager import AudioManager
from ghosttrace.audio.schemas import (
    AudioCategory,
    AudioEventId,
    AudioPlaybackRequest,
    AudioStatus,
    SoundEffect,
)

__all__ = [
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
    "AudioStatus",
    "InvalidVolumeError",
    "MiniAudioBackend",
    "NotificationSeverity",
    "NullAudioBackend",
    "SoundEffect",
]
