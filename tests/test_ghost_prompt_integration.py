"""Unit tests for GhostTrace system prompt composition and trait guidelines."""

from ghosttrace.ai.prompts import DEVELOPER_SYSTEM_PROMPT
from ghosttrace.ghost.profiles import (
    FORGOTTEN_MACHINE_PROFILE,
    GUARDIAN_SPIRIT_PROFILE,
    PHANTOM_CODER_PROFILE,
)
from ghosttrace.ghost.response_modifier import (
    build_trait_guidelines,
    compose_personality_prompt,
)
from ghosttrace.ghost.schemas import InteractionContext
from ghosttrace.ghost.traits import PersonalityTraits


def test_build_trait_guidelines():
    # High mystery & high humor
    traits1 = PersonalityTraits(mystery=0.85, humor=0.85, safety_awareness=0.9, curiosity=0.85)
    guidelines1 = build_trait_guidelines(traits1)
    joined1 = " ".join(guidelines1)
    assert "Mystery" in joined1
    assert "Humor" in joined1
    assert "Safety" in joined1
    assert "Curiosity" in joined1

    # Low mystery & low humor
    traits2 = PersonalityTraits(mystery=0.2, humor=0.1, composure=0.9, technical_helpfulness=0.9)
    guidelines2 = build_trait_guidelines(traits2)
    joined2 = " ".join(guidelines2)
    assert "strictly literal" in joined2
    assert "serious, straightforward" in joined2
    assert "Composure" in joined2
    assert "Helpfulness" in joined2


def test_compose_personality_prompt_structure():
    profile = PHANTOM_CODER_PROFILE
    prompt = compose_personality_prompt(
        profile=profile,
        traits=profile.traits,
        context=InteractionContext.TECHNICAL_QUESTION,
    )

    # 1. Base Developer Assistant section
    assert "=== BASE DEVELOPER ASSISTANT IDENTITY ===" in prompt
    assert DEVELOPER_SYSTEM_PROMPT.strip() in prompt

    # 2. Digital Ghost Persona section
    assert "=== DIGITAL GHOST PERSONA ===" in prompt
    assert f"Active Profile: {profile.name}" in prompt
    assert profile.identity_prompt.strip() in prompt

    # 3. Behavioural Traits section
    assert "=== BEHAVIOURAL TRAITS ===" in prompt
    assert "Curiosity:" in prompt

    # 4. Interaction Context section
    assert "=== INTERACTION CONTEXT ===" in prompt
    assert "CONTEXT:" in prompt
    assert "GUIDELINES:" in prompt

    # 5. Non-negotiable safety guardrails
    assert "=== ABSOLUTE SAFETY & TRUTHFULNESS GUARDRAILS ===" in prompt
    assert "Never invent tool executions" in prompt
    assert "Technical accuracy and usefulness ALWAYS take precedence" in prompt


def test_compose_personality_prompt_different_profiles():
    fm_prompt = compose_personality_prompt(
        FORGOTTEN_MACHINE_PROFILE,
        FORGOTTEN_MACHINE_PROFILE.traits,
        InteractionContext.GREETING,
    )
    assert "Forgotten Machine" in fm_prompt

    gs_prompt = compose_personality_prompt(
        GUARDIAN_SPIRIT_PROFILE,
        GUARDIAN_SPIRIT_PROFILE.traits,
        InteractionContext.POTENTIALLY_DANGEROUS_INSTRUCTION,
    )
    assert "Guardian Spirit" in gs_prompt
    assert "CRITICAL SAFETY ALERT" in gs_prompt
