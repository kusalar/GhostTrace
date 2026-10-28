"""High-level AI engine coordinating model management, conversation, and inference."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import TYPE_CHECKING

from ghosttrace.ai.conversation import ConversationManager
from ghosttrace.ai.inference import InferenceEngine
from ghosttrace.ai.model_manager import ModelManager, check_runtime_availability
from ghosttrace.ai.schemas import AIStatus, InferenceConfig, InferenceResult
from ghosttrace.config.settings import Settings

if TYPE_CHECKING:
    from ghosttrace.developer.engine import DeveloperEngine
    from ghosttrace.ghost.engine import GhostEngine
    from ghosttrace.guardian.engine import GuardianEngine

logger = logging.getLogger("ghosttrace.ai.engine")


class AIEngine:
    """Central AI engine facade integrating model lifecycle, context memory, and inference."""

    def __init__(
        self,
        settings: Settings,
        ghost_engine: GhostEngine | None = None,
        developer_engine: DeveloperEngine | None = None,
        guardian_engine: GuardianEngine | None = None,
    ) -> None:
        self.settings = settings
        if ghost_engine is not None:
            self.ghost_engine = ghost_engine
        else:
            from ghosttrace.ghost.engine import GhostEngine

            self.ghost_engine = GhostEngine(settings)

        if developer_engine is not None:
            self.developer_engine = developer_engine
        else:
            from ghosttrace.developer.engine import DeveloperEngine

            self.developer_engine = DeveloperEngine(settings, ghost_engine=self.ghost_engine)

        if guardian_engine is not None:
            self.guardian_engine = guardian_engine
        else:
            from ghosttrace.guardian.engine import GuardianEngine

            self.guardian_engine = GuardianEngine(settings)
        self.model_manager = ModelManager(settings)
        self.inference_config = InferenceConfig(
            context_size=settings.ai_context_size,
            max_tokens=settings.ai_max_tokens,
            temperature=settings.ai_temperature,
            top_p=settings.ai_top_p,
            threads=settings.ai_threads,
            gpu_layers=settings.ai_gpu_layers,
            batch_size=settings.ai_batch_size,
        )
        self.inference_engine = InferenceEngine(self.inference_config)
        initial_prompt = self.ghost_engine.compose_system_prompt() if self.ghost_engine else None
        self.conversation = ConversationManager(
            system_prompt=initial_prompt,
            history_limit=settings.ai_history_limit,
        )

    def get_status(self) -> AIStatus:
        """Compile and return current operational status of the AI subsystem."""
        runtime_ok, version = check_runtime_availability()
        metadata = self.model_manager.get_metadata()

        return AIStatus(
            runtime_available=runtime_ok,
            runtime_version=version,
            model_status=metadata.status,
            model_path=metadata.model_path,
            model_exists=metadata.exists,
            is_loaded=self.model_manager.is_loaded(),
            is_busy=self.inference_engine.is_busy,
            history_count=self.conversation.exchange_count,
            context_size=self.settings.ai_context_size,
            max_tokens=self.settings.ai_max_tokens,
            threads=self.settings.ai_threads,
            gpu_layers=self.settings.ai_gpu_layers,
        )

    def load_model(self) -> None:
        """Explicitly load the configured model into memory."""
        self.model_manager.load_model()

    def unload_model(self) -> bool:
        """Explicitly unload the model if loaded."""
        return self.model_manager.unload_model()

    def clear_conversation(self) -> None:
        """Reset conversation context while keeping system prompt."""
        self.conversation.reset()

    def stop_generation(self) -> None:
        """Signal ongoing inference to stop."""
        self.inference_engine.stop()

    def _get_guardian_safety_context(self, prompt: str) -> str | None:
        """Analyze commands embedded in query and generate safety guidance for prompt."""
        if not self.guardian_engine or not self.guardian_engine.is_enabled:
            return None

        import re

        from ghosttrace.guardian.patterns import match_dangerous_patterns
        from ghosttrace.guardian.schemas import RiskLevel

        cmd_candidate: str | None = None
        backtick_match = re.search(r"`([^`]+)`", prompt)
        if backtick_match:
            cmd_candidate = backtick_match.group(1).strip()
        else:
            # Check if dangerous patterns or known command words match the prompt
            matched = match_dangerous_patterns(prompt)
            if matched:
                cmd_candidate = prompt.strip()

        if cmd_candidate:
            analysis = self.guardian_engine.analyze(cmd_candidate)
            if analysis.risk_level != RiskLevel.SAFE or analysis.risk_reasons:
                reasons_str = "; ".join(analysis.risk_reasons)
                effects_str = "; ".join(analysis.side_effects) if analysis.side_effects else "None"
                alt_str = (
                    f"Safer Alternative: {analysis.safer_alternative}"
                    if analysis.safer_alternative
                    else ""
                )
                return (
                    f"User inquiry touches a terminal command inspected by Command Guardian:\n"
                    f"• Inspected Command : {analysis.original_command}\n"
                    f"• Risk Classification: {analysis.risk_level.value}\n"
                    f"• Assessed Hazards   : {reasons_str}\n"
                    f"• Expected Side Effects: {effects_str}\n"
                    f"{alt_str}\n"
                    "INSTRUCTIONS: Explain what this command does objectively and warn about "
                    "risks.\n"
                    "Recommend safe alternatives. Never claim to have executed the command."
                )
        return None

    def ask(self, prompt: str) -> InferenceResult:
        """Synchronously ask a question and receive an assistant response."""
        model = self.model_manager.load_model()

        dev_instructions: str | None = None
        if (
            self.developer_engine is not None
            and self.developer_engine.is_enabled
            and self.developer_engine.is_developer_query(prompt)
        ):
            _, dev_instructions = self.developer_engine.prepare_developer_prompt(prompt)

        guardian_instructions = self._get_guardian_safety_context(prompt)

        if self.ghost_engine is not None:
            composed_prompt = self.ghost_engine.compose_system_prompt(
                user_query=prompt,
                developer_instructions=dev_instructions,
                guardian_instructions=guardian_instructions,
            )
            self.conversation.update_system_prompt(composed_prompt)

        self.conversation.add_user_message(prompt)
        messages = self.conversation.get_messages_for_llm()

        result = self.inference_engine.generate(model, messages)
        self.conversation.add_assistant_message(result.text)
        return result

    def ask_stream(self, prompt: str) -> Iterator[str]:
        """Stream assistant response tokens and record completed message in conversation."""
        model = self.model_manager.load_model()

        dev_instructions: str | None = None
        if (
            self.developer_engine is not None
            and self.developer_engine.is_enabled
            and self.developer_engine.is_developer_query(prompt)
        ):
            _, dev_instructions = self.developer_engine.prepare_developer_prompt(prompt)

        guardian_instructions = self._get_guardian_safety_context(prompt)

        if self.ghost_engine is not None:
            composed_prompt = self.ghost_engine.compose_system_prompt(
                user_query=prompt,
                developer_instructions=dev_instructions,
                guardian_instructions=guardian_instructions,
            )
            self.conversation.update_system_prompt(composed_prompt)

        self.conversation.add_user_message(prompt)
        messages = self.conversation.get_messages_for_llm()

        collected: list[str] = []
        try:
            for token in self.inference_engine.generate_stream(model, messages):
                collected.append(token)
                yield token
        finally:
            full_text = "".join(collected).strip()
            if full_text:
                self.conversation.add_assistant_message(full_text)

    def format_missing_model_message(self) -> str:
        """Return formatted instructional text when model file is not found."""
        path = self.model_manager.model_path
        return (
            "LOCAL AI: MODEL NOT FOUND\n\n"
            f"Expected:\n{path}\n\n"
            "Place a compatible GGUF model in the models directory\n"
            "or configure GHOSTTRACE_MODEL_PATH."
        )

    def format_missing_runtime_message(self) -> str:
        """Return formatted instructional text when llama-cpp-python is missing."""
        return (
            "LOCAL AI: RUNTIME UNAVAILABLE\n\n"
            "llama-cpp-python is not installed.\n"
            "Install with:\n"
            "pip install llama-cpp-python"
        )
