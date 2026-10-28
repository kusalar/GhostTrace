"""Tests for the GhostTrace centralized configuration system."""

from pathlib import Path

import pytest
from ghosttrace.config.settings import Settings, get_default_app_data_dir, get_settings
from pydantic import ValidationError


def test_default_configuration() -> None:
    """Verify default configuration attributes and sensible fallback directories."""
    settings = Settings()

    assert settings.app_name == "GhostTrace"
    assert settings.app_version == "1.0.0"
    assert "haunted" in settings.app_description.lower()
    assert settings.env == "development"
    assert settings.debug is False
    assert settings.log_level == "INFO"

    # Verify directories are resolved Path instances
    assert isinstance(settings.app_data_dir, Path)
    assert isinstance(settings.model_dir, Path)
    assert isinstance(settings.db_dir, Path)
    assert isinstance(settings.log_dir, Path)
    assert isinstance(settings.model_path, Path)

    # Subdirectories default to app_data_dir subpaths
    assert settings.db_dir == settings.app_data_dir / "db"
    assert settings.log_dir == settings.app_data_dir / "logs"
    assert settings.model_path == settings.model_dir / "qwen2.5-1.5b-instruct-q4_k_m.gguf"

    # Verify local AI default parameters
    assert settings.ai_enabled is True
    assert settings.ai_context_size == 2048
    assert settings.ai_max_tokens == 512
    assert settings.ai_temperature == 0.7
    assert settings.ai_top_p == 0.9
    assert settings.ai_threads == 2
    assert settings.ai_gpu_layers == 0
    assert settings.ai_batch_size == 128
    assert settings.ai_history_limit == 10

    # Verify ghost personality default parameters
    assert settings.ghost_enabled is True
    assert settings.ghost_profile == "forgotten-machine"
    assert settings.ghost_mood_enabled is True

    # Verify developer assistant default parameters (Step 05)
    assert settings.dev_enabled is True
    assert settings.dev_static_analysis is True
    assert settings.dev_max_code_chars == 20000
    assert settings.dev_max_context_chars == 30000

    # Verify command guardian default parameters (Step 06)
    assert settings.guard_enabled is True
    assert settings.guard_execution_enabled is True
    assert settings.guard_require_approval is True
    assert settings.guard_timeout_seconds == 30
    assert settings.guard_max_timeout_seconds == 120
    assert settings.guard_max_output_chars == 12000
    assert settings.guard_history_limit == 50
    assert settings.guard_block_high_risk is True
    assert settings.guard_blocked_commands_enabled is True


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


