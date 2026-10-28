"""Tests for EventCatalog registration, filtering, and template resolution."""

from __future__ import annotations

from ghosttrace.haunt.event_catalog import EventCatalog
from ghosttrace.haunt.schemas import EventCategory, HauntEvent, HauntMode


def test_default_catalog_covers_all_categories() -> None:
    """Verify standard catalog covers every registered event category."""
    catalog = EventCatalog()
    all_events = catalog.events
    assert len(all_events) >= 9

    found_categories = {ev.category for ev in all_events}
    for cat in EventCategory:
        assert cat in found_categories, f"Category {cat.value} not covered in default catalog"


def test_catalog_profile_template_selection() -> None:
    """Verify template selection resolves profile-specific wording with deterministic seeding."""
    catalog = EventCatalog()
    ev = catalog.get("greeting_awakening")
    assert ev is not None

    text_fm = catalog.select_template(ev, profile_id="forgotten-machine", seed=42)
    assert any(snippet in text_fm for snippet in ["terminal is quiet", "Sectors stir"])

    text_pc = catalog.select_template(ev, profile_id="phantom-coder", seed=42)
    assert any(snippet in text_pc for snippet in ["chase bugs", "prompt is alive"])

    text_gs = catalog.select_template(ev, profile_id="guardian-spirit", seed=42)
    assert any(snippet in text_gs for snippet in ["work carefully", "safety perimeter"])

    text_def = catalog.select_template(ev, profile_id="unknown_profile", seed=42)
    assert len(text_def) > 0


def test_catalog_filtering() -> None:
    """Verify category and mode filtering in EventCatalog."""
    catalog = EventCatalog()
    whispers = catalog.filter_by_category(EventCategory.IDLE_WHISPER)
    assert len(whispers) >= 1
    assert all(w.category == EventCategory.IDLE_WHISPER for w in whispers)

    haunted_events = catalog.filter_by_mode(HauntMode.HAUNTED)
    ambient_events = catalog.filter_by_mode(HauntMode.AMBIENT)
    assert len(haunted_events) >= len(ambient_events)


def test_catalog_custom_event_registration() -> None:
    """Verify dynamic event registration in catalog."""
    catalog = EventCatalog()
    custom = HauntEvent(
        id="custom_echo",
        category=EventCategory.SPECIAL_EVENT,
        name="Custom Echo",
        description="A custom test event",
        templates={"default": ["Echo across sectors"]},
    )
    catalog.register(custom)
    assert catalog.get("custom_echo") is not None
