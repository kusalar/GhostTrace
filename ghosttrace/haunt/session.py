"""Bounded in-memory session history for the GhostTrace haunted experience."""

from __future__ import annotations

import collections
import uuid

from ghosttrace.haunt.schemas import EventCategory, HauntHistoryEntry, HauntMode, TriggerType


class HauntHistoryManager:
    """Maintains an in-memory, bounded FIFO queue of triggered atmospheric events."""

    def __init__(self, max_entries: int = 100) -> None:
        self._max_entries = max_entries
        self._entries: collections.deque[HauntHistoryEntry] = collections.deque(maxlen=max_entries)

    @property
    def count(self) -> int:
        """Return the count of entries in the session history."""
        return len(self._entries)

    def add_entry(
        self,
        event_id: str,
        category: EventCategory,
        mode: HauntMode,
        profile_id: str,
        rendered_text: str,
        trigger_type: TriggerType,
    ) -> HauntHistoryEntry:
        """Record a triggered event into the bounded session history."""
        entry = HauntHistoryEntry(
            id=uuid.uuid4().hex[:8],
            event_id=event_id,
            category=category,
            mode=mode,
            profile_id=profile_id,
            rendered_text=rendered_text,
            trigger_type=trigger_type,
        )
        self._entries.append(entry)
        return entry

    def get_entries(self, limit: int | None = None) -> list[HauntHistoryEntry]:
        """Return session history entries, oldest first (or up to limit most recent)."""
        entries_list = list(self._entries)
        if limit is not None and limit > 0:
            return entries_list[-limit:]
        return entries_list

    def clear(self) -> None:
        """Clear all session event history entries."""
        self._entries.clear()
