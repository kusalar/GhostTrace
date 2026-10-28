"""Low-level inference execution wrapper using llama.cpp."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Iterator
from typing import Any

from ghosttrace.ai.exceptions import InferenceError, ModelBusyError
from ghosttrace.ai.schemas import InferenceConfig, InferenceResult

logger = logging.getLogger("ghosttrace.ai.inference")


class InferenceEngine:
    """Executes chat completion inferences on loaded llama.cpp model."""

    def __init__(self, config: InferenceConfig | None = None) -> None:
        self.config = config or InferenceConfig()
        self._busy_lock = threading.Lock()
        self._is_generating = False
        self._should_stop = False

    @property
    def is_busy(self) -> bool:
        """Return True if an inference request is actively running."""
        return self._is_generating

    def stop(self) -> None:
        """Signal active streaming generation to stop."""
        self._should_stop = True

    def generate(
        self,
        model: Any,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
    ) -> InferenceResult:
        """Run synchronous chat completion and return InferenceResult."""
        if not self._busy_lock.acquire(blocking=False):
            raise ModelBusyError("Inference engine is currently busy processing another request.")

        self._is_generating = True
        self._should_stop = False
        start_time = time.perf_counter()

        try:
            tokens_limit = max_tokens if max_tokens is not None else self.config.max_tokens
            temp = temperature if temperature is not None else self.config.temperature
            tp = top_p if top_p is not None else self.config.top_p

            logger.debug(
                "Generating chat completion (max_tokens=%d, temp=%.2f, top_p=%.2f)...",
                tokens_limit,
                temp,
                tp,
            )
            response = model.create_chat_completion(
                messages=messages,
                max_tokens=tokens_limit,
                temperature=temp,
                top_p=tp,
                stream=False,
            )

            duration = round(time.perf_counter() - start_time, 3)
            choice = response["choices"][0]
            text = choice["message"].get("content", "")
            finish_reason = choice.get("finish_reason", "stop")

            usage = response.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

            return InferenceResult(
                text=text.strip(),
                finish_reason=finish_reason,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                duration_seconds=duration,
            )
        except Exception as exc:
            logger.exception("Inference failed: %s", exc)
            raise InferenceError(f"Model generation failed: {exc}") from exc
        finally:
            self._is_generating = False
            self._busy_lock.release()

    def generate_stream(
        self,
        model: Any,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
    ) -> Iterator[str]:
        """Stream token chunks from chat completion."""
        if not self._busy_lock.acquire(blocking=False):
            raise ModelBusyError("Inference engine is currently busy processing another request.")

        self._is_generating = True
        self._should_stop = False
        try:
            tokens_limit = max_tokens if max_tokens is not None else self.config.max_tokens
            temp = temperature if temperature is not None else self.config.temperature
            tp = top_p if top_p is not None else self.config.top_p

            stream = model.create_chat_completion(
                messages=messages,
                max_tokens=tokens_limit,
                temperature=temp,
                top_p=tp,
                stream=True,
            )

            for chunk in stream:
                if self._should_stop:
                    logger.debug("Streaming generation stopped early by signal.")
                    break
                choices = chunk.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
        except Exception as exc:
            logger.exception("Streaming inference failed: %s", exc)
            raise InferenceError(f"Streaming generation failed: {exc}") from exc
        finally:
            self._is_generating = False
            self._busy_lock.release()
