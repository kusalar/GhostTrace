"""Data schemas and enums for the GhostTrace personality and behaviour subsystem."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class GhostProfileId(StrEnum):
    """Supported ghost personality profile identifiers."""

    FORGOTTEN_MACHINE = "forgotten-machine"
    PHANTOM_CODER = "phantom-coder"
    GUARDIAN_SPIRIT = "guardian-spirit"


class GhostMood(StrEnum):
    """Session-level mood states for the ghost entity."""

    DORMANT = "dormant"
    CURIOUS = "curious"
    FOCUSED = "focused"
    AMUSED = "amused"
    CONCERNED = "concerned"
    SATISFIED = "satisfied"


class InteractionContext(StrEnum):
    """Contextual classification of user interactions for behaviour selection."""

    GREETING = "greeting"
    ORDINARY_CONVERSATION = "ordinary_conversation"
    TECHNICAL_QUESTION = "technical_question"
    DEBUGGING = "debugging"
    ERROR_ENCOUNTERED = "error_encountered"
    SUCCESSFUL_OPERATION = "successful_operation"
    REPEATED_QUESTION = "repeated_question"
    LONG_IDLE_GAP = "long_idle_gap"
    POTENTIALLY_DANGEROUS_INSTRUCTION = "potentially_dangerous_instruction"
    MODEL_UNAVAILABLE = "model_unavailable"


class PersonalityStatus(BaseModel):
    """Snapshot of current personality subsystem operational state."""

    model_config = ConfigDict(frozen=True)

    is_enabled: bool = Field(description="Whether the ghost personality layer is active.")
    profile_id: GhostProfileId = Field(description="Unique ID of the active personality profile.")
    profile_name: str = Field(description="Display name of the active personality profile.")
    mood: GhostMood = Field(description="Current session mood of the ghost.")
    mood_enabled: bool = Field(description="Whether session mood tracking is active.")
    tagline: str = Field(description="Short thematic tagline for the profile.")
    description: str = Field(description="Detailed description of the persona.")
    traits: dict[str, float] = Field(description="Normalized personality trait values (0.0 - 1.0).")
