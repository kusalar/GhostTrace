"""Session mood state and deterministic transitions for GhostTrace."""

from __future__ import annotations

import logging

from ghosttrace.ghost.schemas import GhostMood, InteractionContext

logger = logging.getLogger("ghosttrace.ghost.mood")


class SessionMoodTracker:
    """Tracks a lightweight, explainable mood state across the active terminal session."""

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled
        self._mood = GhostMood.DORMANT
        self._last_reason = "Session initialized; entity is in dormant standby."

    @property
    def is_enabled(self) -> bool:
        """Return whether mood tracking is enabled."""
        return self._enabled

    @is_enabled.setter
    def is_enabled(self, value: bool) -> None:
        """Enable or disable mood tracking."""
        self._enabled = value
        if not value:
            self._mood = GhostMood.DORMANT
            self._last_reason = "Mood tracking disabled by configuration."

    @property
    def current_mood(self) -> GhostMood:
        """Return the current session mood."""
        return self._mood

    @property
    def last_reason(self) -> str:
        """Return the deterministic rationale for the current mood state."""
        return self._last_reason

    def reset(self) -> None:
        """Reset the session mood to dormant."""
        self._mood = GhostMood.DORMANT
        self._last_reason = "Session mood reset to dormant state."
        logger.debug("Session mood tracker reset.")

    def set_mood(self, mood: GhostMood, reason: str = "Manually specified") -> None:
        """Explicitly set the session mood."""
        if not self._enabled:
            return
        self._mood = mood
        self._last_reason = reason
        logger.debug("Mood transitioned to %s: %s", mood.value, reason)

    def transition_for_context(
        self,
        context: InteractionContext,
        query_text: str | None = None,
    ) -> GhostMood:
        """Deterministically transition mood based on the classified interaction context."""
        if not self._enabled:
            return GhostMood.DORMANT

        previous_mood = self._mood

        match context:
            case InteractionContext.GREETING:
                if previous_mood == GhostMood.DORMANT:
                    self._mood = GhostMood.CURIOUS
                    self._last_reason = "Entity greeted by developer; awakening interest."
                else:
                    self._mood = GhostMood.AMUSED
                    self._last_reason = "Friendly exchange greeted in active session."

            case InteractionContext.TECHNICAL_QUESTION:
                self._mood = GhostMood.FOCUSED
                self._last_reason = "Analyzing technical query and formulating structured response."

            case InteractionContext.DEBUGGING:
                self._mood = GhostMood.CURIOUS
                self._last_reason = "Investigating bugs and inspecting stack traces."

            case (
                InteractionContext.ERROR_ENCOUNTERED
                | InteractionContext.POTENTIALLY_DANGEROUS_INSTRUCTION
            ):
                self._mood = GhostMood.CONCERNED
                self._last_reason = "Detected failure, exception, or potentially risky operation."

            case InteractionContext.SUCCESSFUL_OPERATION:
                self._mood = GhostMood.SATISFIED
                self._last_reason = "Confirmed successful operation or resolved technical issue."

            case InteractionContext.MODEL_UNAVAILABLE:
                self._mood = GhostMood.CONCERNED
                self._last_reason = "Model weights or inference runtime unavailable."

            case InteractionContext.REPEATED_QUESTION:
                self._mood = GhostMood.FOCUSED
                self._last_reason = "Clarifying and refining previously addressed inquiry."

            case InteractionContext.LONG_IDLE_GAP:
                self._mood = GhostMood.DORMANT
                self._last_reason = (
                    "No interaction for extended period; resting in low-power state."
                )

            case InteractionContext.ORDINARY_CONVERSATION:
                if self._mood == GhostMood.DORMANT:
                    self._mood = GhostMood.CURIOUS
                    self._last_reason = "New conversational inquiry received."
                # Keep existing mood for continuity during general discussion

        if self._mood != previous_mood:
            logger.debug(
                "Mood changed: %s -> %s (%s)",
                previous_mood.value,
                self._mood.value,
                self._last_reason,
            )

        return self._mood
