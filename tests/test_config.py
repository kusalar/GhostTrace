"""Tests for the GhostTrace centralized configuration system."""

from pathlib import Path

import pytest
from ghosttrace.config.settings import Settings, get_default_app_data_dir, get_settings
from pydantic import ValidationError


def test_default_configuration() -> None:
    """Verify default configuration attributes and sensible fallback directories."""
    settings = Settings()

    assert settings.app_name == "GhostTrace"
    assert settings.app_version == "0.1.0"
    assert "haunted" in settings.app_description.lower()
    assert settings.env == "development"
    assert settings.debug is False
    assert settings.log_level == "INFO"

    # Verify directories are resolved Path instances
    assert isinstance(settings.app_data_dir, Path)
    assert isinstance(settings.model_dir, Path)
    assert isinstance(settings.db_dir, Path)
    assert isinstance(settings.log_dir, Path)

    # Subdirectories default to app_data_dir subpaths
    assert settings.db_dir == settings.app_data_dir / "db"
    assert settings.log_dir == settings.app_data_dir / "logs"


def test_environment_variable_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify configuration fields can be overridden via environment variables."""
    custom_app_data = tmp_path / "custom_app_data"
    custom_model_dir = tmp_path / "custom_models"
    custom_db_dir = tmp_path / "custom_db"
    custom_log_dir = tmp_path / "custom_logs"

    monkeypatch.setenv("GHOSTTRACE_ENV", "production")
    monkeypatch.setenv("GHOSTTRACE_DEBUG", "true")
    monkeypatch.setenv("GHOSTTRACE_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("GHOSTTRACE_APP_DATA_DIR", str(custom_app_data))
    monkeypatch.setenv("GHOSTTRACE_MODEL_DIR", str(custom_model_dir))
    monkeypatch.setenv("GHOSTTRACE_DB_DIR", str(custom_db_dir))
    monkeypatch.setenv("GHOSTTRACE_LOG_DIR", str(custom_log_dir))

    settings = Settings()

    assert settings.env == "production"
    assert settings.debug is True
    assert settings.log_level == "DEBUG"
    assert settings.app_data_dir == custom_app_data.resolve()
    assert settings.model_dir == custom_model_dir.resolve()
    assert settings.db_dir == custom_db_dir.resolve()
    assert settings.log_dir == custom_log_dir.resolve()


def test_debug_mode_elevates_default_log_level() -> None:
    """When debug is True and log_level is left at default INFO, it elevates to DEBUG."""
    settings = Settings(debug=True)
    assert settings.debug is True
    assert settings.log_level == "DEBUG"


def test_invalid_environment_raises_validation_error() -> None:
    """Invalid environment values must raise a Pydantic ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(env="staging")  # type: ignore[arg-type]

    assert "Invalid env 'staging'" in str(exc_info.value)


def test_invalid_log_level_raises_validation_error() -> None:
    """Invalid log level values must raise a Pydantic ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(log_level="VERBOSE")  # type: ignore[arg-type]

    assert "Invalid log_level 'VERBOSE'" in str(exc_info.value)


def test_validator_non_string_values() -> None:
    """Non-string inputs to validators must raise ValidationError."""
    with pytest.raises(ValidationError):
        Settings(env=12345)  # type: ignore[arg-type]

    with pytest.raises(ValidationError):
        Settings(log_level=999)  # type: ignore[arg-type]


def test_get_settings_cached_singleton() -> None:
    """Verify get_settings returns a cached instance and respects cache clearing."""
    get_settings.cache_clear()
    first = get_settings()
    second = get_settings()
    assert first is second

    get_settings.cache_clear()


def test_get_default_app_data_dir_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify fallback behavior when LOCALAPPDATA environment variable is missing."""
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    fallback_dir = get_default_app_data_dir()
    assert fallback_dir == Path.home() / ".ghosttrace"
