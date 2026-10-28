"""Main facade engine coordinating GhostTrace personality, traits, mood, and prompt generation."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ghosttrace.ai.prompts import DEVELOPER_SYSTEM_PROMPT
from ghosttrace.ghost.behaviour import classify_interaction_context
from ghosttrace.ghost.mood import SessionMoodTracker
from ghosttrace.ghost.profiles import (
    DEFAULT_PROFILE_ID,
    PersonalityProfile,
    get_profile,
    list_profiles,
)
from ghosttrace.ghost.response_modifier import compose_personality_prompt
from ghosttrace.ghost.schemas import (
    GhostMood,
    GhostProfileId,
    InteractionContext,
    PersonalityStatus,
)
from ghosttrace.ghost.traits import PersonalityTraits

if TYPE_CHECKING:
    from ghosttrace.config.settings import Settings

logger = logging.getLogger("ghosttrace.ghost.engine")


class GhostEngine:
    """Central coordinator for ghost persona identity, mood transitions, and system prompts."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings
        self._enabled = getattr(settings, "ghost_enabled", True) if settings else True
        profile_name = (
            getattr(settings, "ghost_profile", DEFAULT_PROFILE_ID.value)
            if settings
            else DEFAULT_PROFILE_ID.value
        )
        mood_enabled = getattr(settings, "ghost_mood_enabled", True) if settings else True

        try:
            self._active_profile: PersonalityProfile = get_profile(profile_name)
        except ValueError:
            logger.warning(
                "Configured profile '%s' unrecognised. Falling back to default.", profile_name
            )
            self._active_profile = get_profile(DEFAULT_PROFILE_ID)

        self._default_profile_id: GhostProfileId = self._active_profile.id
        self._traits: PersonalityTraits = self._active_profile.traits
        self._mood_tracker = SessionMoodTracker(enabled=mood_enabled)

    @property
    def is_enabled(self) -> bool:
        """Return whether the personality subsystem is active."""
        return self._enabled

    def enable(self) -> None:
        """Enable personality subsystem."""
        self._enabled = True
        logger.info("Ghost personality engine enabled.")

    def disable(self) -> None:
        """Disable personality subsystem (fall back to neutral developer assistant)."""
        self._enabled = False
        logger.info("Ghost personality engine disabled.")

    @property
    def active_profile(self) -> PersonalityProfile:
        """Return the currently active personality profile."""
        return self._active_profile

    @property
    def traits(self) -> PersonalityTraits:
        """Return the active trait configuration."""
        return self._traits

    @property
    def current_mood(self) -> GhostMood:
        """Return the active session mood."""
        return self._mood_tracker.current_mood

    @property
    def mood_tracker(self) -> SessionMoodTracker:
        """Return the session mood tracker."""
        return self._mood_tracker

    def set_profile(self, profile_id: str | GhostProfileId) -> PersonalityProfile:
        """Switch the active personality profile at runtime immediately."""
        profile = get_profile(profile_id)
        self._active_profile = profile
        self._traits = profile.traits
        logger.info("Active personality switched to: %s (%s)", profile.name, profile.id.value)
        return profile

    def reset_profile(self) -> PersonalityProfile:
        """Restore the default personality profile and reset session mood."""
        profile = get_profile(self._default_profile_id)
        self._active_profile = profile
        self._traits = profile.traits
        self._mood_tracker.reset()
        logger.info("Personality reset to default profile: %s", profile.name)
        return profile

    def list_available_profiles(self) -> list[PersonalityProfile]:
        """Return all available personality profiles."""
        return list_profiles()

    def get_greeting(self, seed: int | None = None) -> str:
        """Return an atmospheric contextual greeting from the active profile."""
        return self._active_profile.get_greeting(seed)

    def process_query_context(self, query: str) -> InteractionContext:
        """Classify user query and transition session mood."""
        context = classify_interaction_context(query)
        self._mood_tracker.transition_for_context(context, query)
        return context

    def compose_system_prompt(
        self,
        context: InteractionContext | None = None,
        user_query: str | None = None,
        developer_instructions: str | None = None,
    ) -> str:
        """Compose the appropriate system prompt for the next AI turn.

        If personality is disabled, returns neutral base prompt (with developer instructions
        if present). Otherwise, builds a multi-layered prompt incorporating persona, traits,
        context, and developer task directives.
        """
        if not self._enabled:
            if developer_instructions:
                return (
                    f"{DEVELOPER_SYSTEM_PROMPT.strip()}\n\n"
                    f"=== DEVELOPER TASK INSTRUCTIONS ===\n{developer_instructions.strip()}"
                )
            return DEVELOPER_SYSTEM_PROMPT

        if context is None:
            if user_query is not None:
                context = self.process_query_context(user_query)
            else:
                context = InteractionContext.ORDINARY_CONVERSATION

        return compose_personality_prompt(
            profile=self._active_profile,
            traits=self._traits,
            context=context,
            base_prompt=DEVELOPER_SYSTEM_PROMPT,
            developer_instructions=developer_instructions,
        )

    def get_status(self) -> PersonalityStatus:
        """Compile a typed status snapshot of the personality subsystem."""
        return PersonalityStatus(
            is_enabled=self._enabled,
            profile_id=self._active_profile.id,
            profile_name=self._active_profile.name,
            mood=self._mood_tracker.current_mood,
            mood_enabled=self._mood_tracker.is_enabled,
            tagline=self._active_profile.tagline,
            description=self._active_profile.description,
            traits=self._traits.to_dict(),
        )
