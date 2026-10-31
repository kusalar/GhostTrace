"""Model lifecycle management, lazy loading, and validation for local GGUF models."""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

from ghosttrace.ai.exceptions import (
    InvalidModelError,
    ModelLoadError,
    ModelNotFoundError,
    RuntimeUnavailableError,
)
from ghosttrace.ai.schemas import ModelMetadata, ModelStatus
from ghosttrace.config.settings import Settings

logger = logging.getLogger("ghosttrace.ai.model_manager")


def check_runtime_availability() -> tuple[bool, str | None]:
    """Check if llama_cpp is importable without crashing or raising exceptions."""
    try:
        import llama_cpp

        version = getattr(llama_cpp, "__version__", "unknown")
        return True, str(version)
    except (ImportError, Exception):
        return False, None


class ModelManager:
    """Manages GGUF model file discovery, validation, lazy loading, and resource release."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._model: Any | None = None
        self._lock = threading.Lock()
        self._status: ModelStatus = ModelStatus.UNLOADED
        self._last_error: str | None = None

    @property
    def model_path(self) -> Path:
        """Resolved path to the configured GGUF model weights."""
        if self.settings.model_path is not None:
            return Path(self.settings.model_path).resolve()
        return (self.settings.model_dir / "qwen2.5-1.5b-instruct-q4_k_m.gguf").resolve()

    def get_metadata(self) -> ModelMetadata:
        """Inspect the filesystem and return current model file metadata and accessibility."""
        target = self.model_path
        exists = False
        file_size_bytes = 0
        file_size_mb = 0.0

        try:
            if target.exists() and target.is_file():
                exists = True
                file_size_bytes = target.stat().st_size
                file_size_mb = round(file_size_bytes / (1024 * 1024), 2)
        except OSError as exc:
            logger.warning("Could not stat model file '%s': %s", target, exc)

        runtime_ok, _ = check_runtime_availability()
        if not runtime_ok:
            status = ModelStatus.UNAVAILABLE
        elif not exists:
            status = ModelStatus.NOT_FOUND
        elif self._model is not None:
            status = ModelStatus.READY
        elif self._status == ModelStatus.ERROR:
            status = ModelStatus.ERROR
        else:
            status = ModelStatus.UNLOADED

        return ModelMetadata(
            model_path=target,
            exists=exists,
            file_size_bytes=file_size_bytes,
            file_size_mb=file_size_mb,
            format="GGUF",
            quantization="Q4_K_M",
            status=status,
            error_message=self._last_error,
        )

    def is_loaded(self) -> bool:
        """Return True if model weights are currently loaded in memory."""
        return self._model is not None

    def get_model(self) -> Any:
        """Return the loaded model instance, loading it lazily if not yet loaded."""
        if self._model is None:
            return self.load_model()
        return self._model

    def load_model(self) -> Any:
        """Lazily load the GGUF model into memory using llama.cpp. Thread-safe."""
        with self._lock:
            if self._model is not None:
                return self._model

            runtime_ok, _ = check_runtime_availability()
            if not runtime_ok:
                self._status = ModelStatus.UNAVAILABLE
                msg = (
                    "llama-cpp-python runtime is not installed or available. "
                    "Install with: pip install llama-cpp-python"
                )
                self._last_error = msg
                raise RuntimeUnavailableError(msg)

            target = self.model_path
            if not target.exists() or not target.is_file():
                self._status = ModelStatus.NOT_FOUND
                msg = f"Model weights not found at: {target}"
                self._last_error = msg
                raise ModelNotFoundError(msg)

            if target.suffix.lower() != ".gguf":
                self._status = ModelStatus.ERROR
                msg = f"Invalid model file '{target.name}'. Expected a '.gguf' file."
                self._last_error = msg
                raise InvalidModelError(msg)

            logger.info(
                "Loading GGUF model from '%s' (threads=%d, ctx=%d, gpu_layers=%d)...",
                target,
                self.settings.ai_threads,
                self.settings.ai_context_size,
                self.settings.ai_gpu_layers,
            )
            self._status = ModelStatus.LOADING

            try:
                import llama_cpp

                # Silence native C-level llama.cpp logging to stderr to prevent terminal corruption
                if hasattr(llama_cpp, "llama_log_set") and hasattr(llama_cpp, "llama_log_callback"):
                    try:

                        def _silent_llama_log(level: int, text: bytes, user_data: Any) -> None:
                            pass

                        _log_cb = llama_cpp.llama_log_callback(_silent_llama_log)
                        llama_cpp.llama_log_set(_log_cb, None)
                    except Exception as log_exc:
                        logger.debug("Failed to set silent llama.cpp logger callback: %s", log_exc)

                self._model = llama_cpp.Llama(
                    model_path=str(target),
                    n_ctx=self.settings.ai_context_size,
                    n_threads=self.settings.ai_threads,
                    n_batch=self.settings.ai_batch_size,
                    n_gpu_layers=self.settings.ai_gpu_layers,
                    verbose=False,
                )
                self._status = ModelStatus.READY
                self._last_error = None
                logger.info("Model '%s' loaded successfully.", target.name)
                return self._model
            except Exception as exc:
                self._status = ModelStatus.ERROR
                self._model = None
                self._last_error = str(exc)
                logger.exception("Failed to load model from '%s'", target)
                msg = f"Failed to initialize model from '{target}': {exc}"
                raise ModelLoadError(msg) from exc

    def unload_model(self) -> bool:
        """Release model weights from memory and trigger garbage collection."""
        with self._lock:
            if self._model is None:
                return False
            try:
                del self._model
                self._model = None
                import gc

                gc.collect()
                self._status = ModelStatus.UNLOADED
                self._last_error = None
                logger.info("Model unloaded from memory.")
                return True
            except Exception as exc:
                logger.warning("Error during model unload: %s", exc)
                self._model = None
                self._status = ModelStatus.UNLOADED
                return False
