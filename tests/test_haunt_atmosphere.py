"""Tests for ASCII art glyphs and atmospheric formatting helpers."""

from __future__ import annotations

from ghosttrace.haunt.atmosphere import (
    format_atmospheric_whisper,
    format_haunt_banner,
    format_mood_shift_banner,
    get_ascii_ghost,
)


def test_ascii_ghost_glyphs() -> None:
    """Verify ASCII glyphs returned for all ghost profiles."""
    fm_glyph = get_ascii_ghost("forgotten-machine")
    pc_glyph = get_ascii_ghost("phantom-coder")
    gs_glyph = get_ascii_ghost("guardian-spirit")
    def_glyph = get_ascii_ghost("unknown")

    assert len(fm_glyph) > 0
    assert len(pc_glyph) > 0
    assert len(gs_glyph) > 0
    assert def_glyph == fm_glyph


def test_format_atmospheric_whisper() -> None:
    """Verify whisper formatting contains profile label and text."""
    formatted = format_atmospheric_whisper("The sectors are quiet.", profile_id="phantom-coder")
    assert "PHANTOM-CODER" in formatted
    assert "The sectors are quiet." in formatted


def test_format_haunt_banner() -> None:
    """Verify banner formatting with and without ASCII glyph."""
    banner_no_glyph = format_haunt_banner("Awakening", "The system awakens", glyph=False)
    assert "AWAKENING" in banner_no_glyph
    assert "The system awakens" in banner_no_glyph

    banner_glyph = format_haunt_banner(
        "Superterrestrial", "Ghost signal", glyph=True, profile_id="forgotten-machine"
    )
    assert "SUPERTERRESTRIAL" in banner_glyph
    assert "Ghost signal" in banner_glyph
    assert "o o" in banner_glyph or "~~~" in banner_glyph


def test_format_mood_shift_banner() -> None:
    """Verify mood transition manifestation banner."""
    res = format_mood_shift_banner("DORMANT", "CURIOUS", "Curiosity awakens in the terminal.")
    assert "DORMANT" in res
    assert "CURIOUS" in res
    assert "Curiosity awakens in the terminal." in res
