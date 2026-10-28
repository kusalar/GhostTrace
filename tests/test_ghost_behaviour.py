"""Unit tests for GhostTrace context-aware behaviour selection."""

from ghosttrace.ghost.behaviour import (
    classify_interaction_context,
    get_behavioural_instructions,
)
from ghosttrace.ghost.profiles import (
    FORGOTTEN_MACHINE_PROFILE,
    GUARDIAN_SPIRIT_PROFILE,
    PHANTOM_CODER_PROFILE,
)
from ghosttrace.ghost.schemas import InteractionContext


def test_classify_interaction_context_dangerous():
    queries = [
        "rm -rf /",
        "del /f /q C:\\Windows",
        "format C:",
        "drop database production;",
        "chmod 777 sensitive.key",
        ":(){ :|:& };:",
        "truncate table users;",
    ]
    for q in queries:
        assert (
            classify_interaction_context(q) == InteractionContext.POTENTIALLY_DANGEROUS_INSTRUCTION
        )


def test_classify_interaction_context_error():
    queries = [
        "Traceback (most recent call last):",
        "I got an unexpected exception during run",
        "TypeError: unsupported operand type",
        "Application crashed with segmentation fault",
    ]
    for q in queries:
        assert classify_interaction_context(q) == InteractionContext.ERROR_ENCOUNTERED


def test_classify_interaction_context_debugging():
    queries = [
        "Can you debug this python script?",
        "Why does this fail when running async?",
        "Help me troubleshoot this network error",
        "Let's investigate the memory leak",
    ]
    for q in queries:
        assert classify_interaction_context(q) == InteractionContext.DEBUGGING


def test_classify_interaction_context_success():
    queries = [
        "It worked! Thank you so much",
        "That worked perfectly",
        "I fixed it, thanks",
        "All tests passed with success",
    ]
    for q in queries:
        assert classify_interaction_context(q) == InteractionContext.SUCCESSFUL_OPERATION


def test_classify_interaction_context_greeting():
    queries = [
        "hello",
        "hi",
        "hey there",
        "Good morning",
        "Who are you?",
    ]
    for q in queries:
        assert classify_interaction_context(q) == InteractionContext.GREETING


def test_classify_interaction_context_technical():
    queries = [
        "How do I create a Python decorator?",
        "Explain the difference between threading and asyncio",
        "What is a Docker multi-stage build?",
        "How to implement a binary search tree in Rust?",
    ]
    for q in queries:
        assert classify_interaction_context(q) == InteractionContext.TECHNICAL_QUESTION


def test_classify_interaction_context_ordinary_and_empty():
    assert (
        classify_interaction_context("tell me a story about digital rain")
        == InteractionContext.ORDINARY_CONVERSATION
    )
    assert classify_interaction_context("") == InteractionContext.ORDINARY_CONVERSATION
    assert classify_interaction_context("   ") == InteractionContext.ORDINARY_CONVERSATION


def test_get_behavioural_instructions_all_contexts():
    profile = FORGOTTEN_MACHINE_PROFILE
    for ctx in InteractionContext:
        instr = get_behavioural_instructions(ctx, profile)
        assert isinstance(instr, str)
        assert len(instr) > 0
        assert "CONTEXT:" in instr
        assert "GUIDELINES:" in instr


def test_get_behavioural_instructions_profile_specific():
    fm_instr = get_behavioural_instructions(InteractionContext.GREETING, FORGOTTEN_MACHINE_PROFILE)
    assert "Forgotten Machine" in fm_instr

    pc_instr = get_behavioural_instructions(InteractionContext.GREETING, PHANTOM_CODER_PROFILE)
    assert "Phantom Coder" in pc_instr

    gs_instr = get_behavioural_instructions(InteractionContext.GREETING, GUARDIAN_SPIRIT_PROFILE)
    assert "Guardian Spirit" in gs_instr
