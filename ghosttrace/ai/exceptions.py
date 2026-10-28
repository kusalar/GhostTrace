"""Domain-specific exceptions for GhostTrace local AI subsystem."""

from __future__ import annotations


class AIError(Exception):
    """Base exception for all AI subsystem errors."""


class RuntimeUnavailableError(AIError):
    """Raised when llama-cpp-python or required native runtime is not installed."""


class ModelNotFoundError(AIError):
    """Raised when the configured model weights file does not exist."""


class InvalidModelError(AIError):
    """Raised when the model file path has an invalid extension or is unreadable."""


class ModelLoadError(AIError):
    """Raised when model weights cannot be loaded into memory."""


class InferenceError(AIError):
    """Raised when an error occurs during text generation."""


class ModelBusyError(AIError):
    """Raised when an inference request is initiated while another is already running."""
