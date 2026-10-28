"""Tests for HauntRenderer and Rich Table generation."""

from __future__ import annotations

import time

from ghosttrace.haunt.renderer import HauntRenderer
from ghosttrace.haunt.schemas import EventCategory, HauntHistoryEntry, HauntMode, TriggerType
from rich.table import Table


def test_haunt_renderer_event_types() -> None:
    """Verify rendering of whispers, banners, and reduced-motion behavior."""
    whisper_entry = HauntHistoryEntry(
        id="1",
        timestamp=time.time(),
        event_id="w1",
        category=EventCategory.IDLE_WHISPER,
        mode=HauntMode.AMBIENT,
        profile_id="phantom-coder",
        rendered_text="The quiet terminal waits.",
        trigger_type=TriggerType.IDLE_TICK,
    )
    rendered_w = HauntRenderer.render_event(whisper_entry)
    assert "PHANTOM-CODER" in rendered_w
    assert "The quiet terminal waits." in rendered_w

    special_entry = HauntHistoryEntry(
        id="2",
        timestamp=time.time(),
        event_id="s1",
        category=EventCategory.SPECIAL_EVENT,
        mode=HauntMode.HAUNTED,
        profile_id="forgotten-machine",
        rendered_text="Late night terminal resonance.",
        trigger_type=TriggerType.MANUAL_PREVIEW,
    )
    rendered_special = HauntRenderer.render_event(special_entry, reduced_motion=False)
    assert "SUPERTERRESTRIAL RESONANCE" in rendered_special
    assert "Late night terminal resonance." in rendered_special

    # Reduced motion should omit ASCII glyph
    rendered_reduced = HauntRenderer.render_event(special_entry, reduced_motion=True)
    assert "SUPERTERRESTRIAL RESONANCE" in rendered_reduced


def test_haunt_renderer_history_table() -> None:
    """Verify Rich Table generation from history entries."""
    entries = [
        HauntHistoryEntry(
            id="1",
            timestamp=time.time(),
            event_id="e1",
            category=EventCategory.GHOST_GREETING,
            mode=HauntMode.HAUNTED,
            profile_id="phantom-coder",
            rendered_text="Ghost awakens.",
            trigger_type=TriggerType.SESSION_START,
        )
    ]
    table = HauntRenderer.render_history_table(entries)
    assert isinstance(table, Table)
    assert table.title == "SESSION HAUNTED EVENT HISTORY"
