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
    app_version: str = "0.2.0"
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

    def model_post_init(self, __context: object) -> None:
        """Resolve computed directories and debug-level adjustments."""
        super().model_post_init(__context)
        # Convert path strings or relative paths to resolved Path instances
        object.__setattr__(self, "app_data_dir", Path(self.app_data_dir).resolve())
        object.__setattr__(self, "model_dir", Path(self.model_dir).resolve())

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
