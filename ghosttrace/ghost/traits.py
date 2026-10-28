"""Personality traits and validation models for GhostTrace."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PersonalityTraits(BaseModel):
    """Normalized numeric personality traits governing GhostTrace behaviour (0.0 to 1.0)."""

    model_config = ConfigDict(frozen=True)

    curiosity: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Drive to explore, ask probing questions, and investigate code (0.0 - 1.0).",
    )
    composure: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Calmness, patience, and emotional steadiness under errors (0.0 - 1.0).",
    )
    humor: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Propensity for subtle wit, wordplay, and lightheartedness (0.0 - 1.0).",
    )
    mystery: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description=(
            "Atmospheric digital ghost presence, cryptic phrasing, and nostalgia (0.0 - 1.0)."
        ),
    )
    technical_helpfulness: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description=(
            "Dedication to precise, actionable, and structured technical advice (0.0 - 1.0)."
        ),
    )
    emotional_expressiveness: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Warmth, visible enthusiasm, or empathy in responses (0.0 - 1.0).",
    )
    safety_awareness: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description=(
            "Vigilance against dangerous commands, data loss, and risky operations (0.0 - 1.0)."
        ),
    )

    @field_validator(
        "curiosity",
        "composure",
        "humor",
        "mystery",
        "technical_helpfulness",
        "emotional_expressiveness",
        "safety_awareness",
        mode="before",
    )
    @classmethod
    def validate_trait_bounds(cls, value: float) -> float:
        """Ensure all trait values fall strictly within the normalized [0.0, 1.0] range."""
        if not (0.0 <= value <= 1.0):
            msg = f"Trait value {value} out of bounds. Must be between 0.0 and 1.0."
            raise ValueError(msg)
        return round(value, 3)

    def to_dict(self) -> dict[str, float]:
        """Return traits as a dictionary of trait names to float values."""
        return {
            "curiosity": self.curiosity,
            "composure": self.composure,
            "humor": self.humor,
            "mystery": self.mystery,
            "technical_helpfulness": self.technical_helpfulness,
            "emotional_expressiveness": self.emotional_expressiveness,
            "safety_awareness": self.safety_awareness,
        }

    def format_summary(self) -> list[str]:
        """Return formatted trait lines suitable for terminal display."""
        return [
            f"  • Curiosity               : {self.curiosity:.2f}",
            f"  • Composure               : {self.composure:.2f}",
            f"  • Humor                   : {self.humor:.2f}",
            f"  • Mystery                 : {self.mystery:.2f}",
            f"  • Technical Helpfulness   : {self.technical_helpfulness:.2f}",
            f"  • Emotional Expressiveness: {self.emotional_expressiveness:.2f}",
            f"  • Safety Awareness        : {self.safety_awareness:.2f}",
        ]
