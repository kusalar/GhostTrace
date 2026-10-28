"""Data schemas and type definitions for GhostTrace AI subsystem."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class ModelStatus(StrEnum):
    """Operational status of the local LLM model."""

    NOT_FOUND = "NOT_FOUND"
    UNLOADED = "UNLOADED"
    LOADING = "LOADING"
    READY = "READY"
    ERROR = "ERROR"
    UNAVAILABLE = "UNAVAILABLE"


class InferenceState(StrEnum):
    """Current inference engine execution state."""

    IDLE = "IDLE"
    BUSY = "BUSY"
    ERROR = "ERROR"


class ChatRole(StrEnum):
    """Role associated with a chat message."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    """A single message within a conversation."""

    role: ChatRole
    content: str


class ModelMetadata(BaseModel):
    """Metadata regarding configured model file and local runtime."""

    model_path: Path
    exists: bool
    file_size_bytes: int = 0
    file_size_mb: float = 0.0
    format: str = "GGUF"
    quantization: str = "Q4_K_M"
    status: ModelStatus = ModelStatus.UNLOADED
    error_message: str | None = None


class InferenceConfig(BaseModel):
    """Configuration parameters for llama.cpp inference execution."""

    context_size: int = Field(default=2048, ge=256, le=32768)
    max_tokens: int = Field(default=512, ge=1, le=4096)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, gt=0.0, le=1.0)
    threads: int = Field(default=2, ge=1, le=32)
    gpu_layers: int = Field(default=0, ge=0, le=128)
    batch_size: int = Field(default=128, ge=1, le=2048)


class InferenceResult(BaseModel):
    """Result of an inference request."""

    text: str
    finish_reason: str = "stop"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    duration_seconds: float = 0.0


class AIStatus(BaseModel):
    """Unified status snapshot of the AI subsystem."""

    runtime_available: bool
    runtime_version: str | None = None
    model_status: ModelStatus
    model_path: Path
    model_exists: bool
    is_loaded: bool
    is_busy: bool
    history_count: int
    context_size: int
    max_tokens: int
    threads: int
    gpu_layers: int
