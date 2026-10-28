"""Trigger evaluation logic mapping application events to atmospheric ghost reactions."""

from __future__ import annotations

import logging

from ghosttrace.haunt.event_catalog import EventCatalog
from ghosttrace.haunt.reactions import GhostReactionBuilder
from ghosttrace.haunt.scheduler import HauntScheduler
from ghosttrace.haunt.schemas import (
    EventCategory,
    HauntEvent,
    HauntMode,
    TriggerContext,
    TriggerResult,
    TriggerType,
)

logger = logging.getLogger("ghosttrace.haunt.triggers")

TRIGGER_TO_CATEGORIES: dict[TriggerType, list[EventCategory]] = {
    TriggerType.SESSION_START: [EventCategory.SESSION_EVENT, EventCategory.GHOST_GREETING],
    TriggerType.COMMAND_INVOKED: [EventCategory.DISCOVERY_EVENT],
    TriggerType.COMMAND_DISCOVERY: [EventCategory.DISCOVERY_EVENT],
    TriggerType.CODING_SUCCESS: [EventCategory.CODING_REACTION],
    TriggerType.APP_ERROR: [EventCategory.ERROR_REACTION],
    TriggerType.GUARDIAN_WARNING: [EventCategory.GUARDIAN_REACTION],
    TriggerType.MOOD_TRANSITION: [EventCategory.MOOD_SHIFT],
    TriggerType.IDLE_TICK: [EventCategory.IDLE_WHISPER],
    TriggerType.MANUAL_PREVIEW: list(EventCategory),
}


class TriggerEvaluator:
    """Evaluates whether an application trigger should produce an atmospheric manifestation."""

    def __init__(self, catalog: EventCatalog, scheduler: HauntScheduler) -> None:
        self.catalog = catalog
        self.scheduler = scheduler

    def evaluate(
        self,
        context: TriggerContext,
        mode: HauntMode,
        enabled: bool = True,
        seed: int | None = None,
    ) -> TriggerResult:
        """Evaluate a trigger context against mode rules, cooldowns, and catalog definitions."""
        is_preview = context.trigger_type == TriggerType.MANUAL_PREVIEW

        # 1. Enabled check (unless preview)
        if not enabled and not is_preview:
            return TriggerResult(
                fired=False,
                reason="Haunted experience subsystem is disabled.",
            )

        # 2. Mode suppression (NORMAL and FOCUS never fire unsolicited events)
        if not is_preview:
            if mode == HauntMode.NORMAL:
                return TriggerResult(
                    fired=False,
                    reason="Atmospheric events are suppressed in NORMAL mode.",
                )
            if mode == HauntMode.FOCUS:
                return TriggerResult(
                    fired=False,
                    reason="Atmospheric events are suppressed in FOCUS mode.",
                )

        # 3. Special handling for idle triggers
        if (
            context.trigger_type == TriggerType.IDLE_TICK
            and not is_preview
            and not self.scheduler.can_trigger_idle(context.idle_seconds)
        ):
            return TriggerResult(
                fired=False,
                reason="Idle duration threshold not met or idle whisper cooldown active.",
            )

        # 4. Resolve candidate categories for this trigger type
        candidate_categories = TRIGGER_TO_CATEGORIES.get(context.trigger_type, [])
        if not candidate_categories:
            return TriggerResult(
                fired=False,
                reason=f"No event categories registered for trigger '{context.trigger_type}'.",
            )

        # 5. Gather eligible events from catalog
        candidates: list[HauntEvent] = []
        for cat in candidate_categories:
            for ev in self.catalog.filter_by_category(cat):
                if is_preview or mode in ev.eligible_modes:
                    candidates.append(ev)

        if not candidates:
            return TriggerResult(
                fired=False,
                reason=f"No eligible events configured for mode '{mode.value}'.",
            )

        # Sort candidate events by priority descending
        candidates.sort(key=lambda ev: ev.priority, reverse=True)

        # 6. Evaluate scheduling eligibility
        selected_event: HauntEvent | None = None
        rejection_reason = "All candidates rejected by scheduler."

        for cand in candidates:
            eligible, reason = self.scheduler.can_trigger(
                event_id=cand.id,
                event_cooldown=cand.cooldown_seconds,
                now=context.timestamp,
                is_preview=is_preview,
            )
            if eligible:
                selected_event = cand
                break
            rejection_reason = reason

        if selected_event is None:
            return TriggerResult(
                fired=False,
                reason=rejection_reason,
            )

        # 7. Render appropriate text based on context and profile
        text = self._render_content(selected_event, context, seed=seed)

        # 8. Record trigger if not preview
        if not is_preview:
            self.scheduler.record_trigger(
                event_id=selected_event.id,
                event_cooldown=selected_event.cooldown_seconds,
                now=context.timestamp,
            )
            if context.trigger_type == TriggerType.IDLE_TICK:
                self.scheduler.record_idle_trigger(now=context.timestamp)

        return TriggerResult(
            fired=True,
            event=selected_event,
            rendered_text=text,
            reason="Atmospheric event triggered successfully.",
            category=selected_event.category,
        )

    def _render_content(
        self, event: HauntEvent, context: TriggerContext, seed: int | None = None
    ) -> str:
        """Compose the final atmospheric text, applying dynamic reactions when available."""
        profile = context.profile_id or "default"

        # Check for dynamic reaction builders
        if event.category == EventCategory.CODING_REACTION and context.dev_intent:
            return GhostReactionBuilder.react_to_coding_success(context.dev_intent, profile)

        if event.category == EventCategory.ERROR_REACTION and context.error_message:
            return GhostReactionBuilder.react_to_error(context.error_message, profile)

        if event.category == EventCategory.GUARDIAN_REACTION:
            binary = context.command_name or "command"
            return GhostReactionBuilder.react_to_guardian_warning(
                context.risk_level, binary, profile
            )

        if event.category == EventCategory.MOOD_SHIFT and context.mood_from and context.mood_to:
            return GhostReactionBuilder.react_to_mood_shift(
                context.mood_from, context.mood_to, profile
            )

        # Fall back to template selection
        return self.catalog.select_template(event, profile_id=profile, seed=seed)
