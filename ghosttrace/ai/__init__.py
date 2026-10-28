"""GhostTrace local AI integration subsystem powered by llama.cpp and Qwen2.5 GGUF."""

from ghosttrace.ai.conversation import ConversationManager
from ghosttrace.ai.engine import AIEngine
from ghosttrace.ai.exceptions import (
    AIError,
    InvalidModelError,
    ModelBusyError,
    ModelLoadError,
    ModelNotFoundError,
    RuntimeUnavailableError,
)
from ghosttrace.ai.inference import InferenceEngine
from ghosttrace.ai.model_manager import ModelManager
from ghosttrace.ai.schemas import AIStatus, ModelMetadata, ModelStatus

__all__ = [
    "AIEngine",
    "AIError",
    "AIStatus",
    "ConversationManager",
    "InferenceEngine",
    "InvalidModelError",
    "ModelBusyError",
    "ModelLoadError",
    "ModelManager",
    "ModelMetadata",
    "ModelNotFoundError",
    "ModelStatus",
    "RuntimeUnavailableError",
]
