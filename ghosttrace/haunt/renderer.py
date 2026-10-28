"""Rendering engine for haunted experience events and terminal widgets."""

from __future__ import annotations

import time

from rich.table import Table

from ghosttrace.haunt.atmosphere import (
    format_atmospheric_whisper,
    format_haunt_banner,
    format_mood_shift_banner,
)
from ghosttrace.haunt.schemas import EventCategory, HauntHistoryEntry, HauntMode


class HauntRenderer:
    """Formats atmospheric events into clean, high-contrast Rich and Textual renderables."""

    @staticmethod
    def render_event(
        entry: HauntHistoryEntry,
        reduced_motion: bool = False,
    ) -> str:
        """Render a triggered atmospheric event entry based on category and motion preference."""
        if entry.category == EventCategory.IDLE_WHISPER:
            return format_atmospheric_whisper(entry.rendered_text, entry.profile_id)

        if entry.category == EventCategory.MOOD_SHIFT:
            return format_mood_shift_banner("PREVIOUS", "CURRENT", entry.rendered_text)

        if entry.category == EventCategory.SPECIAL_EVENT and entry.mode == HauntMode.HAUNTED:
            glyph = not reduced_motion
            return format_haunt_banner(
                "SUPERTERRESTRIAL RESONANCE",
                entry.rendered_text,
                glyph=glyph,
                profile_id=entry.profile_id,
            )

        # Standard atmospheric banner
        return format_haunt_banner(
            entry.category.value.replace("_", " "),
            entry.rendered_text,
            glyph=False,
            profile_id=entry.profile_id,
        )

    @staticmethod
    def render_history_table(entries: list[HauntHistoryEntry]) -> Table:
        """Render a Rich Table displaying session event history."""
        table = Table(
            title="SESSION HAUNTED EVENT HISTORY",
            border_style="#005522",
            show_header=True,
            header_style="bold #00ff66",
        )
        table.add_column("Time", style="dim #888888", width=10)
        table.add_column("Category", style="bold #33ff33", width=18)
        table.add_column("Profile", style="#aaddaa", width=18)
        table.add_column("Trigger", style="#88cc88", width=16)
        table.add_column("Message Preview", style="#ddffdd")

        for item in entries:
            t_str = time.strftime("%H:%M:%S", time.localtime(item.timestamp))
            snippet = item.rendered_text
            if len(snippet) > 60:
                snippet = snippet[:57] + "..."
            table.add_row(
                t_str, item.category.value, item.profile_id, item.trigger_type.value, snippet
            )

        return table
