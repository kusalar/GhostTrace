"""Central facade coordinating the GhostTrace haunted experience subsystem."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rich.table import Table

from ghosttrace.haunt.event_catalog import EventCatalog
from ghosttrace.haunt.renderer import HauntRenderer
from ghosttrace.haunt.scheduler import HauntScheduler
from ghosttrace.haunt.schemas import (
    EventCategory,
    HauntHistoryEntry,
    HauntIntensity,
    HauntMode,
    HauntStatus,
    TriggerContext,
    TriggerResult,
    TriggerType,
)
from ghosttrace.haunt.session import HauntHistoryManager
from ghosttrace.haunt.triggers import TriggerEvaluator

if TYPE_CHECKING:
    from ghosttrace.config.settings import Settings
    from ghosttrace.ghost.engine import GhostEngine

logger = logging.getLogger("ghosttrace.haunt.engine")


class HauntEngine:
    """Facade orchestrating atmospheric events, experience modes, scheduling, and history."""

    def __init__(
        self,
        settings: Settings | None = None,
        ghost_engine: GhostEngine | None = None,
        catalog: EventCatalog | None = None,
    ) -> None:
        self.settings = settings
        self.ghost_engine = ghost_engine

        self._enabled = getattr(settings, "haunt_enabled", True) if settings else True
        raw_mode = getattr(settings, "haunt_mode", "normal") if settings else "normal"
        self._mode = HauntMode(raw_mode.lower())

        raw_intensity = getattr(settings, "haunt_intensity", "medium") if settings else "medium"
        self._intensity = HauntIntensity(raw_intensity.lower())

        cooldown = getattr(settings, "haunt_cooldown_seconds", 60.0) if settings else 60.0
        max_events = getattr(settings, "haunt_max_events_per_session", 30) if settings else 30
        idle_thresh = getattr(settings, "haunt_idle_seconds", 120.0) if settings else 120.0
        idle_enabled = getattr(settings, "haunt_idle_events", False) if settings else False
        self._reduced_motion = (
            getattr(settings, "haunt_reduced_motion", False) if settings else False
        )

        self.catalog = catalog or EventCatalog()
        self.scheduler = HauntScheduler(
            base_cooldown_seconds=cooldown,
            max_events_per_session=max_events,
            intensity=self._intensity,
            idle_threshold_seconds=idle_thresh,
            idle_enabled=idle_enabled,
        )
        self.history = HauntHistoryManager(max_entries=100)
        self.evaluator = TriggerEvaluator(self.catalog, self.scheduler)
        self.renderer = HauntRenderer()

    @property
    def is_enabled(self) -> bool:
        """Return whether the haunted experience subsystem is active."""
        return self._enabled

    def enable(self) -> None:
        """Enable the haunted experience subsystem."""
        self._enabled = True
        logger.info("Haunted experience subsystem enabled.")

    def disable(self) -> None:
        """Disable the haunted experience subsystem."""
        self._enabled = False
        logger.info("Haunted experience subsystem disabled.")

    @property
    def mode(self) -> HauntMode:
        """Return the current experience mode."""
        return self._mode

    def set_mode(self, mode: str | HauntMode) -> HauntMode:
        """Change the experience mode immediately without model reload."""
        if isinstance(mode, str):
            mode = HauntMode(mode.strip().lower())
        self._mode = mode
        logger.info("Haunted experience mode switched to '%s'.", mode.value)
        return self._mode

    @property
    def intensity(self) -> HauntIntensity:
        """Return the current intensity setting."""
        return self._intensity

    def set_intensity(self, intensity: str | HauntIntensity) -> HauntIntensity:
        """Adjust atmospheric event frequency and cooldown scaling."""
        if isinstance(intensity, str):
            intensity = HauntIntensity(intensity.strip().lower())
        self._intensity = intensity
        self.scheduler.intensity = intensity
        logger.info("Haunted experience intensity set to '%s'.", intensity.value)
        return self._intensity

    def set_idle_events(self, enabled: bool) -> None:
        """Toggle idle whisper event generation."""
        self.scheduler.idle_enabled = enabled
        logger.info("Haunted experience idle events set to %s.", enabled)

    @property
    def reduced_motion(self) -> bool:
        """Return whether reduced motion styling is enforced."""
        return self._reduced_motion

    def set_reduced_motion(self, enabled: bool) -> None:
        """Toggle reduced motion styling."""
        self._reduced_motion = enabled

    def process_trigger(self, context: TriggerContext, seed: int | None = None) -> TriggerResult:
        """Evaluate an application trigger and record to session history if an event fires."""
        # Attach active profile if omitted
        if context.profile_id is None and self.ghost_engine is not None:
            context.profile_id = self.ghost_engine.active_profile.id.value

        result = self.evaluator.evaluate(
            context=context,
            mode=self._mode,
            enabled=self._enabled,
            seed=seed,
        )

        if result.fired and result.event is not None and result.rendered_text is not None:
            self.history.add_entry(
                event_id=result.event.id,
                category=result.event.category,
                mode=self._mode,
                profile_id=context.profile_id or "default",
                rendered_text=result.rendered_text,
                trigger_type=context.trigger_type,
            )

        return result

    def preview_event(
        self,
        category: str | EventCategory | None = None,
        profile_id: str | None = None,
        seed: int | None = None,
    ) -> TriggerResult:
        """Preview an atmospheric event safely without recording to history or cooldowns."""
        prof = profile_id
        if prof is None and self.ghost_engine is not None:
            prof = self.ghost_engine.active_profile.id.value

        cat: EventCategory | None = None
        if category is not None:
            cat = EventCategory(category.strip().lower()) if isinstance(category, str) else category

        context = TriggerContext(
            trigger_type=TriggerType.MANUAL_PREVIEW,
            profile_id=prof or "default",
        )

        if cat is not None:
            candidates = self.catalog.filter_by_category(cat)
            if not candidates:
                return TriggerResult(
                    fired=False,
                    reason=f"No events registered in category '{cat.value}'.",
                )
            selected = candidates[0]
            text = self.catalog.select_template(selected, profile_id=prof, seed=seed)
            return TriggerResult(
                fired=True,
                event=selected,
                rendered_text=text,
                reason="Preview generated successfully.",
                category=selected.category,
            )

        return self.evaluator.evaluate(
            context=context,
            mode=self._mode,
            enabled=self._enabled,
            seed=seed,
        )

    def get_status(self) -> HauntStatus:
        """Return a typed status snapshot for inspection."""
        active_prof = (
            self.ghost_engine.active_profile.name if self.ghost_engine is not None else "Unknown"
        )
        curr_mood = (
            self.ghost_engine.current_mood.value if self.ghost_engine is not None else "Unknown"
        )
        return HauntStatus(
            enabled=self._enabled,
            mode=self._mode,
            intensity=self._intensity,
            active_profile=active_prof,
            current_mood=curr_mood,
            total_events_triggered=self.scheduler.total_events,
            session_events_remaining=self.scheduler.remaining_events,
            max_events_per_session=self.scheduler.max_events_per_session,
            cooldown_seconds=self.scheduler.base_cooldown_seconds,
            last_event_time=self.scheduler.last_event_time,
            idle_enabled=self.scheduler.idle_enabled,
            idle_threshold_seconds=self.scheduler.idle_threshold_seconds,
            reduced_motion=self._reduced_motion,
        )

    def clear_history(self) -> None:
        """Clear session event history."""
        self.history.clear()

    def get_history(self, limit: int | None = None) -> list[HauntHistoryEntry]:
        """Return session event history entries."""
        return self.history.get_entries(limit=limit)

    def render_history_table(self) -> Table:
        """Render a Rich Table of session event history."""
        return self.renderer.render_history_table(self.history.get_entries())
