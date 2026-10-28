"""GhostTrace personality and behaviour subsystem."""

from __future__ import annotations

from ghosttrace.ghost.engine import GhostEngine
from ghosttrace.ghost.mood import SessionMoodTracker
from ghosttrace.ghost.profiles import (
    DEFAULT_PROFILE_ID,
    FORGOTTEN_MACHINE_PROFILE,
    GUARDIAN_SPIRIT_PROFILE,
    PHANTOM_CODER_PROFILE,
    PROFILES,
    PersonalityProfile,
    get_profile,
    list_profiles,
)
from ghosttrace.ghost.schemas import (
    GhostMood,
    GhostProfileId,
    InteractionContext,
    PersonalityStatus,
)
from ghosttrace.ghost.traits import PersonalityTraits

__all__ = [
    "DEFAULT_PROFILE_ID",
    "FORGOTTEN_MACHINE_PROFILE",
    "GUARDIAN_SPIRIT_PROFILE",
    "PHANTOM_CODER_PROFILE",
    "PROFILES",
    "GhostEngine",
    "GhostMood",
    "GhostProfileId",
    "InteractionContext",
    "PersonalityProfile",
    "PersonalityStatus",
    "PersonalityTraits",
    "SessionMoodTracker",
    "get_profile",
    "list_profiles",
]
