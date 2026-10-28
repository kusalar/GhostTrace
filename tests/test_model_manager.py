"""Tests for ModelManager lifecycle, discovery, validation, and lazy loading."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from ghosttrace.ai.exceptions import (
    InvalidModelError,
    ModelLoadError,
    ModelNotFoundError,
    RuntimeUnavailableError,
)
from ghosttrace.ai.model_manager import ModelManager, check_runtime_availability
from ghosttrace.ai.schemas import ModelStatus
from ghosttrace.config.settings import Settings


def test_model_path_resolution(tmp_path: Path) -> None:
    """Verify model_path resolves default path or custom settings override."""
    default_settings = Settings()
    manager_default = ModelManager(default_settings)
    assert manager_default.model_path.name == "qwen2.5-1.5b-instruct-q4_k_m.gguf"

    custom_model = tmp_path / "custom.gguf"
    custom_settings = Settings(model_path=custom_model)
    manager_custom = ModelManager(custom_settings)
    assert manager_custom.model_path == custom_model.resolve()


def test_check_runtime_availability_installed() -> None:
    """Verify runtime check detects llama_cpp when installed."""
    ok, version = check_runtime_availability()
    # In this environment, llama_cpp is installed
    assert ok is True
    assert version is not None


def test_check_runtime_availability_missing() -> None:
    """Verify runtime check handles missing llama_cpp gracefully without crashing."""
    with (
        patch.dict("sys.modules", {"llama_cpp": None}),
        patch("builtins.__import__", side_effect=ImportError("No module named 'llama_cpp'")),
    ):
        ok, version = check_runtime_availability()
        assert ok is False
        assert version is None


def test_metadata_when_file_not_found(tmp_path: Path) -> None:
    """When model file does not exist, status is NOT_FOUND and size is 0."""
    nonexistent = tmp_path / "missing.gguf"
    settings = Settings(model_path=nonexistent)
    manager = ModelManager(settings)

    meta = manager.get_metadata()
    assert meta.exists is False
    assert meta.file_size_bytes == 0
    assert meta.status == ModelStatus.NOT_FOUND


def test_metadata_when_file_exists(tmp_path: Path) -> None:
    """When model file exists, status is UNLOADED and size is reported."""
    dummy_model = tmp_path / "test_model.gguf"
    dummy_model.write_bytes(b"GGUF" + b"\x00" * 1024)

    settings = Settings(model_path=dummy_model)
    manager = ModelManager(settings)

    meta = manager.get_metadata()
    assert meta.exists is True
    assert meta.file_size_bytes > 0
    assert meta.status == ModelStatus.UNLOADED


def test_load_model_raises_runtime_unavailable(tmp_path: Path) -> None:
    """Attempting to load model when runtime is missing raises RuntimeUnavailableError."""
    dummy_model = tmp_path / "model.gguf"
    dummy_model.write_bytes(b"GGUF")
    manager = ModelManager(Settings(model_path=dummy_model))

    with (
        patch(
            "ghosttrace.ai.model_manager.check_runtime_availability",
            return_value=(False, None),
        ),
        pytest.raises(RuntimeUnavailableError) as exc_info,
    ):
        manager.load_model()
        assert "runtime is not installed" in str(exc_info.value)
        assert manager.get_metadata().status == ModelStatus.UNAVAILABLE


def test_load_model_raises_model_not_found(tmp_path: Path) -> None:
    """Attempting to load missing model file raises ModelNotFoundError."""
    missing = tmp_path / "absent.gguf"
    manager = ModelManager(Settings(model_path=missing))

    with pytest.raises(ModelNotFoundError) as exc_info:
        manager.load_model()
    assert "not found at" in str(exc_info.value)
    assert manager.get_metadata().status == ModelStatus.NOT_FOUND


def test_load_model_raises_invalid_model_extension(tmp_path: Path) -> None:
    """Files without .gguf extension raise InvalidModelError."""
    invalid_file = tmp_path / "model.bin"
    invalid_file.write_bytes(b"BIN_DATA")
    manager = ModelManager(Settings(model_path=invalid_file))

    with pytest.raises(InvalidModelError) as exc_info:
        manager.load_model()
    assert "Expected a '.gguf' file" in str(exc_info.value)
    assert manager.get_metadata().status == ModelStatus.ERROR


def test_load_model_success_and_lazy_reuse(tmp_path: Path) -> None:
    """Verify successful model loading initializes Llama and reuses instance."""
    dummy_model = tmp_path / "qwen.gguf"
    dummy_model.write_bytes(b"GGUF_TEST_BYTES")

    settings = Settings(
        model_path=dummy_model,
        ai_threads=4,
        ai_context_size=1024,
        ai_gpu_layers=0,
        ai_batch_size=64,
    )
    manager = ModelManager(settings)
    assert manager.is_loaded() is False

    mock_llama_instance = MagicMock()
    with patch("llama_cpp.Llama", return_value=mock_llama_instance) as mock_llama_cls:
        model1 = manager.load_model()
        assert model1 is mock_llama_instance
        assert manager.is_loaded() is True
        assert manager.get_metadata().status == ModelStatus.READY

        mock_llama_cls.assert_called_once_with(
            model_path=str(dummy_model.resolve()),
            n_ctx=1024,
            n_threads=4,
            n_batch=64,
            n_gpu_layers=0,
            verbose=False,
        )

        # Second load call should return same cached instance without re-instantiating
        model2 = manager.get_model()
        assert model2 is mock_llama_instance
        mock_llama_cls.assert_called_once()


def test_load_model_handles_llama_init_failure(tmp_path: Path) -> None:
    """If llama_cpp.Llama raises an exception, wrap in ModelLoadError."""
    dummy_model = tmp_path / "bad.gguf"
    dummy_model.write_bytes(b"CORRUPT")
    manager = ModelManager(Settings(model_path=dummy_model))

    with patch("llama_cpp.Llama", side_effect=RuntimeError("Corrupt GGUF magic header")):
        with pytest.raises(ModelLoadError) as exc_info:
            manager.load_model()
        assert "Failed to initialize model" in str(exc_info.value)
        assert manager.is_loaded() is False
        assert manager.get_metadata().status == ModelStatus.ERROR


def test_unload_model(tmp_path: Path) -> None:
    """Verify unload_model releases resources and updates status."""
    dummy_model = tmp_path / "model.gguf"
    dummy_model.write_bytes(b"GGUF")
    manager = ModelManager(Settings(model_path=dummy_model))

    # Unload when not loaded returns False
    assert manager.unload_model() is False

    # Simulate loaded state
    manager._model = MagicMock()
    assert manager.is_loaded() is True

    # Unload releases and returns True
    assert manager.unload_model() is True
    assert manager.is_loaded() is False
    assert manager.get_metadata().status == ModelStatus.UNLOADED

    # Test unload exception handling
    manager._model = MagicMock()
    with patch("gc.collect", side_effect=RuntimeError("GC error")):
        assert manager.unload_model() is False
        assert manager.is_loaded() is False


def test_metadata_status_unavailable_and_error(tmp_path: Path) -> None:
    """Verify get_metadata status mapping for unavailable runtime and error states."""
    dummy_model = tmp_path / "model.gguf"
    dummy_model.write_bytes(b"GGUF")
    manager = ModelManager(Settings(model_path=dummy_model))

    with patch(
        "ghosttrace.ai.model_manager.check_runtime_availability",
        return_value=(False, None),
    ):
        meta = manager.get_metadata()
        assert meta.status == ModelStatus.UNAVAILABLE

    manager._status = ModelStatus.ERROR
    meta_err = manager.get_metadata()
    assert meta_err.status == ModelStatus.ERROR


def test_metadata_stat_oserror_handled(tmp_path: Path) -> None:
    """Verify stat OSError is logged and handled cleanly in get_metadata."""
    dummy_model = tmp_path / "model.gguf"
    dummy_model.write_bytes(b"GGUF")
    manager = ModelManager(Settings(model_path=dummy_model))

    with patch.object(Path, "stat", side_effect=OSError("Permission denied")):
        meta = manager.get_metadata()
        assert meta.file_size_bytes == 0
        assert meta.file_size_mb == 0.0
