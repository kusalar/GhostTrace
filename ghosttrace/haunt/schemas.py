"""Pydantic schemas and typed data models for the GhostTrace haunted experience subsystem."""

from __future__ import annotations

import time
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class HauntMode(StrEnum):
    """Experience mode controlling atmospheric event frequency and presentation."""

    NORMAL = "normal"
    AMBIENT = "ambient"
    HAUNTED = "haunted"
    FOCUS = "focus"


class HauntIntensity(StrEnum):
    """Intensity levels governing cooldown scaling and event variety."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EventCategory(StrEnum):
    """Taxonomy of interactive supernatural and atmospheric event categories."""

    GHOST_GREETING = "ghost_greeting"
    IDLE_WHISPER = "idle_whisper"
    CODING_REACTION = "coding_reaction"
    ERROR_REACTION = "error_reaction"
    GUARDIAN_REACTION = "guardian_reaction"
    MOOD_SHIFT = "mood_shift"
    SESSION_EVENT = "session_event"
    DISCOVERY_EVENT = "discovery_event"
    SPECIAL_EVENT = "special_event"


class TriggerType(StrEnum):
    """Types of genuine application events that can trigger an atmospheric reaction."""

    SESSION_START = "session_start"
    COMMAND_INVOKED = "command_invoked"
    COMMAND_DISCOVERY = "command_discovery"
    CODING_SUCCESS = "coding_success"
    APP_ERROR = "app_error"
    GUARDIAN_WARNING = "guardian_warning"
    MOOD_TRANSITION = "mood_transition"
    IDLE_TICK = "idle_tick"
    MANUAL_PREVIEW = "manual_preview"


class HauntEvent(BaseModel):
    """Declarative definition of a haunted experience event."""

    id: str = Field(description="Unique event identifier (e.g., 'whisper_terminal_quiet').")
    category: EventCategory = Field(description="Taxonomy category for this event.")
    name: str = Field(description="Human-readable event title.")
    description: str = Field(description="Internal summary of the event's purpose.")
    templates: dict[str, list[str]] = Field(
        default_factory=dict,
        description=(
            "Profile-specific message templates "
            "(forgotten-machine, phantom-coder, guardian-spirit, default)."
        ),
    )
    eligible_modes: list[HauntMode] = Field(
        default_factory=lambda: [HauntMode.AMBIENT, HauntMode.HAUNTED],
        description="Experience modes in which this event is permitted to trigger.",
    )
    priority: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Evaluation priority (1-10); higher takes precedence during evaluation.",
    )
    cooldown_seconds: float = Field(
        default=60.0,
        ge=0.0,
        description="Minimum cooldown in seconds before this specific event may trigger again.",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Contextual tags (e.g., 'code', 'error', 'mood', 'startup').",
    )


class TriggerContext(BaseModel):
    """Contextual metadata accompanying an application event for trigger evaluation."""

    trigger_type: TriggerType
    command_name: str | None = None
    command_args: list[str] | None = None
    dev_intent: str | None = None
    risk_level: str | None = None
    error_message: str | None = None
    mood_from: str | None = None
    mood_to: str | None = None
    profile_id: str | None = None
    idle_seconds: float = 0.0
    extra: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class TriggerResult(BaseModel):
    """Outcome of evaluating a trigger context against the event catalog."""

    fired: bool = Field(description="True if an event was selected and fired.")
    event: HauntEvent | None = Field(default=None, description="The triggered HauntEvent, if any.")
    rendered_text: str | None = Field(
        default=None, description="Rendered atmospheric text matching the active profile."
    )
    reason: str = Field(description="Explanation of why the event fired or was suppressed.")
    category: EventCategory | None = Field(default=None, description="Category of the event.")


class HauntHistoryEntry(BaseModel):
    """Bounded, session-only record of a triggered atmospheric event."""

    id: str = Field(description="Unique entry identifier.")
    timestamp: float = Field(default_factory=time.time)
    event_id: str = Field(description="Identifier of the triggered HauntEvent.")
    category: EventCategory = Field(description="Event category.")
    mode: HauntMode = Field(description="Active mode when event triggered.")
    profile_id: str = Field(description="Active ghost profile when triggered.")
    rendered_text: str = Field(description="Exact atmospheric message displayed.")
    trigger_type: TriggerType = Field(description="Application trigger type that caused this.")


class HauntStatus(BaseModel):
    """Subsystem state snapshot for inspection and status reporting."""

    enabled: bool
    mode: HauntMode
    intensity: HauntIntensity
    active_profile: str
    current_mood: str
    total_events_triggered: int
    session_events_remaining: int
    max_events_per_session: int
    cooldown_seconds: float
    last_event_time: float | None
    idle_enabled: bool
    idle_threshold_seconds: float
    reduced_motion: bool
