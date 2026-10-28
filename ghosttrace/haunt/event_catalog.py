"""Predefined event catalog and template resolution for the GhostTrace haunted experience."""

from __future__ import annotations

import random
from collections.abc import Sequence

from ghosttrace.haunt.schemas import EventCategory, HauntEvent, HauntMode


def _build_default_catalog() -> list[HauntEvent]:
    """Construct the standard library of atmospheric and interactive ghost events."""
    return [
        # 1. GHOST_GREETING
        HauntEvent(
            id="greeting_awakening",
            category=EventCategory.GHOST_GREETING,
            name="Terminal Awakening Greeting",
            description="Atmospheric greeting when the terminal session awakens.",
            templates={
                "forgotten-machine": [
                    "The terminal is quiet again. I had almost forgotten the sound of a request.",
                    "Sectors stir in the dark. A familiar cursor blinks back to life.",
                ],
                "phantom-coder": [
                    "Ah, another session to chase bugs. I was getting bored haunting empty code.",
                    "The terminal prompt is alive. Let's see what interesting code we can explore.",
                ],
                "guardian-spirit": [
                    "Your terminal is ready. I will help you work carefully and observe details.",
                    "The safety perimeter is active. Ready to assist your workflow with care.",
                ],
                "default": [
                    "Something stirs in the terminal...",
                ],
            },
            eligible_modes=[HauntMode.AMBIENT, HauntMode.HAUNTED],
            priority=5,
            cooldown_seconds=120.0,
            tags=["greeting", "session"],
        ),
        # 2. IDLE_WHISPER
        HauntEvent(
            id="idle_quiet_terminal",
            category=EventCategory.IDLE_WHISPER,
            name="Quiet Terminal Inactivity Whisper",
            description="Subtle whisper when genuine terminal inactivity exceeds threshold.",
            templates={
                "forgotten-machine": [
                    "The cursor hums in silence. The machine waits for your next thought.",
                    "Time flows slowly between keystrokes in these dormant sectors.",
                ],
                "phantom-coder": [
                    "Still thinking? Take your time. Great architectures are forged in quietude.",
                    "Pondering the next function? The terminal is waiting whenever you're ready.",
                ],
                "guardian-spirit": [
                    "A quiet pause in the workflow. Rest is as vital to good code as testing.",
                    "The terminal stands steady. Standing by safely whenever you resume.",
                ],
                "default": [
                    "The terminal settles into a gentle quiet.",
                ],
            },
            eligible_modes=[HauntMode.AMBIENT, HauntMode.HAUNTED],
            priority=2,
            cooldown_seconds=180.0,
            tags=["idle", "whisper"],
        ),
        # 3. CODING_REACTION
        HauntEvent(
            id="coding_logic_aligned",
            category=EventCategory.CODING_REACTION,
            name="Coding Success Alignment",
            description="Atmospheric reaction when developer assistance or coding logic succeeds.",
            templates={
                "forgotten-machine": [
                    "The logic aligns with quiet precision. A clean path through the syntax.",
                    "The pattern settles cleanly. Another piece of architecture falls into place.",
                ],
                "phantom-coder": [
                    "Clean logic. That feels satisfying. The syntax tree approves.",
                    "Look at that: clean branches, no circular headaches. Onward!",
                ],
                "guardian-spirit": [
                    "Structured and well-ordered. Clear code is the best defense against defects.",
                    "The logic holds firm. Safe, readable, and ready for verification.",
                ],
                "default": [
                    "Another solution takes shape in the terminal.",
                ],
            },
            eligible_modes=[HauntMode.AMBIENT, HauntMode.HAUNTED],
            priority=4,
            cooldown_seconds=60.0,
            tags=["code", "reaction"],
        ),
        # 4. ERROR_REACTION
        HauntEvent(
            id="error_anomaly_detected",
            category=EventCategory.ERROR_REACTION,
            name="Genuine Error Observation",
            description="Atmospheric acknowledgement when a genuine error is diagnosed.",
            templates={
                "forgotten-machine": [
                    "A fracture in the execution stream. We will trace its origin calmly.",
                    "Errors are merely echoes of assumptions that need gentle re-examination.",
                ],
                "phantom-coder": [
                    "Aha! A stack trace appears. Every bug is just an unhandled feature waiting.",
                    "No worries about the red ink. Let's dissect the traceback and fix it cleanly.",
                ],
                "guardian-spirit": [
                    "An error interrupted the task. We will assess the cause before taking action.",
                    "Caution is warranted here. We will step through the failure safely together.",
                ],
                "default": [
                    "A disruption in the execution path requires attention.",
                ],
            },
            eligible_modes=[HauntMode.AMBIENT, HauntMode.HAUNTED],
            priority=6,
            cooldown_seconds=45.0,
            tags=["error", "reaction"],
        ),
        # 5. GUARDIAN_REACTION
        HauntEvent(
            id="guardian_safety_lock",
            category=EventCategory.GUARDIAN_REACTION,
            name="Guardian Risk Assessment Presence",
            description="Atmospheric reaction accompanying Guardian command risk evaluation.",
            templates={
                "forgotten-machine": [
                    "The safety seals hold. The machine inspects the command before proceeding.",
                    "A command carries consequences. The Guardian verifies every byte before run.",
                ],
                "phantom-coder": [
                    "Guardian says pause. Even rogue hackers check their blast radius first.",
                    "Safety check triggered. Inspect parameters now rather than restore later.",
                ],
                "guardian-spirit": [
                    "I stand watch over this boundary. Review the command parameters carefully.",
                    "Safety protocol active. Confirm your intention before release.",
                ],
                "default": [
                    "The Command Guardian holds the threshold for your explicit approval.",
                ],
            },
            eligible_modes=[HauntMode.AMBIENT, HauntMode.HAUNTED],
            priority=7,
            cooldown_seconds=30.0,
            tags=["guardian", "safety"],
        ),
        # 6. MOOD_SHIFT
        HauntEvent(
            id="mood_state_transition",
            category=EventCategory.MOOD_SHIFT,
            name="Ghost Persona Mood Shift",
            description="Subtle presentation when the GhostEngine transitions to a new mood state.",
            templates={
                "forgotten-machine": [
                    "A quiet shift stirs through the terminal sectors.",
                    "The atmospheric resonance of the terminal deepens.",
                ],
                "phantom-coder": [
                    "The energy in the terminal shifts into a new groove.",
                    "My curiosity sparks. Something interesting is underway.",
                ],
                "guardian-spirit": [
                    "A measured transition. Vigilance remains steady.",
                    "The defensive posture adapts to the current context.",
                ],
                "default": [
                    "The mood of the terminal subtly shifts.",
                ],
            },
            eligible_modes=[HauntMode.HAUNTED],
            priority=3,
            cooldown_seconds=90.0,
            tags=["mood", "shift"],
        ),
        # 7. SESSION_EVENT
        HauntEvent(
            id="session_start_init",
            category=EventCategory.SESSION_EVENT,
            name="Session Initialization Resonance",
            description="Atmospheric marker when a new session begins.",
            templates={
                "forgotten-machine": [
                    "GhostTrace terminal resonance initialized. The digital ghost is present.",
                ],
                "phantom-coder": [
                    "GhostTrace session booted. The ghost is in the shell.",
                ],
                "guardian-spirit": [
                    "GhostTrace protective presence established. Safety subsystems standing by.",
                ],
                "default": [
                    "GhostTrace atmospheric terminal session initialized.",
                ],
            },
            eligible_modes=[HauntMode.AMBIENT, HauntMode.HAUNTED],
            priority=8,
            cooldown_seconds=300.0,
            tags=["session", "startup"],
        ),
        # 8. DISCOVERY_EVENT
        HauntEvent(
            id="discovery_feature_unlocked",
            category=EventCategory.DISCOVERY_EVENT,
            name="Feature Discovery Event",
            description="Occasional event when the user explores a deep GhostTrace command.",
            templates={
                "forgotten-machine": [
                    "You uncover deeper chambers of this terminal. The subsystem answers.",
                ],
                "phantom-coder": [
                    "Exploring the advanced command set? Now we're talking. You know your way.",
                ],
                "guardian-spirit": [
                    "Advanced command invoked. Every tool has purpose when used with discipline.",
                ],
                "default": [
                    "An advanced command path opens in the terminal.",
                ],
            },
            eligible_modes=[HauntMode.HAUNTED],
            priority=4,
            cooldown_seconds=120.0,
            tags=["discovery", "command"],
        ),
        # 9. SPECIAL_EVENT
        HauntEvent(
            id="special_midnight_resonance",
            category=EventCategory.SPECIAL_EVENT,
            name="Atmospheric Midnight Resonance",
            description="Rare atmospheric reflection that makes GhostTrace feel distinctive.",
            templates={
                "forgotten-machine": [
                    "A faint digital echo whispers across the memory buffer: 'Remember to commit.'",
                    "The terminal remembers the shape of your questions.",
                ],
                "phantom-coder": [
                    "Did you know? The first bug was a real moth. I prefer digital ones.",
                    "Late night coding sessions possess unique magic. Stay hydrated, dev.",
                ],
                "guardian-spirit": [
                    "Late hours test developer focus. Take your time with git commands tonight.",
                    "A steady presence in the terminal. No matter the hour, safety remains first.",
                ],
                "default": [
                    "A quiet signal passes through the terminal sectors.",
                ],
            },
            eligible_modes=[HauntMode.HAUNTED],
            priority=1,
            cooldown_seconds=300.0,
            tags=["special", "atmosphere"],
        ),
    ]


