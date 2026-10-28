"""Tests for HauntHistoryManager bounded queue."""

from __future__ import annotations

from ghosttrace.haunt.schemas import EventCategory, HauntMode, TriggerType
from ghosttrace.haunt.session import HauntHistoryManager


def test_session_history_bounded_queue() -> None:
    """Verify session history respects max_entries and FIFO eviction."""
    mgr = HauntHistoryManager(max_entries=3)
    assert mgr.count == 0

    mgr.add_entry(
        "e1",
        EventCategory.GHOST_GREETING,
        HauntMode.HAUNTED,
        "fm",
        "msg1",
        TriggerType.SESSION_START,
    )
    mgr.add_entry(
        "e2",
        EventCategory.CODING_REACTION,
        HauntMode.HAUNTED,
        "fm",
        "msg2",
        TriggerType.CODING_SUCCESS,
    )
    mgr.add_entry(
        "e3",
        EventCategory.SPECIAL_EVENT,
        HauntMode.HAUNTED,
        "fm",
        "msg3",
        TriggerType.MANUAL_PREVIEW,
    )

    assert mgr.count == 3
    entries = mgr.get_entries()
    assert [e.event_id for e in entries] == ["e1", "e2", "e3"]

    # Add 4th entry; 1st should be evicted
    mgr.add_entry(
        "e4", EventCategory.IDLE_WHISPER, HauntMode.HAUNTED, "fm", "msg4", TriggerType.IDLE_TICK
    )
    assert mgr.count == 3
    entries_after = mgr.get_entries()
    assert [e.event_id for e in entries_after] == ["e2", "e3", "e4"]

    # Limit parameter
    limited = mgr.get_entries(limit=2)
    assert len(limited) == 2
    assert limited[-1].event_id == "e4"

    # Clear
    mgr.clear()
    assert mgr.count == 0
