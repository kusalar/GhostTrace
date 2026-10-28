"""Unit tests for GhostTrace personality profiles and profile registry."""

import pytest
from ghosttrace.ghost.profiles import (
    DEFAULT_PROFILE_ID,
    FORGOTTEN_MACHINE_PROFILE,
    GUARDIAN_SPIRIT_PROFILE,
    PHANTOM_CODER_PROFILE,
    PersonalityProfile,
    get_profile,
    list_profiles,
)
from ghosttrace.ghost.schemas import GhostProfileId
from ghosttrace.ghost.traits import PersonalityTraits


def test_default_profiles_exist():
    assert FORGOTTEN_MACHINE_PROFILE.id == GhostProfileId.FORGOTTEN_MACHINE
    assert PHANTOM_CODER_PROFILE.id == GhostProfileId.PHANTOM_CODER
    assert GUARDIAN_SPIRIT_PROFILE.id == GhostProfileId.GUARDIAN_SPIRIT

    assert DEFAULT_PROFILE_ID == GhostProfileId.FORGOTTEN_MACHINE


def test_profile_trait_characteristics():
    # Forgotten Machine: high mystery, high composure
    fm = FORGOTTEN_MACHINE_PROFILE
    assert fm.traits.mystery >= 0.8
    assert fm.traits.composure >= 0.8
    assert fm.traits.humor <= 0.3

    # Phantom Coder: very high curiosity, high humor
    pc = PHANTOM_CODER_PROFILE
    assert pc.traits.curiosity >= 0.9
    assert pc.traits.humor >= 0.8
    assert pc.traits.technical_helpfulness >= 0.9

    # Guardian Spirit: very high safety awareness, very high composure
    gs = GUARDIAN_SPIRIT_PROFILE
    assert gs.traits.safety_awareness >= 0.9
    assert gs.traits.composure >= 0.9
    assert gs.traits.humor <= 0.3


def test_get_profile_by_enum_and_string():
    prof1 = get_profile(GhostProfileId.FORGOTTEN_MACHINE)
    assert prof1.name == "Forgotten Machine"

    prof2 = get_profile("forgotten-machine")
    assert prof2.name == "Forgotten Machine"

    prof3 = get_profile("Phantom Coder")
    assert prof3.id == GhostProfileId.PHANTOM_CODER

    prof4 = get_profile("GUARDIAN-SPIRIT")
    assert prof4.id == GhostProfileId.GUARDIAN_SPIRIT


def test_get_profile_unknown_raises():
    with pytest.raises(ValueError, match="Unknown personality profile 'unknown-ghost'"):
        get_profile("unknown-ghost")


def test_list_profiles():
    profiles = list_profiles()
    assert len(profiles) == 3
    ids = [p.id for p in profiles]
    assert GhostProfileId.FORGOTTEN_MACHINE in ids
    assert GhostProfileId.PHANTOM_CODER in ids
    assert GhostProfileId.GUARDIAN_SPIRIT in ids


def test_profile_greetings():
    fm = FORGOTTEN_MACHINE_PROFILE
    greeting_seed0 = fm.get_greeting(seed=0)
    greeting_seed1 = fm.get_greeting(seed=1)
    assert isinstance(greeting_seed0, str)
    assert len(greeting_seed0) > 0
    assert greeting_seed0 != greeting_seed1

    random_greeting = fm.get_greeting()
    assert isinstance(random_greeting, str)
    assert len(random_greeting) > 0


def test_empty_greetings_fallback():
    custom_prof = PersonalityProfile(
        id=GhostProfileId.FORGOTTEN_MACHINE,
        name="Empty Ghost",
        tagline="Test tagline",
        description="Test description",
        traits=PersonalityTraits(),
        identity_prompt="Test identity",
        speaking_style="Test style",
        greetings=[],
    )
    fallback = custom_prof.get_greeting()
    assert "Empty Ghost" in fallback
