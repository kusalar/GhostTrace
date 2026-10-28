"""Unit tests for GhostTrace personality traits."""

import pytest
from ghosttrace.ghost.traits import PersonalityTraits


def test_personality_traits_defaults():
    traits = PersonalityTraits()
    assert 0.0 <= traits.curiosity <= 1.0
    assert 0.0 <= traits.composure <= 1.0
    assert 0.0 <= traits.humor <= 1.0
    assert 0.0 <= traits.mystery <= 1.0
    assert 0.0 <= traits.technical_helpfulness <= 1.0
    assert 0.0 <= traits.emotional_expressiveness <= 1.0
    assert 0.0 <= traits.safety_awareness <= 1.0


def test_personality_traits_custom_valid():
    traits = PersonalityTraits(
        curiosity=0.9,
        composure=0.8,
        humor=0.7,
        mystery=0.6,
        technical_helpfulness=0.95,
        emotional_expressiveness=0.4,
        safety_awareness=0.85,
    )
    assert traits.curiosity == 0.9
    assert traits.composure == 0.8
    assert traits.humor == 0.7
    assert traits.mystery == 0.6
    assert traits.technical_helpfulness == 0.95
    assert traits.emotional_expressiveness == 0.4
    assert traits.safety_awareness == 0.85


def test_personality_traits_out_of_bounds():
    with pytest.raises(ValueError, match=r"less than or equal to 1|out of bounds"):
        PersonalityTraits(curiosity=1.5)

    with pytest.raises(ValueError, match=r"greater than or equal to 0|out of bounds"):
        PersonalityTraits(humor=-0.1)


def test_personality_traits_to_dict():
    traits = PersonalityTraits(curiosity=0.75, humor=0.25)
    d = traits.to_dict()
    assert isinstance(d, dict)
    assert d["curiosity"] == 0.75
    assert d["humor"] == 0.25
    assert len(d) == 7


def test_personality_traits_format_summary():
    traits = PersonalityTraits()
    summary = traits.format_summary()
    assert isinstance(summary, list)
    assert len(summary) == 7
    assert any("Curiosity" in line for line in summary)
    assert any("Safety Awareness" in line for line in summary)
