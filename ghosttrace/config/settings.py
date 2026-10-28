"""Centralized configuration management for GhostTrace."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnvironment = Literal["development", "production", "testing"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def get_default_app_data_dir() -> Path:
    """Return platform-appropriate default user data directory outside the repository."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "GhostTrace"
    return Path.home() / ".ghosttrace"


class Settings(BaseSettings):
    """Centralized application settings validated with Pydantic Settings."""

    # Application Metadata
    app_name: str = "GhostTrace"
    app_version: str = "0.4.0"
    app_description: str = "Offline-first AI-powered haunted terminal companion."

    # Environment & Execution Mode
    env: AppEnvironment = Field(
        default="development",
        description="Application operational environment (development, production, testing).",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode and verbose operational output.",
    )
    log_level: LogLevel = Field(
        default="INFO",
        description="Application logging verbosity level.",
    )

    # Directories
    app_data_dir: Path = Field(
        default_factory=get_default_app_data_dir,
        description="Base directory for user data, logs, and persistent state outside the repo.",
    )
    model_dir: Path = Field(
        default_factory=lambda: Path("models").resolve(),
        description="Directory for local open-weight model weights.",
    )
    db_dir: Path | None = Field(
        default=None,
        description="Directory for SQLite databases. Defaults to {app_data_dir}/db.",
    )
    log_dir: Path | None = Field(
        default=None,
        description="Directory for rotating log files. Defaults to {app_data_dir}/logs.",
    )

    # Local AI Configuration (Step 03)
    model_path: Path | None = Field(
        default=None,
        description=(
            "Path to local GGUF model weights file. "
            "Defaults to {model_dir}/qwen2.5-1.5b-instruct-q4_k_m.gguf."
        ),
    )
    ai_enabled: bool = Field(
        default=True,
        description="Enable or disable local AI model inference.",
    )
    ai_context_size: int = Field(
        default=2048,
        description="Context window length in tokens for local model.",
    )
    ai_max_tokens: int = Field(
        default=512,
        description="Maximum tokens to generate per completion.",
    )
    ai_temperature: float = Field(
        default=0.7,
        description="Sampling temperature for text generation.",
    )
    ai_top_p: float = Field(
        default=0.9,
        description="Top-p nucleus sampling probability.",
    )
    ai_threads: int = Field(
        default=2,
        description="Number of CPU threads to allocate for inference.",
    )
    ai_gpu_layers: int = Field(
        default=0,
        description="Number of layers to offload to GPU (0 for CPU-only).",
    )
    ai_batch_size: int = Field(
        default=128,
        description="Batch size for prompt evaluation in tokens.",
    )
    ai_history_limit: int = Field(
        default=10,
        description="Maximum number of conversation exchanges retained in memory.",
    )

    # Ghost Personality & Behaviour Engine (Step 04)
    ghost_enabled: bool = Field(
        default=True,
        description="Enable or disable digital ghost personality engine.",
    )
    ghost_profile: str = Field(
        default="forgotten-machine",
        description=(
            "Active ghost personality profile (forgotten-machine, phantom-coder, guardian-spirit)."
        ),
    )
    ghost_mood_enabled: bool = Field(
        default=True,
        description="Enable session mood tracking and contextual transitions.",
    )

    model_config = SettingsConfigDict(
        env_prefix="GHOSTTRACE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("env", mode="before")
    @classmethod
    def normalize_and_validate_env(cls, value: object) -> str:
        if isinstance(value, str):
            normalized = value.strip().lower()
            allowed = ("development", "production", "testing")
            if normalized in allowed:
                return normalized
            msg = f"Invalid env '{value}'. Must be one of: {', '.join(allowed)}"
            raise ValueError(msg)
        return str(value)

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_and_validate_log_level(cls, value: object) -> str:
        if isinstance(value, str):
            normalized = value.strip().upper()
            allowed = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
            if normalized in allowed:
                return normalized
            msg = f"Invalid log_level '{value}'. Must be one of: {', '.join(allowed)}"
            raise ValueError(msg)
        return str(value)

    @field_validator("ghost_profile", mode="before")
    @classmethod
    def normalize_and_validate_ghost_profile(cls, value: object) -> str:
        if isinstance(value, str):
            normalized = value.strip().lower()
            allowed = ("forgotten-machine", "phantom-coder", "guardian-spirit")
            if normalized in allowed:
                return normalized
            msg = f"Invalid ghost_profile '{value}'. Must be one of: {', '.join(allowed)}"
            raise ValueError(msg)
        return str(value)

    @field_validator("ai_context_size")
    @classmethod
    def validate_ai_context_size(cls, value: int) -> int:
        if not (256 <= value <= 32768):
            msg = f"Invalid ai_context_size {value}. Must be between 256 and 32768."
            raise ValueError(msg)
        return value

    @field_validator("ai_max_tokens")
    @classmethod
    def validate_ai_max_tokens(cls, value: int) -> int:
        if not (1 <= value <= 4096):
            msg = f"Invalid ai_max_tokens {value}. Must be between 1 and 4096."
            raise ValueError(msg)
        return value

    @field_validator("ai_temperature")
    @classmethod
    def validate_ai_temperature(cls, value: float) -> float:
        if not (0.0 <= value <= 2.0):
            msg = f"Invalid ai_temperature {value}. Must be between 0.0 and 2.0."
            raise ValueError(msg)
        return value

    @field_validator("ai_top_p")
    @classmethod
    def validate_ai_top_p(cls, value: float) -> float:
        if not (0.0 < value <= 1.0):
            msg = f"Invalid ai_top_p {value}. Must be between 0.0 (exclusive) and 1.0."
            raise ValueError(msg)
        return value

    @field_validator("ai_threads")
    @classmethod
    def validate_ai_threads(cls, value: int) -> int:
        if not (1 <= value <= 32):
            msg = f"Invalid ai_threads {value}. Must be between 1 and 32."
            raise ValueError(msg)
        return value

    @field_validator("ai_gpu_layers")
    @classmethod
    def validate_ai_gpu_layers(cls, value: int) -> int:
        if value < 0:
            msg = f"Invalid ai_gpu_layers {value}. Must be non-negative."
            raise ValueError(msg)
        return value

    @field_validator("ai_batch_size")
    @classmethod
    def validate_ai_batch_size(cls, value: int) -> int:
        if not (1 <= value <= 2048):
            msg = f"Invalid ai_batch_size {value}. Must be between 1 and 2048."
            raise ValueError(msg)
        return value

    @field_validator("ai_history_limit")
    @classmethod
    def validate_ai_history_limit(cls, value: int) -> int:
        if not (1 <= value <= 100):
            msg = f"Invalid ai_history_limit {value}. Must be between 1 and 100."
            raise ValueError(msg)
        return value

    def model_post_init(self, __context: object) -> None:
        """Resolve computed directories and debug-level adjustments."""
        super().model_post_init(__context)
        # Convert path strings or relative paths to resolved Path instances
        object.__setattr__(self, "app_data_dir", Path(self.app_data_dir).resolve())
        object.__setattr__(self, "model_dir", Path(self.model_dir).resolve())

        if self.model_path is not None:
            object.__setattr__(self, "model_path", Path(self.model_path).resolve())
        else:
            default_model = (self.model_dir / "qwen2.5-1.5b-instruct-q4_k_m.gguf").resolve()
            object.__setattr__(self, "model_path", default_model)

        resolved_db_dir = (
            Path(self.db_dir).resolve()
            if self.db_dir is not None
            else (self.app_data_dir / "db").resolve()
        )
        object.__setattr__(self, "db_dir", resolved_db_dir)

        resolved_log_dir = (
            Path(self.log_dir).resolve()
            if self.log_dir is not None
            else (self.app_data_dir / "logs").resolve()
        )
        object.__setattr__(self, "log_dir", resolved_log_dir)

        # In debug mode, elevate log level if set to default INFO
        if self.debug and self.log_level == "INFO":
            object.__setattr__(self, "log_level", "DEBUG")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton instance of validated application settings."""
    return Settings()