def test_ai_settings_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify local AI configuration overrides via environment variables."""
    custom_model = tmp_path / "custom.gguf"
    monkeypatch.setenv("GHOSTTRACE_MODEL_PATH", str(custom_model))
    monkeypatch.setenv("GHOSTTRACE_AI_ENABLED", "false")
    monkeypatch.setenv("GHOSTTRACE_AI_CONTEXT_SIZE", "4096")
    monkeypatch.setenv("GHOSTTRACE_AI_MAX_TOKENS", "1024")
    monkeypatch.setenv("GHOSTTRACE_AI_TEMPERATURE", "0.2")
    monkeypatch.setenv("GHOSTTRACE_AI_TOP_P", "0.85")
    monkeypatch.setenv("GHOSTTRACE_AI_THREADS", "4")
    monkeypatch.setenv("GHOSTTRACE_AI_GPU_LAYERS", "1")
    monkeypatch.setenv("GHOSTTRACE_AI_BATCH_SIZE", "256")
    monkeypatch.setenv("GHOSTTRACE_AI_HISTORY_LIMIT", "20")

    settings = Settings()
    assert settings.model_path == custom_model.resolve()
    assert settings.ai_enabled is False
    assert settings.ai_context_size == 4096
    assert settings.ai_max_tokens == 1024
    assert settings.ai_temperature == 0.2
    assert settings.ai_top_p == 0.85
    assert settings.ai_threads == 4
    assert settings.ai_gpu_layers == 1
    assert settings.ai_batch_size == 256
    assert settings.ai_history_limit == 20


def test_ai_settings_validation_errors() -> None:
    """Verify validation boundaries on numeric AI configuration."""
    with pytest.raises(ValidationError):
        Settings(ai_context_size=100)  # below 256

    with pytest.raises(ValidationError):
        Settings(ai_max_tokens=0)  # below 1

    with pytest.raises(ValidationError):
        Settings(ai_temperature=-0.1)  # below 0.0

    with pytest.raises(ValidationError):
        Settings(ai_temperature=2.5)  # above 2.0

    with pytest.raises(ValidationError):
        Settings(ai_top_p=0.0)  # must be > 0.0

    with pytest.raises(ValidationError):
        Settings(ai_top_p=1.5)  # must be <= 1.0

    with pytest.raises(ValidationError):
        Settings(ai_threads=0)  # must be >= 1

    with pytest.raises(ValidationError):
        Settings(ai_threads=64)  # must be <= 32

    with pytest.raises(ValidationError):
        Settings(ai_gpu_layers=-1)  # must be >= 0

    with pytest.raises(ValidationError):
        Settings(ai_batch_size=0)  # must be >= 1

    with pytest.raises(ValidationError):
        Settings(ai_history_limit=0)  # must be >= 1


def test_ghost_settings_validation() -> None:
    """Verify validation on ghost personality settings."""
    settings = Settings(ghost_profile="PHANTOM-CODER")
    assert settings.ghost_profile == "phantom-coder"

    with pytest.raises(ValidationError, match="Invalid ghost_profile"):
        Settings(ghost_profile="invalid-ghost-profile")


def test_dev_settings_validation() -> None:
    """Verify validation on developer assistant configuration limits."""
    settings = Settings(
        dev_enabled=False,
        dev_static_analysis=False,
        dev_max_code_chars=5000,
        dev_max_context_chars=10000,
    )
    assert settings.dev_enabled is False
    assert settings.dev_static_analysis is False
    assert settings.dev_max_code_chars == 5000
    assert settings.dev_max_context_chars == 10000

    with pytest.raises(ValidationError, match="Invalid dev_max_code_chars"):
        Settings(dev_max_code_chars=10)  # must be >= 100

    with pytest.raises(ValidationError, match="Invalid dev_max_context_chars"):
        Settings(dev_max_context_chars=50)  # must be >= 100


def test_guard_settings_validation() -> None:
    """Verify validation and bounds checking on Guardian settings."""
    # Disabling approval must raise ValidationError (cannot silently bypass)
    with pytest.raises(ValidationError, match="guard_require_approval cannot be disabled"):
        Settings(guard_require_approval=False)

    # Timeout validation (1 to 120)
    with pytest.raises(ValidationError, match="Invalid guard_timeout_seconds"):
        Settings(guard_timeout_seconds=0)

    with pytest.raises(ValidationError, match="Invalid guard_timeout_seconds"):
        Settings(guard_timeout_seconds=200)

    # Max timeout validation (1 to 600)
    with pytest.raises(ValidationError, match="Invalid guard_max_timeout_seconds"):
        Settings(guard_max_timeout_seconds=0)

    with pytest.raises(ValidationError, match="Invalid guard_max_timeout_seconds"):
        Settings(guard_max_timeout_seconds=700)

    # Output chars validation (100 to 1,000,000)
    with pytest.raises(ValidationError, match="Invalid guard_max_output_chars"):
        Settings(guard_max_output_chars=50)

    with pytest.raises(ValidationError, match="Invalid guard_max_output_chars"):
        Settings(guard_max_output_chars=2_000_000)

    # History limit validation (1 to 500)
    with pytest.raises(ValidationError, match="Invalid guard_history_limit"):
        Settings(guard_history_limit=0)

    with pytest.raises(ValidationError, match="Invalid guard_history_limit"):
        Settings(guard_history_limit=600)

    # Timeout clamped to max_timeout if larger
    s = Settings(guard_timeout_seconds=100, guard_max_timeout_seconds=50)
    assert s.guard_timeout_seconds == 50


def test_memory_and_project_configuration() -> None:
    """Verify Step 07 memory and project context settings and validation."""
    s = Settings()
    assert s.memory_enabled is True
    assert s.memory_persist_conversations is True
    assert s.memory_max_items == 500
    assert s.memory_max_content_chars == 10000
    assert s.project_enabled is True
    assert s.project_max_files == 500

    # Validation limits
    with pytest.raises(ValidationError, match="Invalid memory_max_items"):
        Settings(memory_max_items=0)

    with pytest.raises(ValidationError, match="Invalid project_max_files"):
        Settings(project_max_files=0)

    with pytest.raises(ValidationError, match="Invalid memory_max_context_chars"):
        Settings(memory_max_context_chars=50)


def test_system_awareness_configuration() -> None:
    """Verify Step 08 system awareness settings and validation."""
    s = Settings()
    assert s.system_enabled is True
    assert s.system_cache_seconds == 3.0
    assert s.system_process_details is False
    assert s.system_include_hostname is False
    assert s.system_diagnostics_export is False

    # Validation
    with pytest.raises(ValidationError, match="Invalid system_cache_seconds"):
        Settings(system_cache_seconds=-1.0)

    with pytest.raises(ValidationError, match="Invalid system_cache_seconds"):
        Settings(system_cache_seconds=120.0)
