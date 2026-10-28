"""Profile-consistent reaction builder responding to genuine application events."""

from __future__ import annotations


class GhostReactionBuilder:
    """Builds profile-consistent atmospheric reaction lines based on genuine system events."""

    @staticmethod
    def react_to_coding_success(dev_intent: str | None, profile_id: str | None = None) -> str:
        """Atmospheric reaction to completed developer task."""
        profile = (profile_id or "default").lower().replace(" ", "-")
        intent_str = (dev_intent or "operation").lower().replace("_", " ")

        if profile == "phantom-coder":
            return f"That {intent_str} wrapped up nicely. The code flows clean and true."
        if profile == "guardian-spirit":
            return (
                f"The {intent_str} completed with order and structure. Safe code is resilient code."
            )
        # forgotten-machine / default
        return f"The {intent_str} settles into the system. Clean logic leaves quiet echoes."

    @staticmethod
    def react_to_error(error_msg: str | None, profile_id: str | None = None) -> str:
        """Atmospheric reaction to a genuine application or runtime error."""
        profile = (profile_id or "default").lower().replace(" ", "-")

        if profile == "phantom-coder":
            return (
                "Traceback spotted! Let's take it apart and make the compiler regret complaining."
            )
        if profile == "guardian-spirit":
            return (
                "An operational exception occurred. "
                "We will inspect the cause carefully before moving forward."
            )
        # forgotten-machine / default
        return "A momentary fracture in the stream. Let us trace its origin patiently."

    @staticmethod
    def react_to_guardian_warning(
        risk_level: str | None, binary: str | None, profile_id: str | None = None
    ) -> str:
        """Atmospheric reaction acknowledging a genuine Guardian risk assessment."""
        profile = (profile_id or "default").lower().replace(" ", "-")
        bin_str = binary or "the target binary"

        if profile == "phantom-coder":
            return (
                f"Guardian flagged {bin_str} with {risk_level} risk. "
                "Double-check your flags before confirming."
            )
        if profile == "guardian-spirit":
            return f"Safety boundary active for {bin_str}. Verify the command parameters with care."
        # forgotten-machine / default
        return f"The threshold is sealed for {bin_str}. Intent must be confirmed before release."

    @staticmethod
    def react_to_mood_shift(from_mood: str, to_mood: str, profile_id: str | None = None) -> str:
        """Atmospheric reaction manifesting a genuine GhostEngine mood shift."""
        profile = (profile_id or "default").lower().replace(" ", "-")

        if profile == "phantom-coder":
            return (
                f"Energy shifted from {from_mood.lower()} to {to_mood.lower()}. "
                "Ready for the next puzzle."
            )
        if profile == "guardian-spirit":
            return f"Disposition transitions to {to_mood.lower()}. Standing watchful guard."
        # forgotten-machine / default
        return f"A subtle resonance shift: {from_mood.lower()} yields to {to_mood.lower()}."