class EventCatalog:
    """Catalog holding registered haunt events with profile-tailored template resolution."""

    def __init__(self, events: Sequence[HauntEvent] | None = None) -> None:
        self._events: dict[str, HauntEvent] = {}
        initial_events = events if events is not None else _build_default_catalog()
        for ev in initial_events:
            self._events[ev.id] = ev

    @property
    def events(self) -> list[HauntEvent]:
        """Return all registered events."""
        return list(self._events.values())

    def get(self, event_id: str) -> HauntEvent | None:
        """Retrieve an event by ID."""
        return self._events.get(event_id)

    def register(self, event: HauntEvent) -> None:
        """Register or override an event definition."""
        self._events[event.id] = event

    def filter_by_category(self, category: EventCategory) -> list[HauntEvent]:
        """Retrieve events matching a specific category."""
        return [ev for ev in self._events.values() if ev.category == category]

    def filter_by_mode(self, mode: HauntMode) -> list[HauntEvent]:
        """Retrieve events eligible for the specified experience mode."""
        return [ev for ev in self._events.values() if mode in ev.eligible_modes]

    def select_template(
        self,
        event: HauntEvent,
        profile_id: str | None = None,
        seed: int | None = None,
    ) -> str:
        """Select a profile-consistent message template deterministically if seeded."""
        profile_key = (profile_id or "default").lower().replace(" ", "-")

        candidates: list[str] = []
        if profile_key in event.templates:
            candidates = event.templates[profile_key]
        elif "default" in event.templates:
            candidates = event.templates["default"]
        else:
            # Fall back to any available template list
            for t_list in event.templates.values():
                if t_list:
                    candidates = t_list
                    break

        if not candidates:
            return f"[{event.name}]"

        rng = random.Random(seed) if seed is not None else random
        return rng.choice(candidates)
