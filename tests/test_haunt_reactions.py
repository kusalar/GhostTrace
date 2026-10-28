"""Tests for GhostReactionBuilder across all 3 profiles."""

from __future__ import annotations

from ghosttrace.haunt.reactions import GhostReactionBuilder


def test_reaction_coding_success() -> None:
    """Verify coding success reactions vary by profile."""
    rx_fm = GhostReactionBuilder.react_to_coding_success("explain_code", "forgotten-machine")
    rx_pc = GhostReactionBuilder.react_to_coding_success("explain_code", "phantom-coder")
    rx_gs = GhostReactionBuilder.react_to_coding_success("explain_code", "guardian-spirit")

    assert "explain code" in rx_fm
    assert "explain code" in rx_pc
    assert "explain code" in rx_gs

    assert rx_fm != rx_pc
    assert rx_pc != rx_gs


def test_reaction_error() -> None:
    """Verify genuine error reactions vary by profile."""
    rx_fm = GhostReactionBuilder.react_to_error("Division by zero", "forgotten-machine")
    rx_pc = GhostReactionBuilder.react_to_error("Division by zero", "phantom-coder")
    rx_gs = GhostReactionBuilder.react_to_error("Division by zero", "guardian-spirit")

    assert "fracture" in rx_fm.lower()
    assert "traceback" in rx_pc.lower()
    assert "operational exception" in rx_gs.lower()


def test_reaction_guardian_warning() -> None:
    """Verify Guardian warning reactions acknowledge target binary and risk."""
    rx_fm = GhostReactionBuilder.react_to_guardian_warning(
        "MEDIUM", "git reset", "forgotten-machine"
    )
    rx_pc = GhostReactionBuilder.react_to_guardian_warning("HIGH", "del /f", "phantom-coder")
    rx_gs = GhostReactionBuilder.react_to_guardian_warning("HIGH", "rmdir /s", "guardian-spirit")

    assert "git reset" in rx_fm
    assert "del /f" in rx_pc
    assert "rmdir /s" in rx_gs


def test_reaction_mood_shift() -> None:
    """Verify mood shift reactions mention source and target states."""
    rx_fm = GhostReactionBuilder.react_to_mood_shift("DORMANT", "FOCUSED", "forgotten-machine")
    rx_pc = GhostReactionBuilder.react_to_mood_shift("DORMANT", "CURIOUS", "phantom-coder")

    assert "dormant" in rx_fm.lower()
    assert "focused" in rx_fm.lower()
    assert "curious" in rx_pc.lower()
