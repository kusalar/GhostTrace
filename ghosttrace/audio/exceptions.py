"""Domain-specific exceptions for GhostTrace audio and horror sound effects subsystem."""

from __future__ import annotations


class AudioError(Exception):
    """Base exception for all audio subsystem errors."""


class AudioInitializationError(AudioError):
    """Raised when an audio backend or audio device fails to initialize."""


class AudioDisabledError(AudioError):
    """Raised when an audio operation is attempted while audio is globally disabled."""


class AssetNotFoundError(AudioError):
    """Raised when a required sound effect asset file cannot be located on disk."""


class InvalidVolumeError(AudioError):
    """Raised when a volume parameter is outside the valid range [0.0, 1.0]."""
